
# Name: ASR Validation Script
# Author: David Ingty <david.ingty@oracle.com>
# Language: Python 2.7.10
# Last Edited: 2019-05-9 12:00 IST (GMT +5:30)


from threading import Thread
from bs4 import BeautifulSoup
from tabulate import tabulate
import re, os, shutil, datetime, requests, sys, cgi, cgitb
import logging

#logging.basicConfig(level=logging.DEBUG)


swd = os.getcwd()                                       # start working dir
dt = datetime.datetime.utcnow().isoformat().replace(":",".").replace("-",".")
femslink = "https://fems.us.oracle.com/FEMSService/resources/femsservice/femsview/"
hblink = "https://fems.us.oracle.com/PersistenceService/resources/persistenceservice/nph/heartbeatfull/"
asrmlink = "https://fems.us.oracle.com/FEMSService/resources/femsservice/femsview/asrsiteid/"

logdirectory = '/var/log/asrvalidationscript/'
splist = ["    ","    ","        ","      "]
pattlist1 = ["[", "    ,   "]
hashlist = ["####", "####, ##", "##, #", "#, #", ""]
pattlist3 = ["TESTCREATE.*$", "ASR-.*?\,"]
pattlist2 = ["SUN NETWORK QDR INFINIBAND GATEWAY SWITCH", "Sun Network QDR InfiniBand Gateway Switch" ,\
"SUN DATACENTER INFINIBAND SWITCH", "SUN DATACENTER INFINIBAND SWITCH 36"]
hblist = ['<[^<]+?>', "SUN.*$", "ORACLE.*$", "Sun.*$", "SPARC.*$", "\d\d:\d\d:\d\d", "\+.*?,"]

header7 = "Assets in Installed-Base but NOT in list_asset"
header6 = "Assets in list_asset but NOT in Installed-Base"
header5 = ["SERIAL-NO","PRODUCT DESCRIPTION", "ILOM-HOSTNAME", "ZFS/OS-HOSTNAME",\
 "ILOM-TEST", "ZFS/OS-TEST", "ASR-STATUS", "ASRM-HOSTNAME(S)"]
header4 = ["ASRM-HOSTNAME", "RECEIVER", "ASR-SITEID", "ACTIVATION-EMAIL"]
header3 = "ASSET HEARTBEAT INFORMATION (Upto Last 7 recent entries)"
header2 = ["SERIAL-N0", "PRODUCT DESCRIPTION", "HOSTNAME", "SOURCE", "RECEIVER", "TYPE", \
"RECEIVED-TIME", "EVENT-TIME"]
header1 = ["SERIAL-N0","PRODUCT DESCRIPTION","STAT","OWN-HB","HOSTNAME","SOURCE", "RECEIVER", "ASR SITEID",\
"ACTIVATION EMAIL","INFORMATION"]

ib1,ib2,ib3,ib4, ib5 = "SUN NETWORK QDR INFINIBAND GATEWAY SWITCH", \
"Sun Network QDR InfiniBand Gateway Switch" ,\
"SUN DATACENTER INFINIBAND SWITCH", "SUN DATACENTER INFINIBAND SWITCH 36", "SWITCH 36"
ib = "INFINIBAND SWITCH"
dc = "event received multiple times. Duplicate count=\d{1,3}"
tc = "testevent_.*?,"
linebreak1 = [" ", " ", " ", " ", " ", " ", " ", " ", " "]
linebreak2 = [" ", " ", " ", " ", " ", " ", " ", " "]
strp = ["TESTCREATE", "ZFS STORAGE"]
zpatt = "Audit event                        Event status\
                      Complete  Create SR  false  Faultgroup  Unknown SR details"
file_path1 = ""
srnum = ""
sr_arg = ""
list_asset = ""
ibase = ""
scriptpath = "/opt/asrvalidationscript/"
flask_templates_path = "/opt/asrvalidationscript/templates/"



def write_me(filename, variable):
    """ write to a file from a variable """
    with open(filename, 'w') as f:
        for eachline in variable:
            f.write(eachline)
            f.write('\n')
    os.system('clear')


def copytolog():
    """ saves user input to log files """
    if os.path.exists('/var/log/asrvalidationscript/' + srnum):
        os.system('cp list_asset.txt ' + logdirectory + '/' + srnum + '/' + 'list_asset.log')
        os.system('cp ib.txt ' + logdirectory + '/' + srnum + '/' + 'ib.log')
    else:
        os.mkdir('/var/log/asrvalidationscript/' + srnum)
        os.system('cp list_asset.txt ' + logdirectory + '/' + srnum + '/' + 'list_asset.log')
        os.system('cp ib.txt ' + logdirectory + '/' + srnum + '/' + 'ib.log')


def interactivefunc():
    """ This function is used to make the script interactive when run from CLI.
        It will ask for 3 things SRNumber, list_asset and InstalledBase output """

    # get the user to enter the SR Number
    global srnum
    global sr_arg
    try:
        sr_arg = sys.argv[1]    # get sr # passed from CLI
    except:
        pass

    srnum = sr_arg
    print(srnum)
    if srnum == "":
        srnum = raw_input(""" Enter the Service Request Number and press enter OR press 'q' to Quit:\n """)
        if srnum == "q":
            sys.exit()

    os.chdir(scriptpath)
    os.mkdir(srnum + dt)
    os.chdir(srnum + dt)
    os.system('clear')
    cwd = os.getcwd()        # get current working directory
    origpath = cwd

    # get the user to enter the list_asset file
    print("Enter the list_asset output OR type q to quit. Once done press Ctrl-D:")
    userInput = sys.stdin.readlines()
    if userInput == "q":
        sys.exit()
    else:
        write_me('list_asset.txt', userInput)


    # get the user to enter the Installed Base file
    print("Enter the Installed Base output OR type q to quit. Once done press Ctrl-D:")
    ibinput = sys.stdin.readlines()
    if ibinput == "q":
        sys.exit()
    else:
        write_me('ib.txt', ibinput)


    global file_path1
    file_path1 = os.getcwd()
    copytolog()
    print('Processing now. Please stand by...')



