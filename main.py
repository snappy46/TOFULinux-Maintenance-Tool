# coding: utf-8
import urllib
from xml.dom import minidom
import xbmcgui
import os
import hashlib
from xbmcaddon import Addon
import xbmc

#Devices constant
PIVOS_XS = 0
PIVOS_DSM3 = 1
PIVOS_DSM1 = 2
UNKNOWN_DEVICE = -1

#Download location constant
CACHE_DOWNLOAD = 0
SDCARD_DOWNLOAD = 1
USB_DOWNLOAD = 2
UNKNOWN_DOWNLOAD = -1

ACTION_PREVIOUS_MENU = 10

# Global variables
firmwareId = []
firmwareArray = []
revision_dateArray = []
linkArray = []
md5Array = []
internet_is_available = False
device = UNKNOWN_DEVICE
detected_device = UNKNOWN_DEVICE
factory_reset = False
firmware_download_location = UNKNOWN_DOWNLOAD

addonPath = Addon().getAddonInfo('path')
mediaPath = xbmc.translatePath(os.path.join(addonPath, 'resources/media/'))


def media_path_file(media_file):
    return mediaPath + media_file


OverlayBackground = media_path_file('background.png')
logoImage = media_path_file('Tofu-Linux-Logo-white.png')


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
        self.strAction = xbmcgui.ControlLabel(160, 570, 600, 200, '', 'font12', '0xFFEE862A')
        self.addControl(self.strAction)
        self.strAction.setLabel('Installed Firmware:')
        self.strAction = xbmcgui.ControlLabel(330, 570, 600, 200, '', 'font12', '0xFFFFFFFF')
        self.addControl(self.strAction)
        self.strAction.setLabel(convert_version_to_name())
        self.strAction = xbmcgui.ControlLabel(180, 590, 600, 200, '', 'font12', '0xFFEE862A')
        self.addControl(self.strAction)
        self.strAction.setLabel('Latest Firmware:')
        self.strAction = xbmcgui.ControlLabel(330, 590, 600, 200, '', 'font12', '0xFFFFFFFF')
        self.addControl(self.strAction)
        self.strAction.setLabel(get_latest_firmware())
        self.show()
        mainmenu_selection()

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()


class DownloadCancelled(Exception):
    pass


def lang_string(string_id):
    # Return string based on language and id
    return Addon().getLocalizedString(string_id)


def device_to_string(device):
    if device == PIVOS_XS:
        return "Pivos XS"
    elif device == PIVOS_DSM3:
        return "Pivos DS M3"
    elif device == PIVOS_DSM1:
        return "Pivos DS M1"
    else:
        return "Unknown"


def download_location_to_string(location):
    if location == CACHE_DOWNLOAD:
        return "Cache"
    elif location == SDCARD_DOWNLOAD:
        return "SDCard"
    elif location == USB_DOWNLOAD:
        return "USB"
    else:
        return "Unknown"


def get_latest_firmware():
    # return latest firmware if available.
    if firmwareArray:
        return firmwareArray[0]
    else:
        return "Unavailable"


def convert_version_to_name():
    # return firmware name based on current build date.
    build_date = get_build_date()
    count = 0
    for firmware in firmwareId:
        if build_date in firmware:
            return firmwareArray[count]
        count += 1
    return build_date


def get_build_date():
    # return current version based on /etc/build.id, return unknown if file not found.
    p = os.popen("cat /home/marcel/build.id")
    build_date = p.read().replace("\n", "")
    if build_date == "":
        return "Unknown"
    else:
        return build_date


def get_device_type():
    # return current device type based on etc/hostname
    global detected_device
    p = os.popen("cat /home/marcel/hostname")
    device_type = p.read().replace("\n", "")
    if device_type != "":
        if device_type == "pivos-xs":
            detected_device = PIVOS_XS
            return PIVOS_XS
        elif device_type == "pivos-m3":
            detected_device = PIVOS_DSM3
            return PIVOS_DSM3
        elif device_type == "pivos-m1":
            detected_device = PIVOS_DSM1
            return PIVOS_DSM1
        else:
            detected_device = UNKNOWN_DEVICE
            return UNKNOWN_DEVICE


