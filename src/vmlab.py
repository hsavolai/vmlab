#!/usr/bin/env python
'''
This file is part of Virtual Lab Manager.

VM Lab Manager program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2012 Harri Savolainen

@author: hsavolai, epelo
@license: GPLv3

Virtual Lab Manager Main
'''
from kiwi.controllers import BaseController
from kiwi.ui.views import BaseView
from kiwi.python import Settable
from kiwi.ui.objectlist import Column, ObjectList
from kiwi.ui.dialogs import error
# pylint: disable=E0611
from virtlab.virtual import VMCatalog, VMLabException
import gtk
import gobject
import sys
import virtlab.constant as c


class VirtLabControl(BaseController):
    '''
    MVC Controller
    '''
    def __init__(self, view, model):
        BaseController.__init__(self, view)
        self.model = model
        gobject.timeout_add_seconds(1, self.callback)

    def callback(self):
        '''
        Callback for timer of refreshing list of VMs
        '''
        self.view.populate_vmlist()
        return True

    # pylint: disable=W0613
    def on_vmlist_widget__selection_changed(self, vmlist_widget_allrows,
                                            vmlist_widget_row):
        if vmlist_widget_row is None:
            return
        self.view.vmname.set_text(vmlist_widget_row.name)
        text_buffer = self.view.vmdesc.get_buffer()
        text_buffer.set_text(vmlist_widget_row.desc)
        self.view.ordercombo.set_active(vmlist_widget_row.ordinal)
        #get value from table and find a way to look the order value

    def on_okbutton__clicked(self, *args):
        vm_name = self.view.vmname.get_text()
        if vm_name is "":
            return
        vm_order = self.view.ordercombo.get_active()
        vm_time = self.view.startspinner.get_value()
        text_buffer = self.view.vmdesc.get_buffer()
        vm_desc = text_buffer.get_text(text_buffer.get_start_iter(), text_buffer.get_end_iter(), False)

        self.model.get_vm(vm_name).set_desc(vm_desc)
        self.model.get_vm(vm_name).set_order(vm_order)
        self.clear_vm_edit()
        self.view.populate_vmlist(True)

    def on_cancelbutton__clicked(self, *args):
        self.clear_vm_edit()

    def clear_vm_edit(self):
        self.view.vmname.set_text("")
        self.view.vmdesc.get_buffer().set_text("")
        self.view.startspinner.set_value(0)
        self.view.ordercombo.set_active(0)


# pylint: disable=R0904
class VirtLabView(BaseView):
    '''
    MVC View
    '''

    def __init__(self, model):

        self.__vm_list = model

        BaseView.__init__(self,
                               gladefile="virtlab",
                               delete_handler=self.quit_if_last)

        tableColumns = [
                    Column("name", title='VM Name', width=130, sorted=True),
                    Column("state", title='State', width=70),
                    Column("order", title='Order', width=70),
                    Column("ordinal", visible=False),
                    Column("delay", visible=False),
                    Column("desc", title='Description', width=200)
                    ]

        self.vmlist_widget = ObjectList(tableColumns)
        self.vmlist_widget.set_size_request(300, 400)
        self.vmlist_widget.set_selection_mode(gtk.SELECTION_SINGLE)
        self.hbox4.pack_start(self.vmlist_widget)

        store = gtk.ListStore(gobject.TYPE_STRING)

        self.vmlist_widget.show()

        try:
            self.populate_vmlist()
            self.populate_order_dropdown(store, len(self.__vm_list.get_vms()))
        except VMLabException as exception:
            if exception.vme_id is c.EXCEPTION_LIBVIRT_001:
                error("Initialization error",
                      "No connection to Libvirtd.\n Exiting.")
                exit(1)

        self.ordercombo.set_model(store)
        cell = gtk.CellRendererText()
        self.ordercombo.pack_start(cell, True)
        self.ordercombo.add_attribute(cell, 'text', 0)

        self.virtlab.set_size_request(800, 460)

    def populate_vmlist(self, force_reload=False):
        '''
        Populates vmlist with current status
        '''
        if self.__vm_list.refesh() == True or force_reload == True:
            self.vmlist_widget.clear()

            for vmachine in self.__vm_list.get_vms():
                self.vmlist_widget.append(Settable(name=vmachine.get_name(),
                                state=vmachine.get_state().get_state_str(),
                                order=self.get_display_order(vmachine.get_order()),
                                ordinal=vmachine.get_order(),
                                desc=vmachine.get_desc()))

    def populate_order_dropdown(self, list_store, vm_count):
        list_store.clear()
        list_store.append([""])
        if vm_count > 0:
            for num in range(1, vm_count + 1):
                list_store.append([self.get_display_order(num)])

    @staticmethod
    def get_display_order(number):
        if number is 0:
            return ""
        upper_suffixes = {
                "11": "th",
                "12": "th",
                "13": "th"
                }

        lower_suffixes = {
                "1": "st",
                "2": "nd",
                "3": "rd",
                }
        digits = str(number)

        if digits[-2:] in upper_suffixes:
            return digits + upper_suffixes[digits[-2:]]

        if digits[-1:] in lower_suffixes:
            return digits + lower_suffixes[digits[-1:]]
        else:
            return digits + "th"


# pylint: disable=W0613
def main(argv=None):

    MODEL = VMCatalog()
    VIEW = VirtLabView(MODEL)
    VirtLabControl(VIEW, MODEL)
    VIEW.show()
    gtk.main()

if __name__ == "__main__":
    sys.exit(main())
