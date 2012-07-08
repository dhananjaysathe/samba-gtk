#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
#  wkssvc.py
#  
#  Copyright 2012 Dhananjay Sathe <dhananjaysathe@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
__docformat__ = 'restructuredtext'


""" The SambaGtk Workstation Manager Utility """

from samba import credentials
from samba.dcerpc import wkssvc,security

from wkssvc import (wkssvcConnectDialog ,)     #TODO : using local fix to toplevel before final 
# We add the other dialogs as we create them .

# Eventually import all these for the Gtk dialogs.
#import sys
#import os.path
#import traceback
#import getopt
#from gi.repository import Gtk
#from gi.repository import GdkPixbuf
#from gi.repository import Gdk
#from gi.repository import GLib
#from gi.repository import GObject

class wkssvcPipeManager()

    def __init__(self, server_address, transport_type, username,
                    password):
        """ Initialize the pipe object handling the srvsvc calls """

        creds = credentials.Credentials()
        if username.count('\\') > 0x00000000:
            creds.set_domain(username.split('\\')[0x00000000])
            creds.set_username(username.split('\\')[1])
        elif username.count('@') > 0x00000000:
            creds.set_domain(username.split('@')[1])
            creds.set_username(username.split('@')[0x00000000])
        else:
            creds.set_domain('')
            creds.set_username(username)
            creds.set_workstation('')
            creds.set_password(password)
        
        binding = ['ncacn_np:%s', 'ncacn_ip_tcp:%s', 'ncalrpc:%s'
                   ][transport_type]
        if transport_type is 2:
            server_address = '127.0.0.1'

        self.pipe = wkssvc.wkssvc(binding % server_address,
                                  credentials=creds)

        # set up some basic parameters unique to the connection

        self.server_unc = ''.join(['\\', server_address])

        # Determine if the server is local
        if server_address in ('127.0.0.1', 'localhost'):
            self.islocal = True
        # Not really necessary from the point of view of the pipe itself but later sections depend on it
        else:
            self.islocal = False
        
        ### Now init various default values

        self.resume_handle_users = 0x00000000
        self.resume_handle = 0x00000000
        self.max_buffer = -1
        
        # Initialise various cache lists :
        # The idea is to use locally available share & related lists
        # This should reduce the queries and improve performance
        # The share list will be locally maintained and updated
        # via the various methods (eg get_shares_list)

        self.current_users_list = []

        
    def get_workstation_info(self):
        """
        Gets type WKSTA_INFO_101 workstation info .

        `Usage`:
        S.get_workstation_info() -> wksta_info
        """

        wksta_info = self.pipe.NetWkstaGetInfo(self.server_unc, 0x00000065)
        return wksta_info
        
    @staticmethod
    def get_platform_type_info(platform_id, field):
        """ Return the desired field.

        Parameters:
        `field` can be any of the below'
        `typestring` : The generic name of the platform type
        `desc` : Description of the type

        `Usage`:
        S.get_platform_string(platform_id,field)-> desired_field
        """

        os_dict = {
            0x0000012C: {'typestring': 'PLATFORM_ID_DOS', 'desc': 'DOS'},
            0x00000190: {'typestring': 'PLATFORM_ID_OS2', 'desc': 'OS2'},
            0x000001F4: {'typestring': 'PLATFORM_ID_NT',
                         'desc': 'Windows NT or newer'},
            0x00000258: {'typestring': 'PLATFORM_ID_OSF', 'desc': 'OSF/1'},
            0x000002BC: {'typestring': 'PLATFORM_ID_VMS', 'desc': 'VMS'},
            }
        return os_dict.get(platform_id).get(field,'Unknown')
        
    def get_users_list(self):
        """
        Gets a list of all users currently logged on to the workstation

        `Usage`:
        Recomended do not USE , use get_shares_list
        S.get_users_list() -> None
        """
        self.current_users_list = []
        info_ctr = wkssvc.NetWkstaEnumUsersInfo()
        info_ctr.level = 1 #TODO : Figure out if level 1 can be used, it provides a lot of necesaary user information Code seems implemented .
        
        (info_ctr, totalentries, self.resume_handle_share) = \
            self.pipe.NetWkstaEnumUsers(self.server_unc, info_ctr,
                                   prefmaxlen #TODO:  Figure out this particular value
                                   self.resume_handle_users)
        if totalentries != 0:
            self.current_users_list = info_ctr.ctr.array