def message_ok(message):
    # print dialogue window with OK button based on message
    dialog = xbmcgui.Dialog()
    dialog.ok(lang_string(32002), message)


def yesno_dialog(title, message):
    # display yesno dialog and return selection (true=yes, false=no)
    dialog = xbmcgui.Dialog()
    return dialog.yesno(title, message)


def find_storage_based_on_device():
    # Return storage based on the device selected
    if device == PIVOS_XS:
        return int(Addon().getSetting('XSstorage'))
    elif device == PIVOS_DSM3:
        return int(Addon().getSetting('DSM3storage'))
    elif device == PIVOS_DSM1:
        return int(Addon().getSetting('DSM1storage')) + 1


def download_firmware_list(source):
    # Download firmware list and store relevant data in arrays
    global internet_is_available
    try:
        response = urllib.urlopen(source)
        doc = minidom.parse(response)
        firmwares = doc.getElementsByTagName('Version')
        response.close()

        for firmware in firmwares:
          #  version_date = (firmware.getAttribute('Updated')[:-9])
            basic = firmware.getElementsByTagName('Basic')[0]
          #  firmwareArray.append(basic.getAttribute('name') + lang_string(32003) + version_date)
            firmwareId.append(basic.getAttribute('id'))
            firmwareArray.append(basic.getAttribute('name'))
            linkArray.append(basic.getAttribute('URL'))
            md5Array.append(basic.getAttribute('MD5'))
        internet_is_available = True
        return True

    except:
        internet_is_available = False
        message_ok(lang_string(32030))
        return False


def get_firmware_download_location(selected_download_location):
    # return location to save the downloaded firmware and filename
    #download_location = find_storage_based_on_device()
    if selected_download_location == CACHE_DOWNLOAD:  # cache selected
        return '/recovery/update.img'
    elif selected_download_location == SDCARD_DOWNLOAD:  # Sdcard selected
        return mount_location('/dev/cardblksd1') + '/update.img'
    elif selected_download_location == USB_DOWNLOAD:
        return mount_location('/dev/sdb5') + '/marcel/update.img'  # USB Storage
    else:
        return ""


# def firmware_download_location():
#     # return location to save the downloaded firmware and filename
#     download_location = find_storage_based_on_device()
#     if download_location == '0':  # cache selected
#         return '/recovery/update.img'
#     elif download_location == '1':  # Sdcard selected
#         return mount_location('/dev/cardblksd1') + '/update.img'
#     else:
#         return mount_location('/dev/sdb5') + '/marcel/update.img'  # USB Storage

def user_default_selection():
   # return true if firmware install should use addon setting default.
   return yesno_dialog("Firmware Installation", "Use addon default settings?")


def firmware_install_using_settings_values():
    # set firmware install global variables to addon settings values.
    global device
    global factory_reset
    global firmware_download_location
    device = int(Addon().getSetting('device')) - 1
    factory_reset = True if Addon().getSetting('factoryReset') == "true" else False
    firmware_download_location = find_storage_based_on_device()


def display_list_of_device():
   #display devices in a dialogue for selection. Device_Menu_Item = position of selection
    global device
    device = xbmcgui.Dialog().select("Select device", ['Pivos XS', 'Pivos DS M3', 'Pivos DS M1'])
    if device <= 2:
       return True
    else:
       return False


def set_device():
    # set device to detected device or allow user selection.
    global device
    if yesno_dialog("Device confirmation", device_to_string(detected_device) + " was detected.\n\nIs this correct?"):
        device = detected_device
    else:
        if not display_list_of_device():
            message_ok("Error", "Something went wrong")


def set_factory_reset():
    # prompt user for factory reset option.
    global factory_reset
    factory_reset = yesno_dialog("Factory Reset", "Perform a device factory reset")


def create_download_location_list():
    # return download location list based on device
    download_list = []
    if device < 2:
        download_list.append("Cache")
    download_list.append("SDCard")
    if device == 0 or device == 2:
        download_list.append("USB")
    return download_list


def set_download_location():
    # prompt user for firmware download location.
    global firmware_download_location
    firmware_download_location = xbmcgui.Dialog().select("Select download location", create_download_location_list())
    if device == PIVOS_DSM1:
        # account for list offset when using DSM1 since it does not have cache option
        firmware_download_location += 1