def webfunc():
    """ This function will take user input from the html page """
    sr_arg = sys.argv[1]
    global srnum
    srnum = sr_arg
    flaskdir = os.getcwd()   # get flask dir
    os.chdir(scriptpath)
    os.mkdir(srnum + dt)
    os.chdir(srnum + dt)
    os.system('clear')
    cwd = os.getcwd()        # get current working directory
    origpath = cwd
    shutil.move(flaskdir + '/' + srnum + 'list_asset.txt', origpath+'/list_asset.txt')
    shutil.move(flaskdir + '/' + srnum + 'ib.txt', origpath+'/ib.txt')
    global file_path1
    file_path1 = cwd
    copytolog()


try:

# >>> Named Functions <<< #
    def extractUnique(colno, file_name, condition=""):
        """ extractUnique will iterate over a file and extract a
            list of unique values from a given column """
        try:
            for line in open(file_name, 'r').readlines():
                line = line.strip()
                line = line.split()[colno]
                return line
        except:
            pass



    def checkMissing(inlist, outlist):
        """ Function to print a "--" for missing serials """
        return list(outlist.append("----------") if i not in inlist else outlist.append(i) \
        for i in sumserials)



    def getTable(serial, tableNo):
        """ getTable function to parse a html page of a given serial number
        and retrieve a given table """
        try:
            filename = serial.strip()+".html"
            with open(filename) as html_file:
                soup = BeautifulSoup(html_file, "html.parser")
                return soup.find_all('table')[tableNo]
        except IndexError:
                pass



    def replacer(pattlist, word):
        """ Function used to perform string replacement on a given line """
        for i in pattlist:
                return line.replace(i, word)



    def resub(pattlist, word, line):
        """ Function to use regex substitute function called on a list """
        for i in pattlist:
                return re.sub(i, "", line)


    def lineFilter():
        """ Function used to extract dict keys, values """
        for keys,values in tab.items():
                for line in values:
                    line = str(line)
                    return re.sub('<[^<]+?>', ' ', line)


    def downloader(link, path):
        """ Function to download fems pages and daily heartbeat pages """
        for serial in assetserials:
            r = requests.get(link+serial.strip()).content
            with open(path+serial.strip()+".html", 'w+') as f:
                f.write(r)


    def dressup(max, header, listname):
        """ Creating a function for adding field headings for stdout reports """
        listname = filter(None, listname)
        print(header)
        print("-" * max)
        for i in sorted(listname):
            print(i.strip())


    def list_dict(listname1):
        """ unction to get most recent test events from a list
        that contains the testevents """
        ulist = []
        udict = {}
        for serial in tserials:
            for line in listname1:
                if serial in line and serial not in ulist:
                    ulist.append(serial)
                    udict[serial] = line
        return udict.values()


    def linebreaks(seriallist, inlist, outlist, linebreak):
        """ Insert line breaks between different serial number
        occourances in a list """
        for serial in sorted(seriallist):
            indices = [i for i, x in enumerate(inlist) if x[0] == serial]
            for n in indices:
                outlist.append(inlist[n])
            outlist.append(linebreak)


