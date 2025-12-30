<h3>Pushvm tutorial</h3>


This tutorial covers installation and operation of the shell. 
 The installer portion walks though using the installer which gives you the package manager and sets up the lib directory as well as optionally gives you the ability to setup networking that automatically connects on boot.

Wny use push? When I first started using ESP32 and RPI Pico I was amazed that micropython would run on them and learned that the devices later supported networking which opens up a lot of doors for capability. When I used thonny and webrepl I got a chance to interact with the python REPL and learned that many micropython library functions allowed you to do the equivilant actions like on regular operating systems such as list files. In micropython you would import the os library and use os.listdir() from the REPL to list files. I soon found that typing os.listdir() got tiring and also missed the linux shell capabilities. I then found myself building a crude shell that would take the input string "ls" and run os.listdir() in python. I found many library calls to read and manipulate files, control networking /sockets, and other useful utilities. I wanted to build a shell that doesnt solve world hunger but helps elevate capabilities a little.


 What are some of the things Push makes simple?

1. Allows you to easily scan wifi and connect to it with a couple of commands. And if you want your microcontroller to automatically connect to your WIFI router, the installer will help you do that.
2. Read files on disk easily using cat <yourfile>
3. Filter things easily by using grep.
4. Run background jobs as the VM implements coprocessing.



<br>
For this tutorial I will be using thonny to upload and interact with an ESP32
<br
<pre>
1. open thonny
2. ensure that your microcontroller is flashed with micropython.
3. ensure thonny is set for run-->interpreter  ESP32 and the correct USB port selected.
4. You should see the python REPL when connecting with thonny.
5. In thonny select the open file icon and browse to the install_pushvm.py script.
6. Select Save As from thonny and save to the micropython device
7. Run the installer  "import install_pushvm"
8. If you wish to setup networking select y and follow the instructions.
9. Reset the device and run the pushvm shell. "import pushvm"
    "pushvm.repl()
</pre>




Interacting with the shell.
 
1. run import pushvm
2. run pushvm.repl()
3. you should get a push> prompt


The help command provides a list of commands and functions.

<pre>
push> help
PUSH ver: pushvm-complete-0.1

commands: exit, ls, uname, free, df, pwd, cat, cp, cd, mkdir,
grep, rmdir, exec, rm, date,
scanwifi, connect, ifconfig, edit, rename
extras: echo, upper, wc, test, write (>), append (>>), sleep
flow: if/while/for/foreach, break/continue, &&/||, vars x=val $x, jobs &
jobctl: jobs, kill <id>, fg <id>

</pre>


To check what ip address your microcontroller has use "ifconfig"

<pre>
push> ifconfig

IP........... 10.93.61.239
NETMASK.......255.255.255.0
GATEWAY.......10.93.61.20
push> 
</pre>


If you are not connected then you should show IP of "0.0.0.0"

You can scan for all WIFI networks by using the command "scanwifi"
Example:

<pre>
push> scanwifi
network1
ciscoext
alphanet
push> 

</pre>

If you need to connect manually to your WIFI router use the command "connect"
Example:
<pre>

push> connect rpixel
Enter SSID: 
mynet
Enter wifi pw: 
mypassword
attempting to connect..

Check ifconfig..

push> 

</pre>

To list files on the device use "ls"
Example:
<pre>
push> ls
boot.py
dhcp.py
install_pushvm.py
lib
pushvm.py
webrepl_cfg.py
push> 
</pre>

you can count how many files there are by re running that command and putting a PIPE in between the next command called "wc" (word count) as wc will list how many lines are in the output.

Example:
<pre>
push> ls|wc
6
push> 
</pre>

To read a file use "cat"

<pre>
push> cat boot.py
# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
webrepl.start()

import dhcp
push> 

</pre>

If you want to count how many lines were in that file then use "cat|wc"

<pre>
push> cat boot.py|wc 
7

push> 
</pre>

If you want to search for lines that contain the word "import" use "grep"

<pre>
push> cat boot.py|grep import
#import esp
import webrepl
import dhcp

push> 
</pre>

If you want to count how many those results were use "cat boot.py|grep import|wc"

<pre>
push> cat boot.py|grep import|wc
3

push> 
</pre>


To check what python modules are available to use type in "modules"

<pre>
push> modules
__main__          btree             io                ssl
_asyncio          builtins          json              struct
_boot             cmath             machine           sys
_espnow           collections       machine           time
_onewire          cryptolib         math              tls
_thread           deflate           micropython       uasyncio
_webrepl          dht               mip/__init__      uctypes
aioespnow         ds18x20           neopixel          umqtt/robust
apa106            errno             network           umqtt/simple
array             esp               ntptime           upysh
asyncio/__init__  esp32             onewire           urequests
asyncio/core      espnow            os                vfs
asyncio/event     flashbdev         platform          webrepl
asyncio/funcs     framebuf          random            webrepl_setup
asyncio/lock      gc                re                websocket
asyncio/stream    hashlib           requests/__init__
binascii          heapq             select
bluetooth         inisetup          socket
Plus any modules on the filesystem
None
push> 
</pre>

To run a function from one of those modules such as os use the command "exec"

<pre>
ush> exec os.listdir()
['boot.py', 'dhcp.py', 'install_pushvm.py', 'lib', 'pushvm.py', 'webrepl_cfg.py']
push> 
</pre>


To write your own python code and integrate it as a shell command you can put it in /lib directoryi, but for the shell not to have to guess how to execute it define it with a main function. Here is a hello world script example:

<pre>

def main(argv):
  print("Hello World")
    
</pre>

I would normally edit this in thonny and save it to the /lib directory as hello.py (Note that you do have to stop the shell to push files to the microcontroller so use "exit" to exit the shell and then restart it with push.repl() once you have uploaded the new file to save in /lib)

and then run it with the name of the script minus the .py extension:



<pre>
push> hello
Hello World
push> 
</pre>

