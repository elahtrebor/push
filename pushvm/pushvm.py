# pushvm.py
# PUSH VM (ESP32-first complete version)
# Features:
# - Commands: help, ls, uname, free, df, pwd, cat, wc, grep, cp, cd, rename,
#            mkdir, rmdir, exec, rm, date, scanwifi, connect, ifconfig, edit,
#            echo, upper, test ([), write (>), append (>>), sleep
# - Pipelines: |
# - Redirection: > and >> (compiled to | write / | append)
# - Variables: x=3 and $x expansion
# - Control flow:
#     if <pipeline> then <stmts> [else <stmts>] fi
#     while <pipeline> do <stmts> done
#     for i 1 10 [step] do <stmts> done
#     foreach v in a b c do <stmts> done
#     foreach v in <pipeline> do <stmts> done   (splits output by lines)
#     break / continue
# - Short-circuit: && and ||
# - Background jobs: trailing & (jobs/kill/fg)
# - Hybrid pipe spooling: RAM until threshold then spill to STDOUT file
# - REPL: auto selects live mode (non-blocking) on MicroPython when pollable,
#         otherwise uses basic input() (better for desktop testing)
#
# Notes:
# - Designed for ESP32/WebREPL + Thonny; also runs on CPython for development.
# - sleep works correctly in background jobs (no generator re-entrancy).

import os
import time
import sys

try:
    import gc
except Exception:
    gc = None

try:
    import network
except Exception:
    network = None

try:
    import uselect as select  # MicroPython
except Exception:
    try:
        import select  # CPython fallback
    except Exception:
        select = None

VERSION = "pushvm-complete-0.1"

# -----------------------
# Global "current VM" pointer so commands can affect the VM that is actually executing.
# This keeps commands dict shared across background job clones without closures bound to the wrong VM.
# -----------------------
_CURRENT_VM = None

# -----------------------
# Time helpers
# -----------------------
def _sleep_ms(ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(ms)
    else:
        time.sleep(ms / 1000.0)

def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)

def _ticks_add(a, ms):
    if hasattr(time, "ticks_add"):
        return time.ticks_add(a, ms)
    return a + ms

def _ticks_diff(a, b):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(a, b)
    return a - b

def is_micropython():
    try:
        return sys.implementation.name == "micropython"
    except Exception:
        return False

# -----------------------
# Opcodes
# -----------------------
OP_LOAD      = 1
OP_ARG       = 2
OP_PIPE      = 3
OP_EXEC      = 4      # execute + print
OP_SET       = 5
OP_GET       = 6
OP_JMP       = 7
OP_JZ        = 8
OP_EXECQ     = 9      # execute quietly
OP_SETLIST   = 10     # vars[name] = list(items)
OP_SPLITL    = 11     # vars[name] = last_output.splitlines()
OP_FORE_INIT = 12     # init foreach iterator
OP_FORE_NEXT = 13     # advance foreach; if done jump
OP_END       = 255

# -----------------------
# Hybrid PipeData (RAM or spool file)
# -----------------------
class PipeData:
    __slots__ = ("text", "path", "is_file")

    def __init__(self, text=None, path=None, is_file=False):
        self.text = text
        self.path = path
        self.is_file = is_file

    def as_text(self):
        if self.is_file:
            with open(self.path, "r") as f:
                return f.read()
        return "" if self.text is None else str(self.text)

    def open_reader(self):
        if self.is_file:
            return open(self.path, "r")
        return _StringLineReader(self.as_text())

class _StringLineReader:
    __slots__ = ("_s", "_i", "_n")
    def __init__(self, s):
        self._s = s
        self._i = 0
        self._n = len(s)

    def __iter__(self):
        return self

    def __next__(self):
        if self._i >= self._n:
            raise StopIteration
        s = self._s
        j = s.find("\n", self._i)
        if j == -1:
            line = s[self._i:]
            self._i = self._n
            return line
        line = s[self._i:j+1]
        self._i = j + 1
        return line

    def close(self):
        pass

# -----------------------
# Tokenizer (quotes + specials: | ; > >> && || &)
# -----------------------
def tokenize(s):
    out = []
    buf = ""
    in_q = False
    i = 0
    n = len(s)

    def flush():
        nonlocal buf
        if buf != "":
            out.append(buf)
            buf = ""

    while i < n:
        ch = s[i]

        if ch == '"':
            in_q = not in_q
            i += 1
            continue

        if not in_q:
            if ch.isspace():
                flush()
                i += 1
                continue

            # two-char ops
            if ch == "&" and i + 1 < n and s[i+1] == "&":
                flush(); out.append("&&"); i += 2; continue
            if ch == "|" and i + 1 < n and s[i+1] == "|":
                flush(); out.append("||"); i += 2; continue
            if ch == ">" and i + 1 < n and s[i+1] == ">":
                flush(); out.append(">>"); i += 2; continue

            # one-char specials
            if ch in ("|", ";", ">", "&"):
                flush(); out.append(ch); i += 1; continue

        buf += ch
        i += 1

    flush()
    return out

