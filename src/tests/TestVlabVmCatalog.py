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
from virtlab.virtual import VMLabException, LibVirtDao, VMCatalog
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

    def throw_ex(self):
        raise RuntimeError()

    def testExeptionLibVirtdConnectionNotFound(self):
        static_stub = staticmethod(lambda *args, **kwargs: self.throw_ex())
        LibVirtDao.get_libvirt = static_stub
        vmcatalog = VMCatalog()
        # TODO: Add check exception should include vme_id with correct value
        self.assertRaises(VMLabException, vmcatalog.get_conn)

    def testGetSingleStoppedVmInstance(self):
        self.setUpMVMock()
        self.virConnectMock.listDomainsID().AndReturn([])
        vm_name = "TEST-VM-STOP"
        self.virConnectMock.listDefinedDomains().AndReturn([vm_name])
        mox.Replay(self.virConnectMock)
        vm_catalog = VMCatalog()
        vm_catalog.refesh()
        vms = vm_catalog.get_vms()

        self.assertEqual(1, len(vms), "There should be only one vm! / "\
                                                        + str(len(vms)))

        self.assertEqual(vm_name, vms[0].get_name(), \
                "VM name does not match! / " + vms[0].get_name())

        self.assertEqual(c.CONST_STOPPED, vms[0].get_state().get_state_str(), \
                "VM should be stopped / " + vms[0].get_state().get_state_str())

    def testGetSingleRunningVmInstance(self):
        self.setUpMVMock()
        self.virConnectMock.listDomainsID().AndReturn([1])
        vm_name = "TEST-VM-RUN"
        self.virDomainMock.name().AndReturn(vm_name)
        self.virConnectMock.lookupByID(1).AndReturn(self.virDomainMock)
        self.virConnectMock.listDefinedDomains().AndReturn([])
        mox.Replay(self.virConnectMock, self.virDomainMock)
        vm_catalog = VMCatalog()
        vm_catalog.refesh()
        vms = vm_catalog.get_vms()
        self.assertEqual(1, len(vms), "There should be only one vm! / "\
                                                        + str(len(vms)))

        self.assertEqual(vm_name, vms[0].get_name(), \
                "VM name does not match! / " + vms[0].get_name())

        self.assertEqual(c.CONST_RUNNING, vms[0].get_state().get_state_str(), \
                "VM should be running / " + vms[0].get_state().get_state_str())

    def testGetMixedVmInstances(self):
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
        vms = vm_catalog.get_vms()

        self.assertEqual(2, len(vms), "There should be two vms! / "\
                                                        + str(len(vms)))
        self.assertEqual(stop_vm_name, vms[1].get_name(), \
                "VM name does not match! / " \
                                      + stop_vm_name + vms[1].get_name())

        self.assertEqual(c.CONST_STOPPED, vms[1].get_state().get_state_str(), \
                "VM should be stopped / " + vms[1].get_state().get_state_str())

        self.assertEqual(run_vm_name, vms[0].get_name(), \
                "VM name does not match! / " + vms[0].get_name())

        self.assertEqual(c.CONST_RUNNING, vms[0].get_state().get_state_str(), \
                "VM should be running / " + vms[0].get_state().get_state_str())

    def testGetMixedVmInstancesHistoryNoChange(self):
        self.setUpMVMock()

        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.virConnectMock.listDomainsID().AndReturn([1])
        self.virDomainMock.name().AndReturn(run_vm_name)
        self.virConnectMock.lookupByID(1).AndReturn(self.virDomainMock)
        self.virConnectMock.listDefinedDomains().AndReturn([stop_vm_name])
        mox.Replay(self.virConnectMock, self.virDomainMock)

        vm_catalog = VMCatalog()
        history_changed = vm_catalog.refesh()
        self.assertEqual(True, history_changed, "History should be changed")

        mox.Reset(self.virConnectMock, self.virDomainMock)
        self.virConnectMock.listDomainsID().AndReturn([1])
        self.virDomainMock.name().AndReturn(run_vm_name)
        self.virConnectMock.lookupByID(1).AndReturn(self.virDomainMock)
        self.virConnectMock.listDefinedDomains().AndReturn([stop_vm_name])
        mox.Replay(self.virConnectMock, self.virDomainMock)

        history_changed = vm_catalog.refesh()

        self.assertEqual(False, history_changed, \
                         "History should not be changed")

    def testGetMixedVmInstancesHistoryChange(self):
        self.setUpMVMock()

        run_vm_name = "TEST-VM-RUN"
        stop_vm_name = "TEST-VM-STOP"
        self.virConnectMock.listDomainsID().AndReturn([1])
        self.virDomainMock.name().AndReturn(run_vm_name)
        self.virConnectMock.lookupByID(1).AndReturn(self.virDomainMock)
        self.virConnectMock.listDefinedDomains().AndReturn([stop_vm_name])
        mox.Replay(self.virConnectMock, self.virDomainMock)

        vm_catalog = VMCatalog()
        history_changed = vm_catalog.refesh()
        self.assertEqual(True, history_changed, "History should be changed")

        mox.Reset(self.virConnectMock, self.virDomainMock)
        self.virConnectMock.listDomainsID().AndReturn([])
        self.virConnectMock.listDefinedDomains().AndReturn([stop_vm_name, \
                                                             run_vm_name])
        mox.Replay(self.virConnectMock)

        history_changed = vm_catalog.refesh()

        self.assertEqual(True, history_changed, \
                         "History should be changed")

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