# >>> Validation report functions <<< #

    def get1(serial):
        """ get the product description from container info table """
        try:
            for line in conlist:
                if serial in line[0]:                               # check index0 for each line
                    if "EM ASR PRODUCT" not in str(line):           # skip lines containing EM ASR
                        value = re.sub("\(.*?\)", "", str(line[1])) # remove(..)like pattern & get index1
                        if value:
                            return value
                else:                                               # if product desc can't be fetched from conlist check in the testevents list!
                    for eachline in list0:                          # check eachline in list0 - it holds all recent testevents
                        if serial in eachline[0]:                   # if serial in the line index0
                            value = re.sub("\(.*?\)", "", str(eachline[1]))         # remove (....) like pattern and get value of index1
                            return value
        except:
            pass


    def get2(serial):
        """ get the ILOM hostnames """
        try:
            for line in ilomconlist:
                if serial in line[0]:       # check index0 for each line
                    if "ILOM" in line[5]:
                        value = line[4]
                        return value
                if serial not in line[0]:   # is serial is not in conlist, check in testevent list list0
                    for eachline in iloms:
                        if serial in eachline[0]:   # check index0 for each line
                            if "ILOM" in eachline[3]:
                                value = eachline[2]
                                return value
        except:
            pass


    def get5(serial):
        """ get the OS hostnames """
        try:
            if len(osconlist) > 0:
                for line in osconlist:
                    if serial in line[0]:
                        if "EXADATA-SW" in line[5]:
                            return line[4]
                        if "FMA" in line[5]:
                            return line[4]
                        if "SCRK" in line[6]:
                            return line[4]
                    if serial not in line[0]:
                        for eachline in mergedlist:
                            if serial in eachline[0]:
                                if "EXADATA-SW-ADR" or "FMA" in eachline[3]:
                                    return eachline[2]
            else:
                return "None"
        except:
            pass


    def get3(serial, listname):
        """ get the testevents """
        try:
            for line in listname:
                if serial in line:
                    return "YES"
        except:
            pass


    def get4(serial):
        """ get the ASR status information """
        try:
            for line in asset_stat:
                if serial in line:
                    return line[1]
        except:
            pass


    def fetch(serial):
        """ Function to get the asrm-hostname for a specific serialno """
        try:
            hnbox = []
            for line in asrmap:
                if serial in str(line):
                    line = line.split()
                    #return line[-1]
                    hn = line[-1]
                    hnbox.append(hn)
            return hnbox
        except:
            pass


    def printmissing(seriallist, inlist):
        """ see what assets are missing in list_asset and Installed-Base list """
        return [line for serial in seriallist for line in inlist if serial in str(line)]


    def parser(serial, table):
        """ This function will parse asset html page and try and fetch container related information """
        patn1 = "Heartbeat information for Serial Number:"
        newli = []
        try:
            for line in table:
                    sp = "#"
                    line = str(re.sub('<[^<]+?>','   ',str(line))).split('Information               ')
                    if "Container" or "container" in str(line):
                        del line[0]
                        row = re.sub("EXADATA-SW,ADR","EXADATA-SW-ADR", str(line))
                        row = str(row).strip()
                        row = str(row.replace(serial, "#" + serial))
                        row = row.split('#')
                        for eachrow in row:
                            if "ZFS STORAGE" in str(eachrow):
                                newrow = row = re.split(r'\s{2,}', eachrow)
                                #print(newrow)
                                n1,n2 = str(newrow[0]).split(',')
                                n3, n4, n5, n6 = newrow[1], newrow[5], newrow[8], newrow[10]
                                n7, n8, n9 = newrow[11], newrow[12], " - "
                                zline = n1+sp+n2+sp+n3+sp+n4+sp+n5+sp+n6+sp+n9+sp+n7+sp+n8
                                zline = zline.replace("],","  ").replace(",","").replace("'","")\
                                .replace("[","").replace("]","")
                                zline = zline.split('#')
                                if zline not in conlist:
                                    conlist.append(zline)
                        del row[0]
                        for eachrow in row:
                            eachrow = re.sub(":   ", ":", eachrow)
                            row = re.split(r'\s{2,}', eachrow)
                            #r0,r1 = str(re.sub("\(.*?\)","",str(row[0]))).split(',')
                            r0,r1 = str(row[0]).split(',')

                            r1 = r1.replace(ib1,ib).replace(ib2,ib).replace(ib3,ib).replace(ib4,ib)\
                            .replace("X86/X64 SYSTEM", "")
                            r2,r5,r8,r9 = row[1], row[5], row[8], row[9]
                            r10 = row[10]
                            r11,r12,r13 = row[11], row[12], re.sub("Container\(.*?:", "", str(row[13]))
                            r11 = re.sub('\[\d{1,3}\]', '', r11)
                            r13 = r13.replace(patn1,"")
                            myrow = r0+sp+r1+sp+r2+sp+r5+sp+r8+sp+r9+sp+r10+sp+r11+sp+r12+sp+r13
                            myrow = myrow.replace("],","  ").replace(",","").replace("'","")\
                            .replace("[","").replace("]","")
                            myrow = myrow.split('#')
                            if "EM ASR" not in str(myrow):
                                if myrow not in conlist:
                                    conlist.append(myrow)
        except:
            pass


    def managerhn(i):
        """ return the asr-manager hostnames for a specific asset -
        used within validation report """
        box = []
        for line in asrmap:
            if i in str(line):
                li = line.split()
                hn = li[2]
                if hn not in box:
                    box.append(hn)
        string = ', '.join(box)
        return string



    def titleprint(words):
        """ This will print a title on the screen! """
        length = len(words)
        pr = '>' * length
        print(words)
        print(pr)


    def readandwrite(listname, filename):
        """ function to read from list and save in a file """
        with open(file_path1 + "/" + filename, 'w+') as f:
            for eachline in listname:
                f.write(eachline)


    def check_missing(listname, colno, value):
        """ this function will check for assets that have missed specific testevents """
        xlist = []
        for line in listname:
            col = line[colno]
            if value in col:
                if line[0] not in xlist:
                    xlist.append(line[0])
        return xlist


    def get_dup_sources(source, listname, dup_list):
        """ get the serial for assets that have duplicate telemetry sources """
        for serial in assetserials:
            bag = []
            num = 0
            for line in listname:
                if serial in line:
                    if source in line:
                        bag.append(line)
                        num += 1
                        if num > 1:
                            if serial not in dup_list:
                                dup_list.append(serial)
                                continue


    # Main program execution starts!!

    start_time = datetime.datetime.now().replace(microsecond=0)

    # check if the dir exists, if not create it
    if not os.path.exists(logdirectory):
        os.mkdir(logdirectory)

    try:
        arg_sr = ""     # check if an SR argument was passed when executing the script in CLI
        arg_sr = sys.argv[1]    # grab and store the SRnumber/argument
    except:
        pass

    if arg_sr:      # if SR argument was passed and variable is not empty
        webfunc()
    else:
        interactivefunc()

    #webfunc()
    try:
        os.mkdir("/var/log/asrvalidationscript")
    except:
        pass

    os.chdir(scriptpath + srnum + dt)
    os.mkdir(dt)                              # create a temporary dir to hold all script files
    os.chdir(dt)                              # change to temporary dir
    cwd = os.getcwd()
    os.makedirs("fems")                       # create fems dir if it does not exist
    os.makedirs("hb")                         # create hb dir if it does not exist
    os.makedirs("asrm")                       # create asrm dir if it does not exist
    newcwd = os.getcwd()                      # get current working dir containing fems and hb dirs
    femspath = newcwd + "/fems/"              # dir path where fems pages are downloaded
    hbpath = newcwd + "/hb/"                  # dir path where hb pages are downloaded
    asrmpath = newcwd + "/asrm/"              # dir path where asrm pages are downloaded
    list_asset_file = "list_asset.txt"
    ib_file = "ib.txt"
    os.chdir(file_path1)                      # go to the dir that has the list_asset & ib text files




# lserials holds uniqe serial values from list_asset.txt file
    list_assets = [line.split() for line in open('list_asset.txt', 'r').readlines() if "SNMP" in line]
    lserials = list(set([line[2] for line in list_assets if "SNMP" in str(line)]))
    assetserials = lserials


