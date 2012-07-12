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

'''
import virtlab.constant as c
from virtlab.auxiliary import VMLabException
import libvirt
from libvirt import libvirtError


class LibVirtDao():

    def __init__(self, hook="qemu:///system"):
        self.__hook = hook
        self.__conn = self.get_libvirt()

    def get_libvirt(self):
        try:
            return libvirt.open(self.__hook)
        except Exception:
            raise VMLabException(c.EXCEPTION_LIBVIRT_001, \
                                 c.EXCEPTION_LIBVIRT_001_DESC)

    def start_domain(self, vm_instance):
        domain = self.__conn.lookupByName(vm_instance.get_name())
        if domain.isActive() is 0:
            if domain.create() is 0:
                return True
            else:
                return False

    def stop_domain(self, vm_instance):
        domain = self.__conn.lookupByName(vm_instance.get_name())
        if domain.isActive() is 1:
            if domain.destroy() is 0:
                return True
            else:
                return False

    def update_domain_state(self, vm_instance):

        if vm_instance not in self.get_domain_list():
            vm_instance.set_state(VMState.Gone)
            return

        try:
            domain = self.__conn.lookupByName(vm_instance.get_name())
            if domain.isActive() is 1:
                vm_instance.set_state(VMState.Running)
            else:
                vm_instance.set_state(VMState.Stopped)
        except libvirtError:
            vm_instance.set_state(VMState.Gone)

        return

    def get_domain_list(self):
        domains = []
        for domain_id in self.__conn.listDomainsID():
            try:
                domain = self.__conn.lookupByID(domain_id)
                domains.append(domain.name())
            except libvirt.libvirtError:
                pass
        return domains + self.__conn.listDefinedDomains()

    def vm_build(self, vm_instance_name=None):
        vm_instance = VMInstance(vm_instance_name, self)
        return vm_instance


class VMInstance(object):

    def __init__(self, name, daoref):
        self.__name = name
        self.__state = None
        self.__metadataref = None
        self.__vmcatalogref = None
        self.__daoref = daoref

    def get_vmcatalogref(self):
        return self.__vmcatalogref

    def set_vmcatalogref(self, value):
        self.__vmcatalogref = value

    def get_desc(self):
        return self.__metadataref.get_desc()

    def set_desc(self, value):
        self.__metadataref.set_desc(value)

    def set_order(self, value):
        self.__metadataref.set_order(value)

    def get_order(self):
        return self.__metadataref.get_order()

    def set_delay(self, value):
        self.__metadataref.set_delay(value)

    def get_delay(self):
        return self.__metadataref.get_delay()

    def get_name(self):
        return self.__name

    def get_state(self):
        return self.__state

    def set_state(self, value):
        self.__state = value

    def set_time(self, value):
        self.__metadataref.set_time(value)

    def get_time(self):
        return self.__metadataref.get_time()

    def stop(self):
        if self.state is VMState.Running:
            ret = self.__daoref.stop_domain(self)
            self.__daoref.update_domain_state(self)
            self.__vmcatalogref.notify_change()
            return ret
        return None

    def start(self):
        if self.state is VMState.Stopped:
            ret = self.__daoref.start_domain(self)
            self.__daoref.update_domain_state(self)
            self.__vmcatalogref.notify_change()
            return ret
        return None

    def query_state(self):
        previous_state = self.get_state()
        self.__daoref.update_domain_state(self)
        if previous_state is not self.get_state():
            self.__vmcatalogref.notify_change()

    def set_metadataref(self, value):
        self.__metadataref = value

    def get_metadataref(self):
        return self.__metadataref

    def __eq__(self, other):
        if isinstance(other, VMInstance):
            if self.name == other.get_name():
                return True
            else:
                return False
        else:
            if isinstance(other, str):
                if self.name == other:
                    return True
                else:
                    return False
            else:
                return self is other

    def has_defined_role(self):
        return (self.get_order() > 0 or len(self.get_desc()) > 0) and self.get_order() is not -1

    name = property(get_name, "Virtual machine name")
    state = property(get_state, set_state, "Virtual machine state")
    order = property(get_order, set_order, "Virtual machine order")
    desc = property(get_desc, set_desc, "Virtual machine description")
    time = property(get_time, set_time, "Virtual machine delay until start")
    vmcatalogref = property(get_vmcatalogref, set_vmcatalogref, None, None)


class VMMetadata(object):

    def __init__(self):
        self.__order = 0
        self.__desc = ""
        self.__delay = 0.0
        self.__time = 0

    def get_delay(self):
        return self.__delay

    def set_delay(self, value):
        self.__delay = value

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
    delay = property(get_delay, set_delay, None, None)


class VMState(object):

    class State():
        def __init__(self, state_id, state_str):
            self.__state_id = state_id
            self.__state_str = state_str

        def __str__(self):
            return self.__state_str

        def __eq__(self, other):
            return self.__state_id == other.get_state_id()

        def get_state_id(self):
            return self.__state_id

        def get_state_str(self):
            return self.__state_str

    Running = State(1, c.STATE_RUNNING)
    Stopped = State(2, c.STATE_STOPPED)
    Gone = State(3, c.STATE_GONE)
