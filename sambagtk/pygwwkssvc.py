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
import sys
import os.path
import traceback
import getopt
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import Gdk
from gi.repository import GObject

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
        
        self.current_users_list = []

        
    def get_workstation_info(self):
        """
        Gets type WKSTA_INFO_101 workstation info .

        `Usage`:
        S.get_workstation_info() -> wksta_info
        """
        # We could try 102 but that will only work for the Domain Administrator
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
    
    @staticmethod
    def get_encrypted_password_buff(password):
        #TODO : this logic nees to be implemented.
        pass
            
    def join_domain(self, server_address, domain_name, machine_name,
                   username, password, join_flags=None):
        """
        Joins a particular domain as required by the user
        
        `Usage` :
        S.join_domain(server_address, domain_name,
                     machine_name, username, password, flags) -> None
        """
        domain_name = '\\'.join([doamin_name,machine_name])
        username = unicode(username)
        encrypted_password = get_encrypted_password_buff(password)
        # TODO Figure out Join flags as required.
        #join_flags = wkssvc.WKSSVC_JOIN_FLAGS_xxx | wkssvc.WKSSVC_JOIN_FLAGS_xxx
        self.pipe.NetrJoinDomain2(server_address, domain_name, None, 
                        username, encrypted_password, join_flags)
        
        
               
class WkssvcWindow(Gtk.Window)

    def __init__(self, info_callback=None, server='', username='',
                 password='', transport_type=0, connect_now=False):
        super(WkssvcWindow, self).__init__()

        # It's nice to have this info saved when a user wants to reconnect
        self.server_address = server
        self.username = username
        self.transport_type = transport_type

        self.active_page_index = 0
        self.server_info = None

        self.create()
        self.set_status('Disconnected.')
        self.on_connect_item_activate(None, server, transport_type,
                                        username, password, connect_now)
        self.show_all()

        # This is used so the parent program can grab the server info after
        # we've connected.
        if info_callback is not None:
            info_callback(server=self.server_address,
                          username=self.username,
                          transport_type=self.transport_type)

    def connected(self):
        return self.pipe_manager is not None
        
    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
    
    def run_message_dialog(self, type, buttons, message, parent=None):
        if parent is None:
            parent = self

        message_box = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL
                , type, buttons, message)
        response = message_box.run()
        message_box.hide()

        return response
    
    def on_connect_item_activate(self, widget, server='',
                            transport_type=0, username='', password='',
                            connect_now=False):

        transport_type = transport_type or self.transport_type
        if transport_type is 2:
            server = '127.0.0.1'
        else:
            server = server or self.server_address
        username = username or self.username

        try:
            self.pipe_manager = self.run_connect_dialog(None, server,
                    transport_type, username, password, connect_now)
            if self.pipe_manager is not None:
                self.wkst_info = self.pipe_manager.get_workstation_info()

                self.set_status(
                          'Connected to Server: IP=%s NETBios Name=%s.'
                           % (self.server_address,
                            self.wkst_info.server_name))
        except RuntimeError, re:

            msg = 'Failed to connect: %s.' % re.args[1]
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK, msg)
        except Exception, ex:

            msg = 'Failed to connect: %s.' % str(ex)
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(Gtk.MessageType.ERROR,
                                    Gtk.ButtonsType.OK, msg)

        self.update_sensitivity()

    def run_connect_dialog(self, pipe_manager, server_address,
            transport_type, username, password, connect_now=False):

        dialog = srvsvcConnectDialog(server_address, transport_type,
                username, password)
        dialog.show_all()

        while True:
            if connect_now:
                connect_now = False
                response_id = Gtk.ResponseType.OK
            else:
                response_id = dialog.run()

            if response_id != Gtk.ResponseType.OK:
                dialog.hide()
                return None
            else:
                try:
                    server_address = dialog.get_server_address()
                    self.server_address = server_address
                    transport_type = dialog.get_transport_type()
                    self.transport_type = transport_type
                    username = dialog.get_username()
                    self.username = username
                    password = dialog.get_password()

                    pipe_manager = wkssvcPipeManager(server_address,
                            transport_type, username, password)
                    break
                except RuntimeError, re:

                    if re.args[1] == 'Logon failure':  # user got the password wrong
                        self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK,
                                'Failed to connect: Invalid username or password.'
                                , dialog)
                        dialog.password_entry.grab_focus()
                        dialog.password_entry.select_region(0,
                                -1)  # select all the text in the password box
                    elif re.args[0] == 5 or re.args[1]\
                         == 'Access denied':
                        self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK,
                                'Failed to connect: Access Denied.',
                                dialog)
                        dialog.username_entry.grab_focus()
                        dialog.username_entry.select_region(0,
                                -1)
                    elif re.args[1]\
                         == 'NT_STATUS_HOST_UNREACHABLE':
                        self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK,
                                'Failed to connect: Could not contact the server'
                                , dialog)
                        dialog.server_address_entry.grab_focus()
                        dialog.server_address_entry.select_region(0,
                                -1)
                    elif re.args[1]\
                         == 'NT_STATUS_NETWORK_UNREACHABLE':
                        self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK,
                                '''Failed to connect: The network is unreachable.

Please check your network connection.''',
                                dialog)
                    else:
                        msg = 'Failed to connect: %s.'\
                             % re.args[1]
                        print msg
                        traceback.print_exc()
                        self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK, msg, dialog)
                except Exception, ex:

                    msg = 'Failed to connect: %s.' % str(ex)
                    print msg
                    traceback.print_exc()
                    self.run_message_dialog(Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK, msg, dialog)

        response_id = Gtk.ResponseType.OK or dialog.run()
        dialog.hide()

        if response_id != Gtk.ResponseType.OK:
            return None

        return pipe_manager

    def on_about_item_activate(self, widget):
        dialog = AboutDialog('PyGWWkssvc',
                             "A tool to manage domains and workstations.\nBased on Jelmer Vernooij's original Samba-GTK"
                             , self.icon_pixbuf)
        dialog.set_copyright('Copyright \xc2\xa9 2011 Dhananjay Sathe <dhananjaysathe@gmail.com>'
                             )
        dialog.run()
        dialog.hide()

    def on_disconnect_item_activate(self, widget):
        if self.pipe_manager is not None:
            self.pipe_manager.close()
            self.pipe_manager = None
            self.wkst_info = None
        self.set_status('Disconnected.')
        
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
        
    def on_self_delete(self, widget, event):
        if self.pipe_manager is not None:
            self.on_disconnect_item_activate(self.disconnect_item)

        Gtk.main_quit()
        return False
        
    def create(self):
		pass
