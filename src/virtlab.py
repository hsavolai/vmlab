#!/usr/bin/env python
'''
Virtual Lab Manager Main
'''
from gtk import ListStore
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
        if object is None:
            return None
        if not self.view.is_active_vm(vmlist_widget_row.name):
            self.view.active_vms[vmlist_widget_row.name] = \
                                        vmlist_widget_row.name
            vmlist_widget_row.join = True
        else:
            del self.view.active_vms[vmlist_widget_row.name]
            vmlist_widget_row.join = False

    # pylint: disable=W0613
    def on_refreshbutton__clicked(self, *args):
        '''
        When refresh-button is clicked
        '''
        self.view.populate_vmlist()


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
                    Column("join", data_type=bool, title='VM State', width=90)
                    ]

        self.vmlist_widget = ObjectList(tableColumns)
        self.vmlist_widget.set_selection_mode(gtk.SELECTION_SINGLE)
        self.hbox4.pack_start(self.vmlist_widget)
        self.vmlist_widget.show()
        self.active_vms = {}
        try:
            self.populate_vmlist()
        except VMLabException as exception:
            if exception.vm_id == "LIBVIRT-001":
                error("Initialization error",
                      "No connection to Libvirtd.\n Exiting.")
                exit(1)

        self.virtlab.set_size_request(600, 430)


    def populate_vmlist(self, force_reload=False):
        '''
        Populates vmlist with current status
        '''
        if self.__vm_list.refesh() == True or force_reload == True:
            self.vmlist_widget.clear()

            for vmachine in self.__vm_list.get_vms():
                self.vmlist_widget.append(Settable(name=vmachine.get_name(),
                                state=vmachine.get_state().get_state_str(),
                                join=self.is_active_vm(vmachine.get_name())))

    def is_active_vm(self, vm_name):
        if vm_name in self.active_vms:
            return True
        else:
            return False


# pylint: disable=W0613
def main(argv=None):

    VIEW = VirtlabView()
    VirtLabControl(VIEW)
    VIEW.show()
    gtk.main()

if __name__ == "__main__":
    sys.exit(main())
