# push
<pre>
Python Micro Shell - One file shell for micropython micro controllers - cd, pwd, cat , redirect, wget, mkdir, rmdir, rm, etc

A quick shell that hacked together.

This is designed to quickly give you a linix like shell. Tested on ESP32, ESP8266, RPI PICO W.

To install just connect with thonny or whatever your using to manage your microdevice. make sure you have micropython installed.

drop the push.py file on the device and save as push.py
then from the micropython cli "import push"
It has a quick wifi connect built in, a crude editor that works similiar to cat'ng text into the console, a wget that works like curl, an ntp sync tool.

Supports ls, cat, cd, pwd, mkdir, rmdir, rm, cp, ifconfig, wget(works like curl),  and redirect ">".
No pipes yet.

if the shell crashes then you may have to restart it with "import push" and "push.shell()"

Here is the output of a test drive:



MicroPython v1.19.1-773-g988b6e2da on 2022-12-15; ESP32 module with ESP32

Type "help()" for more information.

>>> import push
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
  
  
You can install other libraries from github using wget://yourgithublink  > /lib/yourfilename.py
  
  
 
