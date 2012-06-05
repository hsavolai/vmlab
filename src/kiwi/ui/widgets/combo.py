#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2003-2006 Async Open Source
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
#            Lorenzo Gil Sanchez <lgs@sicem.biz>
#            Johan Dahlin <jdahlin@async.com.br>
#            Gustavo Rahal <gustavo@async.com.br>
#            Daniel Saran R. da Cunha <daniel@async.com.br>
#            Evandro Vale Miquelito <evandro@async.com.br>
#

"""GtkComboBox and GtkComboBoxEntry support for the Kiwi Framework.

The GtkComboBox and GtkComboBoxEntry classes here are also slightly extended
they contain methods to easily insert and retrieve data from combos.
"""

try:
    set
except AttributeError:
    from sets import Set as set

import gobject
import gtk
from gtk import keysyms

from kiwi import ValueUnset
from kiwi.component import implements
from kiwi.datatypes import number
from kiwi.enums import ComboColumn, ComboMode
from kiwi.interfaces import IEasyCombo
from kiwi.python import deprecationwarn
from kiwi.ui.comboboxentry import BaseComboBoxEntry
from kiwi.ui.comboentry import ComboEntry
from kiwi.ui.proxywidget import ProxyWidgetMixin, ValidatableProxyWidgetMixin
from kiwi.ui.widgets.entry import ProxyEntry
from kiwi.utils import gsignal

class _EasyComboBoxHelper(object):

    implements(IEasyCombo)

    def __init__(self, combobox):
        """Call this constructor after the Combo one"""
        if not isinstance(combobox, (gtk.ComboBox, ComboEntry)):
            raise TypeError(
                "combo needs to be a gtk.ComboBox or ComboEntry instance")
        self._combobox = combobox

        model = gtk.ListStore(str, object)
        self._combobox.set_model(model)

        self.mode = ComboMode.UNKNOWN

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        if self.mode != ComboMode.UNKNOWN:
            raise AssertionError
        self.mode = mode

    def clear(self):
        """Removes all items from list"""
        model = self._combobox.get_model()
        model.clear()

    def prefill(self, itemdata, sort=False):
        if not isinstance(itemdata, (list, tuple)):
            raise TypeError("'data' parameter must be a list or tuple of item "
                            "descriptions, found %s" % (type(itemdata),))

        self.clear()
        if len(itemdata) == 0:
            return

        if self.mode == ComboMode.UNKNOWN:
            first = itemdata[0]
            if isinstance(first, basestring):
                self.set_mode(ComboMode.STRING)
            elif isinstance(first, (tuple, list)):
                self.set_mode(ComboMode.DATA)
            else:
                raise TypeError("Could not determine type, items must "
                                "be strings or tuple/list")

        mode = self.mode
        if mode not in (ComboMode.STRING, ComboMode.DATA):
            raise TypeError("Incorrect format for itemdata; see "
                            "docstring for more information")

        model = self._combobox.get_model()

        values = set()
        if mode == ComboMode.STRING:
            if sort:
                itemdata.sort()

            for item in itemdata:
                if item in values:
                    raise KeyError("Tried to insert duplicate value "
                                   "%s into Combo!" % (item,))
                values.add(item)

                model.append((item, None))
        elif mode == ComboMode.DATA:
            if sort:
                itemdata.sort(lambda x, y: cmp(x[0], y[0]))

            for item in itemdata:
                text, data = item
                orig = text
                count = 1
                while text in values:
                    text = orig + ' (%d)' % count
                    count += 1
                values.add(text)
                model.append((text, data))

    def append_item(self, label, data=None):
        """ Adds a single item to the Combo. Takes:
        - label: a string with the text to be added
        - data: the data to be associated with that item
        """
        if not isinstance(label, basestring):
            raise TypeError("label must be string, found %s" % (label,))

        if self.mode == ComboMode.UNKNOWN:
            if data is not None:
                self.set_mode(ComboMode.DATA)
            else:
                self.set_mode(ComboMode.STRING)

        model = self._combobox.get_model()
        if self.mode == ComboMode.STRING:
            if data is not None:
                raise TypeError("data can not be specified in string mode")
            model.append((label, None))
        elif self.mode == ComboMode.DATA:
            if data is None:
                raise TypeError("data must be specified in string mode")
            model.append((label, data))
        else:
            raise AssertionError

    def insert_item(self, position, label, data=None):
        """ Inserts a single item at a position to the Combo.
        @param position: position to insert the item at
        @param label: a string with the text to be added
        @param data: the data to be associated with that item
        """
        if not isinstance(label, basestring):
            raise TypeError("label must be string, found %s" % (label,))

        if self.mode == ComboMode.UNKNOWN:
            if data is not None:
                self.set_mode(ComboMode.DATA)
            else:
                self.set_mode(ComboMode.STRING)

        model = self._combobox.get_model()
        if self.mode == ComboMode.STRING:
            if data is not None:
                raise TypeError("data can not be specified in string mode")
            model.insert(position, (label, None))
        elif self.mode == ComboMode.DATA:
            if data is None:
                raise TypeError("data must be specified in string mode")
            model.insert(position, (label, data))
        else:
            raise AssertionError

    def select(self, data):
        mode = self.mode
        if self.mode == ComboMode.STRING:
            self.select_item_by_label(data)
        elif self.mode == ComboMode.DATA:
            self.select_item_by_data(data)
        else:
            # XXX: When setting the datatype to non string, automatically go to
            #      data mode
            raise TypeError("unknown ComboBox mode. Did you call prefill?")

    def select_item_by_position(self, pos):
        self._combobox.set_active(pos)

    def select_item_by_label(self, label):
        model = self._combobox.get_model()
        for row in model:
            if row[ComboColumn.LABEL] == label:
                self._combobox.set_active_iter(row.iter)
                break
        else:
            raise KeyError("No item correspond to label %r in the combo %s"
                           % (label, self._combobox.name))

    def select_item_by_data(self, data):
        if self.mode != ComboMode.DATA:
            raise TypeError("select_item_by_data can only be used in data mode")

        model = self._combobox.get_model()
        for row in model:
            if row[ComboColumn.DATA] == data:
                self._combobox.set_active_iter(row.iter)
                break
        else:
            raise KeyError("No item correspond to data %r in the combo %s"
                           % (data, self._combobox.name))

    def get_model_strings(self):
        return [row[ComboColumn.LABEL] for row in self._combobox.get_model()]

    def get_model_items(self):
        if self.mode != ComboMode.DATA:
            raise TypeError("get_model_items can only be used in data mode")

        model = self._combobox.get_model()
        items = {}
        for row in model:
            items[row[ComboColumn.LABEL]] = row[ComboColumn.DATA]

        return items

    def get_selected_label(self):
        iter = self._combobox.get_active_iter()
        if not iter:
            return

        model = self._combobox.get_model()
        return model[iter][ComboColumn.LABEL]

    def get_selected_data(self):
        if self.mode != ComboMode.DATA:
            raise TypeError("get_selected_data can only be used in data mode")

        iter = self._combobox.get_active_iter()
        if not iter:
            return

        model = self._combobox.get_model()
        return model[iter][ComboColumn.DATA]

    def get_selected(self):
        mode = self.mode
        if mode == ComboMode.STRING:
            return self.get_selected_label()
        elif mode == ComboMode.DATA:
            return self.get_selected_data()

        return None