# -----------------------
# Compiler with loops + if + chains &&/|| + redirection
# -----------------------
class CompileError(Exception):
    pass

class Compiler:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0
        self.code = []
        self.loop_stack = []   # {"start": pc, "break_jmps":[...]}
        self._tmp_counter = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def pop(self):
        t = self.peek()
        if t is None:
            return None
        self.i += 1
        return t

    def expect(self, s):
        t = self.pop()
        if t != s:
            raise CompileError("Expected '%s' but got '%s'" % (s, t))

    def emit(self, op, arg=None):
        self.code.append((op, arg))
        return len(self.code) - 1

    def patch(self, idx, new_arg):
        op, _ = self.code[idx]
        self.code[idx] = (op, new_arg)

    def new_tmp(self, prefix="__tmp"):
        self._tmp_counter += 1
        return "%s%d" % (prefix, self._tmp_counter)

    def compile(self):
        self.compile_stmts(terminators=set())
        self.emit(OP_END, None)
        return self.code

    def compile_stmts(self, terminators):
        while True:
            t = self.peek()
            if t is None or t in terminators:
                return

            if t == ";":
                self.pop()
                continue

            if t == "if":
                self.compile_if()
            elif t == "while":
                self.compile_while()
            elif t == "for":
                self.compile_for()
            elif t == "foreach":
                self.compile_foreach()
            elif t == "break":
                self.compile_break()
                self.emit(OP_EXECQ, None)  # boundary
            elif t == "continue":
                self.compile_continue()
                self.emit(OP_EXECQ, None)
            else:
                self.compile_chain(stop_tokens=terminators)

            if self.peek() == ";":
                self.pop()

    # ---- if / while / for / foreach ----
    def compile_if(self):
        self.expect("if")
        self.compile_pipeline(stop_tokens={"then"})
        self.emit(OP_EXECQ, None)
        jz_idx = self.emit(OP_JZ, None)

        self.expect("then")
        self.compile_stmts(terminators={"else", "fi"})

        if self.peek() == "else":
            jmp_end = self.emit(OP_JMP, None)
            self.expect("else")
            self.patch(jz_idx, len(self.code))
            self.compile_stmts(terminators={"fi"})
            self.expect("fi")
            self.patch(jmp_end, len(self.code))
        else:
            self.expect("fi")
            self.patch(jz_idx, len(self.code))

    def compile_while(self):
        self.expect("while")
        loop_start = len(self.code)

        self.compile_pipeline(stop_tokens={"do"})
        self.emit(OP_EXECQ, None)
        jz_exit = self.emit(OP_JZ, None)

        self.expect("do")
        ctx = {"start": loop_start, "break_jmps": []}
        self.loop_stack.append(ctx)

        self.compile_stmts(terminators={"done"})
        self.expect("done")

        self.emit(OP_JMP, loop_start)

        exit_target = len(self.code)
        self.patch(jz_exit, exit_target)
        for jidx in ctx["break_jmps"]:
            self.patch(jidx, exit_target)
        self.loop_stack.pop()

    def compile_for(self):
        # for i 1 10 [step] do ... done
        self.expect("for")
        var = self.pop()
        if not var:
            raise CompileError("for: missing variable name")

        start = self.pop()
        end = self.pop()
        if start is None or end is None:
            raise CompileError("for: needs start and end")

        step = None
        if self.peek() != "do":
            step = self.pop()
        if self.peek() != "do":
            raise CompileError("for: expected 'do'")

        # init var=start
        self.emit(OP_ARG, start)
        self.emit(OP_SET, var)

        loop_start = len(self.code)

        # condition using test:
        cmpop = "-le"
        if step is not None:
            try:
                if int(str(step).strip()) < 0:
                    cmpop = "-ge"
            except Exception:
                cmpop = "-le"

        self.emit(OP_LOAD, "test")
        self.emit(OP_GET, var)
        self.emit(OP_ARG, cmpop)
        self.emit(OP_ARG, end)
        self.emit(OP_EXECQ, None)
        jz_exit = self.emit(OP_JZ, None)

        self.expect("do")

        ctx = {"start": loop_start, "break_jmps": []}
        self.loop_stack.append(ctx)

        self.compile_stmts(terminators={"done"})
        self.expect("done")

        if step is None:
            step = "1"
        # increment var by step (quiet)
        self.emit(OP_LOAD, "addv")
        self.emit(OP_ARG, var)
        self.emit(OP_ARG, step)
        self.emit(OP_EXECQ, None)

        self.emit(OP_JMP, loop_start)

        exit_target = len(self.code)
        self.patch(jz_exit, exit_target)
        for jidx in ctx["break_jmps"]:
            self.patch(jidx, exit_target)
        self.loop_stack.pop()

    def compile_foreach(self):
        # foreach v in a b c do ... done
        # foreach v in <pipeline> do ... done   (split pipeline output by lines)
        self.expect("foreach")
        var = self.pop()
        if not var:
            raise CompileError("foreach: missing variable name")
        self.expect("in")

        list_var = self.new_tmp("__foreach_list_")

        collected = []
        while True:
            t = self.peek()
            if t is None:
                raise CompileError("foreach: missing 'do'")
            if t == "do":
                break
            collected.append(self.pop())

        if "|" in collected:
            sub = Compiler(collected)
            sub.compile_pipeline(stop_tokens=set())
            self.code.extend(sub.code)
            self.emit(OP_EXECQ, None)
            self.emit(OP_SPLITL, list_var)
        else:
            self.emit(OP_SETLIST, (list_var, collected))

        self.expect("do")

        self.emit(OP_FORE_INIT, (var, list_var))
        loop_start = len(self.code)
        fore_next = self.emit(OP_FORE_NEXT, None)  # patched to exit

        ctx = {"start": loop_start, "break_jmps": []}
        self.loop_stack.append(ctx)

        self.compile_stmts(terminators={"done"})
        self.expect("done")

        self.emit(OP_JMP, loop_start)

        exit_target = len(self.code)
        self.patch(fore_next, exit_target)
        for jidx in ctx["break_jmps"]:
            self.patch(jidx, exit_target)
        self.loop_stack.pop()

    def compile_break(self):
        self.expect("break")
        if not self.loop_stack:
            raise CompileError("break used outside of a loop")
        jidx = self.emit(OP_JMP, None)
        self.loop_stack[-1]["break_jmps"].append(jidx)

    def compile_continue(self):
        self.expect("continue")
        if not self.loop_stack:
            raise CompileError("continue used outside of a loop")
        self.emit(OP_JMP, self.loop_stack[-1]["start"])

    # ---- && / || chains + redirection ----
    def compile_chain(self, stop_tokens):
        # assignment like x=3
        t = self.peek()
        if t is not None and ("=" in t) and (not t.startswith("$")) and (t != "|"):
            name, val = t.split("=", 1)
            self.pop()
            self.emit(OP_ARG, val)
            self.emit(OP_SET, name)
            # update last_truth quietly based on value
            self.emit(OP_LOAD, "echo")
            self.emit(OP_GET, name)
            self.emit(OP_EXECQ, None)
        else:
            self.compile_pipeline(stop_tokens=stop_tokens.union({"&&", "||", ">", ">>"}))
            self.compile_redirection_if_present()
            self.emit(OP_EXEC, None)

        while True:
            op = self.peek()
            if op not in ("&&", "||"):
                return
            self.pop()

            if op == "&&":
                skip_rhs = self.emit(OP_JZ, None)
                self.compile_pipeline(stop_tokens=stop_tokens.union({"&&", "||", ">", ">>"}))
                self.compile_redirection_if_present()
                self.emit(OP_EXEC, None)
                self.patch(skip_rhs, len(self.code))
            else:
                run_rhs = self.emit(OP_JZ, None)
                skip_rhs = self.emit(OP_JMP, None)
                self.patch(run_rhs, len(self.code))
                self.compile_pipeline(stop_tokens=stop_tokens.union({"&&", "||", ">", ">>"}))
                self.compile_redirection_if_present()
                self.emit(OP_EXEC, None)
                self.patch(skip_rhs, len(self.code))

    def compile_redirection_if_present(self):
        t = self.peek()
        if t not in (">", ">>"):
            return
        op = self.pop()
        fname = self.pop()
        if fname is None:
            raise CompileError("redirection missing filename")
        self.emit(OP_PIPE, None)
        self.emit(OP_LOAD, "append" if op == ">>" else "write")
        self.emit(OP_ARG, fname)

    # ---- pipelines ----
    def compile_pipeline(self, stop_tokens):
        expecting_cmd = True
        while True:
            t = self.peek()
            if t is None or t in stop_tokens or t == ";":
                return

            if t == "|":
                self.pop()
                self.emit(OP_PIPE, None)
                expecting_cmd = True
                continue

            self.pop()

            if t.startswith("$") and len(t) > 1:
                self.emit(OP_GET, t[1:])
                expecting_cmd = False
                continue

            if expecting_cmd:
                self.emit(OP_LOAD, t)
                expecting_cmd = False
            else:
                self.emit(OP_ARG, t)

