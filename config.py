import os
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--configdir', dest='configdir',
                    help='specify a config directory (it must exist), if config directory is not specified, defaults to $HOME/.gcm')
args = parser.parse_args()


class Config(object):
    WORD_SEPARATORS = "-A-Za-z0-9,./?%&#:_=+@~"
    BUFFER_LINES = 200000
    STARTUP_LOCAL = True
    CONFIRM_ON_EXIT = True
    FONT_COLOR = ""
    BACK_COLOR = ""
    TRANSPARENCY = 0
    PASTE_ON_RIGHT_CLICK = 1
    CONFIRM_ON_CLOSE_TAB = 0
    AUTO_CLOSE_TAB = 0
    COLLAPSED_FOLDERS = ""
    LEFT_PANEL_WIDTH = 100
    CHECK_UPDATES = False
    WINDOW_WIDTH = -1
    WINDOW_HEIGHT = -1
    FONT = ""
    HIDE_DONATE = False
    AUTO_COPY_SELECTION = 0
    LOG_PATH = os.path.expanduser("~")
    SHOW_TOOLBAR = True
    SHOW_PANEL = True
    VERSION = 0

    def __init__(self):
        self._CONFIG_DIR = None
        self._CONFIG_FILE = None
        self.KEY_FILE = None
        self.DEFAULT_CONFIG_FILE = "gcm.conf"
        self.DEFAULT_KEY_FILE = ".gcm.key"
        self.configdir = self.get_config_dir()
        self.config_file = self.get_config_file()
        self.key_file = self.get_key_file()

    def get_config_dir(self):
        """
        find the config directory

        will not create a directory that is passed from the command line

        defaults to $HOME/.gcm
        """
        global args
        global parser


        if args.configdir:
            if os.path.exists(args.configdir):
                self.configdir = args.configdir
            else:
                thelp = parser.format_usage()
                thelp = thelp + '\n' + "Config directory does not exist"
                thelp = thelp + '\n    ' + args.configdir

                print thelp
                sys.exit(1)
        else:
            self.configdir = os.path.join(os.getenv("HOME"), ".gcm")
            if not os.path.exists(self.configdir):
                os.makedirs(self.configdir)
        return self.configdir

    def get_config_file(self):
        return os.path.join(self.configdir, self.DEFAULT_CONFIG_FILE)

    def get_key_file(self):
        return os.path.join(self.configdir, self.DEFAULT_KEY_FILE)
