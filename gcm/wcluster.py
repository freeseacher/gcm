# -*- coding: UTF-8 -*-
import gobject
import gtk
import os

from SimpleGladeApp import SimpleGladeApp
from vars import DOMAIN_NAME, GLADE_DIR


class Wcluster(SimpleGladeApp):
    COLOR = gtk.gdk.Color('#FFFC00')

    def __init__(self, path="gnome-connection-manager.glade",
                 root="wCluster",
                 domain=DOMAIN_NAME, terms=None, **kwargs):
        self.terms = terms
        path = os.path.join(GLADE_DIR, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    def new(self):
        self.treeHosts = self.get_widget('treeHosts')
        self.treeStore = gtk.TreeStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_OBJECT)
        for x in self.terms:
            self.treeStore.append(None, (False, x[0], x[1]))
        self.treeHosts.set_model(self.treeStore)

        crt = gtk.CellRendererToggle()
        crt.set_property('activatable', True)
        crt.connect('toggled', self.on_active_toggled)
        col = gtk.TreeViewColumn(_("Activar"), crt, active=0)
        self.treeHosts.append_column(col)
        self.treeHosts.append_column(gtk.TreeViewColumn(_("Host"), gtk.CellRendererText(), text=1))
        self.get_widget("txtCommands").history = []

    #   Write your own methods here

    def on_active_toggled(self, widget, path):
        self.treeStore[path][0] = not self.treeStore[path][0]
        self.change_color(self.treeStore[path][2], self.treeStore[path][0])

    def change_color(self, term, activate):
        obj = term.get_parent()
        if obj == None:
            return
        nb = obj.get_parent()
        if nb == None:
            return
        if activate:
            nb.get_tab_label(obj).change_color(Wcluster.COLOR)
        else:
            nb.get_tab_label(obj).restore_color()

    def on_wCluster_destroy(self, widget, *args):
        self.on_btnNone_clicked(None)

    def on_cancelbutton2_clicked(self, widget, *args):
        self.get_widget("wCluster").destroy()

    def on_btnAll_clicked(self, widget, *args):
        for x in self.treeStore:
            x[0] = True
            self.change_color(x[2], x[0])

    def on_btnNone_clicked(self, widget, *args):
        for x in self.treeStore:
            x[0] = False
            self.change_color(x[2], x[0])

    def on_btnInvert_clicked(self, widget, *args):
        for x in self.treeStore:
            x[0] = not x[0]
            self.change_color(x[2], x[0])

    def on_txtCommands_key_press_event(self, widget, event, *args):
        if not event.state & gtk.gdk.CONTROL_MASK and gtk.gdk.keyval_name(event.keyval).upper() == 'RETURN':
            buf = widget.get_buffer()
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
            buf.set_text('')
            for x in self.treeStore:
                if x[0]:
                    x[2].feed_child(text + '\r')
            widget.history.append(text)
            widget.history_index = -1
            return True
        if event.state & gtk.gdk.CONTROL_MASK and gtk.gdk.keyval_name(event.keyval).upper() in ['UP', 'DOWN']:
            if len(widget.history) > 0:
                if gtk.gdk.keyval_name(event.keyval).upper() == 'UP':
                    widget.history_index -= 1
                    if widget.history_index < -1:
                        widget.history_index = len(widget.history) - 1
                else:
                    widget.history_index += 1
                    if widget.history_index >= len(widget.history):
                        widget.history_index = -1
                widget.get_buffer().set_text(widget.history[widget.history_index] if widget.history_index >= 0 else '')