def confirm_entered_information():
    # return True if user confirm that information is correct.
    message = "Device selected: " + device_to_string(device) + "\n"
    message += "Factory reset: "
    message += 'Yes\n' if factory_reset else 'No\n'
    message += "Download location: " + download_location_to_string(firmware_download_location) + "\n\n"
   # message += "Select 'Yes' to proceed with firmware installation."
    return yesno_dialog("Confirm Information Entered", message)


def downloader(url, dest):
    # download file and display progress in dialog progress window
    dp = xbmcgui.DialogProgress()
    dp.create(lang_string(32004), lang_string(32005), url)
    try:
        urllib.urlretrieve(url, dest, lambda nb, bs, fs, url=url: _pbhook(nb, bs, fs, url, dp))
        return True
    except DownloadCancelled:
        return False


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
        try:
            os.remove(firmware_download_location())
        except OSError:
            pass
        message_ok(lang_string(32031))
        raise DownloadCancelled


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
        if downloader(linkArray[selection], download_file):
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


def get_firmware_url(device):
    # return firmware url based on the device
    if device == PIVOS_XS:
        return 'http://update.pivosgroup.com/linux/mx/update.xml'
    elif device == PIVOS_DSM3:
        return 'http://update.pivosgroup.com/linux/m3/update.xml'
    elif device == PIVOS_DSM1:
        return 'http://update.pivosgroup.com/linux/m1/update.xml'
    else:
        return ''


def install_firmware():
    # firmware installation preliminary setup
    if user_default_selection():
        firmware_install_using_settings_values()
    else:
        set_device()
        set_factory_reset()
        set_download_location()
    if confirm_entered_information():
        message_ok("Everything seems to work")
    else:
        message_ok("nothing seems to work")


def clean_library():
    # clean video and music database
    librarymenu_items = [lang_string(32061), lang_string(32062), lang_string(32063)]
    selection = xbmcgui.Dialog().select(lang_string(32060), librarymenu_items)
    if selection == 0:
        xbmc.executebuiltin('cleanlibrary(video)')
    elif selection == 1:
        xbmc.executebuiltin('cleanlibrary(music)')
    else:
        return


def get_mainmenu_list ():
    # return list to be used by main menu.
    menulist = []
    if internet_is_available:
        menulist.append(lang_string(32051))
    else:
        menulist.append("Firmware installation (Not Available)")
    menulist.append(lang_string(32052))
    menulist.append(lang_string(32053))
    menulist.append(lang_string(32054))
    menulist.append(lang_string(32055))
    menulist.append(lang_string(32056))
    return menulist


def mainmenu_selection():
    """ Create main menu  """
    mainmenu_items = get_mainmenu_list()
    while True:
        # display menu in a dialogue for selection. selectedMenuItem = position of selection
        selected_menu_item = xbmcgui.Dialog().select(lang_string(32050), mainmenu_items)

        if selected_menu_item == 0:  # Install firmware selected
            if internet_is_available:
                # clear firmwareArray
           #     del firmwareArray[:]
                # firmware update.xml URL
           #     imagelist_link = check_hardware()

                # download firmware list for selection
            #    if imagelist_link != '':
             #       if download_firmware_list(imagelist_link):
                        # display firmware list in a dialogue for selection. ret = position of selection
                        ret = xbmcgui.Dialog().select(lang_string(32001), firmwareArray)  #

                        if ret == -1:  # no selection was made just quit
                            continue
                        else:
                            # proceed with firmware installation based on firmware selected.
                           # firmware_update(ret)
                            install_firmware()
            else:
                continue

        elif selected_menu_item == 4: clean_library()  #clean library selected

        elif selected_menu_item == 5 or selected_menu_item == -1:  # exit or no selection made
            break
        else:
            recover_command(selected_menu_item)

if __name__ == "__main__":
    # Get current firmware list for device and setup initial global variable
    download_firmware_list(get_firmware_url(get_device_type()))

    # instantiate main window
    mydisplay = MainWindow()
    # remove main window
    del mydisplay
    quit()
