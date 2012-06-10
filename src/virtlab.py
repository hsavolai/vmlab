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
    def __init__(self, view_param):
        BaseController.__init__(self, view_param)
        gobject.timeout_add_seconds(1, self.callback)

    def callback(self):
        '''
        Callback for timer of refreshing list of vm's
        '''
        self.view.populate_vmlist()
        return True

    # pylint: disable=W0613
    def on_vmlist_widget__selection_changed(self, vmlist_widget_allrows,
                                            vmlist_widget_row):
        self.view.vmname.set_text(vmlist_widget_row.name)
        buffer = self.view.vmdesc.get_buffer()
        if vmlist_widget_row.desc is not None:
            buffer.set_text(vmlist_widget_row.desc)
        else:
            buffer.set_text("")

    def on_kbutton_clicked(self, *args):

    # pylint: disable=W0613
    #def on_refreshbutton__clicked(self, *args):
        '''
        When refresh-button is clicked
        '''
     #   self.view.populate_vmlist()


# pylint: disable=R0904
class VirtlabView(BaseView):
    '''
    MVC View
    '''

    def __init__(self):
        self.foo = False
        self.__vm_list = VMCatalog()

        BaseView.__init__(self,
                               gladefile="virtlab",
                               delete_handler=self.quit_if_last)

        tableColumns = [
                    Column("name", title='VM Name', width=130, sorted=True),
                    Column("state", title='State', width=70),
                    Column("order", title='Startup order', width=120),
                    Column("desc", title='Description', width=200)
                    ]

        self.vmlist_widget = ObjectList(tableColumns)
        self.vmlist_widget.set_size_request(300, 400)
        self.vmlist_widget.set_selection_mode(gtk.SELECTION_SINGLE)
        self.hbox4.pack_start(self.vmlist_widget)
        self.vmlist_widget.show()

        try:
            self.populate_vmlist()

        except VMLabException as exception:
            if exception.vme_id is c.EXCEPTION_LIBVIRT_001:
                error("Initialization error",
                      "No connection to Libvirtd.\n Exiting.")
                exit(1)

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
                                order=vmachine.get_order(),
                                desc=vmachine.get_desc()))


# pylint: disable=W0613
def main(argv=None):

    VIEW = VirtlabView()
    VirtLabControl(VIEW)
    VIEW.show()
    gtk.main()

if __name__ == "__main__":
    sys.exit(main())
