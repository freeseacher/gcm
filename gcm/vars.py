# -*- coding: UTF-8 -*-
import os
import sys


BASE_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
DATA_PATH = os.path.join(BASE_PATH, '..')
SSH_COMMAND = os.path.join(DATA_PATH, 'data/ssh.expect')
ICON_PATH = os.path.join(DATA_PATH, 'data/icon.png')
GLADE_DIR = os.path.join(DATA_PATH, 'data')
LOCALE_DIR = os.path.join(DATA_PATH, 'locale')

app_name = "Gnome Connection Manager"
app_version = "1.1.0"
app_web = "http://www.kuthulu.com/gcm"
app_fileversion = "1"

SSH_BIN = 'ssh'
TEL_BIN = 'telnet'
SHELL = os.environ["SHELL"]
DOMAIN_NAME = "gcm-lang"
HSPLIT = 0
VSPLIT = 1
_COPY = ["copy"]
_PASTE = ["paste"]
_COPY_ALL = ["copy_all"]
_SAVE = ["save"]
_FIND = ["find"]
_CLEAR = ["reset"]
_FIND_NEXT = ["find_next"]
_FIND_BACK = ["find_back"]
_CONSOLE_PREV = ["console_previous"]
_CONSOLE_NEXT = ["console_next"]
_CONSOLE_1 = ["console_1"]
_CONSOLE_2 = ["console_2"]
_CONSOLE_3 = ["console_3"]
_CONSOLE_4 = ["console_4"]
_CONSOLE_5 = ["console_5"]
_CONSOLE_6 = ["console_6"]
_CONSOLE_7 = ["console_7"]
_CONSOLE_8 = ["console_8"]
_CONSOLE_9 = ["console_9"]
_CONSOLE_CLOSE = ["console_close"]
_CONSOLE_RECONNECT = ["console_reconnect"]
_CONNECT = ["connect"]
groups = {}
shortcuts = {}
