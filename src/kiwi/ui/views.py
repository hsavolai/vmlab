#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2001-2006 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
#
# Author(s): Christian Reis <kiko@async.com.br>
#            Jon Nelson <jnelson@securepipe.com>
#            Lorenzo Gil Sanchez <lgs@sicem.biz>
#            Johan Dahlin <jdahlin@async.com.br>
#            Henrique Romano <henrique@async.com.br>
#

"""
Defines the View classes that are included in the Kiwi Framework, which
are the base of Delegates and Proxies.
"""

import os
import re
import string

import gobject
import gtk
from gtk import gdk

from kiwi.environ import environ
from kiwi.interfaces import IValidatableProxyWidget
from kiwi.log import Logger
from kiwi.python import namedAny
from kiwi.utils import gsignal, type_register
from kiwi.ui.gadgets import quit_if_last
from kiwi.ui.proxy import Proxy

log = Logger('kiwi.view')

_non_interactive = (
    gtk.Label,
    gtk.Alignment,
    gtk.AccelLabel,
    gtk.Arrow,
    gtk.EventBox,
    gtk.Fixed,
    gtk.Frame,
    gtk.HBox,
    gtk.HButtonBox,
    gtk.HPaned,
    gtk.HSeparator,
    gtk.Layout,
    gtk.Progress,
    gtk.ProgressBar,
    gtk.ScrolledWindow,
    gtk.Table,
    gtk.VBox,
    gtk.VButtonBox,
    gtk.VPaned,
    gtk.VSeparator,
    gtk.Window,
)

color_red = gdk.color_parse('red')
color_black = gdk.color_parse('black')

#
# Signal brokers
#

method_regex = re.compile(r'^(on|after)_(\w+)__(\w+)$')

class SignalBroker(object):
    def __init__(self, view, controller):
        methods = controller._get_all_methods()
        self._do_connections(view, methods)

    def _do_connections(self, view, methods):
        """This method allows subclasses to add more connection mechanism"""
        self._autoconnect_by_method_name(view, methods)

    def _autoconnect_by_method_name(self, view, methods):
        """
        Offers autoconnection of widget signals based on function names.
        You simply need to define your controller method in the format::

            def on_widget_name__signal_name(self, widget):

        In other words, start the method by "on_", followed by the
        widget name, followed by two underscores ("__"), followed by the
        signal name. Note: If more than one double underscore sequences
        are in the string, the last one is assumed to separate the
        signal name.
        """
        self._autoconnected = {}

        for fname in methods.keys():
            # `on_x__y' has 7 chars and is the smallest possible handler
            if len(fname) < 7:
                continue
            match = method_regex.match(fname)
            if match is None:
                continue
            on_after, w_name, signal = match.groups()
            widget = getattr(view, w_name, None)
            if widget is None:
                raise AttributeError("couldn't find widget %s in %s"
                                     % (w_name, view))
            if not isinstance(widget, gobject.GObject):
                raise AttributeError("%s (%s) is not a widget or an action "
                                     "and can't be connected to"
                                     % (w_name, widget))
            # Must use getattr; using the class method ends up with it
            # being called unbound and lacking, thus, "self".
            try:
                if on_after == 'on':
                    signal_id = widget.connect(signal, methods[fname])
                elif on_after == 'after':
                    signal_id = widget.connect_after(signal, methods[fname])
                else:
                    raise AssertionError
            except TypeError, e:
                raise TypeError("Widget %s doesn't provide a signal %s" % (
                                widget.__class__, signal))
            self._autoconnected.setdefault(widget, []).append((
                signal, signal_id))

    def handler_block(self, widget, signal_name):
        signals = self._autoconnected
        if not widget in signals:
            return

        for signal, signal_id in signals[widget]:
            if signal_name is None or signal == signal_name:
                widget.handler_block(signal_id)

    def handler_unblock(self, widget, signal_name):
        signals = self._autoconnected
        if not widget in signals:
            return

        for signal, signal_id in signals[widget]:
            if signal_name is None or signal == signal_name:
                widget.handler_unblock(signal_id)

    def disconnect_autoconnected(self):
        for widget, signals in self._autoconnected.items():
            for signal in signals:
                widget.disconnect(signal[1])

