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
import libvirt
from copy import copy
import virtlab.constant as c


class VMState(object):

    def __init__(self, state_id, state_str):
        self.__state_id = state_id
        self.__state_str = state_str

    def get_state_id(self):
        return self.__state_id

    def get_state_str(self):
        return self.__state_str


class VMStateRunning(VMState):

    def __init__(self):
        super(VMStateRunning, self).__init__(1, c.STATE_RUNNING)


class VMStateStopped(VMState):

    def __init__(self):
        super(VMStateStopped, self).__init__(2, c.STATE_STOPPED)


class VMStateGone(VMState):

    def __init__(self):
        super(VMStateGone, self).__init__(3, c.STATE_GONE)


class VMInstance(object):

    def __init__(self, metadataref, name, state):
        self.__name = name
        self.__state = state
        assert(metadataref, VMMetadata)
        self.__metadataref = metadataref

    def get_desc(self):
        return self.__metadataref.get_desc()

    def set_desc(self, value):
        self.__metadataref.set_desc(value)

    def set_order(self, value):
        self.__metadataref.set_order(value)

    def get_order(self):
        return self.__metadataref.get_order()

    def get_name(self):
        return self.__name

    def get_state(self):
        return self.__state

    def set_name(self, value):
        self.__name = value

    def set_state(self, value):
        self.__state = value

    name = property(get_name, set_name, "Virtual machine name")
    state = property(get_state, set_state, "Virtual machine state")
    order = property(get_order, set_order, "Virtual machine order")
    desc = property(get_desc, set_desc, "Virtual machine description")


class VMMetadata(object):

    def __init__(self):
        self.__order = None
        self.__desc = ""

    def get_desc(self):
        return self.__desc

    def set_desc(self, value):
        self.__desc = value

    def set_order(self, order):
        self.__order = order

    def get_order(self):
        return self.__order

    order = property(get_order, set_order, "Virtual machine order")
    desc = property(get_desc, set_desc, "Virtual machine description")


class LibVirtDao():

    hook = "qemu:///system"

    def __init__(self):
        pass

    @staticmethod
    def get_libvirt(hook=None):
        if hook is None:
            return libvirt.open(LibVirtDao.hook)
        else:
            return libvirt.open(hook)


class VMCatalog(object):

    def __init__(self):
        self.__vms = {}
        self.__vms_history = {}
        self.__vms_metadata = {}

    def __empty(self):
        self.__vms.clear()

    @classmethod
    def get_conn(cls):
        try:
            return LibVirtDao.get_libvirt()
        except Exception:
            raise VMLabException(c.EXCEPTION_LIBVIRT_001, \
                                 c.EXCEPTION_LIBVIRT_001_DESC)

    def __stopped(self, conn):
        for name in conn.listDefinedDomains():
            if not name in self.__vms_metadata:
                self.__vms_metadata[name] = VMMetadata()
            self.__vms[name] = VMInstance(self.__vms_metadata[name], \
                                          name, VMStateStopped())

    def __running(self, conn):
        for vm_id in conn.listDomainsID():
            domain = conn.lookupByID(vm_id)
            name = domain.name()
            if not name in self.__vms_metadata:
                self.__vms_metadata[name] = VMMetadata()
            self.__vms[name] = VMInstance(self.__vms_metadata[name], \
                                          name, VMStateRunning())

    def get_vm(self, name):
        if name in self.__vms:
            return self.__vms[name]
        else:
            return None

    def get_vms(self):
        return self.__vms.values()

    def get_metadata_handle(self, vm_name):
        return self.__vms_metadata[vm_name]

    def refesh(self):

        self.__empty()
        conn = self.get_conn()
        self.__running(conn)
        self.__stopped(conn)

        changed = False
        for historical_vm_instance_name in self.__vms_history:
            if not historical_vm_instance_name in self.__vms:
                changed = True

        for vm_instance_name in self.__vms:
            vm_instance = self.__vms[vm_instance_name]
            if not vm_instance_name in self.__vms_history:
                changed = True
                break
            if not vm_instance_name in self.__vms_history:
                changed = True
                break
            vm_historical_instance = self.__vms_history[vm_instance_name]
            if vm_instance.state.get_state_id() != \
                            vm_historical_instance.state.get_state_id():
                changed = True
                break

        if changed == True:
            self.__vms_history = copy(self.__vms)
            return True
        else:
            return False

    vms = property(get_vms, None, None, None)


class VMLabException(Exception):
    def __init__(self, vme_id=None, msg=None):
        super(VMLabException, self).__init__()
        self.vme_id = vme_id
        self.msg = msg