class ProxyComboBox(gtk.ComboBox, ProxyWidgetMixin):

    __gtype_name__ = 'ProxyComboBox'
    allowed_data_types = (basestring, object) + number

    data_type = gobject.property(
        getter=ProxyWidgetMixin.get_data_type,
        setter=ProxyWidgetMixin.set_data_type,
        type=str, blurb='Data Type')
    model_attribute = gobject.property(type=str, blurb='Model attribute')
    gsignal('content-changed')
    gsignal('validation-changed', bool)
    gsignal('validate', object, retval=object)

    def __init__(self):
        gtk.ComboBox.__init__(self)
        ProxyWidgetMixin.__init__(self)
        self._helper = _EasyComboBoxHelper(self)
        self.connect('changed', self._on__changed)
        renderer = gtk.CellRendererText()
        self.pack_start(renderer)
        self.add_attribute(renderer, 'text', ComboColumn.LABEL)

    def __len__(self):
        # GtkComboBox is a GtkContainer subclass which implements __len__ in
        # PyGTK in 2.8 and higher. Therefor we need to provide our own
        # implementation to be backwards compatible and override the new
        # behavior in 2.8
        return len(self.get_model())

    def __nonzero__(self):
        return True

    # Callbacks

    def _on__changed(self, combo):
        self.emit('content-changed')

    # IProxyWidget

    def read(self):
        if self._helper.get_mode() == ComboMode.UNKNOWN:
            return ValueUnset

        data = self.get_selected()
        if self._helper.get_mode() == ComboMode.STRING:
            data = self._from_string(data)

        return data

    def update(self, data):
        # We dont need validation because the user always
        # choose a valid value

        if data is None or data is ValueUnset:
            return

        if self._helper.get_mode() == ComboMode.STRING:
            data = self._as_string(data)

        self.select(data)

    # IEasyCombo

    def prefill(self, itemdata, sort=False):
        """
        See L{kiwi.interfaces.IEasyCombo.prefill}
        """
        self._helper.prefill(itemdata, sort)

        # we always have something selected, by default the first item
        self.set_active(0)
        self.emit('content-changed')

    def clear(self):
        """
        See L{kiwi.interfaces.IEasyCombo.clear}
        """
        self._helper.clear()
        self.emit('content-changed')

    def append_item(self, label, data=None):
        """
        See L{kiwi.interfaces.IEasyCombo.append_item}
        """
        self._helper.append_item(label, data)

    def insert_item(self, position, label, data=None):
        """
        See L{kiwi.interfaces.IEasyCombo.insert_item}
        """
        self._helper.insert_item(position, label, data)

    def select(self, data):
        """
        See L{kiwi.interfaces.IEasyCombo.select}
        """
        self._helper.select(data)

    def select_item_by_position(self, pos):
        """
        See L{kiwi.interfaces.IEasyCombo.select}
        """
        self._helper.select_item_by_position(pos)

    def select_item_by_label(self, label):
        """
        See L{kiwi.interfaces.IEasyCombo.select_item_by_position}
        """
        self._helper.select_item_by_label(label)

    def select_item_by_data(self, data):
        """
        See L{kiwi.interfaces.IEasyCombo.select_item_by_label}
        """
        self._helper.select_item_by_data(data)

    def get_model_strings(self):
        """
        See L{kiwi.interfaces.IEasyCombo.select_item_by_data}
        """
        return self._helper.get_model_strings()

    def get_model_items(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_model_strings}
        """
        return self._helper.get_model_items()

    def get_selected_label(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_model_items}
        """
        return self._helper.get_selected_label()

    def get_selected_data(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_selected_label}
        """
        return self._helper.get_selected_data()

    def get_selected(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_selected_data}
        """
        return self._helper.get_selected()