class GladeSignalBroker(SignalBroker):
    def _do_connections(self, view, methods):
        super(GladeSignalBroker, self)._do_connections(view, methods)
        self._connect_glade_signals(view, methods)

    def _connect_glade_signals(self, view, methods):
        # mainly because the two classes cannot have a common base
        # class. studying the class layout carefully or using
        # composition may be necessary.

        # called by framework.basecontroller. takes a controller, and
        # creates the dictionary to attach to the signals in the tree.
        if not methods:
            raise AssertionError("controller must be provided")

        dict = {}
        for name, method in methods.items():
            if callable(method):
                dict[name] = method
        view._glade_adaptor.signal_autoconnect(dict)


class SlaveView(gobject.GObject):
    """
    Base class for all View classes. Defines the essential class
    attributes (controller, toplevel, widgets) and handles
    initialization of toplevel and widgets.  Once
    AbstractView.__init__() has been called, you can be sure
    self.toplevel and self.widgets are sane and processed.

    When a controller is associated with a View (the view should be
    passed in to its constructor) it will try and call a hook in the
    View called _attach_callbacks. See AbstractGladeView for an example
    of this method.
    """
    controller = None
    toplevel = None
    widgets = []
    toplevel_name = None
    gladefile = None
    domain = None

    # This signal is emited when the view wants to return a result value
    gsignal("result", object)

    # This is emitted when validation changed for a view
    # Used by parents views to know when child slaves changes
    gsignal('validation-changed', bool)

    def __init__(self, toplevel=None, widgets=None, gladefile=None,
                 toplevel_name=None, domain=None):
        """ Creates a new SlaveView. Sets up self.toplevel and self.widgets
        and checks for reserved names.
        """
        gobject.GObject.__init__(self)

        self._broker = None
        self.slaves = {}
        self._proxies = []
        self._valid = True

        # slave/widget name -> validation status
        self._validation = {}

        # stores the function that will be called when widgets
        # validity is checked
        self._validate_function = None

        # setup the initial state with the value of the arguments or the
        # class variables
        klass = type(self)
        self.toplevel = toplevel or klass.toplevel
        self.widgets = widgets or klass.widgets
        self.gladefile = gladefile or klass.gladefile
        self.toplevel_name = (toplevel_name or
                              klass.toplevel_name or
                              self.gladefile)
        self.domain = domain or klass.domain

        self._check_reserved()
        self._glade_adaptor = self.get_glade_adaptor()
        self.toplevel = self._get_toplevel()

        # grab the accel groups
        self._accel_groups = gtk.accel_groups_from_object(self.toplevel)

        # XXX: support normal widgets
        # notebook page label widget ->
        #   dict (slave name -> validation status)
        self._notebook_validation = {}
        self._notebooks = self._get_notebooks()

    def _get_notebooks(self):
        if not self._glade_adaptor:
            return []

        return [widget for widget in self._glade_adaptor.get_widgets()
                           if isinstance(widget, gtk.Notebook)]

    def _check_reserved(self):
        for reserved in ["widgets", "toplevel", "gladefile",
                         "tree", "model", "controller"]:
            # XXX: take into account widget constructor?
            if reserved in self.widgets:
                raise ValueError(
                    "The widgets list for %s contains a widget named `%s', "
                    "which is a reserved. name""" % (self, reserved))

    def _get_toplevel(self):
        toplevel = self.toplevel
        if not toplevel and self.toplevel_name:
            toplevel = self.get_widget(self.toplevel_name)

        if not toplevel:
            raise TypeError("A View requires an instance variable "
                            "called toplevel that specifies the "
                            "toplevel widget in it")

        if isinstance(toplevel, gtk.Window):
            if toplevel.flags() & gtk.VISIBLE:
                log.warn("Toplevel widget %s (%s) is visible; that's probably "
                         "wrong" % (toplevel, toplevel.get_name()))

        return toplevel

    def get_glade_adaptor(self):
        """Special init code that subclasses may want to override."""
        if not self.gladefile:
            return

        glade_adaptor = _open_glade(self, self.gladefile, self.domain)

        container_name = self.toplevel_name
        if not container_name:
            raise ValueError(
                "You provided a gladefile %s to grab the widgets from "
                "but you didn't give me a toplevel/container name!" %
                self.gladefile)

        # a SlaveView inside a glade file needs to come inside a toplevel
        # window, so we pull our slave out from it, grab its groups and
        # muerder it later
        shell = glade_adaptor.get_widget(container_name)
        if not isinstance(shell, gtk.Window):
            raise TypeError("Container %s should be a Window, found %s" % (
                container_name, type(shell)))

        self.toplevel = shell.get_child()
        shell.remove(self.toplevel)
        shell.destroy()

        return glade_adaptor

    #
    # Hooks
    #

    def on_attach(self, parent):
        """ Hook function called when attach_slave is performed on slave views.
        """
        pass

    def on_startup(self):
        """
        This is a virtual method that can be customized by classes that
        want to perform additional initalization after a controller has
        been set for it.  If you need this, add this method to your View
        subclass and BaseController will call it when the controller is
        set to the proxy."""
        pass

    #
    # Accessors
    #

    def get_toplevel(self):
        """Returns the toplevel widget in the view"""
        return self.toplevel

    def enable_window_controls(self):
        """Enables the dialog to have the same controls as a window (eg
        minimize, maximize and close buttons in its title bar).
        This method should be called before the window becomes visible.
        """
        toplevel = self.get_toplevel()
        toplevel.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_NORMAL)

    def get_widget(self, name):
        """Retrieves the named widget from the View"""
        name = string.replace(name, '.', '_')

        if self._glade_adaptor:
            widget = self._glade_adaptor.get_widget(name)
        else:
            widget = getattr(self, name, None)

        if widget is None:
            raise AttributeError("Widget %s not found in view %s"
                                 % (name, self))
        if not isinstance(widget, gtk.Widget):
            raise TypeError("%s in view %s is not a Widget"
                            % (name, self))
        return widget

    def set_controller(self, controller):
        """
        Sets the view's controller, checking to see if one has already
        been set before."""
        # Only one controller per view, please
        if self.controller:
            raise AssertionError("This view already has a controller: %s"
                                 % self.controller)
        self.controller = controller

    #
    # GTK+ proxies and convenience functions
    #

    def show_and_loop(self, parent=None):
        """
        Runs show() and runs the GTK+ event loop. If the parent
        argument is supplied and is a valid view, this view is set as a
        transient for the parent view

        @param parent:
        """

        self.show()
        if parent:
            self.set_transient_for(parent)
        gtk.main()

    def show(self, *args):
        """Shows the toplevel widget"""
        self.toplevel.show()

    def show_all(self, *args):
        """Shows all widgets attached to the toplevel widget"""
        if self._glade_adaptor is not None:
            raise AssertionError("You don't want to call show_all on a "
                                 "SlaveView. Use show() instead.")
        self.toplevel.show_all()

    def focus_toplevel(self):
        """Focuses the toplevel widget in the view"""
        # XXX: warn if there is no GdkWindow
        if self.toplevel and self.toplevel.window is not None:
            self.toplevel.grab_focus()

    def focus_topmost(self, widgets=None):
        """
        Looks through widgets specified (if no widgets are specified,
        look through all widgets attached to the view and sets focus to
        the widget that is rendered in the position closest to the view
        window's top and left

            - widgets: a list of widget names to be searched through
        """
        widget = self.get_topmost_widget(widgets, can_focus=True)
        if widget is not None:
            widget.grab_focus()
        # So it can be idle_added safely
        return False

    def get_topmost_widget(self, widgets=None, can_focus=False):
        """
        A real hack; returns the widget that is most to the left and
        top of the window.

            - widgets: a list of widget names.  If widgets is supplied,
              it only checks in the widgets in the list; otherwise, it
              looks at the widgets named in self.widgets, or, if
              self.widgets is None, looks through all widgets attached
              to the view.

            - can_focus: boolean, if set only searches through widget
              that can be focused
        """
        # XXX: recurse through containers from toplevel widget, better
        # idea and will work.
        widgets = widgets or self.widgets or self.__dict__.keys()
        top_widget = None
        for widget_name in widgets:
            widget = getattr(self, widget_name)
            if not isinstance(widget, gtk.Widget):
                continue
            if not widget.flags() & gtk.REALIZED:
                # If widget isn't realized but we have a toplevel
                # window, it's safe to realize it. If this check isn't
                # performed, we get a crash as per
                # http://bugzilla.gnome.org/show_bug.cgi?id=107872
                if isinstance(widget.get_toplevel(), gtk.Window):
                    widget.realize()
                else:
                    log.warn("get_topmost_widget: widget %s was not realized"
                             % widget_name)
                    continue
            if can_focus:
                # Combos don't focus, but their entries do
                if isinstance(widget, gtk.Combo):
                    widget = widget.entry
                if not widget.flags() & gtk.CAN_FOCUS or \
                    isinstance(widget, (gtk.Label, gtk.HSeparator,
                                        gtk.VSeparator, gtk.Window)):
                    continue

            if top_widget:
                allocation = widget.allocation
                top_allocation = getattr(top_widget, 'allocation',  None)
                assert top_allocation != None
                if (top_allocation[0] + top_allocation[1] >
                    allocation[0] + allocation[1]):
                    top_widget = widget
            else:
                top_widget = widget
        return top_widget

    #
    # Callback handling
    #

    def _attach_callbacks(self, controller):
        if self._glade_adaptor is None:
            brokerclass = SignalBroker
        else:
            brokerclass = GladeSignalBroker

        self._broker = brokerclass(self, controller)

        if self.toplevel:
            self.toplevel.connect("key-press-event", controller.on_key_press)

    #
    # Slave handling
    #

    def attach_slave(self, name, slave, placeholder_widget=None):
        """Attaches a slaveview to the current view, substituting the
        widget specified by placeholder_widget. If placeholder_widget is not
        specified, an widget with the name specified must exist.

        The widget specified *must* be a eventbox; its child widget will be
        removed and substituted for the specified slaveview's toplevel widget::

         .-----------------------. the widget that is indicated in the diagram
         |window/view (self.view)| as placeholder will be substituted for the
         |  .----------------.   | slaveview's toplevel.
         |  | eventbox (name)|   |  .-----------------.
         |  |.--------------.|      |slaveview (slave)|
         |  || placeholder  <----.  |.---------------.|
         |  |'--------------'|    \___ toplevel      ||
         |  '----------------'   |  ''---------------'|
         '-----------------------'  '-----------------'

        the original way of attachment (naming the *child* widget
        instead of the eventbox) is still supported for compatibility
        reasons but will print a warning.
        """
        log('%s: Attaching slave %s of type %s' % (self.__class__.__name__,
                                                   name,
                                                   slave.__class__.__name__))

        if name in self.slaves:
            # XXX: TypeError
            log.warn("A slave with name %s is already attached to %r"  % (
                name, self))
        self.slaves[name] = slave

        if not isinstance(slave, SlaveView):
            raise TypeError("slave must be a SlaveView, not a %s" %
                            type(slave))

        shell = slave.get_toplevel()

        if isinstance(shell, gtk.Window): # view with toplevel window
            new_widget = shell.get_child()
            shell.remove(new_widget) # remove from window to allow reparent
        else: # slaveview
            new_widget = shell

        placeholder = placeholder_widget or self.get_widget(name)
        placeholder.set_data('kiwi::slave', self)

        if not placeholder:
            raise AttributeError(
                  "slave container widget `%s' not found" % name)
        parent = placeholder.get_parent()

        if slave._accel_groups:
            # take care of accelerator groups; attach to parent window if we
            # have one; if embedding a slave into another slave, store its
            # accel groups; otherwise complain if we're dropping the
            # accelerators
            win = parent.get_toplevel()
            if isinstance(win, gtk.Window):
                # use idle_add to be sure we attach the groups as late
                # as possible and avoid reattaching groups -- see
                # comment in _attach_groups.
                gtk.idle_add(self._attach_groups, win, slave._accel_groups)
            elif isinstance(self, SlaveView):
                self._accel_groups.extend(slave._accel_groups)
            else:
                log.warn("attached slave %s to parent %s, but parent lacked "
                         "a window and was not a slave view" % (slave, self))
            slave._accel_groups = []

        # Merge the sizegroups of the slave that is being attached  with the
        # sizegroups of where it is being attached to. Only the sizegroups
        # with the same name will be merged.
        for sizegroup in slave.get_sizegroups():
            self._merge_sizegroup(sizegroup)

        if isinstance(placeholder, gtk.EventBox):
            # standard mechanism
            child = placeholder.get_child()
            if child is not None:
                placeholder.remove(child)
            placeholder.set_visible_window(False)
            placeholder.add(new_widget)
        elif isinstance(parent, gtk.EventBox):
            # backwards compatibility
            log.warn("attach_slave's api has changed: read docs, update code!")
            parent.remove(placeholder)
            parent.add(new_widget)
        else:
            raise TypeError(
                "widget to be replaced must be wrapped in eventbox")

        # when attaching a slave we usually want it visible
        parent.show()
        # call slave's callback
        slave.on_attach(self)

        slave.connect('validation-changed',
                      self._on_child__validation_changed,
                      name)

        for notebook in self._notebooks:
            for child in notebook.get_children():
                if not shell.is_ancestor(child):
                    continue

                label = notebook.get_tab_label(child)
                slave.connect('validation-changed',
                              self._on_notebook_slave__validation_changed,
                              name, label)
                self._notebook_validation[label] = {}

        # Fire of an initial notification
        slave.check_and_notify_validity(force=True)

        # return placeholder we just removed
        return placeholder

    def get_sizegroups(self):
        """
        Get a list of sizegroups for the current view.
        """
        if not self._glade_adaptor:
            return []

        return self._glade_adaptor.get_sizegroups()

    def _merge_sizegroup(self, other_sizegroup):
        # Merge sizegroup from other with self that have the same name.
        # Actually, no merging is being done, since the old group is preserved

        name = other_sizegroup.get_data('gazpacho::object-id')
        if name is None:
            return
        sizegroup = getattr(self, name, None)
        if not sizegroup:
            return

        widgets = other_sizegroup.get_data('gazpacho::sizegroup-widgets')
        if not widgets:
            return

        for widget in widgets:
            sizegroup.add_widget(widget)

    def detach_slave(self, name):
        """
        Detatch a slave called name from view
        """
        if not name in self.slaves:
            raise LookupError("There is no slaved called %s attached to %r" %
                              (name, self))
        del self.slaves[name]

    def _attach_groups(self, win, accel_groups):
        # get groups currently attached to the window; we use them
        # to avoid reattaching an accelerator to the same window, which
        # generates messages like:
        #
        # gtk-critical **: file gtkaccelgroup.c: line 188
        # (gtk_accel_group_attach): assertion `g_slist_find
        # (accel_group->attach_objects, object) == null' failed.
        #
        # interestingly, this happens many times with notebook,
        # because libglade creates and attaches groups in runtime to
        # its toplevel window.
        current_groups = gtk.accel_groups_from_object(win)
        for group in accel_groups:
            if group in current_groups:
                # skip group already attached
                continue
            win.add_accel_group(group)

    def get_slave(self, holder):
        return self.slaves.get(holder)



    #
    # Signal connection
    #

    def connect_multiple(self, widgets, signal, handler, after=False):
        """
        Connect the same handler to the specified signal for a number of
        widgets.
            - widgets: a list of GtkWidgets
            - signal: a string specifying the signals
            - handler: a callback method
            - after: a boolean; if TRUE, we use connect_after(), otherwise,
            connect()
        """
        if not isinstance(widgets, (list, tuple)):
            raise TypeError("widgets must be a list, found %s" % widgets)
        for widget in widgets:
            if not isinstance(widget, gtk.Widget):
                raise TypeError(
                "Only Gtk widgets may be passed in list, found\n%s" % widget)
            if after:
                widget.connect_after(signal, handler)
            else:
                widget.connect(signal, handler)

    def disconnect_autoconnected(self):
        """
        Disconnect handlers previously connected with
        autoconnect_signals()"""
        self._broker.disconnect_autoconnected()

    def handler_block(self, widget, signal_name=None):
        # XXX: Warning, or bail out?
        if not self._broker:
            return
        self._broker.handler_block(widget, signal_name)

    def handler_unblock(self, widget, signal_name=None):
        if not self._broker:
            return
        self._broker.handler_unblock(widget, signal_name)

    #
    # Proxies
    #

    def add_proxy(self, model=None, widgets=None):
        """
        Add a proxy to this view that automatically update a model when
        the view changes. Arguments:

          - model. the object we are proxing. It can be None if we don't have
            a model yet and we want to display the interface and set it up with
            future models.
          - widgets. the list of widgets that contains model attributes to be
            proxied. If it is None (or not specified) it will be the whole list
            of widgets this View has.

        This method return a Proxy object that you may want to use to force
        updates or setting new models. Keep a reference to it since there is
        no way to get that proxy later on. You have been warned (tm)
        """
        log('%s: adding proxy for %s' % (
            self.__class__.__name__,
            model and model.__class__.__name__))

        widgets = widgets or self.widgets

        for widget_name in widgets:
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue

            if not IValidatableProxyWidget.providedBy(widget):
                continue

            try:
                widget.connect('validation-changed',
                               self._on_child__validation_changed,
                               widget_name)
            except TypeError:
                raise AssertionError("%r does not have a validation-changed "
                                     "signal." % widget)

        proxy = Proxy(self, model, widgets)
        self._proxies.append(proxy)
        return proxy

    #
    # Validation
    #

    def _on_child__validation_changed(self, child, value, name):
        # Children of the view, eg slaves or widgets are connected to
        # this signal. When validation changes of a validatable child
        # this callback is called
        if isinstance(child, gtk.Widget):
            # Force invisible and insensitive widgets to be valid
            if (not child.get_property('visible') or
                not child.get_property('sensitive')):
                value = True

        self._validation[name] = value

        self.check_and_notify_validity()

    def _on_notebook_slave__validation_changed(self, slave, value, name,
                                               label):
        if not label:
            return

        validation = self._notebook_validation[label]
        validation[name] = value

        is_valid = True
        if False in validation.values():
            is_valid = False

        if is_valid:
            color = color_black
        else:
            color = color_red

        # Only modify active state, since that's the (somewhat badly named)
        # state used for the pages which are not selected.
        label.modify_fg(gtk.STATE_ACTIVE, color)
        label.modify_fg(gtk.STATE_NORMAL, color)

    def check_and_notify_validity(self, force=False):
        # Current view is only valid if we have no invalid children
        # their status are stored as values in the dictionary
        is_valid = True
        if False in self._validation.values():
            is_valid = False

        # Check if validation really changed
        if self._valid == is_valid and force == False:
            return

        self._valid = is_valid
        self.emit('validation-changed', is_valid)

        # FIXME: Remove and update all callsites to use validation-changed
        if self._validate_function:
            self._validate_function(is_valid)

    def force_validation(self):
        self.check_and_notify_validity(force=True)

    def register_validate_function(self, function):
        """The signature of the validate function is:

        def function(is_valid):

        or, if it is a method:

        def function(self, is_valid):

        where the 'is_valid' parameter is True if all the widgets have
        valid data or False otherwise.
        """
        self._validate_function = function

