# -*- coding: UTF-8 -*-
import os

from SimpleGladeApp import SimpleGladeApp
from vars import app_name, app_version, app_web, DOMAIN_NAME, ICON_PATH, GLADE_DIR


class Wabout(SimpleGladeApp):
    def __init__(self, path="gnome-connection-manager.glade",
                 root="wAbout",
                 domain=DOMAIN_NAME, **kwargs):
        path = os.path.join(GLADE_DIR, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)
        self.wAbout.set_icon_from_file(ICON_PATH)

    def new(self):
        self.wAbout.set_name(app_name)
        self.wAbout.set_version(app_version)
        self.wAbout.set_website(app_web)

    #   Write your own methods here

    def on_wAbout_close(self, widget, *args):
        self.wAbout.destroy()
