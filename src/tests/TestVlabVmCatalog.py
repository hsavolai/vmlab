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

Created on Jun 7, 2012

@author: hsavolai
@license: GPLv3
'''
import unittest
import mox
from virtlab.virtual import VMLabException, LibVirtDao, VMCatalog, VMInstance
from libvirt import virConnect, virDomain
import virtlab.constant as c


class Test(unittest.TestCase):

    def setUp(self):
        self.mocker = mox.Mox()
        self.virConnectMock = self.mocker.CreateMock(virConnect)
        self.virDomainMock = self.mocker.CreateMock(virDomain)

    def tearDown(self):
        pass

    def setUpMVMock(self):
        static_stub = staticmethod(lambda *args, **kwargs: self.virConnectMock)
        LibVirtDao.get_libvirt = static_stub

    def addRunningVMs(self, vm_name_prefix, amount=1):
        self.virConnectMock.listDomainsID().AndReturn(range(amount))
        for vm_num in range(0, amount):
            self.virDomainMock.name().AndReturn(vm_name_prefix\
                                             + "-" + str(vm_num))
            self.virConnectMock.lookupByID(vm_num).AndReturn(\
                                                self.virDomainMock)

    def addStoppedVMs(self, vm_name_prefix, amount=1):

        vm_list = []
        for vm_num in range(0, amount):
            vm_list.append(vm_name_prefix + "-" + str(vm_num))

        self.virConnectMock.listDefinedDomains().AndReturn(vm_list)

    def throw_ex(self):
        raise RuntimeError()

    def testExeptionLibVirtdConnectionNotFound(self):
        static_stub = staticmethod(lambda *args, **kwargs: self.throw_ex())
        LibVirtDao.get_libvirt = static_stub
        vmcatalog = VMCatalog()
        # TODO: Add check exception should include vme_id with correct value
        self.assertRaises(VMLabException, vmcatalog.get_conn)

    def testGetSingleStoppedVmInstance(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 0)
        self.addStoppedVMs(stop_vm_name, 1)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        vm_catalog = VMCatalog()
        vm_catalog.refesh()
        vms = vm_catalog.get_vms()
        vm1 = vm_catalog.get_vm(run_vm_name + "-0")
        vm2 = vm_catalog.get_vm(stop_vm_name + "-0")

        #Assert
        self.assertEqual(1, len(vms))
        self.assertFalse(vm1)
        self.assertTrue(vm2)
        self.assertEqual(c.STATE_STOPPED, vm2.get_state().get_state_str())

    def testGetSingleRunningVmInstance(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 0)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        vm_catalog = VMCatalog()
        vm_catalog.refesh()
        vms = vm_catalog.get_vms()
        vm1 = vm_catalog.get_vm(run_vm_name + "-0")
        vm2 = vm_catalog.get_vm(stop_vm_name + "-0")

        #Assert
        self.assertEqual(1, len(vms))
        self.assertFalse(vm2)
        self.assertTrue(vm1)
        self.assertEqual(c.STATE_RUNNING, vm1.get_state().get_state_str())

    def testGetMixedVmInstances(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 1)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        # Test
        vm_catalog = VMCatalog()
        vm_catalog.refesh()
        vms = vm_catalog.get_vms()
        vm1 = vm_catalog.get_vm(stop_vm_name + "-0")
        vm2 = vm_catalog.get_vm(run_vm_name + "-0")

        # Assert
        self.assertEqual(2, len(vms))
        self.assertTrue(vm1)
        self.assertEqual(c.STATE_STOPPED, vm1.get_state().get_state_str())
        self.assertTrue(vm2)
        self.assertEqual(c.STATE_RUNNING, vm2.get_state().get_state_str())

    def testGetMixedVmInstancesHistoryNoChange(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 1)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        vm_catalog = VMCatalog()
        history_changed = vm_catalog.refesh()

        #Assert
        self.assertEqual(True, history_changed)

        #Setup
        mox.Reset(self.virConnectMock, self.virDomainMock)
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 1)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        history_changed = vm_catalog.refesh()

        #Assert
        self.assertEqual(False, history_changed)

    def testGetMixedVmInstancesHistoryChange(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 1)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        vm_catalog = VMCatalog()
        history_changed = vm_catalog.refesh()

        #Assert
        self.assertEqual(True, history_changed)

        #Setup
        mox.Reset(self.virConnectMock, self.virDomainMock)
        self.addRunningVMs(run_vm_name, 0)
        self.addStoppedVMs(stop_vm_name, 2)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        history_changed = vm_catalog.refesh()

        #Assert
        self.assertEqual(True, history_changed)

    def testDescriptionPersistsOverReload(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 0)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        vm_catalog = VMCatalog()
        assert isinstance(vm_catalog, VMCatalog)
        vm_catalog.refesh()

        vm = vm_catalog.get_vm(run_vm_name + "-0")
        assert isinstance(vm, VMInstance)
        desc = "Test"
        vm.set_desc(desc)

        #Setup
        mox.Reset(self.virConnectMock, self.virDomainMock)
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 0)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        vm_catalog.refesh()
        vm = vm_catalog.get_vm(run_vm_name + "-0")
        #Assert
        self.assertEqual(desc, vm.get_desc())

    def testOrderPersistsOverReload(self):
        # Setup
        self.setUpMVMock()
        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 0)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        #Test
        vm_catalog = VMCatalog()
        assert isinstance(vm_catalog, VMCatalog)
        vm_catalog.refesh()

        vm = vm_catalog.get_vm(run_vm_name + "-0")
        assert isinstance(vm, VMInstance)
        order = 1
        vm.set_order(1)

        #Setup
        mox.Reset(self.virConnectMock, self.virDomainMock)
        self.addRunningVMs(run_vm_name, 1)
        self.addStoppedVMs(stop_vm_name, 0)
        mox.Replay(self.virConnectMock, self.virDomainMock)

        vm_catalog.refesh()
        vm = vm_catalog.get_vm(run_vm_name + "-0")
        #Assert
        self.assertEqual(order, vm.get_order())


    def testGetMixedVmInstancesOrderAttached(self):
        self.setUpMVMock()
        # Setup running instance
        self.virConnectMock.listDomainsID().AndReturn([1])
        run_vm_name = "TEST-VM-RUN"
        self.virDomainMock.name().AndReturn(run_vm_name)
        self.virConnectMock.lookupByID(1).AndReturn(self.virDomainMock)

        # Setup stopped instance
        stop_vm_name = "TEST-VM-STOP"
        self.virConnectMock.listDefinedDomains().AndReturn([stop_vm_name])

        mox.Replay(self.virConnectMock, self.virDomainMock)
        vm_catalog = VMCatalog()
        vm_catalog.refesh()
        vm_catalog.attach_order(run_vm_name, 1)
        vms = vm_catalog.get_vms()

        self.assertEqual(2, len(vms), "There should be two vms! / "\
                                                        + str(len(vms)))
        self.assertEqual(stop_vm_name, vms[1].get_name(), \
                "VM name does not match! / " \
                                      + stop_vm_name + vms[1].get_name())

        self.assertEqual(c.STATE_STOPPED, vms[1].get_state().get_state_str(), \
                "VM should be stopped / " + vms[1].get_state().get_state_str())

        self.assertEqual(run_vm_name, vms[0].get_name(), \
                "VM name does not match! / " + vms[0].get_name())

        self.assertEqual(c.STATE_RUNNING, vms[0].get_state().get_state_str(), \
                "VM should be running / " + vms[0].get_state().get_state_str())

        self.assertEqual(1, vms[0].get_order(), \
                "VM should have order / " + str(vms[0].get_order()))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
