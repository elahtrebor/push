import os
import re
import sys
import network
import urequests
import time
import ntptime

NTPSERVER="pool.ntp.org"

def shell():
 print ("******************************")
 print ("* PUSH - Python Micro SHELL  *")
 print ("* ls,pwd,cd,uname,df,cat     *")
 print ("* rmdir,rm,mkdir,cp,edit     *")
 print ("* ifconfig,wget,connect,>    *")
 print ("******************************")

 while True:
   print("$", end="")
   input1 = input()
   output = ""
   redirect = 0

   if re.search('>', input1):
      redirect = 1
      input1, outfile = input1.split(">")
      input1 = input1.rstrip()
      outfile = outfile.lstrip()
   # if nothing then just re loop
   if not re.search('^[A-Za-z]', input1):
       continue
   # if exit.. or do some commands
   if re.search('^exit', input1):
     print("bye..")
     sys.exit()
   elif re.search('^ls',input1):
     input1 = input1.replace("ls", '')
     input1 = input1.strip()
     if re.search('\S+',input1):
       output = ("\n".join(os.listdir(input1)))
     else:
       output = ("\n".join(os.listdir()))
   elif re.search('^uname',input1):
     output = ("\n".join(os.uname()))
   elif re.search('^df',input1):
     total = float(os.statvfs('/')[2]) * float(os.statvfs('/')[0])
     used = float(os.statvfs('/')[3]) * float(os.statvfs('/')[0])
     free = total - used
     output = ("Free: " + str(free) + " Used: " + str(used) + " Total: " + str(total
)  )
   elif re.search('^pwd', input1):
     output = os.getcwd()
   elif re.search('^cat', input1):
     input1 = input1.replace("cat ", '')
     input1 = input1.strip('\n')
     file1 = open(input1, "r")
     output = file1.read()
     file1.close()
   elif re.search('^cp ', input1):
     input1 = input1.strip('\n')
     input1 = input1.replace("cp ", '')
     [source, dest] = input1.split(' ')
     file1 = open(source, "r")
     outputdata = file1.read()
     file1.close()
     file2 = open(dest, "w")
     file2.write(outputdata)
     file2.close()
     outputdata = []
     output = ("File " + source + " copied.")
   elif re.search('^cd', input1):
     input1 = input1.replace("cd ", '')
     if re.search('\S+', input1) and not re.search('/',input1):
         input1 = "./" + input1
     input1 = input1.strip('\n')
     try:
      os.chdir(input1)
      output = input1
     except:
      output = ("Error. Couldn't cd\n")
   elif re.search('^clear', input1):
    print("\x1B\x5B2J", end="")
    print("\x1B\x5BH", end="")
   elif re.search('^mkdir', input1):
     input1 = input1.replace("mkdir ", '')
     input1 = input1.strip('\n')
     os.mkdir(input1)
     output = ("Directory " + input1 + " created.\n")
   elif re.search('^reload', input1):
     input1 = input1.replace("reload ", '')
     input1 = input1.strip('\n')
     del sys.modules[input1]
     output = ("Module " + input1 + " reloaded..\n")
   elif re.search('^wget', input1):
     input1 = input1.replace("wget ", '')
     input1 = input1.strip('\n')
     try:
      r = urequests.get(input1)
      output = (r.content.decode('UTF-8'))
     except:
      output = ("Couldn't get " + input1)
   elif re.search('^rmdir', input1):
     input1 = input1.replace("rmdir ", '')
     input1 = input1.strip('\n')
     os.rmdir(input1)
     output = ("Removed " + input1 + ".\n")
   elif re.search('^rm ', input1):
     input1 = input1.replace("rm ", '')
     input1 = input1.strip('\n')
     os.unlink(input1)
   elif re.search('^ntpsync', input1):
     ntptime.host=NTPSERVER
     ntptime.settime()
     print("time sync'd with: " + NTPSERVER)
     output = str(time.localtime())
   elif re.search('^scanwifi',input1):
       wlan = network.WLAN(network.STA_IF)
       wlan.active(True)
       nets = wlan.scan()
       for i in nets:
         output += (str(i[0].decode()) + "\n")
   elif re.search('^connect', input1):
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
      print("Check ifconfig..\n")
     except:
         output = "Error: couldn't obtain address\n"
   elif re.search('^ifconfig', input1):
     wlan = network.WLAN(network.STA_IF)
     status = wlan.ifconfig()
     output = ("\nIP........... " +
        status[0] +
        "\nNETMASK......." +
        status[1] + "\n" +
        "GATEWAY......." +
        status[2])
   elif re.search('^edit ', input1):
     input1 = input1.replace("edit ", '')
     print("EDIT MODE DETECTED...\n")
     print ("(ENTER STOPEDIT to stop)\n")
     file1 = open(input1, "w")
     flag = 0
     while flag == 0:
       line =input()
       if re.search('STOPEDIT', line):
         file1.close()
         flag = 1
       else:
         file1.write(line + "\n")
     output = ("File " + input1 + " created..\n")
   else:
        print("Error: command not found\n")
   # handle the output
   if not re.search('\S+', output):
       continue

   if redirect:
     fileh = open(outfile, "w")
     fileh.write(output)
     fileh.close()
   else:
       print(output)

shell()

