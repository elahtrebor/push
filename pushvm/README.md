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

push> x=5; while test $x -gt 0 do echo $x; addv x -1; done
5
4
3
2
1


push> x=hi; if echo $x then echo YES else echo NO fi
YES


push> ls > out.txt; cat out.txt
boot.py
dhcp.py
pushvm.py
webrepl_cfg.py


push> for i 1 30 do echo $i; done &
[2] started for i 1 30 do echo $i; done &
push> [2] for i 1 30 do echo $i; done & (done)
jobs
(no jobs)


push> sleep 10 &
[1] started sleep 10 &
push> 
push> jobs
[1] running - sleep 10 &

push> ls
bin
boot.py
dev
lib
push.py
pushvm.py
tmp
push> 
push> [1] sleep 10 & (done)