def compile_line(line):
    toks = tokenize(line.strip())
    bg = False
    if toks and toks[-1] == "&":
        bg = True
        toks = toks[:-1]
    c = Compiler(toks)
    return c.compile(), bg

# -----------------------
# Cooperative job system
# -----------------------
class Job:
    __slots__ = ("jid", "name", "gen", "done", "error")
    def __init__(self, jid, name, gen):
        self.jid = jid
        self.name = name
        self.gen = gen
        self.done = False
        self.error = None

    def step(self, n=1):
        if self.done:
            return
        try:
            for _ in range(n):
                next(self.gen)
        except StopIteration:
            self.done = True
        except Exception as e:
            self.done = True
            self.error = e

# -----------------------
# VM
# -----------------------
class VM:
    def __init__(self, commands=None, spool_path="STDOUT", spool_threshold=2048):
        self.token_stack = []
        self.value_stack = []
        self.vars = {}
        self.pc = 0
        self.code = []
        self.commands = commands or {}

        self.last_output = ""
        self.last_truth = False

        self.spool_path = spool_path
        self.spool_threshold = spool_threshold

        self._foreach_stack = []  # (varname, iterator)

        # jobs
        self.jobs = {}
        self.next_jid = 1

        # scheduler-safe sleep state
        self.sleep_until = None

    def clone_for_job(self):
        jvm = VM(commands=self.commands, spool_path=self.spool_path, spool_threshold=self.spool_threshold)
        jvm.vars = dict(self.vars)
        return jvm

    def truthy(self, s):
        if s is None:
            return False
        txt = str(s).strip()
        if txt == "":
            return False
        low = txt.lower()
        return low not in ("0", "false", "no", "nil")

    def _maybe_spool(self, out):
        if out is None:
            s = ""
        elif isinstance(out, str):
            s = out
        else:
            s = str(out)

        if self.spool_threshold and len(s) >= self.spool_threshold:
            with open(self.spool_path, "w") as f:
                f.write(s)
            return PipeData(path=self.spool_path, is_file=True)

        return PipeData(text=s, is_file=False)

    def run(self, trace=False):
        self.pc = 0
        while self.pc < len(self.code):
            # Foreground sleep: block, but keep background jobs alive.
            if self.sleep_until is not None:
                while _ticks_diff(self.sleep_until, _ticks_ms()) > 0:
                    self.poll_jobs(steps=80)
                    _sleep_ms(20)
                self.sleep_until = None

            op, arg = self.code[self.pc]
            self.pc += 1

            if trace:
                print("PC", self.pc-1, "OP", op, "ARG", arg)

            if op == OP_LOAD:
                self.token_stack.append(("cmd", arg))

            elif op == OP_ARG:
                self.token_stack.append(("arg", arg))
                self.value_stack.append(arg)

            elif op == OP_PIPE:
                self.token_stack.append(("pipe", None))

            elif op == OP_SET:
                val = self.value_stack.pop() if self.value_stack else ""
                self.vars[arg] = val

            elif op == OP_GET:
                val = self.vars.get(arg, "")
                self.token_stack.append(("arg", val))
                self.value_stack.append(val)

            elif op == OP_EXEC or op == OP_EXECQ:
                out = self.exec_pipeline()
                self.last_output = out
                self.last_truth = self.truthy(out)
                if op == OP_EXEC and out is not None and out != "":
                    print(out)
                self.value_stack = []

            elif op == OP_JMP:
                self.pc = int(arg)

            elif op == OP_JZ:
                if not self.last_truth:
                    self.pc = int(arg)

            elif op == OP_SETLIST:
                name, items = arg
                self.vars[name] = list(items)

            elif op == OP_SPLITL:
                s = "" if self.last_output is None else str(self.last_output)
                self.vars[arg] = s.splitlines()

            elif op == OP_FORE_INIT:
                varname, listname = arg
                items = self.vars.get(listname, [])
                if items is None:
                    items = []
                if isinstance(items, str):
                    items = items.splitlines()
                it = iter(items)
                self._foreach_stack.append((varname, it))

            elif op == OP_FORE_NEXT:
                if not self._foreach_stack:
                    self.pc = int(arg)
                else:
                    varname, it = self._foreach_stack[-1]
                    try:
                        nxt = next(it)
                        self.vars[varname] = str(nxt)
                    except StopIteration:
                        self._foreach_stack.pop()
                        self.pc = int(arg)

            elif op == OP_END:
                break

            else:
                raise Exception("Unknown opcode: %r" % op)

        return self.last_output

    def run_generator(self):
        # Cooperative runner: yields frequently so it can be used as a background job.
        self.pc = 0
        while self.pc < len(self.code):
            # Background sleep: yield quickly until wake time (no re-entrancy).
            if self.sleep_until is not None:
                if _ticks_diff(self.sleep_until, _ticks_ms()) > 0:
                    yield None
                    continue
                else:
                    self.sleep_until = None

            op, arg = self.code[self.pc]
            self.pc += 1

            if op == OP_LOAD:
                self.token_stack.append(("cmd", arg))

            elif op == OP_ARG:
                self.token_stack.append(("arg", arg))
                self.value_stack.append(arg)

            elif op == OP_PIPE:
                self.token_stack.append(("pipe", None))

            elif op == OP_SET:
                val = self.value_stack.pop() if self.value_stack else ""
                self.vars[arg] = val

            elif op == OP_GET:
                val = self.vars.get(arg, "")
                self.token_stack.append(("arg", val))
                self.value_stack.append(val)

            elif op == OP_EXEC or op == OP_EXECQ:
                out = self.exec_pipeline()
                self.last_output = out
                self.last_truth = self.truthy(out)
                self.value_stack = []

            elif op == OP_JMP:
                self.pc = int(arg)

            elif op == OP_JZ:
                if not self.last_truth:
                    self.pc = int(arg)

            elif op == OP_SETLIST:
                name, items = arg
                self.vars[name] = list(items)

            elif op == OP_SPLITL:
                s = "" if self.last_output is None else str(self.last_output)
                self.vars[arg] = s.splitlines()

            elif op == OP_FORE_INIT:
                varname, listname = arg
                items = self.vars.get(listname, [])
                if items is None:
                    items = []
                if isinstance(items, str):
                    items = items.splitlines()
                it = iter(items)
                self._foreach_stack.append((varname, it))

            elif op == OP_FORE_NEXT:
                if not self._foreach_stack:
                    self.pc = int(arg)
                else:
                    varname, it = self._foreach_stack[-1]
                    try:
                        nxt = next(it)
                        self.vars[varname] = str(nxt)
                    except StopIteration:
                        self._foreach_stack.pop()
                        self.pc = int(arg)

            elif op == OP_END:
                break

            yield None  # cooperate often

    def exec_pipeline(self):
        items = self.token_stack
        self.token_stack = []

        pipeline = []
        current_cmd = None
        current_args = []

        def flush():
            nonlocal current_cmd, current_args
            if current_cmd is not None:
                pipeline.append((current_cmd, current_args))
            current_cmd = None
            current_args = []

        for kind, val in items:
            if kind == "pipe":
                flush()
            elif kind == "cmd":
                if current_cmd is not None:
                    flush()
                current_cmd = val
            elif kind == "arg":
                current_args.append(val)

        flush()

        out = PipeData(text="", is_file=False)
        for cmd, args in pipeline:
            out_raw = self.run_command(cmd, args, out)
            out = self._maybe_spool(out_raw)

        return out.as_text()

    def run_command(self, cmd, args, input_data):
        global _CURRENT_VM
        fn = self.commands.get(cmd)
        if fn is None:
            # Auto-resolve: if /lib/<cmd>.py exists, treat it like: run <cmd> <args...>
            # This makes installed modules feel like built-in commands.
            try:
                lib_path = "/lib/%s.py" % cmd
                os.stat(lib_path)  # exists?
                runfn = self.commands.get("run")
                if runfn is not None:
                    _CURRENT_VM = self
                    return runfn([cmd] + list(args), input_data)
            except Exception:
                pass
            return "Error: command not found: %s" % cmd
        _CURRENT_VM = self
        return fn(args, input_data)

    # ---- jobs ----
    def start_job(self, code, name):
        jvm = self.clone_for_job()
        jvm.code = code
        jid = self.next_jid
        self.next_jid += 1
        self.jobs[jid] = Job(jid, name, jvm.run_generator())
        return jid

    def poll_jobs(self, steps=50):
        dead = []
        for jid, job in self.jobs.items():
            job.step(n=steps)
            if job.done:
                dead.append(jid)

        for jid in dead:
            job = self.jobs[jid]
            if job.error:
                print("[{}] {} (error: {})".format(jid, job.name, job.error))
            else:
                print("[{}] {} (done)".format(jid, job.name))
            del self.jobs[jid]

