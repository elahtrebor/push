# push
Python Micro Shell - One file shell for micropython micro controllers - cd, pwd, cat , redirect, wget, mkdir, rmdir, rm, etc

A quick shell that hacked together.

This is designed to quickly give you a linix like shell. Tested on ESP32, ESP8266, RPI PICO W.

To install just connect with thonny or whatever your using to manage your microdevice.
drop the file on there and save as push.py
then from the micropython cli "import push"
It has a quick wifi connect built in,a crude editor that works similiar to cat'ng text into the console, an ntp sync tool.
Supports ls, cat, cd, pwd, mkdir, rmdir, rm, cp, ifconfig, wget(works like curl),  and redirect ">".
No pipes yet.


