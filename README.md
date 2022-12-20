# push
<p>
Python Micro Shell - One file shell for micropython micro controllers
- cd, pwd, cat , redirect, wget, mkdir, rmdir, rm, etc

This is designed to quickly give you a mini linix like shell. 
Tested on ESP32, ESP8266, RPI PICO W.

To use make sure you have micropython installed first.

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

Supports ls, cat, cd, pwd, mkdir, rmdir, rm, rename, cp, ifconfig, wget(works like curl),  
and redirect ">".
No pipes yet. No switches or flags.

if for some reason the shell crashes then you can restart it with "import push" and "push.shell()"

Here is the output of a test drive:
</p>
<pre>
MicroPython v1.19.1-773-g988b6e2da on 2022-12-15; ESP32 module with ESP32

Type "help()" for more information.

\>\>\> import push
******************************
* PUSH - Python Micro SHELL  *
* ls,pwd,cd,uname,df,cat     *
* rmdir,rm,mkdir,cp,edit     *
* ifconfig,wget,connect,>    *
******************************
$ifconfig

IP........... 0.0.0.0
NETMASK.......0.0.0.0
GATEWAY.......0.0.0.0
$




$connect
Enter SSID: 
mynetwork
Enter wifi pw: 
mypassword
attempting to connect..

Check ifconfig..



$ifconfig

IP........... 192.168.1.18
NETMASK.......255.255.255.0
GATEWAY.......192.168.1.1
$



$ls
boot.py
push.py
tmp
$mkdir lib
Directory lib created.

$cd lib
lib
$pwd
/lib

$wget https://www.ntppool.org/en/
<!DOCTYPE html>
<html lang="en">
  <head>
    
<title>pool.ntp.org: the internet cluster of ntp servers</title>

<script>
  if (!NP) var NP = {};
</script>

<link rel="stylesheet" href="https://st.pimg.net/ntppool/.g/common.v60ac5d8cf9.css" type="text/css">
 
		
<-- truncated for berevity demo-->  
  
You can install other libraries from 
github using wget://yourgithub_raw_link  > /lib/yourfilename.py
  
  Example (Download uping and ping a network host):
$cd /lib  
$wget https://gist.githubusercontent.com/shawwwn/91cc8979e33e82af6d99ec34c38195fb/raw/ca2e629a54abcb18b1c4f766d594507cea41289a/uping.py > uping.py
$
$cd ..
..
$exec uping.ping("192.168.1.190")
PING 192.168.1.190 (192.168.1.190): 64 data bytes
84 bytes from 192.168.1.190: icmp_seq=1, ttl=64, time=19.888000 ms
84 bytes from 192.168.1.190: icmp_seq=2, ttl=64, time=25.198000 ms
84 bytes from 192.168.1.190: icmp_seq=3, ttl=64, time=16.527000 ms
84 bytes from 192.168.1.190: icmp_seq=4, ttl=64, time=10.604000 ms
4 packets transmitted, 4 packets received
$


$uname
esp32
esp32
1.19.1
v1.19.1-773-g988b6e2da on 2022-12-15
ESP32 module with ESP32



$ntpsync
time sync'd with: pool.ntp.org
(2022, 12, 18, 23, 57, 4, 6, 352)



$
$cd tmp
tmp
$
$edit test.txt
EDIT MODE DETECTED...

(ENTER STOPEDIT to stop)

this
is
a
test
STOPEDIT
File test.txt created..

$cat test.txt
this
is
a
test

$cd ..
..
$exec os.listdir()
['boot.py', 'lib', 'push.py', 'tmp']



$