# -----------------------
# sleep command (scheduler-safe, works for bg jobs)
# -----------------------
def cmd_sleep(args, input_data):
    global _CURRENT_VM
    if not args:
        return ""


def cmd_run(args, input_data):
    # run <module> [args...]
    # Imports module (typically from /lib) and calls its main(argv) if present.
    # argv is a list of strings: e.g. ["install","uping"].
    if not args:
        return "run: usage run <module> [args...]\n"
    modname = args[0]
    argv = [str(a) for a in args[1:]]

    # Allow "foo.py" as module name
    if modname.endswith(".py"):
        modname = modname[:-3]

    # Ensure /lib is on path (MicroPython usually includes it, but make it robust)
    try:
        if "/lib" not in sys.path:
            sys.path.append("/lib")
    except Exception:
        pass

    try:
        mod = __import__(modname)
    except Exception as e:
        return "run: couldn't import %s (%s)\n" % (modname, e)

    # Prefer main(argv). Fallback to run(argv).
    fn = getattr(mod, "main", None)
    if fn is None:
        fn = getattr(mod, "run", None)

    if fn is None:
        return "run: %s has no main(argv)\n" % modname

    try:
        res = fn(argv)
        if res is None:
            return ""
        return str(res)
    except Exception as e:
        return "run: error running %s: %s\n" % (modname, e)

    try:
        secs = float(args[0])
    except Exception:
        return ""
    ms = int(secs * 1000)
    if ms <= 0:
        return ""
    if _CURRENT_VM is None:
        return ""
    _CURRENT_VM.sleep_until = _ticks_add(_ticks_ms(), ms)
    return ""

