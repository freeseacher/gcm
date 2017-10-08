# -*- coding: UTF-8 -*-
import glob
import gtk
import os
from datetime import datetime

import polib

from SimpleGladeApp import bindtextdomain
from vars import ICON_PATH, LOCALE_DIR, DOMAIN_NAME


def msgbox(text, parent=None):
    msgBox = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, text)
    msgBox.set_icon_from_file(ICON_PATH)
    msgBox.run()
    msgBox.destroy()


def msgconfirm(text):
    msgBox = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, text)
    msgBox.set_icon_from_file(ICON_PATH)
    response = msgBox.run()
    msgBox.destroy()
    return response


def show_open_dialog(parent, title, action):
    dlg = gtk.FileChooserDialog(title=title, parent=parent, action=action)
    dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

    dlg.add_button(gtk.STOCK_SAVE if action == gtk.FILE_CHOOSER_ACTION_SAVE else gtk.STOCK_OPEN, gtk.RESPONSE_OK)
    dlg.set_do_overwrite_confirmation(True)
    if not hasattr(parent, 'lastPath'):
        parent.lastPath = os.path.expanduser("~")
    dlg.set_current_folder(parent.lastPath)

    if dlg.run() == gtk.RESPONSE_OK:
        filename = dlg.get_filename()
        parent.lastPath = os.path.dirname(filename)
    else:
        filename = None
    dlg.destroy()
    return filename


def get_key_name(event):
    name = ""
    if event.state & 4:
        name = name + "CTRL+"
    if event.state & 1:
        name = name + "SHIFT+"
    if event.state & 8:
        name = name + "ALT+"
    if event.state & 67108864:
        name = name + "SUPER+"
    return name + gtk.gdk.keyval_name(event.keyval).upper()


class EntryDialog(gtk.Dialog):
    def __init__(self, title, message, default_text='', modal=True, mask=False):
        gtk.Dialog.__init__(self)
        self.set_title(title)
        self.connect("destroy", self.quit)
        self.connect("delete_event", self.quit)
        if modal:
            self.set_modal(True)
        box = gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box)
        box.show()
        if message:
            label = gtk.Label(message)
            box.pack_start(label)
            label.show()
        self.entry = gtk.Entry()
        self.entry.set_text(default_text)
        self.entry.set_visibility(not mask)
        box.pack_start(self.entry)
        self.entry.show()
        self.entry.grab_focus()
        button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect("clicked", self.click)
        self.entry.connect("activate", self.click)
        button.set_flags(gtk.CAN_DEFAULT)
        self.action_area.pack_start(button)
        button.show()
        button.grab_default()
        button = gtk.Button(stock=gtk.STOCK_CANCEL)
        button.connect("clicked", self.quit)
        button.set_flags(gtk.CAN_DEFAULT)
        self.action_area.pack_start(button)
        button.show()
        self.ret = None

    def quit(self, w=None, event=None):
        self.hide()
        self.destroy()

    def click(self, button):
        self.value = self.entry.get_text()
        self.response(gtk.RESPONSE_OK)


def update_localization_files():
    """
    update localization files
    """
    files = glob.glob(os.path.join(LOCALE_DIR, '*.po'))
    for pofile in files:
        bname = os.path.basename(pofile)
        lang = bname.split('_')[0]
        modir = os.path.join(LOCALE_DIR, lang, 'LC_MESSAGES')
        if not os.path.exists(modir):
            os.makedirs(modir)

        mofile = os.path.join(modir, '%s.mo' % DOMAIN_NAME)
        if os.path.exists(mofile):
            mofiletime = datetime.fromtimestamp(os.path.getctime(mofile))
            pofiletime = datetime.fromtimestamp(os.path.getctime(pofile))
            if pofiletime > mofiletime:
                os.remove(mofile)

        if not os.path.exists(mofile):
            po = polib.pofile(pofile, encoding="utf-8")
            po.save_as_mofile(mofile)

    bindtextdomain(DOMAIN_NAME, LOCALE_DIR)


class SingletonMeta(type):
    def __init__(cls, name, bases, dict):
        super(SingletonMeta, cls).__init__(name, bases, dict)
        cls.instance = None
    def __call__(self,*args,**kw):
        if self.instance is None:
            self.instance = super(SingletonMeta, self).__call__(*args, **kw)
        return self.instance
