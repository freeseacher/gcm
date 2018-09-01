# -*- coding: UTF-8 -*-
import ConfigParser
import gobject
import gtk
import operator
import os
import sys
import time
import traceback

import pango
import vte

from SimpleGladeApp import SimpleGladeApp
from config import Config
from models import Host
from utils import EntryDialog, get_key_name, msgbox, msgconfirm, show_open_dialog
from vars import SSH_BIN, TEL_BIN, SHELL, SSH_COMMAND, DOMAIN_NAME, HSPLIT, VSPLIT, _COPY, _PASTE, \
    _COPY_ALL, _SAVE, _FIND, _CLEAR, _FIND_NEXT, _FIND_BACK, _CONSOLE_PREV, _CONSOLE_NEXT, _CONSOLE_CLOSE, \
    _CONSOLE_RECONNECT, _CONNECT, ICON_PATH, GLADE_DIR
from wabout import Wabout
from wcluster import Wcluster
from wconfig import Wconfig
from whost import Whost


def inputbox(title, text, default='', password=False):
    msgBox = EntryDialog(title, text, default, mask=password)
    msgBox.set_icon_from_file(ICON_PATH)
    if msgBox.run() == gtk.RESPONSE_OK:
        response = msgBox.value
    else:
        response = None
    msgBox.destroy()
    return response