# ibserials holds uniqe serial values from ib.txt
    ibserials, combo = [], []
    #ibserials = list(set([line.split()[-3] for line in sorted(open(ib_file, "r").readlines()) \
    #if "Latest" in line if any(re.findall(r"SERVER|ASSY,IB|SUNDC SWITCH|,ZS", line))]))
    with open(ib_file, 'r') as f:
        for line in f:
            if "Latest" in line:
                if not any(re.findall("KVM|Model|CISCO|Rack|family|DUTY|SHELF", line)):
                    line = line.split()
                    if len(line) >2:
                        if len(line[-3]) == 10:
                                if line[-3] not in ibserials:
                                    ibserials.append(line[-3])

    for i in assetserials:
        if i not in combo:
            combo.append(i)
    for i in ibserials:
        if i not in combo:
            combo.append(i)

    assetserials = combo[::]

    # Union of ibserials and lserials
    sumserials = set(lserials).union(set(ibserials))

    # These serials are in IB but NOT in list_asset
    lsmissing = set(ibserials).difference(set(lserials))

    # These serials are in list_asset but NOT in IB
    ibsmissing = set(lserials).difference(set(ibserials))


    xlist = []                      # What serials are missing in list_asset
    ylist = []                      # What serials are missing in IB
    checkMissing(lserials, xlist)
    checkMissing(ibserials, ylist)
    zlist = zip(xlist, ylist)       # Zip both lists together - for side by side viewing


    dash = "-" * 25
    title1 = "List_Asset Installed-Base"+"\n"
    heading0 = title1+dash
    num1 = len(lserials)                         # count the number of serials in list_asset:
    num2 = len(ibserials)                        # count the number of serials in InstalledBase:
    nums = str(num1)+"            "+str(num2)    # Printing out num1 and num2 values in one line


# Remove the unecessary characters to clean the output
    wlist = [str(i).replace("(","").replace(")","").replace(",","").replace("'","") for i in zlist]

    compare = []    # Print lserials and ibserials side by side with headings
    compare.append(heading0)
    for i in wlist: compare.append(i)
    compare.append(dash)
    compare.append(nums)


# extracting product description and serial number key value combination from ibfile
    """
    xl = [[line.strip().split()[:-4],line.strip().split()[-3]] \
    for line in sorted(open(ib_file, 'r').readlines()) \
        if any(re.findall(r"ASSY,IB|SERVER|ASSY,IBSUNDC SWITCH|SUNDC SWITCH|,ZS", line))]
    """
    xl = []
    for line in sorted(open(ib_file, 'r').readlines()):
        line = line.split()
        if len(line) > 3:
            if "Latest" in line[-1]:
                del line[-2:]
                del line[-2]
                if any(re.findall(r"SERVER|ASSY,IBSUNDC SWITCH|SUNDC SWITCH|,ZS|ASSY,IB", str(line))):
                    xl.append(line)

    #for i in x2: print(i)


# after extraction clean the lines to remove unwated characters
    ibinfo =  [ str(i).replace("],","  ").replace("'","").replace("[","").replace("]","") for i in xl]
    #for i in ibinfo: print(i)

# adjusting columns - to relefct serial number and product description form left to right
    ibinfo = [ str(i.split()[-1])+"   "+str(i.split()[:-1])\
    .replace("],","  ").replace("'","").replace("[","").replace("]","")\
    .replace(",,","").replace(", ZS", ",ZS") for i in ibinfo ]


# get the System/Product Catagory from InstalledBase file.
    #ibsys = [str(line.split(':')[0]) for line in open(ib_file, 'r').readlines() if any(re.findall("SuperCluster|Exalogic", line, re.IGNORECASE))]
    for line in open(ib_file, 'r').readlines():
        if "Exalogic" in line:
            ibsys = re.search('Exalogic', line, re.IGNORECASE).group()
        if "SuperCluster" in line:
            ibsys = re.search('SuperCluster', line, re.IGNORECASE).group()
        if "Oracle Public Cloud" in line:
            ibsys = re.search('Oracle Public Cloud', line, re.IGNORECASE).group()
        if "Zero Data Loss" in line:
            ibsys = re.search('Zero Data Loss', line, re.IGNORECASE).group()
# extracting zfs serials and remoeving zfs entries from ibinfo list (this needs ib.txt file)
    zfsserials = [line[:10] for line in ibinfo if any(re.findall(r",ZS|, ZS", line))]
    assetserials = assetserials + zfsserials + ibserials


# Downloading the fems html pages
    t1 = Thread(target=downloader, name="thread1", args=[hblink, hbpath])
    t2 = Thread(target=downloader, name="thread2", args=[femslink, femspath])
    t1.start()
    t2.start()
    t1.join()
    t2.join()



# >>> Extracting and creating the Container Table  (Non ZFS Assets)
    os.chdir(femspath)   # change to fems dir
# list contains serialNo $ hostname & telemetryType mapping
    siteids, conlist, conlist2, lencon, container_list = [], [], [], [], []
    patt = "ID,Status,Own HB,Hostname,Telemetry,ASR Siteid,Activation email,Information"
    ky1, ky2, ky3, sp = "Override activation enabled", "Container", "Parent", ","
    sp, trap = "#", []
    try:
        for serial in assetserials:
            filename = open(serial + ".html", 'r')
            soup = BeautifulSoup(filename, 'html.parser')
            table = soup.find_all('tr')
            if "Own HB" in str(table):
                for iline in table:
                    if serial + "," in str(iline):
                        if "<td>OK</td>" in str(iline):
                            iline = re.sub("<[^<]+?>","#",str(iline))
                            iline =  re.sub('#'+serial+',', serial+',', re.sub('#{1,}', '#', iline))
                            iline = iline.replace(':#', ':')
                            # STD
                            iline = iline.split('#')
                            sn, prod = iline[0].split(',')
                            stat, ownhb, hname = iline[1], iline[5], iline[8]
                            source, recv, sid = iline[9], iline[10], iline[11]
                            sid = re.sub('\[\d{1,3}\]', '', sid)
                            ackemail, cont = iline[12], iline[13]
                            cont = re.sub("Container\(.*?:", "", cont)
                            prod = prod.replace(ib1,ib).replace(ib2,ib).replace(ib3,ib).replace(ib4,ib)\
                        .replace("X86/X64 SYSTEM", "")  ##################################################
                            uline = sn.strip() +sp+ prod.strip() +sp+ stat.strip() +sp+ ownhb.strip() +sp+ \
                                hname.strip() +sp+ source.strip() +sp+ recv.strip() +sp+ sid.strip() +sp+ \
                                ackemail.strip() +sp+ cont.strip()
                            mline = uline.split('#')
                            if not any(re.findall("ZFS|SCRK", str(mline))):
                                if mline not in conlist:
                                    conlist.append(mline)
    except:
        pass
