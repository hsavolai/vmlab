'''
Created on Jun 23, 2012

@author: hsavolai
'''


class VMLabException(Exception):

    def __init__(self, vme_id=None, msg=None):
        super(VMLabException, self).__init__()
        self.vme_id = vme_id
        self.msg = msg