type_register(SlaveView)

class BaseView(SlaveView):
    """A view with a toplevel window."""

    def __init__(self, toplevel=None, widgets=None, gladefile=None,
                 toplevel_name=None, domain=None, delete_handler=None):
        SlaveView.__init__(self, toplevel, widgets, gladefile, toplevel_name,
                           domain)

        if not isinstance(self.toplevel, gtk.Window):
            raise TypeError("toplevel widget must be a Window "
                            "(or inherit from it),\nfound `%s' %s"
                            % (toplevel, self.toplevel))
        self.toplevel.set_name(self.__class__.__name__)

        if delete_handler:
            id = self.toplevel.connect("delete-event", delete_handler)
            if not id:
                raise ValueError(
                    "Invalid delete handler provided: %s" % delete_handler)

    def get_glade_adaptor(self):
        if not self.gladefile:
            return

        return _open_glade(self, self.gladefile, self.domain)

    #
    # Hook for keypress handling
    #

    def _attach_callbacks(self, controller):
        super(BaseView, self)._attach_callbacks(controller)
        self._setup_keypress_handler(controller.on_key_press)

    def _setup_keypress_handler(self, keypress_handler):
        self.toplevel.connect_after("key_press_event", keypress_handler)

    #
    # Proxying for self.toplevel
    #
    def set_transient_for(self, view):
        """Makes the view a transient for another view; this is commonly done
        for dialogs, so the dialog window is managed differently than a
        top-level one.
        """
        if hasattr(view, 'toplevel') and isinstance(view.toplevel, gtk.Window):
            self.toplevel.set_transient_for(view.toplevel)
        # In certain cases, it is more convenient to send in a window;
        # for instance, in a deep slaveview hierarchy, getting the
        # top view is difficult. We used to print a warning here, I
        # removed it for convenience; we might want to put it back when
        # http://bugs.async.com.br/show_bug.cgi?id=682 is fixed
        elif isinstance(view, gtk.Window):
            self.toplevel.set_transient_for(view)
        else:
            raise TypeError("Parameter to set_transient_for should "
                            "be View (found %s)" % view)

    def set_title(self, title):
        """Sets the view's window title"""
        self.toplevel.set_title(title)

    #
    # Focus handling
    #

    def get_focus_widget(self):
        """Returns the currently focused widget in the window"""
        return self.toplevel.focus_widget

    def check_focus(self):
        """ Tests the focus in the window and prints a warning if no
        widget is focused.
        """
        focus = self.toplevel.focus_widget
        if focus:
            return
        values = self.__dict__.values()
        interactive = None
        # Check if any of the widgets is interactive
        for v in values:
            if (isinstance(v, gtk.Widget) and not
                isinstance(v, _non_interactive)):
                interactive = v
        if interactive:
            log.warn("No widget is focused in view %s but you have an "
                     "interactive widget in it: %s""" % (self, interactive))

    #
    # Window show/hide and mainloop manipulation
    #

    def hide(self, *args):
        """Hide the view's window"""
        self.toplevel.hide()

    def show_all(self, parent=None, *args):
        self.toplevel.show_all()
        self.show(parent, *args)

    def show(self, parent=None, *args):
        """Show the view's window.
        If the parent argument is supplied and is a valid view, this view
        is set as a transient for the parent view.
        """
        # Uniconize window if minimized
        self.toplevel.present() # this call win.show() for us
        self.check_focus()
        if parent is not None:
            self.set_transient_for(parent)

    def quit_if_last(self, *args):
        quit_if_last(*args)

    def hide_and_quit(self, *args):
        """Hides the current window and breaks the GTK+ event loop if this
        is the last window.
        Its method signature allows it to be used as a signal handler.
        """
        self.toplevel.hide()
        self.quit_if_last()

