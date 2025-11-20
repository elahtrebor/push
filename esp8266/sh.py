#This code is as free as the word free..
import os
import re
import sys
import network
import time
import gc

VERSION = "11.19.25.22"
redirect = 0
output = ""
ROOTDIR=""
STDOUT = ROOTDIR + "STDOUT"
STDIN = "STDIN"
FIN = 0

def soread():
    sofile = open(STDOUT, "r")
    data = sofile.read()
    sofile.close()
    return data

def soclear():
   open(STDOUT, 'w').close()
   open(STDIN, 'w').close()

def EVAL(input1):
   global FIN
   output = ""
   redirect = 0
   if re.search('>', input1):
      #print("redirect: " + input1)
      redirect = 1
      input1, outfile = input1.split(">")
      input1 = input1.rstrip()
      outfile = outfile.lstrip()

   if re.search('^help', input1):
     print("PUSH ver: " + VERSION + "\n")
     print ("commands: exit, ls, uname, df, pwd, cat, cp, cd, mkdir,\n")
     print ("grep, reload, rmdir, exec, rm, date,\n")
     print ("scanwifi, connect, ifconfig, edit\n")
   elif re.search('^ls',input1):
     input1 = input1.replace("ls", '')
     input1 = input1.strip()
     if re.search('\S+',input1):
       try:
           output = ("\n".join(os.listdir(input1)))
       except:
           output = "Syntax Error\n"
     else:
       output = ("\n".join(os.listdir()))
   elif re.search('^uname',input1):
     output = ("\n".join(os.uname()))
   elif re.search('^free',input1):
     output = str(gc.mem_free())     
   elif re.search('^df',input1):
     total = float(os.statvfs('/')[2]) * float(os.statvfs('/')[0])
     used = float(os.statvfs('/')[3]) * float(os.statvfs('/')[0])
     free = total - used
     output = ("Free: " + str(free) + " Used: " + 
             str(used) + " Total: " + str(total) )
   elif re.search('^pwd', input1):
     output = os.getcwd()
   elif re.search('^cat', input1):
     input1 = input1.replace("cat ", '')
     input1 = input1.strip('\n')
     try:
      file1 = open(input1, "r")
      output = file1.read()
      file1.close()
     except:
         output = "Couldn't open file\n"
   elif re.search('^wc ', input1):
     input1 = input1.replace("wc ", '')
     input1 = input1.strip('\n')
     try:
       x = 0
       with open(input1) as f:
         for line in f:
          x += 1 
       f.close()
       output = (str(x) + "\n")
     except:
         output = "Couldn't open file\n"
   elif re.search('^grep', input1):
     input1 = input1.replace("grep ", '')
     input1 = input1.strip('\n')
     [rgx,fname] = input1.split()
     try:
      with open(fname) as f:
        for line in f:
            if re.search(rgx,line):
              output += line 
      f.close()
     except:
      output = "Couldn't perform.\n"
   elif re.search('^cp ', input1):
     input1 = input1.strip('\n')
     input1 = input1.replace("cp ", '')
     [source, dest] = input1.split(' ')
     try:
      file1 = open(source, "r")
      outputdata = file1.read()
      file1.close()
      file2 = open(dest, "w")
      file2.write(outputdata)
      file2.close()
      outputdata = []
      output = ("File " + source + " copied.")
     except:
        output = "Couldn't copy.\n"
   elif re.search('^cd', input1):
     input1 = input1.replace("cd ", '')
     try:
      os.chdir(input1)
      output = input1
     except:
      output = ("Error. Couldn't cd\n")
   elif re.search('^rename ', input1):
      input1 = input1.replace("rename ", '') 
      [source, dest] = input1.split(' ')  
      try:
        os.rename(source, dest)
        output = (source + " renamed..")
      except:
        output = "Couldn't rename\n"
   elif re.search('^mkdir', input1):
     input1 = input1.replace("mkdir ", '')
     input1 = input1.strip('\n')
     try:
      os.mkdir(input1)
      output = ("Directory " + input1 + " created.\n")
     except:
      output = "Couldn't make directory\n"
   elif re.search('^rmdir', input1):
     input1 = input1.replace("rmdir ", '')
     input1 = input1.strip('\n')
     try:
      os.rmdir(input1)
      output = ("Removed " + input1 + ".\n")
     except:
         output = "Couldn't remove dir.\n"
   elif re.search('^exec ', input1):
     input1 = input1.replace("exec ", '')
     input1 = input1.strip('\n')
     if re.search('\.',input1):
        module = re.search('^(.*?)\.', input1).group(1)
        input1 = input1.replace(module + ".","")
        func = re.search('^(.*?)\(', input1).group(1)
        args = re.search('\((.*?)\)', input1).group(1)        
        try:
          script = getattr(__import__(module), func)
          if not args:
              output = str(script())
          else:
              args = args.replace('"', "")
              output = str(script(args))
        except:
          output = "Error: Check Syntax\n"
   elif re.search('^rm ', input1):
     input1 = input1.replace("rm ", '')
     input1 = input1.strip('\n')
     try:
       os.unlink(input1)
       output = ("Removed file " + input1 + "\n")
     except:
      output = "Couldn't remove file\n"
   elif re.search('^date', input1):
     dateTimeObj = time.localtime()
     year,month,day,hour,min,sec,wday,yday = (dateTimeObj)
     output =  (str(month) + "/" +
         str(day) + "/" +
         str(year) + " " +
         str(hour) + ":" +
         str(min) + ":" +
         str(sec))
   elif re.search('^scanwifi',input1):
       try:
         wlan = network.WLAN(network.STA_IF)
         wlan.active(True)
         nets = wlan.scan()
         for i in nets:
           output += (str(i[0].decode()) + "\n")
       except:
            output = "Couldn't scan networks.\n"
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
       try:
         wlan = network.WLAN(network.STA_IF)
         status = wlan.ifconfig()
         output = ("\nIP........... " +
            status[0] +
            "\nNETMASK......." +
            status[1] + "\n" +
            "GATEWAY......." +
            status[2])
       except:
            output = "Couldn't get interface or check syntax.\n"
   elif re.search('^edit ', input1):
     input1 = input1.replace("edit ", '')
     print("EDIT MODE DETECTED...\n")
     print ("(ENTER STOPEDIT to stop)\n")
     try:
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
     except:
          output = "Couldn't write file\n"
   else:
        print("Error: command not found\n")

   if not re.search('\S+', output):
       return
   if redirect:
     fileh = open(outfile, "w")
     fileh.write(output)
     fileh.close()
     result = soread()
     if re.search(STDOUT, outfile) and FIN:
      print(result)
   else:
    print(output)


