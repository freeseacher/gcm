#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

# Python module gnome_connection_manager.py
# Autogenerated from gnome-connection-manager.glade
# Generated on Tue Jul  6 11:10:43 2010

# Warning: Do not modify any context comment such as #--
# They are required to keep user's code

from __future__ import with_statement

import gtk

from config import Config
from utils import update_localization_files
from wmain import Wmain


def main():
    gtk.gdk.threads_init()

    conf = Config()

    update_localization_files()

    w_main = Wmain()
    w_main.run()


if __name__ == "__main__":
    main()
