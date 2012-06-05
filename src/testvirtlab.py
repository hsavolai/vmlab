'''
Created on May 20, 2012

@author: hsavolai
'''
import unittest
from virtlab.virtual import VMCatalog


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testVmListIsEmpty(self):
        self.assertEqual(VMCatalog().vms.__len__(), 0)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
