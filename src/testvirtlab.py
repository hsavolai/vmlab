'''
Created on May 20, 2012

@author: hsavolai
'''
import unittest
from virtlab.virtual import VMList


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testVmListIsEmpty(self):
        self.assertEqual(VMList().vms.__len__(), 0)

    def testVmPopulated(self):
        vmList = VMList()
        vmList.loadvms()
        self.assertNotEqual(vmList.vms.__len__(), 0, 0)
        vmList.printlist()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