# >>> Extracting and creating the Container Table (ZFS Assets)
    zcon, sp = [], "#"
    try:
        for serial in assetserials:
            filename = open(serial + ".html", 'r')
            soup = BeautifulSoup(filename, 'html.parser')
            tablerow = soup.find_all('tr')
            for row in tablerow:
                if "OK" in str(row):
                    if "SCRK" in str(row):
                        if "Audit event" not in str(row):
                            row = re.sub("<td></td>", "<td>-</td>", str(row))
                            row = re.sub("<[^<]+?>","#",str(row))
                            row =  re.sub('#'+serial+',', serial+',', re.sub('#{1,}', '#', row))
                            row = row.replace(':#', ':')
                            line = row.split('#')
                            zsn, zprod = line[0].split(',')
                            zstat, zownhb, zhname, zsource, zrecv = line[1], line[5], line[8], line[9], line[10]
                            zsid, zactemail, zcont = line[11], line[12], line[13]
                            zcont = re.sub("Container\(\d{6,8}\):", "", zcont)
                            zline = zsn +sp+ zprod +sp+ zstat +sp+ zownhb +sp+ zhname +sp+ zsource +sp+ zrecv \
                                +sp+ zsid +sp+ zactemail +sp+ zcont
                            zline = zline.split('#')
                            if zline not in conlist:
                                conlist.append(zline)
    except:
        pass

    #for i in zcon: print(i)



    cserials = list(set([x[0] for x in conlist]))   # get the unique serials from the containers list
    ilomconlist = [line for line in conlist if "ILOM" in line]      # get lines with only ILOM
    osconlist1 = [line for line in conlist if "EXADATA" in str(line)]  # get lines with EXADATA entries
    osconlist2 = [line for line in conlist if "FMA" in str(line)]  # get lines with FMA entries
    osconlist3 = [line for line in conlist if "ZFS" in str(line)]  # get lines with FMA entries
    scrksls =  [line[0] for line in conlist if "SCRK" in str(line)]  # get serials with SCRK entries
    osconlist = osconlist1 + osconlist2 + osconlist3
    linebreaks(cserials, conlist, container_list, linebreak1)

    scrksl = set(scrksls)
    #for i in scrksl: print(i)

    # get serials
    source_iloms = [i[0] for i in ilomconlist]   # get ILOM serials from conlist
    try:
        source_os = [i[0] for i in osconlist]        # get OS serials from conlist
        os_source_missing = set(source_iloms).difference(set(source_os))        # get diff between OS and ILOM serials
        source_ib = [i[0] for i in conlist if any(re.findall("INFINIBAND", i[1]))]   # get IB switch serials from conlist
    # os_source_missing1 contains serials that do not have OS telemetry sources... excluding IB switches
        os_source_missing1 = set(os_source_missing).difference(set(source_ib))
    except:
        pass


 #  creting assetinfo what holds serial# - product desc mapping
    assetinfo = []
    for i in container_list:
        line = re.sub("\(.*?\)","", (str(i[:2]).replace("],","  ").replace(",","").replace("'","")\
            .replace("[","").replace("]","")))
        if line not in assetinfo:
            assetinfo.append(line)



# >>> Extracting and creating the Testevents Table
    alist, tab, testevent_list, tel, ex1, ex2  = [],{}, [], [], "EXADATA-SW,ADR", "EXADATA-SW-ADR"
    il, ex, fm, sc = "ILOM", "EXADATA-SW", "FMA", "SCRK"
    test_event_list, kl, tab = [], [], []
    list1, list2, list3, list4, telist = [],[], [], [], []
    multiword = "event received multiple times. Duplicate count=\d{1,3}"
    try:
        for serial in assetserials:
            filename = open(serial + ".html", 'r')
            soup = BeautifulSoup(filename, 'html.parser')
            tablerow = soup.find_all('tr')
            for row in tablerow:
                if "SCRK" or "TESTCREATE" in str(row):
                    row = re.sub("<[^<]+?>"," ",str(row)).split('Result  Notifications')
                    for eachrow in row:
                        if "TESTCREATE" in str(eachrow):    # check for asset testevents
                            eachrow = str(eachrow).strip()
                            eachrow = re.sub(multiword,'',eachrow)
                            e = re.split(r'\s{2,}', eachrow)
                            e0,e1,e2,e3,e4,e5,e6 = e[0:7]
                            e0 = str(e0).replace(ib1,ib).replace(ib2,ib).replace(ib3,ib).replace(ib4,ib)\
                            .replace("X86/X64 SYSTEM", "")
                            e4 = str(e4).replace(e4, "testevent")
                            eline = serial,e0,e1,e2,e3,e4,e5,e6
                            eline = list(eline)
                            if eline not in tab:
                                tab.append(eline)
                        if "Audit" in str(eachrow):         # check for zfs auditevents
                            eachrow = re.sub(multiword,'',eachrow)
                            eachrow = re.split(r'\s{2,}', eachrow.strip())
                            z0, z1, z2, z3, z4, z5, z6 = eachrow[:7]
                            z4 = str(z4).replace(z4, "auditevent")
                            zline = serial, z0, z1, z2, z3, z4, z5, z6
                            zline = list(zline)
                            if zline not in tab:
                                tab.append(zline)
    except:
        pass

    tserials = list(set([x[0] for x in tab]))                        # get only the unique asset serials from the tab list by removing duplicates
    iloms = [line for line in tab if "ILOM" in str(line)]            # segregate the testevents by ILOM and store in another list
    exas = [line for line in tab if "EXADATA-SW,ADR" in str(line)]   # segregate the testevents by EXADATA-SW and store in another list
    fmas = [line for line in tab if "FMA" in str(line)]              # segregate the testevents by FMA and store in another list
    scrks = [line for line in tab if "SCRK" in str(line)]            # segregate the testevents by SCRK and store in another list
    mergedlist = exas + fmas + scrks