# -----------------------
# Commands (Signature: fn(args, input_data)->str)
# -----------------------
def cmd_help(args, input_data):
    return (
        "PUSH ver: " + VERSION + "\n\n"
        "commands: exit, ls, uname, free, df, pwd, cat, cp, cd, mkdir,\n"
        "grep, rmdir, exec, rm, date,\n"
        "scanwifi, connect, ifconfig, edit, rename\n"
        "extras: echo, upper, wc, test, write (>), append (>>), sleep\n"
        "flow: if/while/for/foreach, break/continue, &&/||, vars x=val $x, jobs &\n"
        "jobctl: jobs, kill <id>, fg <id>\n"
    )

def cmd_ls(args, input_data):
    path = args[0] if args else ""
    try:
        if path:
            return "\n".join(os.listdir(path))
        return "\n".join(os.listdir())
    except Exception:
        return "Syntax Error\n"

def cmd_uname(args, input_data):
    try:
        return "\n".join(os.uname())
    except Exception:
        return "uname not supported\n"

def cmd_free(args, input_data):
    if gc is None:
        return "free not supported\n"
    return str(gc.mem_free())

def cmd_df(args, input_data):
    try:
        st = os.statvfs("/")
        total = float(st[2]) * float(st[0])
        used  = float(st[3]) * float(st[0])
        free  = total - used
        return "Free: %s Used: %s Total: %s" % (free, used, total)
    except Exception:
        return "df error\n"

