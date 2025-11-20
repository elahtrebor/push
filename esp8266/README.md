# push
<p>
Python Micro Shell (FOR ESP8266) - One file shell for micropython micro controllers
- cd, pwd, cat , redirect, wget, mkdir, rmdir, rm, etc

This is designed to quickly give you a mini linix like shell. 
Tested on ESP8266

To use make sure you have micropython installed first.
Currently tested with: ESP8266_GENERIC-20250911-v1.26.1.bin

To install the shell, just connect with thonny or whatever your using to manage your microdevice.
Copy the push.py file on the device and save as push.py
Then from the micropython cli "import push".
It has a quick wifi connect built in, a crude editor that works similiar to 
cat'ng text into the console, 
wget (that works like curl), an ntp sync tool.
The "exec" command will run a python script.
You may want to make a lib directory first "mkdir lib" for exec
as micropython defaulty has the lib directory is in its path.
So for instance to call test.py with function hello():
place test.py in the lib directory and from the shell
call it with  "exec test.hello()"
exec will also run native micropython functions for example os.listdir()

Its recommended to use the absolute path when working with directories and files.

Supports ls, cat, cd, pwd, mkdir, rmdir, rm, rename, cp, grep, ifconfig, scanwifi, connect, date  
and redirect ">".
Supports PIPE now. No switches or flags.

if for some reason the shell crashes then you can restart it with "import push" and "push.shell()"


