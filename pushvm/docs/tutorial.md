<h3>Pushvm tutorial</h3>


This tutorial covers installation and operation of the shell. 
 The installer portion walks though using the installer which gives you the package manager and sets up the lib directory as well as optionally gives you the ability to setup networking that automatically connects on boot.

Wny use push? When I first started using ESP32 and RPI Pico I was amazed that micropython would run on them and learned that the devices later supported networking which opens up a lot of doors for capability. When I used thonny and webrepl I got a chance to interact with the python REPL and learned that many micropython library functions allowed you to do the equivilant actions like on regular operating systems such as list files. In micropython you would import the os library and use os.listdir() from the REPL to list files. I soon found that typing os.listdir() got tiring and also missed the linux shell capabilities. I then found myself building a crude shell that would take the input string "ls" and run os.listdir() in python. I found many library calls to read and manipulate files, control networking /sockets, and other useful utilities. I wanted to build a shell that doesnt solve world hunger but helps elevate capabilities a little
.
Wny use push? When I first started using ESP32 and RPI Pico I was amazed that micropython would run on them and learned that the devices later supported networking which opens up a lot of doors for capability. When I used thonny and webrepl I got a chance to interact with the python REPL and learned that many micropython library functions allowed you to do things like on regular operating systems such as list files in python you would use os.listdir() from the REPl. I soon found that got tired of typing os.listdir and also missed the linux shell capabilities and then found myself building a crude shell that would take the input string "ls" and run os.listdir() in python. I found many library calls to read and manipulate files, control networking /sockets, and other useful utilities. I then wanted to try to build a shell for the microcontroller which doesnt solve world hunger but helps elevate capabilities and create convenience.  This started as a one file loop taking input and running commands, then later added fake pipes and redirect, and now evolved to a VM.

 What are some of the things Push makes simple?

1. Allows you to easily scan wifi and connect to it with a couple of commands. And if you want your microcontroller to automatically connect to your WIFI router, the installer will help you do that.
2. Read files on disk easily using cat <yourfile>
3. Filter things easily by using grep.
4. Run background jobs as the VM implements time slicing.



<br>
For this tutorial I will be using thonny to upload and interact with an ESP32
<br>
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


Interacting with the shell.
 
1. run import pushvm
2. run pushvm.repl()
3. you should get a push> prompt


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

you can count how many files there are by re running that command and putting a PIPE in between the next command called "wc" (word count) as wc will list how many lines in the file.

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



