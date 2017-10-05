# -*- coding: UTF-8 -*-
import gobject
import gtk
import os

import pango

from SimpleGladeApp import SimpleGladeApp
from config import Config
from src.vars import shortcuts
from vars import DOMAIN_NAME, GLADE_DIR
from utils import get_key_name


def show_font_dialog(parent, title, button):
    if not hasattr(parent, 'dlgFont'):
        parent.dlgFont = None

    if parent.dlgFont == None:
        parent.dlgFont = gtk.FontSelectionDialog(title)
    fontsel = parent.dlgFont.fontsel
    fontsel.set_font_name(button.selected_font.to_string())

    response = parent.dlgFont.run()

    if response == gtk.RESPONSE_OK:
        button.selected_font = pango.FontDescription(fontsel.get_font_name())
        button.set_label(button.selected_font.to_string())
        button.get_child().modify_font(button.selected_font)
    parent.dlgFont.hide()


class Wconfig(SimpleGladeApp):
    def __init__(self, path="gnome-connection-manager.glade",
                 root="wConfig",
                 domain=DOMAIN_NAME, **kwargs):
        path = os.path.join(GLADE_DIR, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

    # -- Wconfig.new {
    def new(self):
        # Agregar controles
        self.tblGeneral = self.get_widget("tblGeneral")
        self.btnFColor = self.get_widget("btnFColor")
        self.btnBColor = self.get_widget("btnBColor")
        self.btnFont = self.get_widget("btnFont")
        self.lblFont = self.get_widget("lblFont")
        self.treeCmd = self.get_widget("treeCommands")
        self.treeCustom = self.get_widget("treeCustom")
        self.dlgColor = None
        self.capture_keys = False

        self.tblGeneral.rows = 0
        self.addParam(_("Separador de Palabras"), "Config.WORD_SEPARATORS", str)
        self.addParam(_(u"Tamaño del buffer"), "Config.BUFFER_LINES", int, 1, 1000000)
        self.addParam(_("Transparencia"), "Config.TRANSPARENCY", int, 0, 100)
        self.addParam(_("Ruta de logs"), "Config.LOG_PATH", str)
        self.addParam(_("Abrir consola local al inicio"), "Config.STARTUP_LOCAL", bool)
        self.addParam(_(u"Pegar con botón derecho"), "Config.PASTE_ON_RIGHT_CLICK", bool)
        self.addParam(_(u"Copiar selección al portapapeles"), "Config.AUTO_COPY_SELECTION", bool)
        self.addParam(_("Confirmar al cerrar una consola"), "Config.CONFIRM_ON_CLOSE_TAB", bool)
        self.addParam(_("Cerrar consola"), "Config.AUTO_CLOSE_TAB", list,
                      [_("Nunca"), _("Siempre"), _(u"Sólo si no hay errores")])
        self.addParam(_("Confirmar al salir"), "Config.CONFIRM_ON_EXIT", bool)
        self.addParam(_("Comprobar actualizaciones"), "Config.CHECK_UPDATES", bool)
        self.addParam(_(u"Ocultar botón donar"), "Config.HIDE_DONATE", bool)

        if len(Config.FONT_COLOR) == 0:
            self.get_widget("chkDefaultColors").set_active(True)
            self.btnFColor.set_sensitive(False)
            self.btnBColor.set_sensitive(False)
            fcolor = "#FFFFFF"
            bcolor = "#000000"
        else:
            self.get_widget("chkDefaultColors").set_active(False)
            self.btnFColor.set_sensitive(True)
            self.btnBColor.set_sensitive(True)
            fcolor = Config.FONT_COLOR
            bcolor = Config.BACK_COLOR

        self.btnFColor.set_color(gtk.gdk.Color(fcolor))
        self.btnBColor.set_color(gtk.gdk.Color(bcolor))
        self.btnFColor.selected_color = fcolor
        self.btnBColor.selected_color = bcolor

        # Fuente
        if len(Config.FONT) == 0 or Config.FONT == 'monospace':
            Config.FONT = 'monospace'
        else:
            self.chkDefaultFont.set_active(False)
        self.btnFont.selected_font = pango.FontDescription(Config.FONT)
        self.btnFont.set_label(self.btnFont.selected_font.to_string())
        self.btnFont.get_child().modify_font(self.btnFont.selected_font)

        # commandos
        self.treeModel = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeCmd.set_model(self.treeModel)
        column = gtk.TreeViewColumn(_(u"Acción"), gtk.CellRendererText(), text=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_expand(True)
        self.treeCmd.append_column(column)

        renderer = gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.treeModel, 1)
        renderer.connect('editing-started', self.on_editing_started, self.treeModel, 1)
        column = gtk.TreeViewColumn(_("Atajo"), renderer, text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_expand(False)
        self.treeCmd.append_column(column)

        self.treeModel2 = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeCustom.set_model(self.treeModel2)
        renderer = MultilineCellRenderer()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.treeModel2, 0)
        column = gtk.TreeViewColumn(_("Comando"), renderer, text=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_expand(True)
        self.treeCustom.append_column(column)
        renderer = gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.treeModel2, 1)
        renderer.connect('editing-started', self.on_editing_started, self.treeModel2, 1)
        column = gtk.TreeViewColumn(_("Atajo"), renderer, text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_expand(False)
        self.treeCustom.append_column(column)

        slist = sorted(shortcuts.iteritems(), key=lambda (k, v): (v, k))

        for s in slist:
            if type(s[1]) == list:
                self.treeModel.append(None, [s[1][0], s[0]])
        for s in slist:
            if type(s[1]) != list:
                self.treeModel2.append(None, [s[1], s[0]])

        self.treeModel2.append(None, ['', ''])

    # -- Wconfig.new }

    # -- Wconfig custom methods {
    def addParam(self, name, field, ptype, *args):
        x = self.tblGeneral.rows
        self.tblGeneral.rows += 1
        value = eval(field)
        if ptype == bool:
            obj = gtk.CheckButton()
            obj.set_label(name)
            obj.set_active(value)
            obj.set_alignment(0, 0.5)
            obj.show()
            obj.field = field
            self.tblGeneral.attach(obj, 0, 2, x, x + 1, gtk.EXPAND | gtk.FILL, 0)
        elif ptype == int:
            obj = gtk.SpinButton(climb_rate=10)
            if len(args) == 2:
                obj.set_range(args[0], args[1])
            obj.set_increments(1, 10)
            obj.set_numeric(True)
            obj.set_value(value)
            obj.show()
            obj.field = field
            lbl = gtk.Label(name)
            lbl.set_alignment(0, 0.5)
            lbl.show()
            self.tblGeneral.attach(lbl, 0, 1, x, x + 1, gtk.FILL, 0)
            self.tblGeneral.attach(obj, 1, 2, x, x + 1, gtk.EXPAND | gtk.FILL, 0)
        elif ptype == list:
            obj = gtk.combo_box_new_text()
            for s in args[0]:
                obj.append_text(s)
            obj.set_active(value)
            obj.show()
            obj.field = field
            lbl = gtk.Label(name)
            lbl.set_alignment(0, 0.5)
            lbl.show()
            self.tblGeneral.attach(lbl, 0, 1, x, x + 1, gtk.FILL, 0)
            self.tblGeneral.attach(obj, 1, 2, x, x + 1, gtk.EXPAND | gtk.FILL, 0)
        else:
            obj = gtk.Entry()
            obj.set_text(value)
            obj.show()
            obj.field = field
            lbl = gtk.Label(name)
            lbl.set_alignment(0, 0.5)
            lbl.show()
            self.tblGeneral.attach(lbl, 0, 1, x, x + 1, gtk.FILL, 0)
            self.tblGeneral.attach(obj, 1, 2, x, x + 1, gtk.EXPAND | gtk.FILL, 0)

    def on_edited(self, widget, rownum, value, model, colnum):
        model[rownum][colnum] = value
        if model == self.treeModel2:
            i = self.treeModel2.get_iter_first()
            while i != None:
                j = self.treeModel2.iter_next(i)
                self.treeModel2[i]
                if self.treeModel2[i][0] == self.treeModel2[i][1] == "":
                    self.treeModel2.remove(i)
                i = j
            self.treeModel2.append(None, ['', ''])
            if self.capture_keys:
                self.capture_keys = False

    def on_editing_started(self, widget, entry, rownum, model, colnum):
        self.capture_keys = True
        entry.connect('key-press-event', self.on_treeCommands_key_press_event, model, rownum, colnum)

    # -- Wconfig custom methods }

    # -- Wconfig.on_cancelbutton1_clicked {
    def on_cancelbutton1_clicked(self, widget, *args):
        self.get_widget("wConfig").destroy()

    # -- Wconfig.on_cancelbutton1_clicked }

    # -- Wconfig.on_okbutton1_clicked {
    def on_okbutton1_clicked(self, widget, *args):
        for obj in self.tblGeneral:
            if hasattr(obj, "field"):
                if isinstance(obj, gtk.CheckButton):
                    value = obj.get_active()
                elif isinstance(obj, gtk.SpinButton):
                    value = obj.get_value_as_int()
                elif isinstance(obj, gtk.ComboBox):
                    value = obj.get_active()
                else:
                    value = '"%s"' % (obj.get_text())
                exec ("%s=%s" % (obj.field, value))

        if self.get_widget("chkDefaultColors").get_active():
            Config.FONT_COLOR = ""
            Config.BACK_COLOR = ""
        else:
            Config.FONT_COLOR = self.btnFColor.selected_color
            Config.BACK_COLOR = self.btnBColor.selected_color

        if self.btnFont.selected_font.to_string() != 'monospace' and not self.chkDefaultFont.get_active():
            Config.FONT = self.btnFont.selected_font.to_string()
        else:
            Config.FONT = ''

        # Guardar shortcuts
        scuts = {}
        for x in self.treeModel:
            if x[0] != '' and x[1] != '':
                scuts[x[1]] = [x[0]]
        for x in self.treeModel2:
            if x[0] != '' and x[1] != '':
                scuts[x[1]] = x[0]
        global shortcuts
        shortcuts = scuts

        # Boton donate
        global wMain
        if Config.HIDE_DONATE:
            wMain.get_widget("btnDonate").hide_all()
        else:
            wMain.get_widget("btnDonate").show_all()

        # Recrear menu de comandos personalizados
        wMain.populateCommandsMenu()
        wMain.writeConfig()

        self.get_widget("wConfig").destroy()

    # -- Wconfig.on_okbutton1_clicked }

    # -- Wconfig.on_btnBColor_clicked {
    def on_btnBColor_clicked(self, widget, *args):
        widget.selected_color = widget.get_color().to_string()

    # -- Wconfig.on_btnBColor_clicked }

    # -- Wconfig.on_btnFColor_clicked {
    def on_btnFColor_clicked(self, widget, *args):
        widget.selected_color = widget.get_color().to_string()

    # -- Wconfig.on_btnFColor_clicked }

    # -- Wconfig.on_chkDefaultColors_toggled {
    def on_chkDefaultColors_toggled(self, widget, *args):
        self.btnFColor.set_sensitive(not widget.get_active())
        self.btnBColor.set_sensitive(not widget.get_active())

    # -- Wconfig.on_chkDefaultColors_toggled }

    # -- Wconfig.on_chkDefaultFont_toggled {
    def on_chkDefaultFont_toggled(self, widget, *args):
        self.btnFont.set_sensitive(not widget.get_active())
        self.lblFont.set_sensitive(not widget.get_active())

    # -- Wconfig.on_chkDefaultFont_toggled }

    # -- Wconfig.on_btnFont_clicked {
    def on_btnFont_clicked(self, widget, *args):
        show_font_dialog(self, _("Seleccione la fuente"), self.btnFont)

    # -- Wconfig.on_btnFont_clicked }

    # -- Wconfig.on_treeCommands_key_press_event {
    def on_treeCommands_key_press_event(self, widget, event, *args):
        if self.capture_keys and len(args) == 3 and (event.keyval != gtk.keysyms.Return or
                                                             event.state != 0):
            model, rownum, colnum = args
            widget.set_text(get_key_name(event))
            # -- Wconfig.on_treeCommands_key_press_event }


class MultilineCellRenderer(gtk.CellRendererText):
    __gtype_name__ = "MultilineCellRenderer"

    def __init__(self):
        gtk.CellRendererText.__init__(self)
        self._in_editor_menu = False

    def _on_editor_focus_out_event(self, editor, *args):
        if self._in_editor_menu: return
        editor.remove_widget()
        self.emit("editing-canceled")

    def _on_editor_key_press_event(self, editor, event):
        if event.state & (gtk.gdk.SHIFT_MASK | gtk.gdk.CONTROL_MASK): return
        if event.keyval in (gtk.keysyms.Return, gtk.keysyms.KP_Enter):
            editor.remove_widget()
            self.emit("edited", editor.get_data("path"), editor.get_text())
        elif event.keyval == gtk.keysyms.Escape:
            editor.remove_widget()
            self.emit("editing-canceled")

    def _on_editor_populate_popup(self, editor, menu):
        self._in_editor_menu = True

        def on_menu_unmap(menu, self):
            self._in_editor_menu = False

        menu.connect("unmap", on_menu_unmap, self)

    def do_start_editing(self, event, widget, path, bg_area, cell_area, flags):
        editor = CellTextView()
        editor.modify_font(self.props.font_desc)
        editor.set_text(self.props.text)
        editor.set_size_request(cell_area.width, cell_area.height)
        editor.set_border_width(min(self.props.xpad, self.props.ypad))
        editor.set_data("path", path)
        editor.connect("focus-out-event", self._on_editor_focus_out_event)
        editor.connect("key-press-event", self._on_editor_key_press_event)
        editor.connect("populate-popup", self._on_editor_populate_popup)
        editor.show()
        return editor


class CellTextView(gtk.TextView, gtk.CellEditable):
    __gtype_name__ = "CellTextView"

    __gproperties__ = {
        'editing-canceled': (bool, 'Editing cancelled', 'Editing was cancelled', False, gobject.PARAM_READWRITE),
    }

    def do_editing_done(self, *args):
        self.remove_widget()

    def do_remove_widget(self, *args):
        pass

    def do_start_editing(self, *args):
        pass

    def get_text(self):
        text_buffer = self.get_buffer()
        bounds = text_buffer.get_bounds()
        return text_buffer.get_text(*bounds)

    def set_text(self, text):
        self.get_buffer().set_text(text)