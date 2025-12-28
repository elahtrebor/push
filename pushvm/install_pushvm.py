import urequests
import json
import gc
import uos

REPO_LINK = "https://raw.githubusercontent.com/elahtrebor/xpkg/main"

def mem(tag=""):
    try:
        print("[mem]", tag, "free=", gc.mem_free(), "alloc=", gc.mem_alloc())
    except:
        pass

def fetch_index(repo_url):
    # If index grows large, switch repo to index.txt and parse line-by-line.
    url = repo_url + "/index.json"
    r = urequests.get(url)
    try:
        if r.status_code != 200:
            raise Exception("HTTP %d" % r.status_code)

        # Keep this for now; index.json should stay small.
        data = r.content  # bytes (often a bit cheaper than r.text)
    finally:
        try: r.close()
        except: pass

    gc.collect()
    return json.loads(data)

def cmd_list():
    idx = fetch_index(REPO_LINK)
    out_lines = []
    for name, meta in idx.items():
        if name in ("repo", "updated"):
            continue
        out_lines.append("%-10s %s - %s" % (
            name,
            meta.get("version", "?"),
            meta.get("desc", "")
        ))
    return "\n".join(out_lines) + "\n"

def download_to_file(url, dst, chunk=1024):
    # Stream HTTP response to a file to avoid ENOMEM.
    tmp = dst + ".tmp"
    try:
        uos.remove(tmp)
    except OSError:
        pass

    r = urequests.get(url, stream=True)  # stream is important if supported
    try:
        if r.status_code != 200:
            raise Exception("HTTP %d" % r.status_code)

        # Some urequests versions expose r.raw; this is the streaming path.
        raw = getattr(r, "raw", None)
        if raw is None:
            # Fallback: worst case, but better than crashing without explanation
            # (If this triggers ENOMEM, we'll switch to sockets-based fetch.)
            data = r.content
            with open(tmp, "wb") as f:
                f.write(data)
        else:
            with open(tmp, "wb") as f:
                while True:
                    buf = raw.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    # optional GC for long downloads
                    gc.collect()
    finally:
        try: r.close()
        except: pass

    # Atomic-ish replace
    try:
        uos.remove(dst)
    except OSError:
        pass
    uos.rename(tmp, dst)
    gc.collect()

def cmd_install(pkg):
    idx = fetch_index(REPO_LINK)
    if pkg not in idx:
        return "xpkg: package not found\n"

    meta = idx[pkg]
    src = REPO_LINK + "/" + meta["file"]
    dst = meta.get("install", "/lib/" + pkg + ".py")

    download_to_file(src, dst)
    return "installed %s -> %s\n" % (pkg, dst)

def main(argv):
    if not argv:
        return "xpkg: missing command\n"

    cmd = argv[0]
    if cmd == "list":
        return cmd_list()
    elif cmd == "install":
        if len(argv) < 2:
            return "xpkg: install <pkg>\n"
        return cmd_install(argv[1])
    return "xpkg: unknown command\n"