def cmd_pwd(args, input_data):
    return os.getcwd()

def cmd_cd(args, input_data):
    path = args[0] if args else ""
    try:
        os.chdir(path)
        return path
    except Exception:
        return "Error. Couldn't cd\n"

def cmd_cat(args, input_data):
    if args:
        try:
            with open(args[0], "r") as f:
                return f.read()
        except Exception:
            return "Couldn't open file\n"
    return input_data.as_text() if input_data is not None else ""

def cmd_wc(args, input_data):
    try:
        if args:
            x = 0
            with open(args[0], "r") as f:
                for _ in f:
                    x += 1
            return str(x) + "\n"
        s = input_data.as_text() if input_data is not None else ""
        return str(len(s.splitlines())) + "\n"
    except Exception:
        return "Couldn't open file\n"

def cmd_grep(args, input_data):
    import re
    if not args:
        return ""
    rgx = args[0]
    out = []
    try:
        if len(args) >= 2:
            with open(args[1], "r") as f:
                for line in f:
                    if re.search(rgx, line):
                        out.append(line)
        else:
            r = input_data.open_reader() if input_data is not None else _StringLineReader("")
            try:
                for line in r:
                    if re.search(rgx, line):
                        out.append(line)
            finally:
                try: r.close()
                except: pass
        return "".join(out)
    except Exception:
        return "Couldn't perform.\n"

def cmd_cp(args, input_data):
    if len(args) < 2:
        return "Couldn't copy.\n"
    src, dst = args[0], args[1]
    try:
        with open(src, "r") as f:
            data = f.read()
        with open(dst, "w") as f:
            f.write(data)
        return "File " + src + " copied."
    except Exception:
        return "Couldn't copy.\n"

def cmd_rename(args, input_data):
    if len(args) < 2:
        return "Couldn't rename\n"
    src, dst = args[0], args[1]
    try:
        os.rename(src, dst)
        return src + " renamed.."
    except Exception:
        return "Couldn't rename\n"

def cmd_mkdir(args, input_data):
    name = args[0] if args else ""
    try:
        os.mkdir(name)
        return "Directory " + name + " created.\n"
    except Exception:
        return "Couldn't make directory\n"

def cmd_rmdir(args, input_data):
    name = args[0] if args else ""
    try:
        os.rmdir(name)
        return "Removed " + name + ".\n"
    except Exception:
        return "Couldn't remove dir.\n"

def cmd_rm(args, input_data):
    name = args[0] if args else ""
    try:
        os.unlink(name)
        return "Removed file " + name + "\n"
    except Exception:
        return "Couldn't remove file\n"

def cmd_date(args, input_data):
    dateTimeObj = time.localtime()
    year,month,day,hour,minu,sec,wday,yday = (dateTimeObj)
    return "%s/%s/%s %s:%s:%s" % (month, day, year, hour, minu, sec)

def cmd_exec(args, input_data):
    # exec module.func("arg")
    import re
    s = " ".join(args)
    if "." not in s or "(" not in s or ")" not in s:
        return "Error: Check Syntax\n"
    try:
        module = re.search(r"^(.*?)\.", s).group(1)
        rest = s[len(module)+1:]
        func = re.search(r"^(.*?)\(", rest).group(1)
        argstr = re.search(r"\((.*?)\)", rest).group(1)

        script = getattr(__import__(module), func)
        if not argstr:
            return str(script())
        argstr = argstr.replace('"', "")
        return str(script(argstr))
    except Exception:
        return "Error: Check Syntax\n"

