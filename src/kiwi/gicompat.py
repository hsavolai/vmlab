import sys

def install_compat():
    from gi.repository import Gtk
    from gi.repository import Gdk
    from gi.repository import GdkPixbuf
    sys.modules['gtk'] = Gtk
    sys.modules['gtk.gdk'] = Gdk
    Gtk.gdk = Gdk
    Gtk.keysyms = Gdk
    Gdk.Pixbuf = GdkPixbuf.Pixbuf

    def pixbuf_new_from_file(filename):
        return GdkPixbuf.Pixbuf()
    Gdk.pixbuf_new_from_file = pixbuf_new_from_file

    Gtk.gtk_version = (Gtk.get_major_version(),
                       Gtk.get_minor_version(),
                       Gtk.get_micro_version())

    Gtk.widget_get_default_direction = Gtk.Widget.get_default_direction

    class GenericCellRenderer(Gtk.CellRenderer):
        pass
    Gtk.GenericCellRenderer = GenericCellRenderer

    # Enums
    Gtk.ICON_SIZE_MENU = Gtk.IconSize.MENU
    Gtk.JUSTIFY_LEFT = Gtk.Justification.LEFT
    Gtk.JUSTIFY_RIGHT = Gtk.Justification.RIGHT
    Gtk.POS_RIGHT = Gtk.PositionType.RIGHT
    Gtk.POLICY_AUTOMATIC = Gtk.PolicyType.AUTOMATIC
    Gtk.POLICY_ALWAYS = Gtk.PolicyType.ALWAYS
    Gtk.SELECTION_BROWSE = Gtk.SelectionMode.BROWSE
    Gtk.SELECTION_NONE = Gtk.SelectionMode.NONE
    Gtk.SORT_ASCENDING = Gtk.SortType.ASCENDING
    Gtk.SHADOW_ETCHED_IN = Gtk.ShadowType.ETCHED_IN
    Gtk.STATE_NORMAL = Gtk.StateType.NORMAL
    Gdk.BUTTON_PRESS = Gdk.EventType.BUTTON_PRESS
    Gtk.TEXT_DIR_RTL = Gtk.TextDirection.RTL

try:
    import gi
except ImportError:
    gi = None

if gi:
    install_compat()