def _get_gazpacho():
    try:
        from kiwi.ui.gazpacholoader import GazpachoWidgetTree
    except ImportError:
        return
    return GazpachoWidgetTree

def _get_libglade():
    try:
        from kiwi.ui.libgladeloader import LibgladeWidgetTree
    except ImportError:
        return
    return LibgladeWidgetTree

def _get_gaxml():
    try:
        from kiwi.ui.gaxmlloader import GAXMLWidgetTree
    except ImportError:
        return
    return GAXMLWidgetTree

def _get_builder():
    try:
        from kiwi.ui.builderloader import BuilderWidgetTree
    except ImportError:
        return
    return BuilderWidgetTree

def _open_glade(view, gladefile, domain):
    if not gladefile:
        raise ValueError("A gladefile wasn't provided.")
    elif not isinstance(gladefile, basestring):
        raise TypeError(
              "gladefile should be a string, found %s" % type(gladefile))

    if gladefile.endswith('.ui'):
        directory = os.path.dirname(namedAny(view.__module__).__file__)
        gladefile = os.path.join(directory, gladefile)
    else:
        filename = os.path.splitext(os.path.basename(gladefile))[0]
        try:
            gladefile = environ.find_resource("glade", filename + '.glade')
        except EnvironmentError:
            gladefile = environ.find_resource("glade", filename + '.ui')


    fp = open(gladefile)
    sniff = fp.read(200)
    fp.close()

    if '<interface' in sniff:
        WidgetTree = _get_builder()
        loader_name = 'builder'
    # glade-2: <!DOCTYPE glade-interface SYSTEM "http://glade.gnome.org/glade-2.0.dtd">
    # glade-3: <!DOCTYPE glade-interface SYSTEM "glade-2.0.dtd">
    elif 'glade-2.0.dtd' in sniff:
        WidgetTree = _get_libglade()
        loader_name = 'libglade'
    elif 'gaxml-0.1.dtd' in sniff:
        WidgetTree = _get_gaxml()
        loader_name = 'gaxml'
    # gazpacho: <!DOCTYPE glade-interface SYSTEM "http://gazpacho.sicem.biz/gazpacho-0.1.dtd">
    elif 'gazpacho-0.1.dtd' in sniff:
        WidgetTree = _get_gazpacho()
        loader_name = 'gazpacho.loader'
    else:
        log.warning("Could not determine type/dtd of gladefile %s" % gladefile)
        # Defaulting to builder
        WidgetTree = _get_builder()
        loader_name = 'builder'

    # None means, failed to import
    if WidgetTree is None:
        raise RuntimeError(
            "Could not find %s, it needs to be installed to "
            "load the gladefile %r" % (loader_name, gladefile))

    return WidgetTree(view, gladefile, domain)