def cmd_scanwifi(args, input_data):
    if network is None:
        return "scanwifi: network module not available\n"
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        nets = wlan.scan()
        out = []
        for i in nets:
            try:
                out.append(i[0].decode())
            except Exception:
                out.append(str(i[0]))
        return "\n".join(out) + ("\n" if out else "")
    except Exception:
        return "Couldn't scan networks.\n"

def cmd_connect(args, input_data):
    if network is None:
        return "connect: network module not available\n"
    print("Enter SSID: ")
    ssid = input()
    print("Enter wifi pw: ")
    wifipw = input()
    try:
        print("attempting to connect..\n")
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, wifipw)
        time.sleep(5)
        return "Check ifconfig..\n"
    except Exception:
        return "Error: couldn't obtain address\n"

def cmd_ifconfig(args, input_data):
    if network is None:
        return "ifconfig: network module not available\n"
    try:
        wlan = network.WLAN(network.STA_IF)
        status = wlan.ifconfig()
        return (
            "\nIP........... " + status[0] +
            "\nNETMASK......." + status[1] + "\n" +
            "GATEWAY......." + status[2]
        )
    except Exception:
        return "Couldn't get interface or check syntax.\n"

def cmd_edit(args, input_data):
    if not args:
        return "Couldn't write file\n"
    path = args[0]
    print("EDIT MODE DETECTED...\n")
    print("(ENTER STOPEDIT to stop)\n")
    try:
        with open(path, "w") as f:
            while True:
                line = input()
                if "STOPEDIT" in line:
                    break
                f.write(line + "\n")
        return "File " + path + " created..\n"
    except Exception:
        return "Couldn't write file\n"

# extras
def cmd_echo(args, input_data):
    return " ".join([str(a) for a in args])

def cmd_upper(args, input_data):
    s = input_data.as_text() if input_data is not None else ""
    return s.upper()

def cmd_write(args, input_data):
    if not args:
        return "write: missing filename\n"
    path = args[0]
    s = input_data.as_text() if input_data is not None else ""
    try:
        with open(path, "w") as f:
            f.write(s)
        return ""
    except Exception:
        return "Couldn't write file\n"

def cmd_append(args, input_data):
    if not args:
        return "append: missing filename\n"
    path = args[0]
    s = input_data.as_text() if input_data is not None else ""
    try:
        with open(path, "a") as f:
            f.write(s)
        return ""
    except Exception:
        # fallback if append not supported
        try:
            old = ""
            try:
                with open(path, "r") as r:
                    old = r.read()
            except Exception:
                old = ""
            with open(path, "w") as w:
                w.write(old + s)
            return ""
        except Exception:
            return "Couldn't append file\n"

def cmd_test(args, input_data):
    # support [ ... ] by ignoring trailing ]
    if args and args[-1] == "]":
        args = args[:-1]
    if not args:
        return ""

    if len(args) == 2:
        op, a = args[0], args[1]
        if op == "-f":
            try:
                os.stat(a)
                return "1"
            except Exception:
                return ""
        if op == "-d":
            try:
                os.listdir(a)
                return "1"
            except Exception:
                return ""
        if op == "-z":
            return "1" if str(a) == "" else ""
        if op == "-n":
            return "1" if str(a) != "" else ""

    if len(args) >= 3:
        a, op, b = args[0], args[1], args[2]
        if op == "=":
            return "1" if str(a) == str(b) else ""
        if op == "!=":
            return "1" if str(a) != str(b) else ""
        if op in ("-eq", "-ne", "-lt", "-le", "-gt", "-ge"):
            try:
                ai = int(str(a).strip())
                bi = int(str(b).strip())
            except Exception:
                return ""
            if op == "-eq": return "1" if ai == bi else ""
            if op == "-ne": return "1" if ai != bi else ""
            if op == "-lt": return "1" if ai <  bi else ""
            if op == "-le": return "1" if ai <= bi else ""
            if op == "-gt": return "1" if ai >  bi else ""
            if op == "-ge": return "1" if ai >= bi else ""
    return ""