# use the list_dict function and extract only recent test events for each telemetry source. \
# results are appended to a new list.
    if len(iloms) > 0:
        list1 = list_dict(iloms)
    if len(exas) > 0:
        list2 = list_dict(exas)
    if len(fmas) > 0:
        list3 = list_dict(fmas)
    if len(scrks) > 0:
        list4 = list_dict(scrks)

# list0 stores most recent single testevent for each telemetry source
    list0 = list1 + list2 + list3 + list4
    linebreaks(tserials, list0, test_event_list, linebreak2)


# >>> Getting The ASR Status of the assets
    try:
        asset_stat = []
        word1, word2 = "Asset serial number is not found in My Oracle Support. \
        Please contact Oracle Support Services.", "Serial not in MOS"
        word3, word4 = "Pending activation approval in My Oracle Support", "Pending MOS"
        word5, word6 = "ASR has been De-Activated.", "De-Activated"
        word7, word8 = "Asset serial number is not found in My Oracle Support. Please contact Oracle Support Services.", "Serial not in MOS"


        for serial in sumserials:
                with open(serial+".html") as html_file:
                        soup = BeautifulSoup(html_file, "lxml")
                        soupdata = soup.find_all('h3')
                        for eachline in soupdata:
                                status = eachline.text
                                status = status.replace("ASR Status:", "").replace(word1, word2)\
                                .replace(word3, word4).replace(word5, word6).replace(word7, word8)
                                line = serial+","+status
                                line = line.split(',')
                                if line not in asset_stat:
                                        asset_stat.append(line)
    except:
        pass

# >>> Extracting and creating the HeartbeatInfo table
    os.chdir(hbpath)  # change to hb directory to generate hb details
    tableinfo, heart, hbinfo, tt = [], {}, [], {}
    try:
        for serial in assetserials:
            table_rows = getTable(serial, 1).find_all('tr')
            thb = []
            for line in table_rows:
                line = str(line.find_all('td'))
                line = resub(hblist,"", line)
                line = line.replace("[","").replace("]","").strip().rstrip(',$')
                line = re.sub(",.*?,", "+", line)
                line = re.sub("\+.*$"," ", line)
                line = re.sub("\d\d:\d\d:\d\d","",line)
                if line not in thb:
                    thb.append(line)
                    heart[serial] = line
            heart[serial] = thb[0:8]
    except:
        pass
    try:
        for keys,values in heart.items():
            line = "{}:-> {}".format(keys, values)
            line = str(line).replace("],","  ").replace(",","").replace("'","")\
            .replace("[","").replace("]","")
            line = re.sub("\d\d:\d\d:\d\d","",line)
            if line not in hbinfo:
                    hbinfo.append(line)
    except:
        pass


# remove lines that contain ZFS assets from the ibinfo asset list
    #ibinfo = [line for line in ibinfo if ",ZS" not in line]
    lsmissinglist = printmissing(lsmissing, ibinfo)


    # removeing zfs from lsmissinglist, because zfs is never expected to be in the list_asset output.
    lsmissinglist  = [line for line in lsmissinglist if ",ZS" not in line]
    ibsmissinglist = printmissing(ibsmissing, assetinfo)



# ASR-Manager siteID extraction
    sid2serial = []                         # list will contain serial# - asrsiteID
    try:
        for line in conlist:                # check eachline in conlist
            line = line[0] +" "+ line[7]    # get serial#(index[0]) and siteID(index(6))
            if line not in sid2serial:      # check if serial + siteID combo exists in sid2serial list?
                sid2serial.append(line)     # if not append to the list
    except:
        pass

    # asrmsiteids list will hold unique asrm siteID(s)
    asrmsiteids = list(set([str(i.split()[1]) for i in sid2serial]))
    asrmsiteids = [item for item in asrmsiteids if any(re.findall("[0-9A-Z]{32}", item))]

    asrmlist, keyword = [], "Marked as container"
    k1, k2 = "No activation received", "No-activation-received"
    try:
        for item in asrmsiteids:
            r = requests.get(asrmlink + item).content
            with open(asrmpath + item + ".html", 'w+') as f:        # download the asrm related html file
                    f.write(r)                                      # write to sid.html file
    except:
        pass

    os.chdir(asrmpath)

    try:
        for serial in asrmsiteids:
            for line in conlist:
                if serial in line:
                    regemail = line[8]
                    break
            with open(serial + ".html", 'r') as filename:
                soup = BeautifulSoup(filename, 'lxml')
                for row in soup.find_all('tr'):
                    if "Marked as container" in str(row):
                        for tr in row.find_all('tr'):
                            if "Marked as container" in str(tr):
                                data = re.sub("<[^<]+?>"," ",str(tr))
                                data = re.sub('Marked as container.*$', '', str(data))
                                data = re.sub(serial, " "+serial+" ", str(data))
                                data = re.split(r'\s{2,}', data.strip())
                                d1, d2, d3 = data[10], data[12], data[13]
                                sline = str(d1 +","+ d2 +","+ d3 +","+ regemail).split(',')
                                if sline not in asrmlist:
                                    asrmlist.append(sline)
    except:
        pass


    asrsid = []                             # contains asr siteid value(s) w/o EM sids
    try:
        for line in conlist:
            if "EM AS" not in line:             # exclude lines that have EM entries
                sid = line[6]
    except:
        pass

    alen = len(asrsid)                      # get the length/how many actual asr sid's are present
    row = "{}#" * alen                      # will create placeholders * count of total sid's
    pholder = row.rstrip('#')

    asrmap = []                             # list will contain serial - asrsiteid - asrmhostname map
    try:
        for line in asrmlist:
            for row in sid2serial:
                if line[2] in str(row):         #line[2] is siteID
                    data = row +" "+line[0]     #line[0] is the asrm hostname
                    if data not in asrmap:
                        asrmap.append(data)
    except:
        pass


