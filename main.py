# coding: utf-8
import urllib
from xml.dom import minidom
import xbmcgui
import os
import hashlib
from xbmcaddon import Addon
import xbmc

firmwareArray = []
firmware_nameArray = []
revision_dateArray = []
linkArray = []
md5Array = []

addonPath = Addon().getAddonInfo('path')
mediaPath = xbmc.translatePath(os.path.join(addonPath, 'resources/media/'))


def media_path_file(media_file):
    return mediaPath + media_file


OverlayBackground = media_path_file('background.png')
logoImage = media_path_file('Tofu-Linux-Logo-white.png')

ACTION_PREVIOUS_MENU = 10


class MainWindow(xbmcgui.Window):  # xbmcgui.Window): ##xbmcgui.Window

    def __init__(self, l=140, t=60, w=1000, h=560):
        super(MainWindow, self).__init__()
        self.background = OverlayBackground
        self.BG = xbmcgui.ControlImage(l, t, w, h, self.background, aspectRatio=0)  # ,colorDiffuse='0xFF3030FF')
        self.addControl(self.BG)
        l2 = 320
        t2 = 70
        w2 = 640
        h2 = 64
        self.logo = logoImage
        self.LOGO = xbmcgui.ControlImage(l2, t2, w2, h2, logoImage, aspectRatio=2)
        self.addControl(self.LOGO)
        self.show()
        mainmenu_selection()

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()


def lang_string(string_id):
    # Return string based on language and id
    return Addon().getLocalizedString(string_id)


def message_ok(message):
    # print dialogue window with OK button based on message
    dialog = xbmcgui.Dialog()
    dialog.ok(lang_string(32002), message)


def yesno_dialog(title, message):
    # display yesno dialog and return selection (true=yes, false=no)
    dialog = xbmcgui.Dialog()
    return dialog.yesno(title, message)


def find_childnode_by_name(parent, name):
    # Return parent childnode that match name
    for node in parent.childNodes:
        if node.nodeType == node.ELEMENT_NODE and node.localName == name:
            return node
    return None


def find_storage_based_on_device():
    # Return storage based on the device selected
    device = Addon().getSetting('device')
    if device == '1':
        return Addon().getSetting('XSstorage')
    elif device == '2':
        return Addon().getSetting('DSM3storage')
    elif device == '3':
        return str(int(Addon().getSetting('DSM1storage')) + 1)


def download_firmware_list(source):
    # Download firmware list and store relevant data in arrays
    try:
        response = urllib.urlopen(source)
        doc = minidom.parse(response)
        firmwares = doc.getElementsByTagName('Version')

        for firmware in firmwares:
            version_date = (firmware.getAttribute('Updated')[:-9])
            basic = find_childnode_by_name(firmware, 'Basic')
            firmware_nameArray.append(basic.getAttribute('name'))
            firmwareArray.append(basic.getAttribute('name') + lang_string(32003) + version_date)
            linkArray.append(basic.getAttribute('URL'))
            md5Array.append(basic.getAttribute('MD5'))

    except:
        message_ok(lang_string(32030))


def firmware_download_location():
    # return location to save the downloaded firmware and filename
    download_location = find_storage_based_on_device()
    if download_location == '0':  # cache selected
        return '/recovery/update.img'
    elif download_location == '1':  # Sdcard selected
        return mount_location('/dev/cardblksd1') + '/update.img'
    else:
        return mount_location('/dev/sdb5') + '/marcel/update.img'  # USB Storage


def downloader(url, dest):
    # download file and display progress in dialog progress window
    dp = xbmcgui.DialogProgress()
    dp.create(lang_string(32004), lang_string(32005), url)
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
        os.remove(firmware_download_location())
        message_ok(lang_string(32031))
        quit()


def firmware_location_onreboot():
    # return the firmware location on reboot recovery
    reboot_firmware_location = find_storage_based_on_device()
    if reboot_firmware_location == '0':  # cache selected
        return 'cache'
    elif reboot_firmware_location == '1':  # Sdcard selected
        return 'sdcard'
    else:
        return 'udisk'


def mount_location(dev):
    # This function will return the mount location of dev
    p = os.popen("df | grep '" + dev + "' | grep -oE '[^ ]+$' | head -n1")
    return p.read().replace("\n", "")


