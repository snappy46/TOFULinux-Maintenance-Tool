# coding: utf-8
import urllib
from xml.dom import minidom
import xbmcgui
import os
import subprocess
import hashlib
from xbmcaddon import Addon
import xbmc

firmwareArray = []
linkArray = []
md5Array = []
webfile = ""

addonPath=Addon().getAddonInfo('path')
mediaPath=xbmc.translatePath(os.path.join(addonPath,'resources/media/'))


def mediaPathFile(file):
    return mediaPath + file


OverlayBackground = mediaPathFile('background.png')
logoImage = mediaPathFile('Tofu-Linux-Logo-white.png')

ACTION_PREVIOUS_MENU = 10


class MainWindow(xbmcgui.Window):  # xbmcgui.Window): ##xbmcgui.Window

    def __init__(self,  L=140,T=60,W=1000,H=560):
        self.background = OverlayBackground
        self.BG = xbmcgui.ControlImage(L,T,W,H,self.background,aspectRatio=0) #,colorDiffuse='0xFF3030FF')
        self.addControl(self.BG)
        L2=320; T2=70; W2=640; H2=64
        self.logo = logoImage
        self.LOGO = xbmcgui.ControlImage(L2, T2, W2, H2,logoImage,aspectRatio=0)
        self.addControl(self.LOGO)
        self.show()
        mainMenuSelection()

    def onAction(self, action):
      if action == ACTION_PREVIOUS_MENU:
        self.close()


def langString(id):
    # Return string based on language and id
    return Addon().getLocalizedString(id)


def messageOK(message):
    # print dialogue window with OK button based on message
    dialog = xbmcgui.Dialog()
    dialog.ok(langString(32002), message)


def yesnoDialog(title, message):
    # display yesno dialog and return selection (true=yes, false=no)
    dialog = xbmcgui.Dialog()
    return dialog.yesno(title, message)


def findChildNodeByName(parent, name):
    # Return parent childnode that match name
    for node in parent.childNodes:
        if node.nodeType == node.ELEMENT_NODE and node.localName == name:
            return node
    return None


def findStorageBasedOnDevice():
    # Return storage based on the device selected
    device = Addon().getSetting('device')
    if device == '1':
        return Addon().getSetting('XSstorage')
    elif device == '2':
        return Addon().getSetting('DSM3storage')
    elif device == '3':
        return str(int(Addon().getSetting('DSM1storage')) + 1)


def downloadFirmwareList(source):
    # Download firmware list and store relevant data in arrays
    try:
        response = urllib.urlopen(source)
        doc = minidom.parse(response)
        firmwares = doc.getElementsByTagName('Version')

        for firmware in firmwares:
            versionDate = firmware.getAttribute('Updated')
            basic = findChildNodeByName(firmware, 'Basic')
            firmwareArray.append(basic.getAttribute('name') + langString(32003) + versionDate)
            linkArray.append(basic.getAttribute('URL'))
            md5Array.append(basic.getAttribute('MD5'))

    except:
        messageOK(langString(32030))


def firmwareDownloadLocation():
    # return location to save the downloaded firmware and filename
    downloadLocation = findStorageBasedOnDevice()
    if downloadLocation == '0': #cache selected
        return '/recovery/update.img'
    elif downloadLocation == '1': #Sdcard selected
        return mountLocation('/dev/cardblksd1') + '/update.img'
    else:
        return mountLocation('/dev/sdb5') + '/marcel/update.img' #USB Storage


def DownloaderClass(url, dest):
    # download file and display progress in dialog progress window
    dp = xbmcgui.DialogProgress()
    dp.create(langString(32004), langString(32005), url)
    urllib.urlretrieve(url, dest, lambda nb, bs, fs, url=url: _pbhook(nb, bs, fs, url, dp))


def _pbhook(numblocks, blocksize, filesize, url=None, dp=None):
    try:
        percent = min((numblocks * blocksize * 100) / filesize, 100)
        print percent
        dp.update(percent)
    except:
        percent = 100
        dp.update(percent)
        dp.close()
    if dp.iscanceled():
        dp.close()
        os.remove(firmwareDownloadLocation())
        messageOK(langString(32031))
        quit()


def firmwareLocationOnReboot():
    # return the firmware location on reboot recovery
    rebootFirmwareLocation = findStorageBasedOnDevice()
    if rebootFirmwareLocation == '0': #cache selected
        return 'cache'
    elif rebootFirmwareLocation == '1': #Sdcard selected
        return 'sdcard'
    else:
        return 'udisk'


def mountLocation(dev):
    # This function will return the mount location of dev
    p = os.popen("df | grep '" + dev + "' | grep -oE '[^ ]+$' | head -n1")
    return p.read().replace("\n", "")


