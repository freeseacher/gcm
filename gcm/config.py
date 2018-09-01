# -*- coding: UTF-8 -*-
import ConfigParser
import argparse
import base64
import os
import sys
from operator import xor

import pyaes
import vte

from gcm.models import Host
from utils import msgbox, SingletonMeta

from vars import app_fileversion, SSH_BIN, TEL_BIN, SHELL, SSH_COMMAND, DOMAIN_NAME, HSPLIT, VSPLIT, _COPY, _PASTE, \
    _COPY_ALL, _SAVE, _FIND, _CLEAR, _FIND_NEXT, _FIND_BACK, _CONSOLE_PREV, _CONSOLE_NEXT, _CONSOLE_CLOSE, \
    _CONSOLE_RECONNECT, _CONNECT, ICON_PATH, GLADE_DIR, _CONSOLE_1, _CONSOLE_2, _CONSOLE_3, _CONSOLE_4, \
    _CONSOLE_5, _CONSOLE_6, _CONSOLE_7, _CONSOLE_8, _CONSOLE_9

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--configdir', dest='configdir',
                    help='specify a config directory (it must exist), if config directory is not specified, defaults to $HOME/.gcm')
args = parser.parse_args()


class Config(object):
    __metaclass__ = SingletonMeta

    AUTO_CLOSE_TAB = 0
    AUTO_COPY_SELECTION = 0
    BACK_COLOR = ""
    BUFFER_LINES = 200000
    COLLAPSED_FOLDERS = ""
    CONFIRM_ON_CLOSE_TAB = 0
    CONFIRM_ON_EXIT = True
    FONT = ""
    FONT_COLOR = ""
    LEFT_PANEL_WIDTH = 100
    LOG_PATH = os.path.expanduser("~")
    PASTE_ON_RIGHT_CLICK = 1
    SHOW_PANEL = True
    SHOW_TOOLBAR = True
    STARTUP_LOCAL = True
    TRANSPARENCY = 0
    VERSION = 0
    WINDOW_HEIGHT = -1
    WINDOW_WIDTH = -1
    WORD_SEPARATORS = "-A-Za-z0-9,./?%&#:_=+@~"

    def __init__(self):
        self._CONFIG_DIR = None
        self._CONFIG_FILE = None
        self.KEY_FILE = None
        self.DEFAULT_CONFIG_FILE = "gcm2.conf"
        self.DEFAULT_KEY_FILE = ".gcm2.key"
        self.configdir = self.get_config_dir()
        self.config_file = self.get_config_file()
        self.key_file = self.get_key_file()
        self.groups = {}
        self.shortcuts = {}
        self.collapsed_folders = []
        self.hp_position = 100

        self.load_encryption_key()
        self.loadConfig()

    def get_config_dir(self):
        """
        find the config directory

        will not create a directory that is passed from the command line

        defaults to $HOME/.gcm
        """
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

    def load_host_from_ini(self, cp, section):
        group = cp.get(section, "group")
        name = cp.get(section, "name")
        host = cp.get(section, "host")
        user = cp.get(section, "user")
        tpw = cp.get(section, "pass")
        if tpw:
            password = self.decrypt(tpw)
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

    def save_host_to_ini(self, cp, section, host):

        cp.set(section, "group", host.group)
        cp.set(section, "name", host.name)
        cp.set(section, "description", host.description)
        cp.set(section, "host", host.host)
        cp.set(section, "user", host.user)
        if host.password:
            cp.set(section, "pass", self.encrypt(host.password))
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

    def encrypt(self, string):
        aes = pyaes.AESModeOfOperationCTR(self.enc_passwd)
        try:
            s = aes.encrypt(string)
        except:
            s = ""
        return base64.b64encode(s)

    def decrypt(self, string):
        aes = pyaes.AESModeOfOperationCTR(self.enc_passwd)
        try:
            if self.VERSION == 0:
                s = self.decrypt_old(self.enc_passwd, string)
            else:
                s = base64.b64decode(string)
                s = aes.decrypt(s)
        except:
            s = ""
        return s

    def writeConfig(self, **kwargs):
        cp = ConfigParser.RawConfigParser()
        cp.read(self.config_file + ".tmp")

        cp.add_section("options")
        cp.set("options", "word-separators", self.WORD_SEPARATORS)
        cp.set("options", "buffer-lines", self.BUFFER_LINES)
        cp.set("options", "startup-local", self.STARTUP_LOCAL)
        cp.set("options", "confirm-exit", self.CONFIRM_ON_EXIT)
        cp.set("options", "font-color", self.FONT_COLOR)
        cp.set("options", "back-color", self.BACK_COLOR)
        cp.set("options", "transparency", self.TRANSPARENCY)
        cp.set("options", "paste-right-click", self.PASTE_ON_RIGHT_CLICK)
        cp.set("options", "confirm-close-tab", self.CONFIRM_ON_CLOSE_TAB)
        cp.set("options", "font", self.FONT)
        cp.set("options", "auto-copy-selection", self.AUTO_COPY_SELECTION)
        cp.set("options", "log-path", self.LOG_PATH)
        cp.set("options", "version", app_fileversion)
        cp.set("options", "auto-close-tab", self.AUTO_CLOSE_TAB)

        collapsed_folders = ','.join(kwargs.get('collapsed_nodes', self.collapsed_folders))
        cp.add_section("window")
        cp.set("window", "collapsed-folders", collapsed_folders)
        cp.set("window", "left-panel-width", kwargs.get('hp_position', self.hp_position))
        cp.set("window", "window-width", self.WINDOW_WIDTH)
        cp.set("window", "window-height", self.WINDOW_HEIGHT)
        cp.set("window", "show-panel", self.SHOW_PANEL)
        cp.set("window", "show-toolbar", self.SHOW_TOOLBAR)

        i = 1
        for grupo in self.groups:
            for host in self.groups[grupo]:
                section = "host " + str(i)
                cp.add_section(section)
                self.save_host_to_ini(cp, section, host)
                i += 1

        cp.add_section("shortcuts")
        i = 1
        for s in self.shortcuts:
            if type(self.shortcuts[s]) == list:
                cp.set("shortcuts", self.shortcuts[s][0], s)
            else:
                cp.set("shortcuts", "shortcut%d" % (i), s)
                cp.set("shortcuts", "command%d" % (i), self.shortcuts[s].replace('\n', '\\n'))
                i = i + 1

        f = open(self.config_file + ".tmp", "w")
        cp.write(f)
        f.close()
        os.rename(self.config_file + ".tmp", self.config_file)

    def loadConfig(self):

        cp = ConfigParser.RawConfigParser()
        if os.path.exists(self.config_file):
            cp.read(self.config_file)
        else:
            self.writeConfig()
            cp.read(self.config_file)

        # Leer configuracion general
        try:
            self.WORD_SEPARATORS = cp.get("options", "word-separators")
            self.BUFFER_LINES = cp.getint("options", "buffer-lines")
            self.CONFIRM_ON_EXIT = cp.getboolean("options", "confirm-exit")
            self.FONT_COLOR = cp.get("options", "font-color")
            self.BACK_COLOR = cp.get("options", "back-color")
            self.TRANSPARENCY = cp.getint("options", "transparency")
            self.PASTE_ON_RIGHT_CLICK = cp.getboolean("options", "paste-right-click")
            self.CONFIRM_ON_CLOSE_TAB = cp.getboolean("options", "confirm-close-tab")
            self.COLLAPSED_FOLDERS = cp.get("window", "collapsed-folders")
            self.LEFT_PANEL_WIDTH = cp.getint("window", "left-panel-width")
            self.WINDOW_WIDTH = cp.getint("window", "window-width")
            self.WINDOW_HEIGHT = cp.getint("window", "window-height")
            self.FONT = cp.get("options", "font")
            self.AUTO_COPY_SELECTION = cp.getboolean("options", "auto-copy-selection")
            self.LOG_PATH = cp.get("options", "log-path")
            self.VERSION = cp.get("options", "version")
            self.AUTO_CLOSE_TAB = cp.getint("options", "auto-close-tab")
            self.SHOW_PANEL = cp.getboolean("window", "show-panel")
            self.SHOW_TOOLBAR = cp.getboolean("window", "show-toolbar")
            self.STARTUP_LOCAL = cp.getboolean("options", "startup-local")
        except:
            print "%s: %s" % (_("Invalid entry in configuration file"), sys.exc_info()[1])

        # Leer shorcuts
        scuts = {}
        try:
            scuts[cp.get("shortcuts", "copy")] = _COPY
        except:
            scuts["CTRL+SHIFT+C"] = _COPY
        try:
            scuts[cp.get("shortcuts", "paste")] = _PASTE
        except:
            scuts["CTRL+SHIFT+V"] = _PASTE
        try:
            scuts[cp.get("shortcuts", "copy_all")] = _COPY_ALL
        except:
            scuts["CTRL+SHIFT+A"] = _COPY_ALL
        try:
            scuts[cp.get("shortcuts", "save")] = _SAVE
        except:
            scuts["CTRL+S"] = _SAVE
        try:
            scuts[cp.get("shortcuts", "find")] = _FIND
        except:
            scuts["CTRL+F"] = _FIND
        try:
            scuts[cp.get("shortcuts", "find_next")] = _FIND_NEXT
        except:
            scuts["F3"] = _FIND_NEXT
        try:
            scuts[cp.get("shortcuts", "find_back")] = _FIND_BACK
        except:
            scuts["SHIFT+F3"] = _FIND_BACK

        try:
            scuts[cp.get("shortcuts", "console_previous")] = _CONSOLE_PREV
        except:
            scuts["CTRL+SHIFT+LEFT"] = _CONSOLE_PREV

        try:
            scuts[cp.get("shortcuts", "console_next")] = _CONSOLE_NEXT
        except:
            scuts["CTRL+SHIFT+RIGHT"] = _CONSOLE_NEXT

        try:
            scuts[cp.get("shortcuts", "console_close")] = _CONSOLE_CLOSE
        except:
            scuts["CTRL+W"] = _CONSOLE_CLOSE

        try:
            scuts[cp.get("shortcuts", "console_reconnect")] = _CONSOLE_RECONNECT
        except:
            scuts["CTRL+N"] = _CONSOLE_RECONNECT

        try:
            scuts[cp.get("shortcuts", "connect")] = _CONNECT
        except:
            scuts["CTRL+RETURN"] = _CONNECT

        ##kaman
        try:
            scuts[cp.get("shortcuts", "reset")] = _CLEAR
        except:
            scuts["CTRL+K"] = _CLEAR

        # shortcuts para cambiar consola1-consola9
        for x in range(1, 10):
            try:
                scuts[cp.get("shortcuts", "console_%d" % (x))] = eval("_CONSOLE_%d" % (x))
            except:
                scuts["F%d" % (x)] = eval("_CONSOLE_%d" % (x))
        try:
            i = 1
            while True:
                scuts[cp.get("shortcuts", "shortcut%d" % (i))] = cp.get("shortcuts", "command%d" % (i)).replace('\\n',
                                                                                                                '\n')
                i = i + 1
        except:
            pass
        self.shortcuts = scuts

        # Leer lista de hosts
        for section in cp.sections():
            if not section.startswith("host "):
                continue
            host = cp.options(section)
            try:
                host = self.load_host_from_ini(cp, section)

                if not self.groups.has_key(host.group):
                    self.groups[host.group] = []

                self.groups[host.group].append(host)
            except:
                print "%s: %s" % (_("Invalid entry in configuration file"), sys.exc_info()[1])
