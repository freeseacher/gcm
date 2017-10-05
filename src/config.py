# -*- coding: UTF-8 -*-
import base64
import os
import sys
import argparse
from operator import xor

import pyaes
import vte

from src.whost import Host
from utils import msgbox

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
        self.DEFAULT_CONFIG_FILE = "gcm2.conf"
        self.DEFAULT_KEY_FILE = ".gcm2.key"
        self.configdir = self.get_config_dir()
        self.config_file = self.get_config_file()
        self.key_file = self.get_key_file()
        self.enc_passwd = ''

        if Config.VERSION == 0:
            self.initialise_encryption_key()

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

    def load_encryption_key(self):
        try:
            if os.path.exists(self.key_file):
                with open(self.key_file) as f:
                    self.enc_passwd = f.read()
            else:
                self.initialise_encryption_key()
        except:
            msgbox("Error trying to open key_file")
            vars.enc_passwd = ''

    def initialise_encryption_key(self):
        import uuid
        uid = uuid.uuid4()
        self.enc_passwd = uid.hex
        try:
            with os.fdopen(os.open(self.key_file, os.O_WRONLY | os.O_CREAT, 0600), 'w') as f:
                f.write(self.enc_passwd)
        except:
            msgbox("Error initialising key_file")

    def get_val(self, cp, section, name, default):
        try:
            return cp.get(section, name) if type(default) != type(True) else cp.getboolean(section, name)
        except:
            return default

    def load_host_from_ini(self, cp, section, pwd=''):
        group = cp.get(section, "group")
        name = cp.get(section, "name")
        host = cp.get(section, "host")
        user = cp.get(section, "user")
        tpw = cp.get(section, "pass")
        if tpw:
            password = self.decrypt(self.enc_passwd, tpw)
        else:
            password = ''
        description = self.get_val(cp, section, "description", "")
        private_key = self.get_val(cp, section, "private_key", "")
        port = self.get_val(cp, section, "port", "22")
        tunnel = self.get_val(cp, section, "tunnel", "")
        ctype = self.get_val(cp, section, "type", "ssh")
        commands = self.get_val(cp, section, "commands", "").replace('\x00', '\n')
        keepalive = self.get_val(cp, section, "keepalive", "")
        fcolor = self.get_val(cp, section, "font-color", "")
        bcolor = self.get_val(cp, section, "back-color", "")
        x11 = self.get_val(cp, section, "x11", False)
        agent = self.get_val(cp, section, "agent", False)
        compression = self.get_val(cp, section, "compression", False)
        compressionLevel = self.get_val(cp, section, "compression-level", "")
        extra_params = self.get_val(cp, section, "extra_params", "")
        log = self.get_val(cp, section, "log", False)
        backspace_key = int(self.get_val(cp, section, "backspace-key", int(vte.ERASE_AUTO)))
        delete_key = int(self.get_val(cp, section, "delete-key", int(vte.ERASE_AUTO)))
        h = Host(group, name, description, host, user, password, private_key, port, tunnel, ctype, commands, keepalive,
                 fcolor, bcolor, x11, agent, compression, compressionLevel, extra_params, log, backspace_key,
                 delete_key)
        return h

    def save_host_to_ini(self, cp, section, host, pwd=''):

        cp.set(section, "group", host.group)
        cp.set(section, "name", host.name)
        cp.set(section, "description", host.description)
        cp.set(section, "host", host.host)
        cp.set(section, "user", host.user)
        if host.password:
            cp.set(section, "pass", self.encrypt(self.enc_passwd, host.password))
        else:
            cp.set(section, "pass", "")
        cp.set(section, "private_key", host.private_key)
        cp.set(section, "port", host.port)
        cp.set(section, "tunnel", host.tunnel_as_string())
        cp.set(section, "type", host.type)
        cp.set(section, "commands", host.commands.replace('\n', '\x00'))
        cp.set(section, "keepalive", host.keep_alive)
        cp.set(section, "font-color", host.font_color)
        cp.set(section, "back-color", host.back_color)
        cp.set(section, "x11", host.x11)
        cp.set(section, "agent", host.agent)
        cp.set(section, "compression", host.compression)
        cp.set(section, "compression-level", host.compressionLevel)
        cp.set(section, "extra_params", host.extra_params)
        cp.set(section, "log", host.log)
        cp.set(section, "backspace-key", host.backspace_key)
        cp.set(section, "delete-key", host.delete_key)

    def encrypt_old(self, passw, string):
        try:
            ret = xor(passw, string)
            s = base64.b64encode("".join(ret))
        except:
            s = ""
        return s


    def decrypt_old(self, passw, string):
        try:
            ret = xor(passw, base64.b64decode(string))
            s = "".join(ret)
        except:
            s = ""
        return s


    def encrypt(self, passw, string):
        aes = pyaes.AESModeOfOperationCTR(passw)
        try:
            s = aes.encrypt(string)
        except:
            s = ""
        return s


    def decrypt(self, passw, string):
        aes = pyaes.AESModeOfOperationCTR(passw)
        try:
            s = self.decrypt_old(passw, string) if Config.VERSION == 0 else aes.decrypt(string)
        except:
            s = ""
        return s

    def writeConfig(self):
        global groups

        cp = ConfigParser.RawConfigParser()
        conf = Config()
        cp.read(conf.config_file + ".tmp")

        cp.add_section("options")
        cp.set("options", "word-separators", Config.WORD_SEPARATORS)
        cp.set("options", "buffer-lines", Config.BUFFER_LINES)
        cp.set("options", "startup-local", Config.STARTUP_LOCAL)
        cp.set("options", "confirm-exit", Config.CONFIRM_ON_EXIT)
        cp.set("options", "font-color", Config.FONT_COLOR)
        cp.set("options", "back-color", Config.BACK_COLOR)
        cp.set("options", "transparency", Config.TRANSPARENCY)
        cp.set("options", "paste-right-click", Config.PASTE_ON_RIGHT_CLICK)
        cp.set("options", "confirm-close-tab", Config.CONFIRM_ON_CLOSE_TAB)
        cp.set("options", "font", Config.FONT)
        cp.set("options", "donate", Config.HIDE_DONATE)
        cp.set("options", "auto-copy-selection", Config.AUTO_COPY_SELECTION)
        cp.set("options", "log-path", Config.LOG_PATH)
        cp.set("options", "version", app_fileversion)
        cp.set("options", "auto-close-tab", Config.AUTO_CLOSE_TAB)

        collapsed_folders = ','.join(self.get_collapsed_nodes())
        cp.add_section("window")
        cp.set("window", "collapsed-folders", collapsed_folders)
        cp.set("window", "left-panel-width", self.hpMain.get_position())
        cp.set("window", "window-width", Config.WINDOW_WIDTH)
        cp.set("window", "window-height", Config.WINDOW_HEIGHT)
        cp.set("window", "show-panel", Config.SHOW_PANEL)
        cp.set("window", "show-toolbar", Config.SHOW_TOOLBAR)

        i = 1
        for grupo in groups:
            for host in groups[grupo]:
                section = "host " + str(i)
                cp.add_section(section)
                Config.save_host_to_ini(cp, section, host)
                i += 1

        cp.add_section("shortcuts")
        i = 1
        for s in shortcuts:
            if type(shortcuts[s]) == list:
                cp.set("shortcuts", shortcuts[s][0], s)
            else:
                cp.set("shortcuts", "shortcut%d" % (i), s)
                cp.set("shortcuts", "command%d" % (i), shortcuts[s].replace('\n', '\\n'))
                i = i + 1

        f = open(conf.config_file + ".tmp", "w")
        cp.write(f)
        f.close()
        os.rename(conf.config_file + ".tmp", conf.config_file)