def recoverCommand(menuSelection):
    # Construct recovery command and reboot pivos device
    shellCommand = ':'
    if menuSelection == 0 :
        # issue shell command to install selected firmware and reset to factory settings if specify in the setting file.
        storage = firmwareLocationOnReboot()
        if Addon().getSetting('factoryReset') == 'true':
            shellCommand = 'echo -e "--update_package=/' + storage + '/update.img\n--wipe_cache\n--wipe_data" > /recovery/recovery/command || exit 1'
        else:
            shellCommand = 'echo -e "--update_package=/' + storage + '/update.img\n--wipe_cache" > /recovery/recovery/command || exit 1'
    elif menuSelection == 1:
        if yesnoDialog("Pivos Maintenance", "Wipe Pivos device cache and data (Factory Reset)?"):
            shellCommand = 'echo -e "--wipe_data\n--wipe_cache\n" > /recovery/recovery/command || exit 1'
    elif menuSelection == 2:
        if yesnoDialog("Pivos Maintenance Tool", "Wipe Pivos device cache?"):
            shellCommand = 'echo -e "--wipe_cache\n" > /recovery/recovery/command || exit 1'
    elif menuSelection == 3:
        if yesnoDialog("Pivos Maintenance Tool", "Reboot Pivos device in recovery mode?"):
            try:
                os.remove('/recovery/recovery/command')
            except OSError:
                pass

    result = os.system(shellCommand)
    if result == 0 and shellCommand != ':':
        dialog = xbmcgui.Dialog()
        dialog.notification(langString(32009), langString(32016), icon='', time=3000)
        shellCommand = 'reboot recovery'
        os.system(shellCommand)
    if result != 0:
        messageOK(langString(32033))


def md5(fname):
    # return md5 of the file fname
    dpMd5 = xbmcgui.DialogProgress()
    message = langString(32017)
    dpMd5.create(langString(32018), message)
    fileSize = os.path.getsize(fname)
    stepSize = round(fileSize/409600)
    percent = 0
    count = 0
    hash = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
            dpMd5.update(percent)
            count += 1
            if count > stepSize and percent < 100:
                percent += 1
                count = 0
    dpMd5.close()
    return hash.hexdigest()


def firmwareUpdate(message,downloadLink,md5Sum):
    # control the firmware selected installation
    dialog = xbmcgui.Dialog()
    message = message + langString(32006)
    runscript = dialog.yesno(langString(32002), message)

    if runscript and Addon().getSetting('factoryReset') == 'true':
        runscript = dialog.yesno(langString(32007), langString(32008))

    if runscript:
        downloadFile = firmwareDownloadLocation()
        DownloaderClass(downloadLink, downloadFile)
        if md5(downloadFile) <> md5Sum:
            # display error message
            messageOK(langString(32036))
        else:
            dialog = xbmcgui.Dialog()
            dialog.notification(langString(32019), langString(32020), icon='', time=3000)
            recoverCommand(0)


def checkHardware():
    # Check hardware to determine correct firmware list link and device
    device = Addon().getSetting('device')
    if device == '1':
        return 'http://update.pivosgroup.com/linux/mx/update.xml'
    elif device == '2':
        return 'http://update.pivosgroup.com/linux/m3/update.xml'
    elif device == '3':
        return 'http://update.pivosgroup.com/linux/m1/update.xml'
    else:
        messageOK(langString(32035))
        Addon().openSettings()
        return ''


def createMainMenuItems():
    # Create menu items
    mainMenuItems = []
    mainMenuItems.append(langString(32051))
    mainMenuItems.append(langString(32052))
    mainMenuItems.append(langString(32053))
    mainMenuItems.append(langString(32054))
    mainMenuItems.append(langString(32055))
    return mainMenuItems


def mainMenuSelection():
    while True:
        #display menu in a dialogue for selection. selectedMenuItem = position of selection
        selectedMenuItem = xbmcgui.Dialog().select(langString(32050), createMainMenuItems())

        if selectedMenuItem == 0: # Install firmware selected
            #clear firmwareArray
            del firmwareArray[:]
            # firmware update.xml URL
            imageListLink = checkHardware()

            # download firmware list for selection
            if imageListLink != '':
                downloadFirmwareList(imageListLink)

                # display firmware list in a dialogue for selection. ret = position of selection
                ret = xbmcgui.Dialog().select(langString(32001), firmwareArray)  #

                if ret == -1: #no selection was made just quit
                    continue
                else:
                    # proceed with firmware installation based on firmware selected.
                    firmwareUpdate(firmwareArray[ret], linkArray[ret], md5Array[ret])

        elif selectedMenuItem == 4 or selectedMenuItem == -1:  #exit or no selection made
            break
        else:
            recoverCommand(selectedMenuItem)

# instanciate main window
mydisplay = MainWindow()

# remove main window
del mydisplay

quit()