class Wmain(SimpleGladeApp):
    def __init__(self, path="gnome-connection-manager.glade",
                 root="wMain",
                 domain=DOMAIN_NAME, **kwargs):
        path = os.path.join(GLADE_DIR, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

        self.config = Config()

        self.initLeftPane()

        self.createMenu()

        settings = gtk.settings_get_default()
        settings.props.gtk_menu_bar_accel = None

        self.real_transparency = False
        if self.config.TRANSPARENCY > 0:
            # Revisar si hay soporte para transparencia
            screen = self.get_widget("wMain").get_screen()
            colormap = screen.get_rgba_colormap()
            if colormap != None and screen.is_composited():
                self.get_widget("wMain").set_colormap(colormap)
                self.real_transparency = True

        if self.config.WINDOW_WIDTH != -1 and self.config.WINDOW_HEIGHT != -1:
            self.get_widget("wMain").resize(self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT)
        else:
            self.get_widget("wMain").maximize()
        self.get_widget("wMain").show()
        # Just added children in glade to eliminate GTK warning, remove all children
        for x in self.nbConsole.get_children():
            self.nbConsole.remove(x)
        self.nbConsole.set_scrollable(True)
        self.nbConsole.set_group_id(11)
        self.nbConsole.connect('page_removed', self.on_page_removed)
        self.nbConsole.connect("page-added", self.on_page_added)

        self.hpMain.previous_position = 150

        if self.config.LEFT_PANEL_WIDTH != 0:
            self.set_panel_visible(self.config.SHOW_PANEL)
        self.set_toolbar_visible(self.config.SHOW_TOOLBAR)

        # a veces no se posiciona correctamente con 400 ms, asi que se repite el llamado
        gobject.timeout_add(400, lambda: self.hpMain.set_position(self.config.LEFT_PANEL_WIDTH))
        gobject.timeout_add(900, lambda: self.hpMain.set_position(self.config.LEFT_PANEL_WIDTH))

        # Por cada parametro de la linea de comandos buscar el host y agregar un tab
        for arg in sys.argv[1:]:
            i = arg.rfind("/")
            if i != -1:
                group = arg[:i]
                name = arg[i + 1:]
                if group != '' and name != '' and self.config.groups.has_key(group):
                    for h in self.config.groups[group]:
                        if h.name == name:
                            self.addTab(self.nbConsole, h)
                            break

        self.get_widget('txtSearch').modify_text(gtk.STATE_NORMAL, gtk.gdk.Color('darkgray'))
        self.get_widget('filtertree').modify_text(gtk.STATE_NORMAL, gtk.gdk.Color('darkgray'))

        if self.config.STARTUP_LOCAL:
            self.addTab(self.nbConsole, 'local')

    def get_username(self):
        return os.getenv('USER') or os.getenv('LOGNAME') or os.getenv('USERNAME')

    def new(self):
        self.hpMain = self.get_widget("hpMain")
        self.nbConsole = self.get_widget("nbConsole")
        self.treeServers = self.get_widget("treeServers")
        self.menuServers = self.get_widget("menuServers")
        self.menuCustomCommands = self.get_widget("menuCustomCommands")
        self.current = None
        self.count = 0

    def on_terminal_click(self, widget, event, *args):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            if self.config.PASTE_ON_RIGHT_CLICK:
                widget.paste_clipboard()
            else:
                self.popupMenu.mnuCopy.set_sensitive(widget.get_has_selection())
                self.popupMenu.mnuLog.set_active(hasattr(widget, "log_handler_id") and widget.log_handler_id != 0)
                self.popupMenu.terminal = widget
                self.popupMenu.popup(None, None, None, event.button, event.time)
            return True

    def on_terminal_keypress(self, widget, event, *args):
        if self.config.shortcuts.has_key(get_key_name(event)):
            cmd = self.config.shortcuts[get_key_name(event)]
            if type(cmd) == list:
                # comandos predefinidos
                if cmd == _COPY:
                    self.terminal_copy(widget)
                elif cmd == _PASTE:
                    self.terminal_paste(widget)
                elif cmd == _COPY_ALL:
                    self.terminal_copy_all(widget)
                elif cmd == _SAVE:
                    self.show_save_buffer(widget)
                elif cmd == _FIND:
                    self.get_widget('txtSearch').select_region(0, -1)
                    self.get_widget('txtSearch').grab_focus()
                elif cmd == _FIND_NEXT:
                    if hasattr(self, 'search'):
                        self.find_word()
                elif cmd == _CLEAR:
                    widget.reset(True, True)
                elif cmd == _FIND_BACK:
                    if hasattr(self, 'search'):
                        self.find_word(backwards=True)
                elif cmd == _CONSOLE_PREV:
                    widget.get_parent().get_parent().prev_page()
                elif cmd == _CONSOLE_NEXT:
                    widget.get_parent().get_parent().next_page()
                elif cmd == _CONSOLE_CLOSE:
                    wid = widget.get_parent()
                    page = widget.get_parent().get_parent().page_num(wid)
                    if page != -1:
                        widget.get_parent().get_parent().remove_page(page)
                        wid.destroy()
                elif cmd == _CONSOLE_RECONNECT:
                    if not hasattr(widget, "command"):
                        widget.fork_command(SHELL)
                    else:
                        widget.fork_command(widget.command[0], widget.command[1])
                        while gtk.events_pending():
                            gtk.main_iteration(False)

                        # esperar 2 seg antes de enviar el pass para dar tiempo a que se levante expect y prevenir que se muestre el pass
                        if widget.command[2] != None and widget.command[2] != '':
                            gobject.timeout_add(2000, self.send_data, widget, widget.command[2])
                    widget.get_parent().get_parent().get_tab_label(widget.get_parent()).mark_tab_as_active()
                    return True
                elif cmd == _CONNECT:
                    self.on_btnConnect_clicked(None)
                elif cmd[0][0:8] == "console_":
                    page = int(cmd[0][8:]) - 1
                    widget.get_parent().get_parent().set_current_page(page)
            else:
                # comandos del usuario
                widget.feed_child(cmd)

            return True
        return False

    def on_terminal_selection(self, widget, *args):
        if self.config.AUTO_COPY_SELECTION:
            self.terminal_copy(widget)
        return True

    def find_word(self, backwards=False):
        pos = -1
        if backwards:
            lst = range(0, self.search['index'])
            lst.reverse()
            lst.extend(reversed(range(self.search['index'], len(self.search['lines']))))
        else:
            lst = range(self.search['index'], len(self.search['lines']))
            lst.extend(range(0, self.search['index']))
        for i in lst:
            pos = self.search['lines'][i].find(self.search['word'])
            if pos != -1:
                self.search['index'] = i if backwards else i + 1
                # print 'found at line %d column %d, index=%d' % (i, pos, self.search['index'])
                gobject.timeout_add(0, lambda: self.search['terminal'].get_adjustment().set_value(i))
                self.search['terminal'].queue_draw()
                break
        if pos == -1:
            self.search['index'] = len(self.search['lines']) if backwards else 0

    def init_search(self):
        if hasattr(self, 'search') and \
                        self.get_widget('txtSearch').get_text() == self.search['word'] and \
                        self.current == self.search['terminal']:
            return True

        terminal = self.find_active_terminal(self.hpMain)
        if terminal == None:
            terminal = self.current
        else:
            self.current = terminal
        if terminal == None:
            return False

        self.search = {}
        self.search['lines'] = terminal.get_text_range(0, 0, terminal.get_property('scrollback-lines'),
                                                       terminal.get_column_count(), lambda *args: True, None,
                                                       None).rstrip().splitlines()
        self.search['index'] = len(self.search['lines'])
        self.search['terminal'] = terminal
        self.search['word'] = self.get_widget('txtSearch').get_text()
        return True

    def on_popupmenu(self, widget, item, *args):
        if item == 'V':  # PASTE
            self.terminal_paste(self.popupMenu.terminal)
            return True
        elif item == 'C':  # COPY
            self.terminal_copy(self.popupMenu.terminal)
            return True
        elif item == 'CV':  # COPY and PASTE
            self.terminal_copy_paste(self.popupMenu.terminal)
            return True
        elif item == 'A':  # SELECT ALL
            self.terminal_select_all(self.popupMenu.terminal)
            return True
        elif item == 'CA':  # COPY ALL
            self.terminal_copy_all(self.popupMenu.terminal)
            return True
        elif item == 'X':  # CLOSE CONSOLE
            widget = self.popupMenu.terminal.get_parent()
            notebook = widget.get_parent()
            page = notebook.page_num(widget)
            notebook.remove_page(page)
            return True
        elif item == 'CP':  # CUSTOM COMMANDS
            self.popupMenu.terminal.feed_child(args[0])
        elif item == 'S':  # SAVE BUFFER
            self.show_save_buffer(self.popupMenu.terminal)
            return True
        elif item == 'H':  # COPY HOST ADDRESS TO CLIPBOARD
            if self.treeServers.get_selection().get_selected()[1] != None and not self.treeModel.iter_has_child(
                    self.treeServers.get_selection().get_selected()[1]):
                host = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1], 1)
                cb = gtk.Clipboard()
                cb.set_text(host.host)
                cb.store()
            return True
        elif item == 'SCPF':  # COPY TO CLIPBOARD SCP STRING TO RECEIVE FROM HOST
            if self.treeServers.get_selection().get_selected()[1] != None and not self.treeModel.iter_has_child(
                    self.treeServers.get_selection().get_selected()[1]):
                host = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1], 1)
                cb = gtk.Clipboard()
                scpstr = "scp"
                if host.port != "22":
                    scpstr += " -P " + host.port
                scpstr += host.user + "@" + host.host + ":"
                cb.set_text(scpstr)
                cb.store()
            return True
        elif item == 'SCPT':  # COPY TO CLIPBOARD SCP STRING to SEND TO HOST
            if self.treeServers.get_selection().get_selected()[1] != None and not self.treeModel.iter_has_child(
                    self.treeServers.get_selection().get_selected()[1]):
                host = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1], 1)
                cb = gtk.Clipboard()
                scpstr = "scp ./ " + host.user + "@" + host.host + ":"
                if host.port != "22":
                    scpstr += " -P " + host.port
                cb.set_text(scpstr)
                cb.store()
            return True

        elif item == 'D':  # DUPLICATE HOST
            if self.treeServers.get_selection().get_selected()[1] != None and not self.treeModel.iter_has_child(
                    self.treeServers.get_selection().get_selected()[1]):
                selected = self.treeServers.get_selection().get_selected()[1]
                group = self.get_group(selected)
                host = self.treeModel.get_value(selected, 1)
                newname = '%s (copy)' % (host.name)
                newhost = host.clone()
                for h in self.config.groups[group]:
                    if h.name == newname:
                        newname = '%s (copy)' % (newname)
                newhost.name = newname
                self.config.groups[group].append(newhost)
                self.updateTree()
                self.config.writeConfig(collapsed_nodes=self.get_collapsed_nodes(),
                                        hp_position=self.hpMain.get_position())
            return True
        elif item == 'R':  # RENAME TAB
            text = inputbox(_('Rename tab'), _('Enter new name'),
                            self.popupMenuTab.label.get_text().strip())
            if text != None and text != '':
                self.popupMenuTab.label.set_text("  %s  " % (text))
            return True
        elif item == 'RS' or item == 'RS2':  # RESET CONSOLE
            if (item == 'RS'):
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget.get_child()
            else:
                term = self.popupMenu.terminal
            term.reset(True, False)
            return True
        elif item == 'RC' or item == 'RC2':  # RESET AND CLEAR CONSOLE
            if (item == 'RC'):
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget.get_child()
            else:
                term = self.popupMenu.terminal
            term.reset(True, True)
            return True
        elif item == 'RO':  # REOPEN SESION
            tab = self.popupMenuTab.label.get_parent().get_parent()
            term = tab.widget.get_child()
            if not hasattr(term, "command"):
                term.fork_command(SHELL)
            else:
                term.fork_command(term.command[0], term.command[1])
                while gtk.events_pending():
                    gtk.main_iteration(False)

                # esperar 2 seg antes de enviar el pass para dar tiempo a que se levante expect y prevenir que se muestre el pass
                if term.command[2] != None and term.command[2] != '':
                    gobject.timeout_add(2000, self.send_data, term, term.command[2])
            tab.mark_tab_as_active()
            return True
        elif item == 'CC' or item == 'CC2':  # CLONE CONSOLE
            if item == 'CC':
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget.get_child()
                ntbk = tab.get_parent()
            else:
                term = self.popupMenu.terminal
                ntbk = term.get_parent().get_parent()
                tab = ntbk.get_tab_label(term.get_parent())
            if not hasattr(term, "host"):
                self.addTab(ntbk, tab.get_text())
            else:
                host = term.host.clone()
                host.name = tab.get_text()
                host.log = hasattr(term, "log_handler_id") and term.log_handler_id != 0
                self.addTab(ntbk, host)
            return True
        elif item == 'L' or item == 'L2':  # ENABLE/DISABLE LOG
            if item == 'L':
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget.get_child()
            else:
                term = self.popupMenu.terminal
            if not self.set_terminal_logger(term, widget.get_active()):
                widget.set_active(False)
            return True

    def createMenu(self):
        self.popupMenu = gtk.Menu()
        self.popupMenu.mnuCopy = menuItem = gtk.ImageMenuItem(_("Copy"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'C')
        menuItem.show()

        self.popupMenu.mnuPaste = menuItem = gtk.ImageMenuItem(_("Paste"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_PASTE, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'V')
        menuItem.show()

        self.popupMenu.mnuCopyPaste = menuItem = gtk.ImageMenuItem(_("Copy and Paste"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CV')
        menuItem.show()

        self.popupMenu.mnuSelect = menuItem = gtk.ImageMenuItem(_("Select all"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_SELECT_ALL, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'A')
        menuItem.show()

        self.popupMenu.mnuCopyAll = menuItem = gtk.ImageMenuItem(_("Copy all"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_SELECT_ALL, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CA')
        menuItem.show()

        self.popupMenu.mnuSelect = menuItem = gtk.ImageMenuItem(_("Save buffer to file"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_SAVE, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'S')
        menuItem.show()

        menuItem = gtk.MenuItem()
        self.popupMenu.append(menuItem)
        menuItem.show()

        self.popupMenu.mnuReset = menuItem = gtk.ImageMenuItem(_("Reset console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RS2')
        menuItem.show()

        self.popupMenu.mnuClear = menuItem = gtk.ImageMenuItem(_("Reset and Clear console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RC2')
        menuItem.show()

        self.popupMenu.mnuClone = menuItem = gtk.ImageMenuItem(_("Clone console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CC2')
        menuItem.show()

        self.popupMenu.mnuLog = menuItem = gtk.CheckMenuItem(_("Enable logging"))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'L2')
        menuItem.show()

        self.popupMenu.mnuClose = menuItem = gtk.ImageMenuItem(_("Close console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'X')
        menuItem.show()

        menuItem = gtk.MenuItem()
        self.popupMenu.append(menuItem)
        menuItem.show()

        # Menu de comandos personalizados
        self.popupMenu.mnuCommands = gtk.Menu()

        self.popupMenu.mnuCmds = menuItem = gtk.ImageMenuItem(_("Custom commands"))
        menuItem.set_submenu(self.popupMenu.mnuCommands)
        self.popupMenu.append(menuItem)
        menuItem.show()
        self.populateCommandsMenu()

        # Menu contextual para panel de servidores
        self.popupMenuFolder = gtk.Menu()

        self.popupMenuFolder.mnuConnect = menuItem = gtk.ImageMenuItem(_("Connect"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_btnConnect_clicked)
        menuItem.show()

        self.popupMenuFolder.mnuCopyAddress = menuItem = gtk.ImageMenuItem(_("Copy Address"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'H')
        menuItem.show()

        self.popupMenuFolder.mnuCopySCPto = menuItem = gtk.ImageMenuItem(_("Copy SCP string to clipboard <--"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'SCPF')
        menuItem.show()

        self.popupMenuFolder.mnuCopySCPfrom = menuItem = gtk.ImageMenuItem(_("Copy SCP string to clipboard -->"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'SCPT')
        menuItem.show()

        self.popupMenuFolder.mnuAdd = menuItem = gtk.ImageMenuItem(_("Add Host"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_btnAdd_clicked)
        menuItem.show()

        self.popupMenuFolder.mnuEdit = menuItem = gtk.ImageMenuItem(_("Edit"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_bntEdit_clicked)
        menuItem.show()

        self.popupMenuFolder.mnuDel = menuItem = gtk.ImageMenuItem(_("Remove"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_btnDel_clicked)
        menuItem.show()

        self.popupMenuFolder.mnuDup = menuItem = gtk.ImageMenuItem(_("Duplicate Host"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_DND_MULTIPLE, gtk.ICON_SIZE_MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'D')
        menuItem.show()

        menuItem = gtk.MenuItem()
        self.popupMenuFolder.append(menuItem)
        menuItem.show()

        self.popupMenuFolder.mnuExpand = menuItem = gtk.ImageMenuItem(_("Expand all"))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", lambda *args: self.treeServers.expand_all())
        menuItem.show()

        self.popupMenuFolder.mnuCollapse = menuItem = gtk.ImageMenuItem(_("Collapse all"))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", lambda *args: self.treeServers.collapse_all())
        menuItem.show()

        # Menu contextual para tabs
        self.popupMenuTab = gtk.Menu()

        self.popupMenuTab.mnuRename = menuItem = gtk.ImageMenuItem(_("Rename tab"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'R')
        menuItem.show()

        self.popupMenuTab.mnuReset = menuItem = gtk.ImageMenuItem(_("Reset console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RS')
        menuItem.show()

        self.popupMenuTab.mnuClear = menuItem = gtk.ImageMenuItem(_("Reset and Clear console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RC')
        menuItem.show()

        self.popupMenuTab.mnuReopen = menuItem = gtk.ImageMenuItem(_("Reconnect to host"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_CONNECT, gtk.ICON_SIZE_MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RO')
        # menuItem.show()

        self.popupMenuTab.mnuClone = menuItem = gtk.ImageMenuItem(_("Clone console"))
        menuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CC')
        menuItem.show()

        self.popupMenuTab.mnuLog = menuItem = gtk.CheckMenuItem(_("Enable logging"))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'L')
        menuItem.show()

    def createMenuItem(self, shortcut, label):
        menuItem = gtk.MenuItem('')
        menuItem.get_child().set_markup("<span color='blue'  size='x-small'>[%s]</span> %s" % (shortcut, label))
        menuItem.show()
        return menuItem

    def populateCommandsMenu(self):
        self.popupMenu.mnuCommands.foreach(lambda x: self.popupMenu.mnuCommands.remove(x))
        self.menuCustomCommands.foreach(lambda x: self.menuCustomCommands.remove(x))
        for x in self.config.shortcuts:
            if type(self.config.shortcuts[x]) != list:
                menuItem = self.createMenuItem(x, self.config.shortcuts[x][0:30])
                self.popupMenu.mnuCommands.append(menuItem)
                menuItem.connect("activate", self.on_popupmenu, 'CP', self.config.shortcuts[x])

                menuItem = self.createMenuItem(x, self.config.shortcuts[x][0:30])
                self.menuCustomCommands.append(menuItem)
                menuItem.connect("activate", self.on_menuCustomCommands_activate, self.config.shortcuts[x])

    def on_menuCustomCommands_activate(self, widget, command):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            terminal.feed_child(command)

    def terminal_copy(self, terminal):
        terminal.copy_clipboard()

    def terminal_paste(self, terminal):
        terminal.paste_clipboard()

    def terminal_copy_paste(self, terminal):
        terminal.copy_clipboard()
        terminal.paste_clipboard()

    def terminal_select_all(self, terminal):
        terminal.select_all()

    def terminal_copy_all(self, terminal):
        terminal.select_all()
        terminal.copy_clipboard()
        terminal.select_none()

    def on_menuCopy_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_copy(terminal)

    def on_menuPaste_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_paste(terminal)

    def on_menuCopyPaste_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_copy_paste(terminal)

    def on_menuSelectAll_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_select_all(terminal)

    def on_menuCopyAll_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_copy_all(terminal)

    def on_contents_changed(self, terminal):
        col, row = terminal.get_cursor_position()
        if terminal.last_logged_row != row:
            text = terminal.get_text_range(terminal.last_logged_row, terminal.last_logged_col, row, col,
                                           lambda *args: True, None, None)
            terminal.last_logged_row = row
            terminal.last_logged_col = col
            terminal.log.write(text[:-1])

    def set_terminal_logger(self, terminal, enable_logging=True):
        if enable_logging:
            terminal.last_logged_col, terminal.last_logged_row = terminal.get_cursor_position()
            if hasattr(terminal, "log_handler_id"):
                if terminal.log_handler_id == 0:
                    terminal.log_handler_id = terminal.connect('contents-changed', self.on_contents_changed)
                return True
            terminal.log_handler_id = terminal.connect('contents-changed', self.on_contents_changed)
            p = terminal.get_parent()
            title = p.get_parent().get_tab_label(p).get_text().strip()
            prefix = "%s/%s-%s" % (os.path.expanduser(self.config.LOG_PATH), title, time.strftime("%Y%m%d"))
            filename = ''
            for i in range(1, 1000):
                if not os.path.exists("%s-%03i.log" % (prefix, i)):
                    filename = "%s-%03i.log" % (prefix, i)
                    break
            filename == "%s-%03i.log" % (prefix, 1)
            try:
                terminal.log = open(filename, 'w', 0)
                terminal.log.write(
                    "Session '%s' opened at %s\n%s\n" % (title, time.strftime("%Y-%m-%d %H:%M:%S"), "-" * 80))
            except:
                traceback.print_exc()
                msgbox("%s\n%s" % (_("Can't open log file for writting"), filename))
                terminal.disconnect(terminal.log_handler_id)
                del terminal.log_handler_id
                return False
        else:
            if hasattr(terminal, "log_handler_id") and terminal.log_handler_id != 0:
                terminal.disconnect(terminal.log_handler_id)
                terminal.log_handler_id = 0
        return True

    def addTab(self, notebook, host):
        try:
            v = vte.Terminal()
            v.set_word_chars(self.config.WORD_SEPARATORS)
            v.set_scrollback_lines(self.config.BUFFER_LINES)
            if v.get_emulation() != os.getenv("TERM"):
                os.environ['TERM'] = v.get_emulation()

            if isinstance(host, basestring):
                host = Host('', host)

            fcolor = host.font_color
            bcolor = host.back_color
            if fcolor == '' or fcolor == None or bcolor == '' or bcolor == None:
                fcolor = self.config.FONT_COLOR
                bcolor = self.config.BACK_COLOR

            palette_components = [
                # background
                '#000000', '#CC0000', '#4E9A06', '#C4A000',
                '#3465A4', '#75507B', '#06989A', '#D3D7CF',
                # foreground
                '#555753', '#EF2929', '#8AE234', '#FCE94F',
                '#729FCF', '#729FCF', '#34E2E2', '#EEEEEC'
            ]

            palette = []
            for components in palette_components:
                color = gtk.gdk.color_parse(components)
                palette.append(color)

            if len(fcolor) > 0 and len(bcolor) > 0:
                v.set_colors(gtk.gdk.Color(fcolor), gtk.gdk.Color(bcolor), palette)

            if len(self.config.FONT) == 0:
                self.config.FONT = 'monospace'
            else:
                v.set_font(pango.FontDescription(self.config.FONT))

            scrollPane = gtk.ScrolledWindow()
            scrollPane.connect('button_press_event', lambda *args: True)
            scrollPane.set_property('hscrollbar-policy', gtk.POLICY_NEVER)
            tab = NotebookTabLabel("  %s  " % (host.name), self.nbConsole, scrollPane, self.popupMenuTab)

            v.connect("child-exited", lambda widget: tab.mark_tab_as_closed())
            v.connect('focus', self.on_tab_focus)
            v.connect('button_press_event', self.on_terminal_click)
            v.connect('key_press_event', self.on_terminal_keypress)
            v.connect('selection-changed', self.on_terminal_selection)

            if self.config.TRANSPARENCY > 0:
                if not self.real_transparency:
                    v.set_background_transparent(True)
                    v.set_background_saturation(self.config.TRANSPARENCY / 100.0)
                    if len(bcolor) > 0:
                        v.set_background_tint_color(gtk.gdk.Color(bcolor))
                else:
                    v.set_opacity(int((100 - self.config.TRANSPARENCY) / 100.0 * 65535))

            v.set_backspace_binding(host.backspace_key)
            v.set_delete_binding(host.delete_key)

            scrollPane.show()
            scrollPane.add(v)
            v.show()

            notebook.append_page(scrollPane, tab_label=tab)
            notebook.set_current_page(self.nbConsole.page_num(scrollPane))
            notebook.set_tab_reorderable(scrollPane, True)
            notebook.set_tab_detachable(scrollPane, True)
            self.wMain.set_focus(v)
            self.on_tab_focus(v)
            self.set_terminal_logger(v, host.log)

            gobject.timeout_add(200, lambda: self.wMain.set_focus(v))

            # Dar tiempo a la interfaz para que muestre el terminal
            while gtk.events_pending():
                gtk.main_iteration(False)

            if host.host == '' or host.host == None:
                v.fork_command(SHELL)
            else:
                cmd = SSH_COMMAND
                password = host.password
                if host.type == 'ssh':
                    if len(host.user) == 0:
                        host.user = self.get_username()
                    if host.password == '':
                        cmd = SSH_BIN
                        args = [SSH_BIN, '-l', host.user, '-p', host.port]
                    else:
                        args = [SSH_COMMAND, host.type, '-l', host.user, '-p', host.port]
                    if host.keep_alive != '0' and host.keep_alive != '':
                        args.append('-o')
                        args.append('ServerAliveInterval=%s' % (host.keep_alive))
                    for t in host.tunnel:
                        if t != "":
                            if t.endswith(":*:*"):
                                args.append("-D")
                                args.append(t[:-4])
                            else:
                                args.append("-L")
                                args.append(t)
                    if host.x11:
                        args.append("-X")
                    if host.agent:
                        args.append("-A")
                    if host.compression:
                        args.append("-C")
                        if host.compressionLevel != '':
                            args.append('-o')
                            args.append('CompressionLevel=%s' % (host.compressionLevel))
                    if host.private_key != None and host.private_key != '':
                        args.append("-i")
                        args.append(host.private_key)
                    if host.extra_params != None and host.extra_params != '':
                        args += host.extra_params.split()
                    args.append(host.host)
                else:
                    if host.user == '' or host.password == '':
                        password = ''
                        cmd = TEL_BIN
                        args = [TEL_BIN]
                    else:
                        args = [SSH_COMMAND, host.type, '-l', host.user]
                    if host.extra_params != None and host.extra_params != '':
                        args += host.extra_params.split()
                    args += [host.host, host.port]
                v.command = (cmd, args, password)
                v.fork_command(cmd, args)
                while gtk.events_pending():
                    gtk.main_iteration(False)

                # esperar 2 seg antes de enviar el pass para dar tiempo a que se levante expect y prevenir que se muestre el pass
                if password != None and password != '':
                    gobject.timeout_add(2000, self.send_data, v, password)

            # esperar 3 seg antes de enviar comandos
            if host.commands != None and host.commands != '':
                basetime = 700 if len(host.host) == 0 else 3000
                lines = []
                for line in host.commands.splitlines():
                    if line.startswith("##D=") and line[4:].isdigit():
                        if len(lines):
                            gobject.timeout_add(basetime, self.send_data, v, "\r".join(lines))
                            lines = []
                        basetime += int(line[4:])
                    else:
                        lines.append(line)
                if len(lines):
                    gobject.timeout_add(basetime, self.send_data, v, "\r".join(lines))
            v.queue_draw()

            # guardar datos de consola para clonar consola
            v.host = host
        except:
            traceback.print_exc()
            msgbox("%s: %s" % (_("Error connecting to server"), sys.exc_info()[1]))

    def send_data(self, terminal, data):
        terminal.feed_child('%s\r' % (data))
        return False

    def initLeftPane(self):
        self.treeModel = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT, gtk.gdk.Pixbuf)
        self.treeServers.set_model(self.treeModel)

        self.treeServers.set_level_indentation(5)
        # Force the alternating row colors, by default it's off with one column
        self.treeServers.set_property('rules-hint', True)
        gtk.rc_parse_string("""
                style "custom-treestyle"{
                    GtkTreeView::allow-rules = 1
                }
                widget "*treeServers*" style "custom-treestyle"
            """)
        column = gtk.TreeViewColumn()
        column.set_title('Servers')
        self.treeServers.append_column(column)

        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, expand=False)
        column.add_attribute(renderer, 'pixbuf', 2)

        renderer = gtk.CellRendererText()
        column.pack_start(renderer, expand=True)
        column.add_attribute(renderer, 'text', 0)

        self.treeServers.set_has_tooltip(True)
        self.treeServers.connect('query-tooltip', self.on_treeServers_tooltip)
        self.updateTree()

    def on_treeServers_tooltip(self, widget, x, y, keyboard, tooltip):
        x, y = widget.convert_widget_to_bin_window_coords(x, y)
        pos = widget.get_path_at_pos(x, y)
        if pos:
            host = list(widget.get_model()[pos[0]])[1]
            if host:
                text = "<span><b>%s</b>\n%s:%s@%s\n</span><span size='smaller'>%s</span>" % (
                    host.name, host.type, host.user, host.host, host.description)
                tooltip.set_markup(text)
                return True
        return False

    def is_node_collapsed(self, model, path, iter, nodes):
        if self.treeModel.get_value(iter, 1) == None and not self.treeServers.row_expanded(path):
            nodes.append(self.treeModel.get_string_from_iter(iter))

    def get_collapsed_nodes(self):
        nodes = []
        self.treeModel.foreach(self.is_node_collapsed, nodes)
        return nodes

    def set_collapsed_nodes(self):
        self.treeServers.expand_all()
        if self.treeModel.get_iter_root():
            for node in self.config.COLLAPSED_FOLDERS.split(","):
                if node != '':
                    self.treeServers.collapse_row(node)

    def on_refresh_clicked(self, widget, *args):
        self.updateTree()
        #self.config.loadConfig()

    def updateTree(self):
        # clean empty groups
        for g in dict(self.config.groups):
            if len(self.config.groups[g]) == 0:
                del self.config.groups[g]

        if not self.config.COLLAPSED_FOLDERS:
            self.config.COLLAPSED_FOLDERS = ','.join(self.get_collapsed_nodes())

        self.menuServers.foreach(self.menuServers.remove)
        self.treeModel.clear()

        iconHost = self.treeServers.render_icon("gtk-network", size=gtk.ICON_SIZE_BUTTON, detail=None)
        iconDir = self.treeServers.render_icon("gtk-directory", size=gtk.ICON_SIZE_BUTTON, detail=None)

        groups = self.config.groups.keys()
        groups.sort(lambda x, y: cmp(y, x))

        for g in groups:
            group = None
            path = ""
            menuNode = self.menuServers

            for folder in g.split("/"):
                path = path + '/' + folder
                row = self.get_folder(self.treeModel, '', path)
                if not row:
                    group = self.treeModel.prepend(group, [folder, None, iconDir])
                else:
                    group = row.iter

                menu = self.get_folder_menu(self.menuServers, '', path)
                if not menu:
                    menu = gtk.ImageMenuItem(folder)
                    # menu.set_image(gtk.image_new_from_stock(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU))
                    menuNode.prepend(menu)
                    menuNode = gtk.Menu()
                    menu.set_submenu(menuNode)
                    menu.show()
                else:
                    menuNode = menu

            self.config.groups[g].sort(key=operator.attrgetter('name'))
            for host in self.config.groups[g]:
                self.treeModel.append(group, [host.name, host, iconHost])
                mnuItem = gtk.ImageMenuItem(host.name)
                mnuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_NETWORK, gtk.ICON_SIZE_MENU))
                mnuItem.show()
                mnuItem.connect("activate", lambda arg, nb, h: self.addTab(nb, h), self.nbConsole, host)
                menuNode.append(mnuItem)

        self.set_collapsed_nodes()
        self.config.COLLAPSED_FOLDERS = None

    def get_folder(self, obj, folder, path):
        if not obj:
            return None
        for row in obj:
            if path == folder + '/' + row[0]:
                return row
            i = self.get_folder(row.iterchildren(), folder + '/' + row[0], path)
            if i:
                return i

    def get_folder_menu(self, obj, folder, path):
        if not obj or not (isinstance(obj, gtk.Menu) or isinstance(obj, gtk.MenuItem)):
            return None
        for item in obj.get_children():
            if path == folder + '/' + item.get_label():
                return item.get_submenu()
            i = self.get_folder_menu(item.get_submenu(), folder + '/' + item.get_label(), path)
            if i:
                return i

    def on_tab_focus(self, widget, *args):
        if isinstance(widget, vte.Terminal):
            self.current = widget

    def split_notebook(self, direction):
        csp = self.current.get_parent() if self.current != None else None
        cnb = csp.get_parent() if csp != None else None

        # Separar solo si hay mas de 2 tabs en el notebook actual
        if csp != None and cnb.get_n_pages() > 1:
            # Crear un hpaned, en el hijo 0 dejar el notebook y en el hijo 1 el nuevo notebook
            # El nuevo hpaned dejarlo como hijo del actual parent
            hp = gtk.HPaned() if direction == HSPLIT else gtk.VPaned()
            nb = gtk.Notebook()
            nb.set_group_id(11)
            nb.connect('button_press_event', self.on_double_click, None)
            nb.connect('page_removed', self.on_page_removed)
            nb.connect("page-added", self.on_page_added)
            nb.set_property("scrollable", True)
            cp = cnb.get_parent()

            if direction == HSPLIT:
                cnb.set_size_request(cnb.allocation.width / 2, cnb.allocation.height)
            else:
                cnb.set_size_request(cnb.allocation.width, cnb.allocation.height / 2)
            # cnb.set_size_request(cnb.allocation.width/2, cnb.allocation.height/2)

            cp.remove(cnb)
            cp.add(hp)
            hp.add1(cnb)

            text = cnb.get_tab_label(csp).get_text()

            csp.reparent(nb)
            csp = nb.get_nth_page(0)

            tab = NotebookTabLabel(text, nb, csp, self.popupMenuTab)
            nb.set_tab_label(csp, tab_label=tab)
            nb.set_tab_reorderable(csp, True)
            nb.set_tab_detachable(csp, True)

            hp.add2(nb)
            nb.show()
            hp.show()
            hp.queue_draw()
            self.current = cnb.get_nth_page(cnb.get_current_page()).get_children()[0]

    def find_notebook(self, widget, exclude=None):
        if widget != exclude and isinstance(widget, gtk.Notebook):
            return widget
        else:
            if not hasattr(widget, "get_children"):
                return None
            for w in widget.get_children():
                wid = self.find_notebook(w, exclude)
                if wid != exclude and isinstance(wid, gtk.Notebook):
                    return wid
            return None

    def find_active_terminal(self, widget):
        if isinstance(widget, vte.Terminal) and widget.is_focus():
            return widget
        else:
            if not hasattr(widget, "get_children"):
                return None

            for w in widget.get_children():
                wid = self.find_active_terminal(w)
                if isinstance(wid, vte.Terminal) and wid.is_focus():
                    return wid
            return None

    def check_notebook_pages(self, widget):
        if widget.get_n_pages() == 0:
            # eliminar el notebook solo si queda otro notebook y no quedan tabs en el actual
            paned = widget.get_parent()
            if paned == None or paned == self.hpMain:
                return
            container = paned.get_parent()
            save = paned.get_child2() if paned.get_child1() == widget else paned.get_child1()
            container.remove(paned)
            paned.remove(save)
            container.add(save)
            if widget == self.nbConsole:
                if isinstance(save, gtk.Notebook):
                    self.nbConsole = save
                else:
                    self.nbConsole = self.find_notebook(save)

    def on_page_removed(self, widget, *args):
        self.count -= 1
        if hasattr(widget, "is_closed") and widget.is_closed:
            # tab has been closed
            self.check_notebook_pages(widget)
        else:
            # tab has been moved to another notebook
            # save a reference to this notebook, on_page_added check if the notebook must be removed
            self.check_notebook = widget

    def on_page_added(self, widget, *args):
        self.count += 1
        if hasattr(self, "check_notebook"):
            self.check_notebook_pages(self.check_notebook)
            delattr(self, "check_notebook")

    def show_save_buffer(self, terminal):
        dlg = gtk.FileChooserDialog(title=_("Save as"), parent=self.wMain, action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name(os.path.basename("gcm-buffer-%s.txt" % (time.strftime("%Y%m%d%H%M%S"))))
        if not hasattr(self, 'lastPath'):
            self.lastPath = os.path.expanduser("~")
        dlg.set_current_folder(self.lastPath)

        if dlg.run() == gtk.RESPONSE_OK:
            filename = dlg.get_filename()
            self.lastPath = os.path.dirname(filename)

            try:
                buff = terminal.get_text_range(0, 0, terminal.get_property('scrollback-lines') - 1,
                                               terminal.get_column_count() - 1, lambda *args: True, None, None).strip()
                f = open(filename, "w")
                f.write(buff)
                f.close()
            except:
                traceback.print_exc()
                dlg.destroy()
                msgbox("%s: %s" % (_("Can't open file for writting"), filename))
                return

        dlg.destroy()

    def set_panel_visible(self, visibility):
        if visibility:
            gobject.timeout_add(200, lambda: self.hpMain.set_position(
                self.hpMain.previous_position if self.hpMain.previous_position > 10 else 150))
        else:
            self.hpMain.previous_position = self.hpMain.get_position()
            gobject.timeout_add(200, lambda: self.hpMain.set_position(0))
        self.get_widget("show_panel").set_active(visibility)
        self.config.SHOW_PANEL = visibility

    def set_toolbar_visible(self, visibility):
        # self.get_widget("toolbar1").set_visible(visibility)
        if visibility:
            self.get_widget("toolbar1").show()
        else:
            self.get_widget("toolbar1").hide()
        self.get_widget("show_toolbar").set_active(visibility)
        self.config.SHOW_TOOLBAR = visibility

    def on_wMain_destroy(self, widget, *args):
        self.config.writeConfig(collapsed_nodes=self.get_collapsed_nodes(), hp_position=self.hpMain.get_position())
        gtk.main_quit()

    def on_wMain_delete_event(self, widget, *args):
        (self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT) = self.get_widget("wMain").get_size()
        if self.config.CONFIRM_ON_EXIT and self.count > 0 and msgconfirm("%s %d %s" % (
                _("There are"), self.count, _("open consoles, exit anyway?"))) != gtk.RESPONSE_OK:
            return True

    def on_guardar_como1_activate(self, widget, *args):
        term = self.find_active_terminal(self.hpMain)
        if term == None:
            term = self.current
        if term != None:
            self.show_save_buffer(term)

    def on_importar_servidores1_activate(self, widget, *args):
        filename = show_open_dialog(parent=self.wMain, title=_("Open"), action=gtk.FILE_CHOOSER_ACTION_OPEN)
        if filename != None:
            password = inputbox(_('Import Servers'), _('Enter password: '), password=True)
            if password == None:
                return

            # abrir archivo con lista de servers y cargarlos en el arbol
            try:
                cp = ConfigParser.RawConfigParser()
                cp.read(filename)

                # validar el pass
                s = decrypt(password, cp.get("gcm", "gcm"))
                if (s != password[::-1]):
                    msgbox(_("Invalid password"))
                    return

                if msgconfirm(_(u'Server list will be overwritten, continue?')) != gtk.RESPONSE_OK:
                    return

                grupos = {}
                for section in cp.sections():
                    if not section.startswith("host "):
                        continue
                    host = self.config.load_host_from_ini(cp, section, password)

                    if not grupos.has_key(host.group):
                        grupos[host.group] = []

                    grupos[host.group].append(host)
            except:
                traceback.print_exc()
                msgbox(_("Invalid file"))
                return
            # sobreescribir lista de hosts
            self.updateTree()

    def on_exportar_servidores1_activate(self, widget, *args):
        filename = show_open_dialog(parent=self.wMain, title=_("Save as"), action=gtk.FILE_CHOOSER_ACTION_SAVE)
        if filename != None:
            password = inputbox(_('Export Servers'), _('Enter password: '), password=True)
            if password == None:
                return

            try:
                cp = ConfigParser.RawConfigParser()
                cp.read(filename + ".tmp")
                i = 1
                cp.add_section("gcm")
                cp.set("gcm", "gcm", encrypt(password, password[::-1]))

                for grupo in self.config.groups:
                    for host in self.config.groups[grupo]:
                        section = "host " + str(i)
                        cp.add_section(section)
                        self.config.save_host_to_ini(cp, section, host, password)
                        i += 1
                f = open(filename + ".tmp", "w")
                cp.write(f)
                f.close()
                os.rename(filename + ".tmp", filename)
            except:
                traceback.print_exc()
                msgbox(_("Invalid file"))

    def on_salir1_activate(self, widget, *args):
        (self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT) = self.get_widget("wMain").get_size()
        self.config.writeConfig(collapsed_nodes=self.get_collapsed_nodes(), hp_position=self.hpMain.get_position())
        gtk.main_quit()

    def on_show_toolbar_toggled(self, widget, *args):
        self.set_toolbar_visible(widget.get_active())

    def on_show_panel_toggled(self, widget, *args):
        self.set_panel_visible(widget.get_active())

    def on_acerca_de1_activate(self, widget, *args):
        w_about = Wabout()

    def on_double_click(self, widget, event, *args):
        if event.type in [gtk.gdk._2BUTTON_PRESS, gtk.gdk._3BUTTON_PRESS] and event.button == 1:
            if isinstance(widget, gtk.Notebook):
                pos = event.x + widget.get_allocation().x
                size = widget.get_tab_label(widget.get_nth_page(widget.get_n_pages() - 1)).get_allocation()
                if pos <= size.x + size.width + 2 * widget.get_property(
                        "tab-vborder") + 8 or event.x >= widget.get_allocation().width - widget.style_get_property(
                    "scroll-arrow-hlength"):
                    return True
            self.addTab(widget if isinstance(widget, gtk.Notebook) else self.nbConsole, 'local')
            return True

    def on_btnLocal_clicked(self, widget, *args):
        if self.current != None and self.current.get_parent() != None and isinstance(
                self.current.get_parent().get_parent(), gtk.Notebook):
            ntbk = self.current.get_parent().get_parent()
        else:
            ntbk = self.nbConsole
        self.addTab(ntbk, 'local')

    def on_btnConnect_clicked(self, widget, *args):
        if self.treeServers.get_selection().get_selected()[1] != None:
            if not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                self.on_tvServers_row_activated(self.treeServers)
            else:
                selected = self.treeServers.get_selection().get_selected()[1]
                group = self.treeModel.get_value(selected, 0)
                parent_group = self.get_group(selected)
                if parent_group != '':
                    group = parent_group + '/' + group

                for g in self.config.groups:
                    if g == group or g.startswith(group + '/'):
                        for host in self.config.groups[g]:
                            self.addTab(self.nbConsole, host)

    def on_btnAdd_clicked(self, widget, *args):
        group = ""
        if self.treeServers.get_selection().get_selected()[1] != None:
            selected = self.treeServers.get_selection().get_selected()[1]
            group = self.get_group(selected)
            if self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                selected = self.treeServers.get_selection().get_selected()[1]
                group = self.treeModel.get_value(selected, 0)
                parent_group = self.get_group(selected)
                if parent_group != '':
                    group = parent_group + '/' + group
        wHost = Whost()
        wHost.init(group)

    def get_group(self, i):
        if self.treeModel.iter_parent(i):
            p = self.get_group(self.treeModel.iter_parent(i))
            return (p + '/' if p != '' else '') + self.treeModel.get_value(self.treeModel.iter_parent(i), 0)
        else:
            return ''

    def on_bntEdit_clicked(self, widget, *args):
        if self.treeServers.get_selection().get_selected()[1] != None and not self.treeModel.iter_has_child(
                self.treeServers.get_selection().get_selected()[1]):
            selected = self.treeServers.get_selection().get_selected()[1]
            host = self.treeModel.get_value(selected, 1)
            wHost = Whost()
            wHost.init(host.group, host)
            # self.updateTree()

    def on_btnDel_clicked(self, widget, *args):
        if self.treeServers.get_selection().get_selected()[1] != None:
            if not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                # Remove solo el nodo
                name = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1], 0)
                if msgconfirm("%s [%s]?" % (_("Do you really want to remove host"), name)) == gtk.RESPONSE_OK:
                    host = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1], 1)
                    self.config.groups[host.group].remove(host)
                    self.updateTree()
            else:
                # Remove todo el grupo
                group = self.get_group(self.treeModel.iter_children(self.treeServers.get_selection().get_selected()[1]))
                if msgconfirm("%s [%s]?" % (
                        _("Do you really want to remove all hosts in group"), group)) == gtk.RESPONSE_OK:
                    try:
                        del self.config.groups[group]
                    except:
                        pass
                    for h in dict(self.config.groups):
                        if h.startswith(group + '/'):
                            del self.config.groups[h]
                    self.updateTree()
        self.config.writeConfig(collapsed_nodes=self.get_collapsed_nodes(), hp_position=self.hpMain.get_position())

    def on_btnHSplit_clicked(self, widget, *args):
        self.split_notebook(HSPLIT)

    def on_btnVSplit_clicked(self, widget, *args):
        self.split_notebook(VSPLIT)

    def on_btnUnsplit_clicked(self, widget, *args):
        wid = self.find_notebook(self.hpMain, self.nbConsole)
        while wid != None:
            # Mover los tabs al notebook principal
            while wid.get_n_pages() != 0:
                csp = wid.get_nth_page(0)
                text = wid.get_tab_label(csp).get_text()
                csp.reparent(self.nbConsole)
                csp = self.nbConsole.get_nth_page(self.nbConsole.get_n_pages() - 1)
                tab = NotebookTabLabel(text, self.nbConsole, csp, self.popupMenuTab)
                self.nbConsole.set_tab_label(csp, tab_label=tab)
                self.nbConsole.set_tab_reorderable(csp, True)
                self.nbConsole.set_tab_detachable(csp, True)
            wid = self.find_notebook(self.hpMain, self.nbConsole)

    def on_btnConfig_clicked(self, widget, *args):
        wConfig = Wconfig()
        self.populateCommandsMenu()

    def on_txtSearch_focus(self, widget, *args):
        if widget.get_text() == _('search...'):
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color('black'))
            widget.set_text('')

    def on_filtertree_focus_in_event(self, widget, *args):
        if widget.get_text() == _('filter...'):
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color('black'))
            widget.set_text('')

    def on_filtertree_focus_out_event(self, widget, *args):
        if widget.get_text() == '':
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color('darkgray'))
            widget.set_text(_('filter...'))

    def on_txtSearch_focus_out_event(self, widget, *args):
        if widget.get_text() == '':
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.Color('darkgray'))
            widget.set_text(_('search...'))

    def on_btnSearchBack_clicked(self, widget, *args):
        if self.init_search():
            self.find_word(backwards=True)

    def on_btnSearch_clicked(self, widget, *args):
        if self.init_search():
            self.find_word()

    def on_btnCluster_clicked(self, widget, *args):
        if hasattr(self, 'wCluster'):
            if not self.wCluster.get_property("visible"):
                self.wCluster.destroy()
                create = True
        else:
            create = True

        if not create:
            return True

        # obtener lista de consolas abiertas
        consoles = []
        obj = self.hpMain
        s = []
        s.append(obj)
        while len(s) > 0:
            obj = s.pop()
            # agregar hijos de p a s
            if hasattr(obj, "get_children"):
                for w in obj.get_children():
                    if isinstance(w, gtk.Notebook) or hasattr(w, "get_children"):
                        s.append(w)

            if isinstance(obj, gtk.Notebook):
                n = obj.get_n_pages()
                for i in range(0, n):
                    terminal = obj.get_nth_page(i).get_child()
                    title = obj.get_tab_label(obj.get_nth_page(i)).get_text()
                    consoles.append((title, terminal))

        if len(consoles) == 0:
            msgbox(_("No open consoles"))
            return True

        self.wCluster = Wcluster(terms=consoles).get_widget('wCluster')

    def on_hpMain_button_press_event(self, widget, event, *args):
        if event.type in [gtk.gdk._2BUTTON_PRESS]:
            p = self.hpMain.get_position()
            self.set_panel_visible(p == 0)

    def on_tvServers_row_activated(self, widget, *args):
        if not self.treeModel.iter_has_child(widget.get_selection().get_selected()[1]):
            selected = widget.get_selection().get_selected()[1]
            host = self.treeModel.get_value(selected, 1)
            self.addTab(self.nbConsole, host)

    def on_tvServers_button_press_event(self, widget, event, *args):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = self.treeServers.get_path_at_pos(x, y)

            if pthinfo is None:
                self.popupMenuFolder.mnuDel.hide()
                self.popupMenuFolder.mnuEdit.hide()
                self.popupMenuFolder.mnuCopyAddress.hide()
                self.popupMenuFolder.mnuDup.hide()
                self.popupMenuFolder.mnuCopySCPfrom.hide()
                self.popupMenuFolder.mnuCopySCPto.hide()
            else:
                path, col, cellx, celly = pthinfo
                if self.treeModel.iter_children(self.treeModel.get_iter(path)):
                    self.popupMenuFolder.mnuEdit.hide()
                    self.popupMenuFolder.mnuCopyAddress.hide()
                    self.popupMenuFolder.mnuDup.hide()
                    self.popupMenuFolder.mnuCopySCPfrom.hide()
                    self.popupMenuFolder.mnuCopySCPto.hide()
                else:
                    self.popupMenuFolder.mnuEdit.show()
                    self.popupMenuFolder.mnuCopyAddress.show()
                    self.popupMenuFolder.mnuDup.show()
                    self.popupMenuFolder.mnuCopySCPfrom.show()
                    self.popupMenuFolder.mnuCopySCPto.show()

                self.popupMenuFolder.mnuDel.show()
                self.treeServers.grab_focus()
                self.treeServers.set_cursor(path, col, 0)
            self.popupMenuFolder.popup(None, None, None, event.button, event.time)
            return True


class NotebookTabLabel(gtk.HBox):
    '''Notebook tab label with close button.
    '''

    def __init__(self, title, owner_, widget_, popup_):
        gtk.HBox.__init__(self, False, 0)

        self.title = title
        self.owner = owner_
        self.eb = gtk.EventBox()
        label = self.label = gtk.Label()
        self.eb.connect('button-press-event', self.popupmenu, label)
        label.set_alignment(0.0, 0.5)
        label.set_text(title)
        self.eb.add(label)
        self.pack_start(self.eb)
        label.show()
        self.eb.show()
        close_image = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        image_w, image_h = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
        self.widget = widget_
        self.popup = popup_
        close_btn = gtk.Button()
        close_btn.set_relief(gtk.RELIEF_NONE)
        close_btn.connect('clicked', self.on_close_tab, owner_)
        close_btn.set_size_request(image_w + 7, image_h + 6)
        close_btn.add(close_image)
        style = close_btn.get_style()
        self.eb2 = gtk.EventBox()
        self.eb2.add(close_btn)
        self.pack_start(self.eb2, False, False)
        self.eb2.show()
        close_btn.show_all()
        self.is_active = True
        self.show()
        self.config = Config()

    def change_color(self, color):
        self.eb.modify_bg(gtk.STATE_ACTIVE, color)
        self.eb2.modify_bg(gtk.STATE_ACTIVE, color)
        self.eb.modify_bg(gtk.STATE_NORMAL, color)
        self.eb2.modify_bg(gtk.STATE_NORMAL, color)

    def restore_color(self):
        bg = self.label.style.bg
        self.eb.modify_bg(gtk.STATE_ACTIVE, bg[gtk.STATE_ACTIVE])
        self.eb2.modify_bg(gtk.STATE_ACTIVE, bg[gtk.STATE_ACTIVE])
        self.eb.modify_bg(gtk.STATE_NORMAL, bg[gtk.STATE_NORMAL])
        self.eb2.modify_bg(gtk.STATE_NORMAL, bg[gtk.STATE_NORMAL])

    def on_close_tab(self, widget, notebook, *args):
        if self.config.CONFIRM_ON_CLOSE_TAB and msgconfirm(
                        "%s [%s]?" % (_("Close console"), self.label.get_text().strip())) != gtk.RESPONSE_OK:
            return True

        self.close_tab(widget)

    def close_tab(self, widget):
        notebook = self.widget.get_parent()
        page = notebook.page_num(self.widget)
        if page >= 0:
            notebook.is_closed = True
            notebook.remove_page(page)
            notebook.is_closed = False
            self.widget.destroy()

    def mark_tab_as_closed(self):
        self.label.set_markup("<span color='darkgray' strikethrough='true'>%s</span>" % (self.label.get_text()))
        self.is_active = False
        if self.config.AUTO_CLOSE_TAB != 0:
            if self.config.AUTO_CLOSE_TAB == 2:
                terminal = self.widget.get_parent().get_nth_page(
                    self.widget.get_parent().page_num(self.widget)).get_child()
                if terminal.get_child_exit_status() != 0:
                    return
            self.close_tab(self.widget)

    def mark_tab_as_active(self):
        self.label.set_markup("%s" % (self.label.get_text()))
        self.is_active = True

    def get_text(self):
        return self.label.get_text()

    def popupmenu(self, widget, event, label):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            self.popup.label = self.label
            if self.is_active:
                self.popup.mnuReopen.hide()
            else:
                self.popup.mnuReopen.show()

            # enable or disable log checkbox according to terminal
            self.popup.mnuLog.set_active(
                hasattr(self.widget.get_child(), "log_handler_id") and self.widget.get_child().log_handler_id != 0)
            self.popup.popup(None, None, None, event.button, event.time)
            return True
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 2:
            self.close_tab(self.widget)
