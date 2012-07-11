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

Created on May 20, 2012

@author: hsavolai, epelo
@license: GPLv3
'''
#import threading
import time
import threading
from vm import LibVirtDao, VMInstance
from virtlab.project import Project
from virtlab.vm import VMMetadata, VMState


class VMCatalog(object):

    def __init__(self):
        self.__view = None
        self.__vms = []
        self.__project = Project()
        self.libvirtdao = LibVirtDao()
        self.__reload_flag = False
        self.__threads = []
        #Initialize catalog state
        self.refresh_vms_list()

    def get_project(self):
        return self.__project

    def inject_project(self, value):
        self.__project = value
        for vm_instance_name in self.__project.get_metadata():
            self.set_vms_metadata(self.__project.get_metadata()[vm_instance_name], vm_instance_name)

    def notify_change(self):
        self.__reload_flag = True

    def reset_change_notify(self):
        self.__reload_flag = False

#    def empty(self):
#        del self.__vms[:]

    def start_all_related_vms_once(self):
        self.scheduled_vm_launcher(True)

    def stop_all_related_vms_once(self):
        delay = 0
        for vm_instance in self.__vms:
            if vm_instance.has_defined_role():
                t = threading.Timer(delay, VMLaunchworker.stop_worker, args=(VMLaunchworker(), vm_instance),)
                t.start()
                delay += 2

    def stop_all_vms_once(self):
        delay = 0
        for vm_instance in self.__vms:
            t = threading.Timer(delay, VMLaunchworker.stop_worker, args=(VMLaunchworker(), vm_instance),)
            t.start()
            delay += 2

    def get_vm(self, name_or_instance):
        return self.__vms[self.__vms.index(name_or_instance)]

    def get_vms(self):
        return self.__vms

    def set_vms_metadata(self, metadata, vm_instance_name):
        if vm_instance_name in self.__vms:
            self.get_vm(vm_instance_name).set_metadataref(metadata)
        else:
            self.catalog(vm_instance_name)
            self.get_vm(vm_instance_name).set_metadataref(metadata)

    def get_vms_metadata(self):
        metadata = {}
        for vm_instance in self.__vms:
            metadata[vm_instance.get_name()] = vm_instance.get_metadataref()
        return metadata

    def refresh_vms_list(self):
        '''
        Refresh state of the vm_list
        Returns False if no status change from hypervisor
        Returns True if status change is occured
        '''
        domains = self.libvirtdao.get_domain_list()

        for vm_instance_name in domains:
            if vm_instance_name not in self.__vms:
                self.catalog(vm_instance_name)

        self.request_state_reload()

        return self.__reload_flag

    def catalog(self, vm_instance_name):
        vm_instance = self.libvirtdao.vm_build(vm_instance_name)
        vm_instance.set_metadataref(VMMetadata())
        vm_instance.set_vmcatalogref(self)
        self.__vms.append(vm_instance)

    def request_state_reload(self):
        for vm_istance in self.__vms:
            vm_istance.query_state()

    def set_view(self, view):
        if self.__view:
            msg = "This model already has a view: %s"
            raise AssertionError(msg % self.__view)
        self.__view = view

    def get_view(self):
        return self.__view

    def scheduled_vm_launcher(self, zero_delay=False):
        # Do not start launch if launch is already running.
        if len(self.__threads) is 0:
            startable = []

            # Which instances should be started
            for vm_instance in self.__vms:
                if vm_instance.get_state() is VMState.Stopped and vm_instance.has_defined_role():
                    startable.append(vm_instance)

            # Sort according to order
            startable.sort(cmp=None, key=lambda x: x.get_order(), reverse=False)
            # Sort according to start delay if same order
            startable.sort(lambda x, y: x.get_order() == y.get_order() and x.get_delay() < y.get_delay(), reverse=False)

            incr_delay = 0
            for vm_instance in startable:
                if incr_delay > 0:
                    self.__view.add_status_dialogbox(vm_instance.get_name() + " starts in " + str(incr_delay * 60) + " seconds.")
                if vm_instance is startable[-1]:
                    t = threading.Timer(incr_delay * 60, VMLaunchworker.start_worker, args=(VMLaunchworker(), self, vm_instance, True),)
                else:
                    t = threading.Timer(incr_delay * 60, VMLaunchworker.start_worker, args=(VMLaunchworker(), self, vm_instance, False),)
                if not zero_delay:
                    incr_delay = incr_delay + vm_instance.get_delay()
                t.start()
                self.__threads.append(t)

            if len(startable) is 0:
                self.__view.set_statusbar("Nothing to launch.")


    def cancel_vm_launch(self):
        if len(self.__threads) > 0:
            for thread in self.__threads:
                thread.cancel()
            self.__view.add_status_dialogbox("Launch terminated.")
            self.__view.set_statusbar("Launch terminated.")
            self.clear_vm_launch()

    def clear_vm_launch(self):
        del self.__threads[:]


class VMLaunchworker(object):
    def start_worker(self, model, vm_instance, last=False):
        model.get_view().add_status_dialogbox(vm_instance.get_name() + " started.")
        vm_instance.start()
        if last:
            model.get_view().set_statusbar("Launch completed.")
            model.get_view().add_status_dialogbox("Launch completed.")
            model.clear_vm_launch()
        else:
            model.get_view().set_statusbar("Launch in progress.")
        return

    def stop_worker(self, vm_instance):
        vm_instance.stop()
        return

