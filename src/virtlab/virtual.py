'''
Created on May 20, 2012

@author: hsavolai
'''
import libvirt
from copy import copy


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
        super(VMStateRunning, self).__init__(1, "RUNNING")


class VMStateStopped(VMState):

    def __init__(self):
        super(VMStateStopped, self).__init__(2, "STOPPED")


class VMIstance(object):

    def __init__(self, name, state):
        self.__name = name
        self.__state = state

    def get_name(self):
        return self.__name

    def get_state(self):
        return self.__state

    def set_name(self, value):
        self.__name = value

    def set_state(self, value):
        self.__state = value

    def del_name(self):
        del self.__name

    def del_state(self):
        del self.__state

    name = property(get_name, set_name, del_name, "Virtual machine name")
    state = property(get_state, set_state, del_state, "Virtual machine state")


class VMCatalog(object):

    hook = "qemu:///system"

    def __init__(self):
        self.__vms = {}
        self.__vms_history = {}

    def __empty(self):
        self.__vms.clear()

    @classmethod
    def get_conn(cls):
        try:
            return libvirt.open(cls.hook)
        except Exception:
            raise VMLabException("LIBVIRT-001", "Failed to connect libvirtd")

    def __stopped(self):
        conn = self.get_conn()
        for name in conn.listDefinedDomains():
            self.__vms[name] = VMIstance(name, VMStateStopped())

    def __running(self):
        conn = self.get_conn()
        for vm_id in conn.listDomainsID():
            domain = conn.lookupByID(vm_id)
            name = domain.name()
            self.__vms[name] = VMIstance(name, VMStateRunning())

    def get_vms(self):
        return self.__vms.values()

    def refesh(self):

        self.__empty()
        self.__running()
        self.__stopped()

        changed = False

        for vm_instance_name in self.__vms:
            vm_instance = self.__vms[vm_instance_name]
            if not self.__vms_history.has_key(vm_instance_name):
                changed = True
                break
            vm_historical_instance = self.__vms_history[vm_instance_name]
            if vm_instance.state.get_state_id() != vm_historical_instance.state.get_state_id():
                changed = True
                break

        if changed == True:
            self.__vms_history = copy(self.__vms)
            return True
        else:
            return False
    


    vms = property(get_vms, None, None, None)


class VMLabException(Exception):
    def __init__(self, id=None, msg=None):
        super(VMLabException, self).__init__()
        self.id = id

