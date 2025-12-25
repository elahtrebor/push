<pre>
pushvm 

A userland virtual machine that provides the same funcitons as push.py , however this VM also provides Job control/Backgrounding. This also gives a rich syntax similar to bash allowing you to set variables and create flow control (if, while, break , continue)


Here is a demo:

>>> import pushvm
>>> pushvm.repl()
PUSH VM pushvm-complete-0.1
Type 'help'. Use 'exit' to quit.
Background: add '&' at end. Job control: jobs/kill/fg.
Interactive mode: live (background jobs run while you type)
push> 


PUSH ver: pushvm-complete-0.1

commands: exit, ls, uname, free, df, pwd, cat, cp, cd, mkdir,
grep, rmdir, exec, rm, date,
scanwifi, connect, ifconfig, edit, rename
extras: echo, upper, wc, test, write (>), append (>>)
flow: if/while/for/foreach, break/continue, &&/||, vars x=val $x, jobs &
jobctl: jobs, kill <id>, fg <id>

push> 

push> ls
boot.py
dhcp.py
pushvm.py
webrepl_cfg.py

push> ls | grep web
webrepl_cfg.py

push> ls|wc
4

push> uname
esp32
esp32
1.19.1
v1.19.1 on 2022-06-18
ESP32S3 module with ESP32S3

push> df
Free: 57344.0 Used: 6234112.0 Total: 6291456.0

push> myvar="test"
push> echo $myvar
test



