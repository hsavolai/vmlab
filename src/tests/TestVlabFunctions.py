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

@author: hsavolai
@license: GPLv3
'''
import unittest
from vmlab import VirtLabView


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testOrdinalCounter(self):

        ordinal = VirtLabView.get_display_order(1)
        self.assertEqual("1st", ordinal)
        ordinal = VirtLabView.get_display_order(2)
        self.assertEqual("2nd", ordinal)
        ordinal = VirtLabView.get_display_order(3)
        self.assertEqual("3rd", ordinal)
        for num in range(4, 10):
            ordinal = VirtLabView.get_display_order(num)
            self.assertEqual(str(num) + "th", ordinal)
        num = VirtLabView.get_display_order(11)
        self.assertEqual("11th", num)
        num = VirtLabView.get_display_order(12)
        self.assertEqual("12th", num)
        num = VirtLabView.get_display_order(13)
        self.assertEqual("13th", num)
        for num in range(14, 20):
            ordinal = VirtLabView.get_display_order(num)
            self.assertEqual(str(num) + "th", ordinal)
        num = VirtLabView.get_display_order(21)
        self.assertEqual("21st", num)
        num = VirtLabView.get_display_order(22)
        self.assertEqual("22nd", num)
        num = VirtLabView.get_display_order(23)
        self.assertEqual("23rd", num)
        for num in range(24, 30):
            ordinal = VirtLabView.get_display_order(num)
            self.assertEqual(str(num) + "th", ordinal)




if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