# >>> ASR Validation report
    record = []
    try:
        for i in assetserials:
            if i in cserials:
                #if i in str(list0):
                    row = "{}#{}#{}#{}#{}#{}#{}".format(i, get1(i), get2(i), get5(i), \
                    get3(i, iloms), get3(i, mergedlist), get4(i))
                    # adding entry for ASRM-Hostname
                    row1 = "{}".format(managerhn(i))
                    realrow = row +"#"+ row1
                    row = realrow.split('#')
                    if row not in record:
                        record.append(row)
    except:
        pass



# editing IB switches, SPARC row to reflect "NA" for OS testevents
# and "NA" for Exalocic or cloud machines
    try:
        for line in record:
            if "INFINIBAND" in str(line):
                line[5] = "NA"
                line[3] = "NA"
            if "SPARC" in line[1]:
                line[5] = "NA"
                line[3] = "NA"
    except:
        pass

    try:
        for line in record:
            if any(re.findall("Exalogic|Oracle Public Cloud", ibsys)):
                if "ZFS" not in str(line):
                    line[3] = "NA"
    except:
        pass


# Edit the ASR Validation report - make changes based on Product Catagoty!
    try:
        for line in record:
            if "Exalogic" in ibsys:
                if "ZFS" not in str(line):
                    line[5] = "NA"
            if "Oracle Public Cloud" in ibsys:
                if "ZFS" not in str(line):
                    line[5] = "NA"
            if "ZFS" in str(line):
                line[4] = "NA"
    except:
        pass

    # some zfs asset names will not be ZFS.. find out assets with SCRK as telemetry and
    # make necessary changes to ASR validation reprot
    try:
        for sl in scrksl:  # the assets that are actuall ZFS assets
            for line in record:
                if sl in line[0]:
                    line[2] = "NA"
                    line[4] = "NA"
                    line[3] = get5(sl)
                    line[5] = get3(sl, mergedlist)
    except:
        pass


# sorting eachlines in the record list
    report = [line for line in sorted(record)]

# get the max lenght in a List
    try:
        max5 = max([len(str(line)) for line in ibinfo])
        max4 = max([len(str(line)) for line in assetinfo])
        max3 = max([len(line) for line in hbinfo])
        max2 = max([len(str(line)) for line in test_event_list])
    except:
        pass


#>>>> report analysis
    report_msg, bullet, pma1, pma2 = [], ">>>> ", {}, []
    for line in asrmlist:
        if "localhost" in str(line):
            mgrsid = line[2]
            msg1 = "ASR-manager with siteID \"{}\" is set to localhost. See => Platinum Gateway hostname in ASR is set incorrectly to localhost (Doc ID 2106740.1)" .format(mgrsid)
            if msg1 not in report_msg:
                report_msg.append(bullet + msg1)
        #if "SW-ASR-REG" not in str(line):
        if not any(re.findall(r"SW-ASR-REG|prod-cta", str(line))):
            if not any(re.findall("EM|UNKNOWN", line[1], re.IGNORECASE)):
                mgreg = line[3]
                msg2 = "ASR-Manager is registerd with {}. Gateway needs to  be registered with SW-ASR-REG-07_US@oracle.com".format(mgreg)
                if msg2 not in report_msg:
                    report_msg.append(bullet + msg2)

    for line in record:
        if "De-Activated" in line[6]:
            sl = line[0]
            msg7 = "Asset is deactivated. Please check and re-activate " + sl
            report_msg.append(bullet + msg7)


    ilom_missing = check_missing(report, 4, 'None')
    os_missing = check_missing(report, 5, 'None')

    if len(ilom_missing) > 0:
        msg3 = "ILOM Testevents missing for the following asset(s):"
        report_msg.append(bullet + msg3)
        #report_msg.append(str(ilom_missing).strip('[]'))
        pri_list = " ".join(ilom_missing)
        report_msg.append(pri_list)


    if len(os_missing) > 0:
        msg4 = "ZFS/OS Testevents missing for the following asset(s):"
        report_msg.append(bullet + msg4)
        #report_msg.append(str(os_missing).strip('[]'))
        pri_list = " ".join(os_missing)
        report_msg.append(pri_list)


    assets_with_multi_asrm = []
    for line in record:
        asrmline = line[7].split(',')
        li = len(asrmline)
        if li > 1:
            assetsl = line[0]
            if assetsl not in assets_with_multi_asrm:
                assets_with_multi_asrm.append(assetsl)

    if len(assets_with_multi_asrm) > 0:
        msg5 = "Following Assets are activated with 2 or more ASR-managers:"
        report_msg.append(bullet + msg5)
        #report_msg.append(str(assets_with_multi_asrm).strip('[]'))
        pri_list = " ".join(assets_with_multi_asrm)
        report_msg.append(pri_list)


    snim_list = []
    for i in report:
        if "Serial not in MOS" in i[6]:
            ser = i[0]
            if ser not in snim_list:
                #print(ser)
                snim_list.append(ser)

    if len(snim_list) > 0:
        msg5 = "Please check with the MOS team as the serial number of these assets are not found in MOS:"
        report_msg.append(bullet + msg5)
        pri_list = " ".join(snim_list)
        report_msg.append(pri_list)


    try:
        if any(re.findall("Exadata|Zero Data", ibsys)):
            if len(os_source_missing1) > 0:
                msg6 = "These assets do not have EXADATA-SW,ADR Telemetry source enabled for ASR:"
                report_msg.append(bullet + msg6)
                pri_list = " ".join(os_source_missing1)
                report_msg.append(pri_list)
    except:
        pass


    # Find if any assets have duplicate ILOM telemetry sources
    ilom_dup_list = []
    get_dup_sources("ILOM", ilomconlist, ilom_dup_list)
    if len(ilom_dup_list) > 0:
        msg8 = "Please check these serial(s) as there may be duplicate ILOM sources:"
        report_msg.append(bullet + msg8)
        pri_list = " ".join(ilom_dup_list)
        report_msg.append(pri_list)

    # Find if any assets have duplicate EXADATA-SW,ADR telemetry sources
    exa_dup_list = []
    get_dup_sources("ILOM", ilomconlist, exa_dup_list)
    if len(ilom_dup_list) > 0:
        msg8 = "Please check these serial(s) as there may be duplicate ILOM sources:"
        report_msg.append(bullet + msg8)
        pri_list = " ".join(exa_dup_list)
        report_msg.append(pri_list)




