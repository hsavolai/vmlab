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
from libvirt import virConnect
import virtlab.constant as c


class Test(unittest.TestCase):

    def setUp(self):
        self.virConnect_mocker = mox.Mox()

    def tearDown(self):
        pass

    def setUpMVMock(self):
        self.virConnectMock = self.virConnect_mocker.CreateMock(virConnect)
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

    def testGetSingleNotRunningVmInstance(self):
        self.setUpMVMock()
        self.virConnectMock.listDomainsID().AndReturn([])
        vm_name = "TEST-VM"
        #self.virConnectMock.listDomainsID().lookupByID(1).AndReturn()
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

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
