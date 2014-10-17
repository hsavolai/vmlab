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
from kiwi.ui.dialogs import error, messagedialog
# pylint: disable=E0611
from virtlab.virtual import VMCatalog
import gtk
import gobject
import sys
from time import strftime, localtime
import virtlab.constant as c
from virtlab.project import Project, ProjectDao
from virtlab.auxiliary import VMLabException
from gtk import TRUE
import os
import virtlab
from virtlab.vm import VMState

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
        self.reload_view_vmlist()
        return True

    def reload_view_vmlist(self, force_view_reload=False):
        if self.model.refresh_vms_list() or force_view_reload:
            self.model.reset_change_notify()
            self.view.populate_vmlist()

    # pylint: disable=W0613
    def on_vmlist_widget__selection_changed(self, vmlist_widget_allrows,
                                            vmlist_widget_row):
        if vmlist_widget_row is None:
            return
        self.view.vmname.set_text(vmlist_widget_row.name)
        text_buffer = self.view.vmdesc.get_buffer()
        text_buffer.set_text(vmlist_widget_row.desc)
        self.view.ordercombo.set_active(vmlist_widget_row.ordinal)
        self.view.startspinner.set_value(vmlist_widget_row.delay)
        #get value from table and find a way to look the order value

    def on_okbutton__clicked(self, *args):
        vm_name = self.view.vmname.get_text()
        if vm_name is "":
            self.clear_vm_edit()
            return
        vm_order = self.view.ordercombo.get_active()
        vm_time = self.view.startspinner.get_value()
        text_buffer = self.view.vmdesc.get_buffer()
        vm_desc = text_buffer.get_text(text_buffer.get_start_iter(), text_buffer.get_end_iter(), False)

        self.model.get_vm(vm_name).set_desc(vm_desc)
        if vm_order > 0:
            self.model.get_vm(vm_name).set_order(vm_order)
            self.model.get_vm(vm_name).set_delay(vm_time)
        else:
            self.model.get_vm(vm_name).set_order(0)
        self.clear_vm_edit()
        self.reload_view_vmlist(True)

    def on_cancelbutton__clicked(self, *args):
        self.clear_vm_edit()

    def clear_vm_edit(self):
        self.view.vmname.set_text("")
        self.view.vmdesc.get_buffer().set_text("")
        self.view.startspinner.set_value(0)
        self.view.ordercombo.set_active(0)

    def on_newmenuitem__activate(self, *args):
        self.model.reset()
        self.reload_view_vmlist(True)
        self.view.projectname.set_text("")

    def on_openmenuitem__activate(self, *args):
        file_name = self.view.dialog_filechooser_open()
        if file_name is None:
            return

        try:
            project = ProjectDao.load_project(file_name)
            self.view.set_statusbar("File open succesful.")

        except IOError as e:
            self.view.dialog_file_error("IO error({0}): {1}".format(e.errno, e.strerror))
            self.view.set_statusbar("Error in file operation.")
            project = Project()
        except:
            self.view.dialog_file_error("Unknown error.")
            self.view.set_statusbar("Error in file operation.")
            project = Project()

        self.model.inject_project(project)
        self.view.projectname.set_text(project.get_project_name())
        self.reload_view_vmlist(True)
        self.view.change_title(project.get_project_file())

    def on_saveasmenuitem__activate(self, *args):

        file_name = self.view.dialog_filechooser_save()
        if file_name is None:
            return

        file_name = self.form_filename(file_name)

        if self.file_overwrite_confirmation(file_name) is False:
            self.view.set_statusbar("File operation cancelled.")
            return
        try:
            project = self.model.get_project()
            project.set_project_name(self.view.projectname.get_text())
            
            project.set_project_file(file_name)
            

            project.set_metadata(self.model.get_vms_metadata())
            ProjectDao.save_project(project)
            self.view.change_title(project.get_project_file())
            self.view.set_statusbar("File save succesful.")
        except IOError as e:
            self.view.dialog_file_error("IO error ({0}): {1}".format(e.errno, e.strerror))
            self.view.set_statusbar("Error in file operation.")
        except:
            self.view.dialog_file_error("Unknown error.")
            self.view.set_statusbar("Error in file operation.")
            return

    def on_savemenuitem__activate(self, *args):
        project = self.model.get_project()
        file_name = project.get_project_file()
        if file_name is "" or None:
            file_name = self.view.dialog_filechooser_save()
            if file_name is None:
                return
            file_name = self.form_filename(file_name)
            if self.file_overwrite_confirmation(file_name) is False:
                self.view.set_statusbar("File operation cancelled.")
                return


        project.set_project_name(self.view.projectname.get_text())
        project.set_project_file(file_name)

        try:
            project.set_metadata(self.model.get_vms_metadata())
            ProjectDao.save_project(project)
            self.view.change_title(project.get_project_file())
            self.view.set_statusbar("File save succesful.")
        except IOError as e:
            self.view.dialog_file_error("IO error {0}): {1}".format(e.errno, e.strerror))
            self.view.set_statusbar("Error in file operation.")
        except:
            self.view.dialog_file_error("Unknown error.")
            self.view.set_statusbar("Error in file operation.")
            return

    def on_quitmenuitem__activate(self, *args):
        sys.exit(0)

    def on_aboutmenuitem__activate(self, *args):
        self.view.show_about()

    def on_launchbutton__clicked(self, *args):
        self.view.show_dialog()

    def on_stopallbutton__clicked(self, *args):
        self.model.stop_all_vms_once()

    def on_stoprelatedbutton__clicked(self, *args):
        self.model.stop_all_related_vms_once()

    def hook_dialog_terminate_clicked(self, *args):
        self.model.cancel_vm_launch()

    def hook_dialog_start_clicked(self, *args):
        self.model.scheduled_vm_launcher()

    def hook_dialog_all_start_clicked(self, *args):
        self.model.start_all_related_vms_once()

    def form_filename(self, file_name):
        if not file_name.endswith(c.SAVE_FILE_SUFFIX):
            return file_name+c.SAVE_FILE_SUFFIX
        return file_name

    def file_overwrite_confirmation(self, file_name):
         # File exitst
         if os.path.isfile(file_name):
            # Ask user what shoild be done
            if self.view.dialog_overwrite() is False:
                return False
         return True