# >>> write to file >>>
    #os.system('clear')
    with open(file_path1 +"/"+ dt + ".txt", "a") as f:
        f.write("=+" * 50 + "\n")
        f.write("SR-Number: " + str(srnum) + "\n")
        f.write("Start Time: " + str(start_time) + "\n")
        f.write("\n" * 4)

    try:
        if len(compare) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                for i in compare:
                    f.write(i + "\n")
                f.write("\n" * 4)

        if len(asrmlist) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write(tabulate(asrmlist, headers = header4))
                f.write("\n" * 4)
    except:
        pass
    try:
        if len(hbinfo) > 0:
            #dressup(max3, header3, hbinfo)
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write(header3 + "\n")
                f.write('-' * max3 + "\n")
                for line in hbinfo:
                    f.write(line+"\n")
                f.write("\n" * 4)
    except:
        pass
    try:

        if len(container_list) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write("ASSET INFORMATION\n")
                f.write(">" * 17 + "\n")
                f.write(tabulate(container_list, headers = header1))
                f.write("\n" * 4)
    except:
        pass
    try:
        if len(test_event_list) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write("TESTEVENTS\n")
                f.write(">" * 10 + "\n")
                f.write(tabulate(test_event_list, headers = header2))
                f.write("\n" * 4)
    except:
        pass
    try:
        if len(report) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write("ASR VALIDATION REPORT\n")
                f.write(">" * 21 + "\n")
                f.write(tabulate(report, headers = header5))
                f.write("\n" * 4)
    except:
        pass
    try:
        if len(lsmissinglist) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write(header7 + "\n")
                f.write('-' * max5 + "\n")
                for line in lsmissinglist:
                    f.write(line+"\n")
                f.write("\n" * 2)
    except:
        pass
    try:
        if len(ibsmissinglist) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write(header6 + "\n")
                f.write('-' * max4 + "\n")
                for line in ibsmissinglist:
                    f.write(line+"\n")
                f.write("\n" * 2)
    except:
        pass
    try:
        if len(report_msg) > 0:
            with open(file_path1 +"/"+ dt + ".txt", "a") as f:
                f.write("\n" + 'ACTION(S) REQUIRED:' + "\n>>>>>>>>>>>>>>>>>>>>\n")
                for line in report_msg:
                    f.write(line+"\n")
                f.write("\n" * 2)
    except:
        pass

    end_time = datetime.datetime.now().replace(microsecond=0)

    with open(file_path1 +"/"+ dt + ".txt", "a") as f:
        f.write("Execution Completed...." + "\n")

    with open(file_path1 +"/"+ dt + ".txt", "a") as f:
        f.write("End Time: " + str(end_time) + "\n")

        f.write("Time Elapsed: " + str(end_time-start_time)+ "\n")
        f.write("=+" * 50 + "\n")


    savedfilename = srnum + '.' + dt + '.report.log'
    output_file_name = srnum + '-out.html'

    # copy file output to /var/log/asrvalidationscript/3-xxxx DIR
    shutil.copy(file_path1 +"/"+ dt + ".txt", logdirectory + '/' + srnum + '/' + savedfilename)

    try:
        shutil.copy(file_path1 +"/"+ dt + ".txt", flask_templates_path + output_file_name)
    except:
        pass


    #for eachline in open(file_path1 +"/"+ dt + ".txt", "r").readlines():
    #    print(eachline.strip())

    #######################################################

    if not arg_sr:              # if an SR argument was passed during execution
        for eachline in open(file_path1 +"/"+ dt + ".txt", "r").readlines():
            print(eachline.strip())

        print("logs stored in Path: " + logdirectory  + srnum )
        print('\n' * 3)
        try:
            shutil.copy(file_path1 +"/"+ dt + ".txt", flask_templates_path + output_file_name)
        except:
            pass
    else:
        print("Script Completed! The logs stored in Path: " + logdirectory  + srnum )


    try:
        #file_content = ""
        flask_templates_path = "/opt/asrvalidationscript/templates/"
        in_file_name = flask_templates_path + srnum + "-out.html"
        out_file_name = flask_templates_path + srnum + "-out.html"

        # creating jinj2 template format for "out_file_name" file.
        with open(in_file_name, 'r') as f:
            global file_content
            file_content = f.read()

        with open(out_file_name, 'w') as r:
            r.write("{% extends \"layout.html\" %}")
            r.write("\n")
            r.write("{% block content %}")
            r.write("\n")
            r.write("<pre>")
            r.write("\n")

        with open(out_file_name, 'a') as r:
            for line in file_content:
                r.write(line)
            r.write("</pre>")
            r.write("\n")
            r.write("{% endblock content %}")
            r.write("\n")

        for serial in assetserials:
            os.system("sed -i 's/{}/{}#/g' {}"\
                .format(serial, serial, out_file_name))

        for serial in assetserials:
            os.system("sed -i 's/{}#/<a href=https:\/\/fems.us.oracle.com\/FEMSService\/resources\/femsservice\/femsview\/{} target=\"_blank\">{}<\/a>/g' {}"\
                .format(serial, serial, serial, out_file_name))

        os.system("sed -i 's/#//g' {}".format(out_file_name))
    except:
        pass


except Exception as e:
    print(e.__class__.__name__, e)
    print(e)
    print("Program interrupted or crashed!!")
    pass

finally:
    try:
        shutil.rmtree(scriptpath + srnum + dt)
    except:
        pass

