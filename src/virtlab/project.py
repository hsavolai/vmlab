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
import virtlab.constant as c
from virtlab.virtual import VMMetadata
from configobj import ConfigObj


class ProjectDao(object):
    def __init__(self):
        pass

    @staticmethod
    def load_project(pfile):
        vms_metadata = {}
        config = ConfigObj(pfile)
        project = Project()
        project.set_project_file(pfile)
        project.set_project_name(config['Project']['name'])
        for vm_name in config['VMInstaces']:
            metadata = VMMetadata()
            metadata.set_delay(float(config['VMInstaces'][vm_name]['delay']))
            metadata.set_desc(config['VMInstaces'][vm_name]['desc'])
            metadata.set_order(int(config['VMInstaces'][vm_name]['order']))
            vms_metadata[vm_name] = metadata
        project.set_metadata(vms_metadata)
        return project

    @staticmethod
    def save_project(project):
        pfile = project.get_project_file()
        assert(isinstance(project, Project))
        config = ConfigObj()
        config.filename = pfile
        config['Project'] = {}
        config['Project']['name'] = project.get_project_name()

        config['VMInstaces'] = {}
        for vm_name in project.get_metadata():
            vm_meta = project.get_metadata()[vm_name]
            config['VMInstaces'][vm_name] = {}
            config['VMInstaces'][vm_name]['desc'] = vm_meta.get_desc()
            config['VMInstaces'][vm_name]['delay'] = vm_meta.get_delay()
            config['VMInstaces'][vm_name]['order'] = vm_meta.get_order()

        config.write()
        project.set_project_file(pfile)

class Project(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.__project_file = ""
        self.__project_name = ""
        self.__config = {}
        self.__metadata = {}

    def get_project_file(self):
        return self.__project_file

    def get_project_name(self):
        return self.__project_name

    def get_config(self):
        return self.__config

    def get_metadata(self):
        return self.__metadata

    def set_project_file(self, value):
        self.__project_file = value

    def set_project_name(self, value):
        self.__project_name = value

    def set_config(self, value):
        self.__config = value

    def set_metadata(self, value):
        self.__metadata = value

    def del_project_file(self):
        del self.__project_file

    def del_project_name(self):
        del self.__project_name

    def del_config(self):
        del self.__config

    def del_metadata(self):
        del self.__metadata