def tokenize(expr):
  tokens = expr.split('|')
  x = 0
  l = []
  for i in tokens:
    i = re.sub('\s+$',"",i)
    i = re.sub('^\s+',"",i)
    if x == 0:
     l.append(i + ">" + STDOUT)
    elif re.search(">", i):
     i = i.replace(">", "STDOUT >")
     l.append(i)
    else:
     l.append (i + " " + STDOUT + " >" + STDOUT)
    x += 1
  return l


def shell():
 global FIN
 print ("******************************")
 print ("* PUSH - Python Micro SHELL  *")
 print ("* ls,pwd,cd,uname,df,cat     *")
 print ("* rmdir,rm,mkdir,cp,edit     *")
 print ("* ifconfig,connect,grep      *")
 print ("******************************")

 soclear()
 while True:
   soclear()
   print("$", end="")
   input1 = input()

   if re.search('\|',input1):
      tokens = tokenize(input1)
      tlen = len(tokens)
      x = 0
      for i in tokens:
        if x == (tlen - 1):
            FIN = 1
        EVAL(i)
        x += 1
      continue

   # if nothing then just re loop
   if not re.search('^[A-Za-z]', input1):
       continue
   # if exit.. or do some commands
   elif re.search('^exit', input1):
     print("bye..")
     os.unlink(STDOUT)
     os.unlink(STDIN)
     sys.exit()
   else:
       EVAL(input1)
       

shell()