# -----------------------
# VM construction (commands + job control)
# -----------------------
def make_vm():
    # If you're tight on RAM, lower this to 512 or 256.
    vm = VM(commands={}, spool_path="STDOUT", spool_threshold=2048)

    def cmd_addv(args, input_data):
        # addv var delta (quiet)
        if len(args) < 2:
            return ""
        name, delta_s = args[0], args[1]
        v = vm.vars.get(name, "0")
        try:
            n = int(str(v).strip())
        except Exception:
            n = 0
        try:
            d = int(str(delta_s).strip())
        except Exception:
            d = 0
        vm.vars[name] = str(n + d)
        return ""

    def cmd_jobs(args, input_data):
        if not vm.jobs:
            return "(no jobs)\n"
        lines = []
        for jid, job in vm.jobs.items():
            state = "done" if job.done else "running"
            lines.append("[{}] {} - {}".format(jid, state, job.name))
        return "\n".join(lines) + "\n"

    def cmd_kill(args, input_data):
        if not args:
            return "kill: usage kill <jobid>\n"
        try:
            jid = int(args[0])
        except Exception:
            return "kill: bad jobid\n"
        job = vm.jobs.get(jid)
        if not job:
            return "kill: no such job\n"
        job.done = True
        return ""

    def cmd_fg(args, input_data):
        if not args:
            return "fg: usage fg <jobid>\n"
        try:
            jid = int(args[0])
        except Exception:
            return "fg: bad jobid\n"
        job = vm.jobs.get(jid)
        if not job:
            return "fg: no such job\n"
        while not job.done:
            job.step(n=200)
        err = job.error
        del vm.jobs[jid]
        if err:
            return "fg: job error: %s\n" % err
        return ""

    vm.commands.update({
        # your commands
        "help": cmd_help,
        "ls": cmd_ls,
        "uname": cmd_uname,
        "free": cmd_free,
        "df": cmd_df,
        "pwd": cmd_pwd,
        "cat": cmd_cat,
        "wc": cmd_wc,
        "grep": cmd_grep,
        "cp": cmd_cp,
        "cd": cmd_cd,
        "rename": cmd_rename,
        "mkdir": cmd_mkdir,
        "rmdir": cmd_rmdir,
        "exec": cmd_exec,
        "rm": cmd_rm,
        "date": cmd_date,
        "scanwifi": cmd_scanwifi,
        "connect": cmd_connect,
        "ifconfig": cmd_ifconfig,
        "edit": cmd_edit,

        # extras
        "echo": cmd_echo,
        "upper": cmd_upper,

        # redirection
        "write": cmd_write,
        "append": cmd_append,

        # test + helpers used by loops/chains
        "test": cmd_test,
        "[": cmd_test,
        "addv": cmd_addv,

        # sleep
        "sleep": cmd_sleep,
        "run": cmd_run,

        # job control
        "jobs": cmd_jobs,
        "kill": cmd_kill,
        "fg": cmd_fg,
    })

    return vm

# -----------------------
# REPL (auto: live on MicroPython when pollable, basic otherwise)
# -----------------------
def stdin_is_pollable():
    if select is None:
        return False
    try:
        p = select.poll()
        p.register(sys.stdin, select.POLLIN)
        p.poll(0)
        return True
    except Exception:
        return False

def run_line(vm, line):
    code, bg = compile_line(line)
    if bg:
        jid = vm.start_job(code, name=line)
        print("[{}] started {}".format(jid, line))
    else:
        vm.code = code
        vm.run(trace=False)

def repl_blocking(vm):
    while True:
        vm.poll_jobs(steps=200)
        try:
            line = input("push> ")
        except Exception:
            break
        if not line:
            continue
        line = line.strip()
        if not line:
            continue
        if line == "exit":
            break
        try:
            run_line(vm, line)
        except CompileError as ce:
            print("Compile error:", ce)
        except Exception as e:
            print("Error:", e)

def repl_nonblocking(vm):
    p = select.poll()
    p.register(sys.stdin, select.POLLIN)

    buf = ""
    sys.stdout.write("push> ")
    try:
        sys.stdout.flush()
    except Exception:
        pass

    while True:
        vm.poll_jobs(steps=80)

        try:
            ev = p.poll(0)
        except Exception:
            print("\n(live input unavailable; switching to basic mode)")
            repl_blocking(vm)
            return

        if not ev:
            _sleep_ms(10)
            continue

        try:
            ch = sys.stdin.read(1)
        except Exception:
            _sleep_ms(10)
            continue

        if not ch:
            _sleep_ms(10)
            continue

        if ch == "\r":
            continue

        if ch == "\n":
            line = buf.strip()
            buf = ""
            sys.stdout.write("\n")
            try:
                sys.stdout.flush()
            except Exception:
                pass

            if line == "exit":
                return
            if line:
                try:
                    run_line(vm, line)
                except CompileError as ce:
                    print("Compile error:", ce)
                except Exception as e:
                    print("Error:", e)

            sys.stdout.write("push> ")
            try:
                sys.stdout.flush()
            except Exception:
                pass
            continue

        if ch == "\x08" or ch == "\x7f":
            if buf:
                buf = buf[:-1]
                sys.stdout.write("\b \b")
                try:
                    sys.stdout.flush()
                except Exception:
                    pass
            continue

        buf += ch
        sys.stdout.write(ch)
        try:
            sys.stdout.flush()
        except Exception:
            pass

def repl_auto(vm):
    # Avoid "double-echo" issues on desktop terminals: only do live mode on MicroPython.
    if is_micropython() and stdin_is_pollable():
        print("Interactive mode: live (background jobs run while you type)")
        repl_nonblocking(vm)
    else:
        print("Interactive mode: basic (background jobs run between commands)")
        repl_blocking(vm)

def repl():
    vm = make_vm()
    print("PUSH VM", VERSION)
    print("Type 'help'. Use 'exit' to quit.")
    print("Background: add '&' at end. Job control: jobs/kill/fg.")
    repl_auto(vm)

if __name__ == "__main__":
    repl()