def recover_command(menu_selection):
    # Construct recovery command and reboot pivos device
    shell_command = ':'
    if menu_selection == 0:
        # issue shell command to install selected firmware and reset to factory settings if specify in the setting file.
        storage = firmware_location_onreboot()
        if Addon().getSetting('factoryReset') == 'true':
            shell_command = 'echo -e "--update_package=/' + storage + '/update.img\n--wipe_cache\n--wipe_data" > /recovery/recovery/command || exit 1'
        else:
            shell_command = 'echo -e "--update_package=/' + storage + '/update.img\n--wipe_cache" > /recovery/recovery/command || exit 1'
    elif menu_selection == 1:
        if yesno_dialog("Pivos Maintenance", "Wipe Pivos device cache and data (Factory Reset)?"):
            shell_command = 'echo -e "--wipe_data\n--wipe_cache\n" > /recovery/recovery/command || exit 1'
    elif menu_selection == 2:
        if yesno_dialog("Pivos Maintenance Tool", "Wipe Pivos device cache?"):
            shell_command = 'echo -e "--wipe_cache\n" > /recovery/recovery/command || exit 1'
    elif menu_selection == 3:
        if yesno_dialog("Pivos Maintenance Tool", "Reboot Pivos device in recovery mode?"):
            try:
                os.remove('/recovery/recovery/command')
            except OSError:
                pass

    result = os.system(shell_command)
    if result == 0 and shell_command != ':':
        dialog = xbmcgui.Dialog()
        dialog.notification(lang_string(32009), lang_string(32016), icon=xbmcgui.NOTIFICATION_INFO, time=3000)
        shell_command = 'reboot recovery'
        os.system(shell_command)
    if result != 0:
        message_ok(lang_string(32033))


def md5(fname):
    # return md5 of the file fname
    dp_md5 = xbmcgui.DialogProgress()
    message = lang_string(32017)
    dp_md5.create(lang_string(32018), message)
    file_size = os.path.getsize(fname)
    step_size = round(file_size / 409600)
    percent = 0
    count = 0
    file_hash = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            file_hash.update(chunk)
            dp_md5.update(percent)
            count += 1
            if count > step_size and percent < 100:
                percent += 1
                count = 0
    dp_md5.close()
    return file_hash.hexdigest()


def firmware_update(selection):
    # control the firmware selected installation
    dialog = xbmcgui.Dialog()
    message = firmwareArray[selection] + lang_string(32006)
    runscript = dialog.yesno(lang_string(32002), message)

    if runscript and Addon().getSetting('factoryReset') == 'true':
        runscript = dialog.yesno(lang_string(32007), lang_string(32008))

    if runscript:
        download_file = firmware_download_location()
        downloader(linkArray[selection], download_file)
        if md5(download_file) != md5Array[selection]:
            # display error message
            message_ok(lang_string(32036))
        else:
            dialog = xbmcgui.Dialog()
            dialog.notification(lang_string(32019), lang_string(32020), icon='', time=3000)
            recover_command(0)


def check_hardware():
    # Check hardware to determine correct firmware list link and device
    device = Addon().getSetting('device')
    if device == '1':
        return 'http://update.pivosgroup.com/linux/mx/update.xml'
    elif device == '2':
        return 'http://update.pivosgroup.com/linux/m3/update.xml'
    elif device == '3':
        return 'http://update.pivosgroup.com/linux/m1/update.xml'
    else:
        message_ok(lang_string(32035))
        Addon().openSettings()
        return ''


def mainmenu_selection():
    """ Create main menu  """
    mainmenu_items = [lang_string(32051), lang_string(32052), lang_string(32053), lang_string(32054), lang_string(32055)]
    while True:
        # display menu in a dialogue for selection. selectedMenuItem = position of selection
        selected_menu_item = xbmcgui.Dialog().select(lang_string(32050), mainmenu_items)

        if selected_menu_item == 0:  # Install firmware selected
            # clear firmwareArray
            del firmwareArray[:]
            # firmware update.xml URL
            imagelist_link = check_hardware()

            # download firmware list for selection
            if imagelist_link != '':
                download_firmware_list(imagelist_link)

                # display firmware list in a dialogue for selection. ret = position of selection
                ret = xbmcgui.Dialog().select(lang_string(32001), firmwareArray)  #

                if ret == -1:  # no selection was made just quit
                    continue
                else:
                    # proceed with firmware installation based on firmware selected.
                    firmware_update(ret)

        elif selected_menu_item == 4 or selected_menu_item == -1:  # exit or no selection made
            break
        else:
            recover_command(selected_menu_item)

if __name__ == "__main__":
    # instantiate main window
    mydisplay = MainWindow()
    # remove main window
    del mydisplay
    quit()