def populate_image(_state):
    if _state is VMState.Running:
        return gtk.gdk.pixbuf_new_from_file("pixmaps/computer-on.png")
    else:
        if _state is VMState.Stopped:
            return gtk.gdk.pixbuf_new_from_file("pixmaps/computer-off.png")

    return gtk.gdk.pixbuf_new_from_file("pixmaps/computer-gone.png")


# pylint: disable=R0904
class VirtLabView(BaseView):
    '''
    MVC View
    '''

    def __init__(self, model):

        self.__model = model
        #self.__model.set_view(self)

        BaseView.__init__(self,
                               gladefile="virtlab",
                               delete_handler=self.quit_if_last)

  #      self.__col_pixbuf = gtk.TreeViewColumn("Image")
  #      cellrenderer_pixbuf = gtk.CellRendererPixbuf()
  #      cellrenderer_pixbuf.set_properties("pixbuf", )
  #      self.__col_pixbuf.pack_start(cellrenderer_pixbuf, False)
  #      self.__col_pixbuf.add_attribute(cellrenderer_pixbuf, "pixbuf", 1)

        tableColumns = [
                    Column("image", title=" ", width=30, data_type=gtk.gdk.Pixbuf, sorted=False),
                    Column("name", title='VM Name', width=130, sorted=True),
                    Column("state", title='State', width=70),
                    Column("order", title='Order (Delay/min)', width=145),
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

        self.__dialog = None
        self.__status_text = gtk.TextBuffer()

        try:
            self.populate_vmlist()
            self.populate_order_dropdown(store, len(self.__model.get_vms()))
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

        self.change_title("")
        self.__statusbar_ctx = self.statusbar.get_context_id("virtlab")
        self.virtlab.set_icon(gtk.gdk.pixbuf_new_from_file("pixmaps/about-logo.png"))

    def __delaystring(self, delay):
        if delay > 0:
            return " (" + str(delay) + ")"
        else:
            return ""

    def change_title(self, value):
        if value == "" or None:
            self.virtlab.set_title(c.WINDOW_TITLE)
        else:
            self.virtlab.set_title(c.WINDOW_TITLE + "(" + value + ")")

    def dialog_filechooser_open(self):
        chooser = gtk.FileChooserDialog(title="Open VMLab Project", action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                  buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        filter = gtk.FileFilter()
        filter.add_pattern("*"+c.SAVE_FILE_SUFFIX)
        chooser.set_filter(filter)
        file_name = ""
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            file_name = chooser.get_filename()
            chooser.destroy()
            return file_name
        elif response == gtk.RESPONSE_CANCEL:
            chooser.destroy()
            return

    def dialog_filechooser_save(self):
        chooser = gtk.FileChooserDialog(title="Save VMLab Project", action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_CANCEL)
        filter = gtk.FileFilter()
        filter.add_pattern("*"+c.SAVE_FILE_SUFFIX)
        file_name = ""
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            file_name = chooser.get_filename()
            chooser.destroy()
            return file_name
        elif response == gtk.RESPONSE_CANCEL:
            chooser.destroy()
            return
        elif response == gtk.RESPONSE_CLOSE:
            chooser.destroy()
            return

    def populate_vmlist(self):
        '''
        Populates view with current status
        '''
        self.vmlist_widget.clear()

        for vm_instance in self.__model.get_vms():
            self.vmlist_widget.append(Settable(image=populate_image(vm_instance.get_state()), name=vm_instance.get_name(),
                            state=vm_instance.get_state().get_state_str(),
                            order=self.get_display_order(vm_instance.get_order()) + self.__delaystring(vm_instance.get_delay()),
                            ordinal=vm_instance.get_order(),
                            delay=vm_instance.get_delay(),
                            desc=vm_instance.get_desc()))


    def populate_order_dropdown(self, list_store, vm_count):
        list_store.clear()
        list_store.append([""])
        if vm_count > 0:
            for num in range(1, vm_count + 1):
                list_store.append([self.get_display_order(num)])

    def add_status_dialogbox(self, text):
        field_content = self.__status_text.get_text(self.__status_text.get_start_iter(), self.__status_text.get_end_iter(), False)
        field_content += strftime("%d %b %Y %H:%M:%S", localtime()) + " " + text + "\n"
        self.__status_text.set_text(field_content)

    def clear_dialog_log(self):
        self.__status_text.set_text("")

    def show_dialog(self):
        self.__dialog = gtk.Dialog(title="Launch status", parent=self.virtlab, flags=gtk.DIALOG_MODAL, buttons=None)
        self.__dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.__dialog.set_transient_for(self.virtlab)
        close_button = gtk.Button("Close window")
        terminate_button = gtk.Button("Terminate")
        clear_button = gtk.Button("Clear log")
        start_button = gtk.Button("Launch scheduled")
        start_once_button = gtk.Button("Launch all once")
        close_button.connect("clicked", lambda d, r: r.destroy(), self.__dialog)
        clear_button.connect("clicked", lambda d, r: r.clear_dialog_log(), self)
        terminate_button.connect("clicked", self.controller.hook_dialog_terminate_clicked, None)
        start_button.connect("clicked", self.controller.hook_dialog_start_clicked, None)
        start_once_button.connect("clicked", self.controller.hook_dialog_all_start_clicked, None)
        scrolled_window = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        text_view = gtk.TextView()
        scrolled_window.add_with_viewport(text_view)
        scrolled_window.show()
        text_view.set_buffer(self.__status_text)
        # pylint: disable=E1101
        self.__dialog.action_area.pack_start(start_button, True, True, 0)
        self.__dialog.action_area.pack_start(start_once_button, True, True, 0)
        self.__dialog.action_area.pack_start(clear_button, True, True, 0)
        self.__dialog.action_area.pack_start(terminate_button, True, True, 0)
        self.__dialog.action_area.pack_start(close_button, True, True, 0)
        self.__dialog.vbox.pack_start(scrolled_window, True, True, 0)
        scrolled_window.set_size_request(500, 200)
        start_button.show()
        start_once_button.show()
        terminate_button.show()
        close_button.show()
        clear_button.show()
        text_view.show()
        self.__dialog.show()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)

    def show_about(self):
        about = gtk.AboutDialog()
        about.set_program_name("Virtual Lab Manager")
        about.set_version("1.0 RC")
        import os
        path = os.path.dirname(virtlab.__file__)
        f = open(path + '/LICENCE', 'r')
        about.set_license(f.read())
        about.set_copyright("GPLv3, (c) Authors")
        about.set_logo(gtk.gdk.pixbuf_new_from_file("pixmaps/about-logo.png"))
        about.set_authors(["Harri Savolainen", "Esa Elo"])
        about.set_comments("Virtual Machine lab tool")
        about.set_website("https://github.com/hsavolai/vmlab")
        about.run()
        about.hide()

    def dialog_overwrite(self):
        response = messagedialog(gtk.MESSAGE_QUESTION, 
                    "File exists, overwrite?",
                    None,
                    self.toplevel,
                    gtk.BUTTONS_OK_CANCEL
                    )
        if response == gtk.RESPONSE_OK:
            return True
        return False

    def dialog_file_error(self, error_msg):
        messagedialog(gtk.MESSAGE_ERROR, 
                    "File operation failed!",
                    error_msg,
                    self.toplevel,
                    gtk.BUTTONS_OK
                    )

    def set_statusbar(self, value):
        #self.statusbar.remove_all(self.__statusbar_ctx)
        self.statusbar.pop(self.__statusbar_ctx)
        self.statusbar.push(self.__statusbar_ctx, value)

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

    model = VMCatalog()
    view = VirtLabView(model)
    VirtLabControl(view, model)
    model.set_view(view)
    view.show()
    gtk.main()

if __name__ == "__main__":
    sys.exit(main())