class ProxyComboBoxEntry(BaseComboBoxEntry,
                         ValidatableProxyWidgetMixin):
    allowed_data_types = (basestring, object) + number
    __gtype_name__ = 'ProxyComboBoxEntry'
    data_type = gobject.property(
        getter=ProxyWidgetMixin.get_data_type,
        setter=ProxyWidgetMixin.set_data_type,
        type=str, blurb='Data Type')
    mandatory = gobject.property(type=bool, default=False)
    model_attribute = gobject.property(type=str, blurb='Model attribute')
    gsignal('content-changed')
    gsignal('validation-changed', bool)
    gsignal('validate', object, retval=object)

    # it doesn't make sense to connect to this signal
    # because we want to monitor the entry of the combo
    # not the combo box itself.

    def __init__(self, **kwargs):
        deprecationwarn(
            'ProxyComboBoxEntry is deprecated, use ProxyComboEntry instead',
            stacklevel=3)

        BaseComboBoxEntry.__init__(self)
        ValidatableProxyWidgetMixin.__init__(self, widget=self.entry)

        self._helper = _EasyComboBoxHelper(self)
        for key, value in kwargs.items():
            setattr(self.props, key, value)

        self.set_text_column(ComboColumn.LABEL)

        # here we connect the expose-event signal directly to the entry
        self.child.connect('changed', self._on_child_entry__changed)

        # HACK! we force a queue_draw because when the window is first
        # displayed the icon is not drawn.
        gobject.idle_add(self.queue_draw)

        self.set_events(gtk.gdk.KEY_RELEASE_MASK)
        self.connect("key-release-event", self._on__key_release_event)


    def __nonzero__(self):
        return True

    def __len__(self):
        return len(self.get_model())

    # Properties

    def _get_list_editable(self):
        if self._helper.get_mode() == ComboMode.DATA:
            return False

        return self.entry.get_editable()

    def _set_list_editable(self, value):
        if self._helper.get_mode() != ComboMode.DATA:
            self.entry.set_editable(value)

    list_editable = gobject.property(getter=_get_list_editable,
                                     setter=_set_list_editable,
                                     type=bool, default=True,
                                     nick="Editable")


    # Private

    def _update_selection(self, text=None):
        if text is None:
            text = self.entry.get_text()

        self.select_item_by_label(text)

    def _add_text_to_combo_list(self):
        text = self.entry.get_text()
        if not text.strip():
            return

        if text in self.get_model_strings():
            return

        self.entry.set_text('')
        self.append_item(text)
        self._update_selection(text)

    # Callbacks

    def _on__key_release_event(self, widget, event):
        """Checks for "Enter" key presses and add the entry text to
        the combo list if the combo list is set as editable.
        """
        if not self.list_editable:
            return

        if event.keyval in (keysyms.KP_Enter,
                            keysyms.Return):
            self._add_text_to_combo_list()

    def _on_child_entry__changed(self, widget):
        """Called when something on the entry changes"""
        if not widget.get_text():
            return

        self.emit('content-changed')

    # IProxyWidget

    def read(self):
        if self._helper.get_mode() == ComboMode.UNKNOWN:
            return ValueUnset
        return self.get_selected()

    def update(self, data):
        if data is ValueUnset or data is None:
            self.entry.set_text("")
        else:
            self.select(data)

    # IEasyCombo

    def prefill(self, itemdata, sort=False, clear_entry=True):
        """
        See L{kiwi.interfaces.IEasyCombo.prefill}
        """
        self._helper.prefill(itemdata, sort)
        if clear_entry:
            self.entry.set_text("")

        # setup the autocompletion
        auto = gtk.EntryCompletion()
        auto.set_model(self.get_model())
        auto.set_text_column(ComboColumn.LABEL)
        self.entry.set_completion(auto)

        # we always have something selected, by default the first item
        self.set_active(0)
        self.emit('content-changed')

    def clear(self):
        """
        See L{kiwi.interfaces.IEasyCombo.clear}
        """
        self._helper.clear()
        self.entry.set_text("")

    def append_item(self, label, data=None):
        """
        See L{kiwi.interfaces.IEasyCombo.append_item}
        """
        self._helper.append_item(label, data)

    def insert_item(self, position, label, data=None):
        """
        See L{kiwi.interfaces.IEasyCombo.insert_item}
        """
        self._helper.insert_item(position, label, data)

    def select(self, data):
        """
        See L{kiwi.interfaces.IEasyCombo.select}
        """
        self._helper.select(data)

    def select_item_by_position(self, pos):
        """
        See L{kiwi.interfaces.IEasyCombo.select}
        """
        self._helper.select_item_by_position(pos)

    def select_item_by_label(self, label):
        """
        See L{kiwi.interfaces.IEasyCombo.select_item_by_position}
        """
        self._helper.select_item_by_label(label)

    def select_item_by_data(self, data):
        """
        See L{kiwi.interfaces.IEasyCombo.select_item_by_label}
        """
        self._helper.select_item_by_data(data)

    def get_model_strings(self):
        """
        See L{kiwi.interfaces.IEasyCombo.select_item_by_data}
        """
        return self._helper.get_model_strings()

    def get_model_items(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_model_strings}
        """
        return self._helper.get_model_items()

    def get_selected_label(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_model_items}
        """
        return self._helper.get_selected_label()

    def get_selected_data(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_selected_label}
        """
        return self._helper.get_selected_data()

    def get_selected(self):
        """
        See L{kiwi.interfaces.IEasyCombo.get_selected_data}
        """
        return self._helper.get_selected()

    # Public API

    def set_mode(self, mode):
        # If we're in the transition to go from
        # unknown->label set editable to False
        if (self._helper.get_mode() == ComboMode.UNKNOWN and
            mode == ComboMode.DATA):
            self.entry.set_editable(False)

        self._helper.set_mode(self, mode)

class ProxyComboEntry(ComboEntry, ValidatableProxyWidgetMixin):
    __gtype_name__ = 'ProxyComboEntry'
    allowed_data_types = (basestring, object) + number

    data_type = gobject.property(
        getter=ProxyWidgetMixin.get_data_type,
        setter=ProxyWidgetMixin.set_data_type,
        type=str, blurb='Data Type')
    mandatory = gobject.property(type=bool, default=False)
    model_attribute = gobject.property(type=str, blurb='Model attribute')
    gsignal('content-changed')
    gsignal('validation-changed', bool)
    gsignal('validate', object, retval=object)

    def __init__(self):
        entry = ProxyEntry()
        ComboEntry.__init__(self, entry=entry)
        ValidatableProxyWidgetMixin.__init__(self)
        entry.connect('content-changed', self._on_entry__content_changed)
        entry.connect('validation-changed',
                       self._on_entry__validation_changed)

    def __nonzero__(self):
        return True

    def __len__(self):
        return len(self.get_model())

    # Properties

    def _get_list_editable(self):
        return self.entry.get_editable()

    def _set_list_editable(self, value):
        self.entry.set_editable(value)
    list_editable = gobject.property(getter=_get_list_editable,
                                     setter=_set_list_editable,
                                     type=bool, default=True,
                                     nick="Editable")

    # Callbacks

    def _on_entry__content_changed(self, entry):
        # We only need to listen for changes in the entry, it's updated
        # even if you select something in the popup list
        self.emit('content-changed')

    def _on_entry__validation_changed(self, entry, value):
        # Propagate entry's validity state
        self.emit('validation-changed', value)

    # IconEntry

    def set_tooltip(self, text):
        self.entry.set_tooltip(text)

    # IProxyWidget

    def read(self):
        return self.get_selected()

    def update(self, data):
        if data is ValueUnset or data is None:
            self.entry.set_text("")
        else:
            self.select(data)

    #FIXME: This is really an ugly workaround. But for some dark and
    #       misterious force, we need to override this method because
    #       the method in superclass fails to retrieve the selected data.
    def get_selected_data(self):
        return self.entry.read()
