#!/usr/bin/python2.6
# -*- coding: utf-8 -*-

#       pygwshare.py
#       Frontends to Samba-Gtk Share Management
#
#       Copyright 2011 Dhananjay Sathe <dhananjaysathe@gmail.com>
#       Copyright 2011 Jelmer Vernooij <jelmer@samba.org>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
#
__docformat__ = 'restructuredtext'

import sys
import os.path
import traceback
import getopt
import gobject
import gtk

sys.path.append('/usr/local/samba/lib/python2.7/site-packages/')
# default for ./configure.developer for use on python 2.7
# Unhash the above line if it is yor your config , else edit it as req

from samba import credentials
from samba.dcerpc import srvsvc, security

from sambagtk.dialogs import AboutDialog
from pysrvsvc import DeleteDialog, ShareAddEditDialog, \
    srvsvcConnectDialog, ShareWizardDialog


class srvsvcPipeManager(object):

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

        # binding = "ncacn_np:%s" # srvsvc allows only named pipes
        # tcp/upd not allowed under MS-SRVS specifications


        binding = ['ncacn_np:%s', 'ncacn_ip_tcp:%s', 'ncalrpc:%s'
                   ][transport_type]
        if transport_type is 2:
            server_address = '127.0.0.1'

        self.pipe = srvsvc.srvsvc(binding % server_address,
                                  credentials=creds)

        # set up some basic parameters unique to the connection

        self.server_unc = ''.join(['\\', server_address])

        # Retrive some info about the share server

        self.server_info = self.get_server_info()
        self.tod = self.get_tod()

        ### Now init various default values

        self.resume_handle_conn = 0x00000000
        self.resume_handle_share = 0x00000000
        self.resume_handle = 0x00000000
        self.max_buffer = -1

        if server_address in ('127.0.0.1', 'localhost'):
            self.islocal = True
        # Not really necessary from the point of view of the pipe itself but later sections depend on it
        else:
            self.islocal = False

        # Initialise various cache lists :
        # The idea is to use locally available share & related lists
        # This should reduce the queries and improve performance
        # The share list will be locally maintained and updated
        # via the various methods (eg get_shares_list)

        self.conn_list = []
        self.share_list = []
        self.share_names_list = []
        self.share_types_list = []
        self.get_list_disks()

        # attempt to control listing of shares.
        self.show_all_shares = False
        self.get_shares_list()

    def close(self):
        pass
        # apparently there's no .Close() method for this pipe

    @staticmethod
    def get_share_type_info(stype, field):
        """
        Return the desired info about a share type
        S.get_share_type_info(stype,field) -> desired information

        Parameters:
        'field' : can be one of the below :
        -`typestring`: The generic name of the share type
        -`desc`: Description of the type
        -`base_type`: Base share type
        -`flags`: special flags (Boolean temporary,Boolean hidden)


        """

        base_dict = {
            srvsvc.STYPE_DISKTREE: {'typestring': 'STYPE_DISKTREE',
                                    'desc': 'Disktree (Folder) Share'},
            srvsvc.STYPE_PRINTQ: {'typestring': 'STYPE_PRINTQ',
                                  'desc': 'Print Queue Share'},
            srvsvc.STYPE_DEVICE: {'typestring': 'STYPE_DEVICE',
                                  'desc': 'Device Share'},
            srvsvc.STYPE_IPC: {'typestring': 'STYPE_IPC',
                               'desc': 'IPC Share'},
            }

        flag_temp = False
        flag_hidden = False
        if stype & srvsvc.STYPE_TEMPORARY:
            flag_temp = True
        if stype & srvsvc.STYPE_HIDDEN:
            flag_hidden = True

        if flag_temp is True and flag_hidden is False:
            stype_base = stype - srvsvc.STYPE_TEMPORARY
            base_str = base_dict.get(stype_base).get('typestring')
            stype_typestring = ''.join([base_str, '_TEMPORARY'])
            stype_desc = ' '.join(['Temporary',
                                  base_dict.get(stype_base).get('desc'
                                  )])
        elif flag_temp is False and flag_hidden is True:

            stype_base = stype + srvsvc.STYPE_HIDDEN
            base_str = base_dict.get(stype_base).get('typestring')
            stype_typestring = ''.join([base_str, '_HIDDEN'])
            stype_desc = ' '.join(['Hidden',
                                  base_dict.get(stype_base).get('desc'
                                  )])
        elif flag_temp is True and flag_hidden is True:

            stype_base = stype - srvsvc.STYPE_TEMPORARY\
                 + srvsvc.STYPE_HIDDEN
            base_str = base_dict.get(stype_base).get('typestring')
            stype_typestring = ''.join([base_str, '_TEMPORARY_HIDDEN'])
            stype_desc = ' '.join(['Temporary Hidden',
                                  base_dict.get(stype_base).get('desc'
                                  )])
        else:
            stype_base = stype
            stype_typestring = \
                base_dict.get(stype_base).get('typestring')
            stype_desc = base_dict.get(stype_base).get('desc')

        stype_info_dict = {
            'typestring': stype_typestring,
            'desc': stype_desc,
            'base_type': stype_base,
            'flags': [flag_temp, flag_hidden],
            }

        return stype_info_dict.get(field)

    def fix_path_format(self, path=''):
        """
        Fixes and checks the given path to make it in tthe correct format

        Convert the unix path to relavant Info Struct path for samba
        share object.It also checks for validity of path if it is local.
        To be used for distktree (Files not IPC etc) type shares.
        `Usage` :
        S.fix_path_format(path= "") -> path
        """

        if self.islocal:
            if path.startswith('C:'):
                path = path[2:].replace('\\', '/')
            if os.path.exists(path):
                path = os.path.realpath(path)  # gets canonical path
            else:
                raise OSError('Path does not exist !')

        if path.startswith('/'):
            path = path.replace('/', '\\')
            path = ''.join(['C:', path])
            path = unicode(path)

        return path

    # NOT supported yet
    def get_connections(self, level=1, max_buffer=-1):
        """ DO NOT USE : UNSUPPORTED BY SAMBA-4 YET """

        self.conn_list = []
        info_ctr = srvsvc.NetConnInfoCtr()
        info_ctr.level = level  #
        (no_ent, info_ctr, resume_handle) = \
            self.pipe.NetConnEnum(self.server_unc,
                                  self.server_info_basic.path,
                                  info_ctr, max_buffer,
                                  self.resume_handle_conn)
        if no_ent != 0:
            for i in info_ctr.ctr.array:
                self.conn_list.append(i)

    def modify_share(self, share=None):
        """ Modifies share 502 object.

        Usage:
        S.modify_share(self,share)-> parm_error
        """

        if share is None:
            raise KeyError('Non existant Share cannot be modified')

        parm_error = 0x00000000
        name = share.name
        parm_error = self.pipe.NetShareSetInfo(self.server_unc, name,
                502, share, parm_error)
        return parm_error

    def get_shares_list(self):
        """
        Updates the share list of the pipe object .

        If show_all_shares is set to flase Hidden shares are set to
        false and not returned .It first tries to list all shares if
        that fails it falls back to list standard shares and sets the
        show_all_shares boolean accordingly
        """

        if self.show_all_shares is False:
            self.list_shares()
        else:
            try:
                self.list_shares_all()
                self.show_all_shares = True
            except RuntimeError:
                self.list_shares()
                self.show_all_shares = False

    def list_shares(self):
        """
        Gets a list of all (not hidden/special)active shares and update
        the share and share_name list.

        `Usage`:
        Recomended do not USE , use get_shares_list
        S.list_shares() -> None
        """
        self.share_list = []
        self.share_names_list = []
        self.share_types_list = []
        info_ctr = srvsvc.NetShareInfoCtr()
        info_ctr.level = 502
        (info_ctr, totalentries, self.resume_handle_share) = \
            self.pipe.NetShareEnum(self.server_unc, info_ctr,
                                   self.max_buffer,
                                   self.resume_handle_share)
        if totalentries != 0:
            self.share_list = info_ctr.ctr.array
            for i in self.share_list:
                self.share_names_list.append(i.name)
                self.share_types_list.append(i.type)

    def list_shares_all(self):
        """
        Gets a list of all (including hiden/special)active shares and
        update the share and share_name list.

        `Usage`:
        S.list_shares() -> None
        """

        self.share_list = []
        self.share_names_list = []
        self.share_types_list = []
        info_ctr = srvsvc.NetShareInfoCtr()
        info_ctr.level = 502
        (info_ctr, totalentries, self.resume_handle_share) = \
            self.pipe.NetShareEnumAll(self.server_unc, info_ctr,
                self.max_buffer, self.resume_handle_share)
        if totalentries != 0:
            self.share_list = info_ctr.ctr.array
            for i in self.share_list:
                self.share_names_list.append(i.name)
                self.share_types_list.append(i.type)

    def add_share(self, share=None):
        """
        Adds a share with a given name and type
        This uses a share info 502 object.
        Should be followed by modify_share to complete the addition of the share.

        `Usage` :
        S.add_share(self,share=None) -> parm_error
        """

        if share is None:
            raise KeyError('Illegal to add an Empty Share ')
        # Uses the default 502 share info

        parm_error = 0x00000000
        parm_error = self.pipe.NetShareAdd(self.server_unc, 502, share,
                parm_error)
        return parm_error

    def get_share_info_local(self, name=''):
        """
        Gets share info for a share with a particular name from local cache lists.

        `Usage`:
        S.get_share_info_local(self,name= "") -> sahre_info (502 type)
        """

        name = unicode(name)
        for i in self.share_names_list:
            if name is i:
                return self.share_list[i.index()]

    def get_share_info_rpc(self, name=''):
        """
        Gets share info for a share with a particular name from the rpc server.

        `Usage`:
        S.get_share_info_local(self,name= "") -> sahre_info (502 type)
        """

        name = unicode(name)
        info = self.pipe.NetShareGetInfo(self.server_unc, name, 502)
        return info

    def get_server_info(self):
        """
        Gets type 102 server info .

        `Usage`:
        S.get_server_info() -> server_info
        """

        server_info = self.pipe.NetSrvGetInfo(self.server_unc, 102)
        return server_info

    def delete_share(self, name=''):
        """
        Delete a share with the given name.

        `Usage`:
        S.delete_share (self,name= "") -> Boolean indicating success or faliure ,[error object]
        """

        name = unicode(name)
        self.pipe.NetShareDel(self.server_unc, name, 0)

    # NOT supported yet
    def remove_persistance(self, name=''):
        """ Removes persistance of a share """

        reserved = None
        name = unicode(name)
        self.pipe.NetShareDelSticky(self.server_unc, name, reserved)

    def get_share_type(self, name=''):
        """
        Returns type of share code

        uses local cache for now as the rpc server in samba4 does not support it yet
        `Usage`:
        S.update_tod()
        """

        name = unicode(name)
        for i in self.share_names_list:
            if name is i:
                stype = self.share_types_list[i.index()]
            else:
                raise KeyError('Share Does no exist')
        return stype

    def get_file_security(self, secdesc, filename='', filepath='', share=None):
        """
        Returns a security descriptor buffer of a file .
        Filepath must be full path relative to basepath of share's path.

        `Usage`:
        S.get_file_security(self,secdesc,sharename="",filepath= "")-> sd_buf
        """

        filename = unicode(filename)
        sd_buf = self.pipe.NetGetFileSecurity(self.server_unc, share,
                filename, secdesc)
        return sd_buf

    def get_tod(self):
        """
        Updates Time and date (TOD) Info of the pipe object.

        `Usage`:
        update_tod() -> tod info object
        """

        tod_info = self.pipe.NetRemoteTOD(self.server_unc)
        return tod_info

    def set_file_security(self, secdesc, sd_buf, sharename='',
                        filepath='', share=None):
        """
        Sets the security  of a file .

        Filepath must be full path relative to basepath of share's path.

        `Usage`:
        S.set_file_security (self,secdesc,sd_buf,sharename= "",filepath= "") -> Boolean succes,[error]
        """

        sharename = unicode(sharename)
        self.pipe.NetSetFileSecurity(self.server_unc, share, filepath,
                secdesc, sd_buf)

    @staticmethod
    def get_platform_info(platform_id, field):
        """ Return the desired field.

        Parameters:
        `field` can be any of the below'
        `typestring` : The generic name of the platform type
        `desc` : Description of the type

        `Usage`:
        S.get_platform_string(platform_id,field)-> desired_field
        """

        os_dict = {
            srvsvc.PLATFORM_ID_DOS: {'typestring': 'PLATFORM_ID_DOS',
                    'desc': 'DOS'},
            srvsvc.PLATFORM_ID_OS2: {'typestring': 'PLATFORM_ID_OS2',
                    'desc': 'OS2'},
            srvsvc.PLATFORM_ID_NT: {'typestring': 'PLATFORM_ID_NT',
                                    'desc': 'Windows NT or newer'},
            srvsvc.PLATFORM_ID_OSF: {'typestring': 'PLATFORM_ID_OSF',
                    'desc': 'OSF/1'},
            srvsvc.PLATFORM_ID_VMS: {'typestring': 'PLATFORM_ID_VMS',
                    'desc': 'VMS'},
            }
        return os_dict.get(platform_id).get(field)

    def get_share_object(self, name='', stype=0, comment='',
                    max_users=0xFFFFFFFF, password='', path=''):
        """
        Gets a 502 type share object.

        Usage:
        S.get_share_object(self,name= "",comment= "",max_users= 0xFFFFFFFF,password= "",path= "",permissions= None,sd_buf=None) -> share (502 type share object)
        """

        share = srvsvc.NetShareInfo502()

        share.comment = unicode(comment)
        share.name = unicode(name)
        share.type = stype
        share.current_users = 0x00000000
        share.max_users = max_users
        share.password = password
        share.path = path
        share.permissions = 0
        share.sd_buf = security.sec_desc_buf()

        return share

    def name_validate(self, name):
        """
        Validate a Given Share Name .
        Returns True for a given share name and false for a invalid one .
        It does so gracefully without raising a exception. Thus validating  name cleanly
        `Usage` :
        S.name_validate(name) -> Boolean Indicating Validity
        """

        try:
            self.pipe.NetNameValidate(self.server_unc, name, 9,
                    0)
            return True
        except RuntimeError:
            return False

    def get_list_disks(self):
        """
        Returns a list of disk names on the system.
        In samaba rpc server these are hard coded .
        Refreshes Disk list of the pipe object.

        `Usage`:
        S.get_list_disks()-> None
        """

        disk_info = srvsvc.NetDiskInfo()
        self.disks_list = []
        (disk_info, totalentries, self.resume_handle) = \
            self.pipe.NetDiskEnum(self.server_unc, 0x00000000,
                                  disk_info, 26, self.resume_handle)
        if totalentries != 0:
            for i in disk_info.disks:
                if i.disk != '':
                    self.disks_list.append(i.disk)


class ShareWindow(gtk.Window):

    """ Share management interface window """

    def __init__(self, info_callback=None, server='', username='',
                 password='', transport_type=0, connect_now=False):
        super(ShareWindow, self).__init__()

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
        self.fill_active_pane()
        self.fill_server_info()

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

        message_box = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, type,
                buttons, message)
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
                self.pipe_manager.get_shares_list()
                self.server_info = self.pipe_manager.server_info

                self.set_status(
                          'Connected to Server: IP=%s NETBios Name=%s.'
                           % (self.server_address,
                            self.pipe_manager.server_info.server_name))
        except RuntimeError, re:

            msg = 'Failed to connect: %s.' % re.args[1]
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)
        except Exception, ex:

            msg = 'Failed to connect: %s.' % str(ex)
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)

        self.refresh_shares_view()
        self.update_sensitivity()
        self.fill_server_info()

    def run_connect_dialog(self, pipe_manager, server_address,
            transport_type, username, password='', connect_now=False):

        dialog = srvsvcConnectDialog(server_address, transport_type,
                username, password)
        dialog.show_all()

        while True:
            if connect_now:
                connect_now = False
                response_id = gtk.RESPONSE_OK
            else:
                response_id = dialog.run()

            if response_id != gtk.RESPONSE_OK:
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

                    pipe_manager = srvsvcPipeManager(server_address,
                            transport_type, username, password)
                    break
                except RuntimeError, re:

                    if re.args[1] == 'Logon failure':  # user got the password wrong
                        self.run_message_dialog(gtk.MESSAGE_ERROR,
                                gtk.BUTTONS_OK,
                                'Failed to connect: Invalid username or password.'
                                , dialog)
                        dialog.password_entry.grab_focus()
                        dialog.password_entry.select_region(0,
                                -1)  # select all the text in the password box
                    elif re.args[0] == 5 or re.args[1]\
                         == 'Access denied':
                        self.run_message_dialog(gtk.MESSAGE_ERROR,
                                gtk.BUTTONS_OK,
                                'Failed to connect: Access Denied.',
                                dialog)
                        dialog.username_entry.grab_focus()
                        dialog.username_entry.select_region(0,
                                -1)
                    elif re.args[1]\
                         == 'NT_STATUS_HOST_UNREACHABLE':
                        self.run_message_dialog(gtk.MESSAGE_ERROR,
                                gtk.BUTTONS_OK,
                                'Failed to connect: Could not contact the server'
                                , dialog)
                        dialog.server_address_entry.grab_focus()
                        dialog.server_address_entry.select_region(0,
                                -1)
                    elif re.args[1]\
                         == 'NT_STATUS_NETWORK_UNREACHABLE':
                        self.run_message_dialog(gtk.MESSAGE_ERROR,
                                gtk.BUTTONS_OK,
                                '''Failed to connect: The network is unreachable.

Please check your network connection.''',
                                dialog)
                    else:
                        msg = 'Failed to connect: %s.'\
                             % re.args[1]
                        print msg
                        traceback.print_exc()
                        self.run_message_dialog(gtk.MESSAGE_ERROR,
                                gtk.BUTTONS_OK, msg, dialog)
                except Exception, ex:

                    msg = 'Failed to connect: %s.' % str(ex)
                    print msg
                    traceback.print_exc()
                    self.run_message_dialog(gtk.MESSAGE_ERROR,
                            gtk.BUTTONS_OK, msg, dialog)

        response_id = gtk.RESPONSE_OK or dialog.run()
        dialog.hide()

        if response_id != gtk.RESPONSE_OK:
            return None

        return pipe_manager

    def on_switch_fill_active_pane(self, widget):
        """ Function doc """

        self.fill_active_pane()

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()

    def fill_server_info(self):
        """ Gracious fill out server info """

        for widget in self.sd_frame.get_children():
            if type(widget) is gtk.Table:
                self.sd_frame.remove(widget)

        if self.server_info is None:
            self.srv_info_label.set_markup('<b>Server Disconnected</b>')

            my_lables = \
                self.srvinfo_frame.get_children()[0].get_children()
            for label in my_lables:
                label.set_sensitive(False)

            table = gtk.Table(2, 2, True)
            table.set_border_width(5)
            table.set_row_spacings(4)
            label = gtk.Label('Not connected to share server.')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, 1, 2, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)
        else:

            self.srv_info_label.set_markup('<b>Share Server Details</b>'
                    )

            my_lables = \
                self.srvinfo_frame.get_children()[0].get_children()
            for label in my_lables:
                label.set_sensitive(True)

            label_data = \
                self.pipe_manager.get_platform_info(
                                   self.server_info.platform_id, 'desc')
            self.srvinfo_tos_label.set_text(label_data)            
            self.srvinfo_name_label.set_text('\\'
                     + self.server_info.server_name)
            self.srvinfo_hidden_label.set_text(
                                     str(bool(self.server_info.hidden)))
            self.srvinfo_comment_label.set_text(self.server_info.comment)
            label_data = '.'.join([str(self.server_info.version_major),
                                  str(self.server_info.version_minor)])
            self.srvinfo_version_label.set_text(label_data)
            server_typedict = {
                1: ('SV_TYPE_WORKSTATION',
                             'Workstation Service'),
                2: ('SV_TYPE_SERVER', 'Server Service'),
                4: ('SV_TYPE_SQLSERVER', 'SQL Server'),
                8: ('SV_TYPE_DOMAIN_CTRL',
                             'Primary Domain Controller'),
                0x00000010: ('SV_TYPE_DOMAIN_BAKCTRL',
                             'Backup Domain Controller'),
                0x00000020: ('SV_TYPE_TIME_SOURCE', 'Time Source'),
                0x00000040: ('SV_TYPE_AFP', 'Apple File Protocol Server'
                             ),
                0x00000080: ('SV_TYPE_NOVELL', 'Novel Server'),
                0x00000100: ('SV_TYPE_DOMAIN_MEMBER',
                             'LAN Manager 2.x Domain Member'),
                0x40000000: ('SV_TYPE_LOCAL_LIST_ONLY',
                             'Server Maintained By the Browser'),
                0x00000200: ('SV_TYPE_PRINTQ_SERVER',
                             'Print Queue Server'),
                0x00000400: ('SV_TYPE_DIALIN_SERVER', 'Dial-In Server'
                             ),
                0x00000800: ('SV_TYPE_XENIX_SERVER', 'Xenix Server'),
                0x00004000: ('SV_TYPE_SERVER_MFPN',
                             'Microsoft File and Print for NetWare'),
                0x00001000: ('SV_TYPE_NT', 'Windows NT/XP/2003 or Newer'
                             ),
                0x00002000: ('SV_TYPE_WFW', 'Windows for Workgroups'),
                0x00008000: ('SV_TYPE_SERVER_NT',
                             'Non DC Windows Server 2000/2003 or Newer'
                             ),
                0x00010000: ('SV_TYPE_POTENTIAL_BROWSER',
                             'Potential Browser Service '),
                0x00020000: ('SV_TYPE_BACKUP_BROWSER',
                             'Browser Service As Backup'),
                0x00040000: ('SV_TYPE_MASTER_BROWSER',
                             'Master Browser Service'),
                0x00080000: ('SV_TYPE_DOMAIN_MASTER',
                             'Domain Master Browser'),
                0x80000000: ('SV_TYPE_DOMAIN_ENUM', 'Primary Domain'),
                0x00400000: ('SV_TYPE_WINDOWS', 'Windows ME/98/95'),
                0xFFFFFFFF: ('SV_TYPE_ALL', 'All Servers'),
                0x02000000: ('SV_TYPE_TERMINALSERVER', 'Terminal Server'
                             ),
                0x10000000: ('SV_TYPE_CLUSTER_NT', 'Server Cluster'),
                0x04000000: ('SV_TYPE_CLUSTER_VS_NT',
                             'Virtual Server Cluster'),
                }

            label_data = \
                server_typedict.get(self.server_info.server_type, ('',
                                    'Multiple Capablities'))[1]
            self.srvinfo_type_label.set_text(label_data)
            self.srvinfo_upath_label.set_text(
                                    self.server_info.userpath.upper())
            self.srvinfo_to_label.set_text(str(self.server_info.disc))
            label_data = '/'.join([str(self.server_info.announce),
                                  str(self.server_info.anndelta)])
            self.srvinfo_aa_label.set_text(label_data)

            num_disks = len(self.pipe_manager.disks_list)
            table = gtk.Table(num_disks + 2, 2, True)
            table.set_border_width(5)
            table.set_row_spacings(4)
            label = gtk.Label('<b> Disks </b>')
            label.set_use_markup(True)
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, 1, 2, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

            for i in self.pipe_manager.disks_list:
                label = gtk.Label(i)
                label.set_alignment(1, 0.5)
                attach_index = self.pipe_manager.disks_list.index(i)+2

                table.attach(label, 0, 1, attach_index,attach_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.sd_frame.add(table)
        self.sd_frame.show_all()

    def get_selected_share(self):
        if not self.connected():
            return None

        (model, iter) = \
            self.shares_tree_view.get_selection().get_selected()
        if iter is None:  # no selection
            return None
        else:
            share_name = model.get_value(iter, 0)
            share_list = [share for share in
                          self.pipe_manager.share_list if share.name
                           == share_name]
            if len(share_list) > 0:
                return share_list[0]
            else:
                return None

    def on_about_item_activate(self, widget):
        dialog = AboutDialog('PyGWShare',
                             "A tool to manage user shares on a SRVS Share server.\nBased on Jelmer Vernooij's original Samba-GTK"
                             , self.icon_pixbuf)
        dialog.set_copyright('Copyright \xc2\xa9 2011 Dhananjay Sathe <dhananjaysathe@gmail.com>'
                             )
        dialog.run()
        dialog.hide()

    def run_delete_dialog(self, share=None):
        dialog = DeleteDialog(self.pipe_manager, share)
        dialog.show_all()
        response_id = dialog.run()
        dialog.hide()
        return response_id

    def run_share_add_edit_dialog(self, share=None, apply_callback=None,
                                  wizard_mode=False):

        if wizard_mode: # wizard only for a new share
            dialog = ShareWizardDialog(self.pipe_manager, None)
        else:
            dialog = ShareAddEditDialog(self.pipe_manager, share)
        dialog.show_all()

        while True:
            response_id = dialog.run()

            if response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]:
                problem_msg = dialog.validate_fields()

                if problem_msg is not None:
                    self.run_message_dialog(gtk.MESSAGE_ERROR,
                            gtk.BUTTONS_OK, problem_msg, dialog)
                else:
                    dialog.fields_to_share()

                    if apply_callback is not None:
                        apply_callback(dialog.share)
                        dialog.share_to_fields()
                        dialog.fields_to_gui()

                    if response_id == gtk.RESPONSE_OK:
                        dialog.hide()
                        break
            else:

                dialog.hide()
                return None

        return dialog.share

    def update_sensitivity(self):

        connected = self.pipe_manager is not None
        share_page_active = not self.active_page_index
        selected = self.get_selected_share() is not None\
             and share_page_active

        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)

        self.new_item.set_sensitive(connected and share_page_active)
        self.delete_item.set_sensitive(connected and selected)
        self.edit_item.set_sensitive(connected and selected)
        self.new_share_wizard_item.set_sensitive(connected
                 and share_page_active)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)

        self.new_button.set_sensitive(connected and share_page_active)
        self.delete_button.set_sensitive(connected and selected)
        self.edit_button.set_sensitive(connected and selected)
        self.new_share_wizard_button.set_sensitive(connected
                 and share_page_active)

        self.active_frame_new_button.set_sensitive(connected
                 and share_page_active)
        self.active_frame_delete_button.set_sensitive(connected
                 and selected)
        self.active_frame_edit_button.set_sensitive(connected
                 and selected)

    def on_disconnect_item_activate(self, widget):
        if self.pipe_manager is not None:
            self.pipe_manager.close()
            self.pipe_manager = None
            self.server_info = None

        self.shares_store.clear()
        self.update_sensitivity()
        self.fill_active_pane()
        self.fill_server_info()

        self.set_status('Disconnected.')

    def toggle_share_view_visiblity(self, widget, Junk):
        """ Toggels Visiblity of hidden shares if authorised """

        is_visible = self.show_all_share_checkbox.get_active()
        self.pipe_manager.show_all_shares = is_visible
        self.pipe_manager.get_shares_list()

        self.show_all_share_checkbox.set_active(
                                    self.pipe_manager.show_all_shares)

        self.refresh_shares_view()

    def on_key_press(self, widget, event):
        if event.keyval == gtk.keysyms.F5:
            self.on_refresh_item_activate(None)
        elif event.keyval == gtk.keysyms.Delete:
            self.on_delete_item_activate(None)
        elif event.keyval == gtk.keysyms.Return:
            myev = gtk.gdk.Event(gtk.gdk._2BUTTON_PRESS)
            # emulates a double-click
            if self.active_page_index == 0:
                self.on_shares_tree_view_button_press(None, myev)

    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)

    def on_new_item_activate(self, widget, wizard_mode=False):

        share = self.run_share_add_edit_dialog(wizard_mode=wizard_mode)

        if share is None:
            self.set_status('Share creation canceled.')
            return

        try:
            self.pipe_manager.add_share(share)
            self.set_status("Successfully added share \'%s\'."
                             % share.name)
        except RuntimeError, re:
            msg = 'Failed to add share: %s.' % re.args[1]
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)
        except Exception, ex:
            msg = 'Failed to ad share: %s.' % str(ex)
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)

        self.refresh_shares_view()

    def on_edit_item_activate(self, widget):
        share = self.get_selected_share()
        share = self.run_share_add_edit_dialog(share,
                self.update_share_callback)
        if share is None:
            self.set_status('Last Share Edit Cancelled.')
            return

        try:
            self.pipe_manager.modify_share(share)
            self.set_status("Successfully modified share \'%s\'."
                             % share.name)
        except RuntimeError, re:
            msg = 'Failed to add share: %s.' % re.args[1]
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)
        except Exception, ex:
            msg = 'Failed to ad share: %s.' % str(ex)
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)

        self.refresh_shares_view()

    def on_delete_item_activate(self, widget):
        share = self.get_selected_share()

        response = self.run_delete_dialog(share)
        if response in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]:

            try:
                self.pipe_manager.delete_share(share.name)
                self.set_status("Successfully deleted share \'%s\'."
                                 % share.name)
            except RuntimeError, re:

                msg = 'Failed to delete share: %s.'\
                     % re.args[1]
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR,
                        gtk.BUTTONS_OK, msg)
            except Exception, ex:
                msg = 'Failed to delete share: %s.' % str(ex)
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR,
                        gtk.BUTTONS_OK, msg)

            self.refresh_shares_view()

    def on_notebook_switch_page(self, widget, page, page_num):
        self.active_page_index = page_num
        self.update_sensitivity()

    def update_share_callback(self, share):
        try:
            self.pipe_manager.modify_share(share)
            self.set_status("Share \'%s\' Modified." % share.name)
        except RuntimeError, re:
            msg = 'Failed to Modify Share: %s.' % re.args[1]
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)
        except Exception, ex:

            msg = 'Failed to Modify Share: %s.' % str(ex)
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)
        finally:
            self.refresh_shares_view()

    def on_refresh_item_activate(self, widget):
        try:
            self.pipe_manager.get_shares_list()
        except RuntimeError, re:
            msg = 'Failed to Refresh SRV Info: %s.'\
                 % re.args[1]
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)
        except Exception, ex:
            msg = 'Failed to Refresh SRV Info: %s.' % str(ex)
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                    msg)

        self.refresh_shares_view()
        self.set_status('Successfully Refreshed Shares List.')

        (model, iter) = \
            self.shares_tree_view.get_selection().get_selected()
        if iter is None:
            return
        selector = self.shares_tree_view.get_selection()
        selector.unselect_iter(iter)

    def on_shares_tree_view_button_press(self, widget, event):
        if self.get_selected_share() is None:
            return

        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.on_edit_item_activate(self.edit_item)

    def on_self_delete(self, widget, event):
        if self.pipe_manager is not None:
            self.on_disconnect_item_activate(self.disconnect_item)

        gtk.main_quit()
        return False

    def refresh_shares_view(self):
        if not self.connected():
            return None

        (model, paths) = \
            self.shares_tree_view.get_selection().get_selected_rows()
        self.pipe_manager.get_shares_list()

        self.shares_store.clear()
        for share in self.pipe_manager.share_list:
            type_comment = \
                self.pipe_manager.get_share_type_info(share.type, 'desc'
                    )
            view_compat_data = [share.name, type_comment,
                                share.comment, share.path]
            self.shares_store.append(view_compat_data)

        if len(paths) > 0:
            self.shares_tree_view.get_selection().select_path(paths[0])

    def fill_active_pane(self):
        """ Fills sthe active left pane """

        share = self.get_selected_share()


        widget_to_delete = \
            self.shareinfo_frame.get_children()[0]
        self.shareinfo_frame.remove(widget_to_delete)

        if share is None:
            table = gtk.Table(1, 2)
            table.set_border_width(5)
            self.active_pane_frame_label.set_markup(
                                        '<b> No Share Selected </b>')

            label = gtk.Label('Please Select a Share First')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, 0, 1, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

            label = gtk.Label(' ' * 55)
            label.set_alignment(1, 0.5)
            table.attach(label, 1, 2, 0, 1, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        else:

            stype = share.type
            flag_set = self.pipe_manager.get_share_type_info(stype,
                    'flags')

            rows_required = ((8 - int(share.password is ''))
                              - int(share.max_users == 0xFFFFFFFF))\
                 - int(not flag_set[1]) + len(share.path) / 35\
                 + 1 + len(share.comment) / 35 + 1

            table = gtk.Table(rows_required, 2)
            table.set_border_width(5)
            table.set_row_spacings(2)
            table.set_col_spacings(6)

            row_index = 0

            self.active_pane_frame_label.set_markup(
                                    '<b>Selected Share Details</b>')

            label = gtk.Label(' Share Name  : ')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)


            label = gtk.Label(share.name)
            label.set_alignment(0, 0.5)
            table.attach(label, 1, 2, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
            row_index += 1

            label = gtk.Label(' Comment  : ')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

            if len(share.comment) > 35:
                for i in range(len(share.comment) / 35 + 1):
                    label = gtk.Label(share.comment[i * 35:i * 35 + 35])
                    label.set_alignment(0, 0.5)
                    table.attach(label, 1, 2, row_index, row_index + 1,
                                  gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                    row_index += 1
            else:
                padding = (35 - len(share.comment)) * ' '
                label = gtk.Label(''.join([share.comment, padding]))
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

            label = gtk.Label(' Path  : ')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

            if len(share.path) > 35:
                for i in range(len(share.path) / 35 + 1):
                    label = gtk.Label(share.path[i * 35:i * 35 + 35])
                    label.set_alignment(0, 0.5)
                    table.attach(label, 1, 2, row_index, row_index + 1,
                                 gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                    row_index += 1
            else:
                if share.path == '':
                    padding = 41 * ' '
                else:
                    padding = (35 - len(share.path)) * ' '
                label = gtk.Label(''.join([share.path, padding]))
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

            if share.password:
                label = gtk.Label(' Password  : ')
                label.set_alignment(1, 0.5)
                table.attach(label, 0, 1, row_index, row_index + 1,
                                gtk.SHRINK, gtk.FILL | gtk.EXPAND, 0, 0)

                label = gtk.Label('Protection Enabled')
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

            label = gtk.Label('<b> Share Type</b>')
            label.set_use_markup(True)
            label.set_alignment(0, 0.5)
            table.attach(label, 0, 1, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
            row_index += 1

            label = gtk.Label(' Type Description  : ')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
            label_data = self.pipe_manager.get_share_type_info(
                                                    stype, 'desc')

            label = gtk.Label(label_data)
            label.set_alignment(0, 0.5)
            table.attach(label, 1, 2, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
            row_index += 1

            label = gtk.Label()
            label.set_markup('<b> Special Flags </b>')
            label.set_alignment(0, 0.5)
            table.attach(label, 0, 1, row_index, row_index + 1,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
            row_index += 1

            flags_present = False
            if flag_set[0]:
                flags_present = True
                label = gtk.Label(' Temporary  : ')
                label.set_alignment(1, 0.5)
                table.attach(label, 0, 1, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

                label = gtk.Label(str(flag_set[0]))
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

            if flag_set[1]:
                flags_present = True
                label = gtk.Label(' Hidden  : ')
                label.set_alignment(1, 0.5)
                table.attach(label, 0, 1, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

                label = gtk.Label(str(flag_set[1]))
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

            if not flags_present:
                label = gtk.Label('No Special Flags')
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

            if not share.max_users == 0xFFFFFFFF:
                label = gtk.Label(' Max Users  : ')
                label.set_alignment(1, 0.5)
                table.attach(label, 0, 1, row_index, row_index + 1,
                                 gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

                label = gtk.Label(share.max_users)
                label.set_alignment(0, 0.5)
                table.attach(label, 1, 2, row_index, row_index + 1,
                                gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
                row_index += 1

        self.shareinfo_frame.add(table)
        self.shareinfo_frame.show_all()

    def create(self):

        # main window
        self.set_title('Samba-Gtk Share Management Interface')
        self.set_default_size(800, 600)
        self.icon_filename = os.path.join(sys.path[0], 'images'
                , 'network.png')
        self.share_icon_filename = os.path.join(sys.path[0],
                'images', 'network.png')
        self.icon_pixbuf = \
            gtk.gdk.pixbuf_new_from_file(self.icon_filename)
        self.set_icon(self.icon_pixbuf)

        accel_group = gtk.AccelGroup()
        toplevel_vbox = gtk.VBox(False, 0)
        self.add(toplevel_vbox)

        # menu
        self.menubar = gtk.MenuBar()
        toplevel_vbox.pack_start(self.menubar, False, False, 0)

        self.file_item = gtk.MenuItem('_File')
        self.menubar.add(self.file_item)

        file_menu = gtk.Menu()
        self.file_item.set_submenu(file_menu)

        self.connect_item = gtk.ImageMenuItem(gtk.STOCK_CONNECT,
                accel_group)
        file_menu.add(self.connect_item)

        self.disconnect_item = gtk.ImageMenuItem(gtk.STOCK_DISCONNECT,
                accel_group)
        self.disconnect_item.set_sensitive(False)
        file_menu.add(self.disconnect_item)

        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        file_menu.add(menu_separator_item)

        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)

        self.view_item = gtk.MenuItem('_View')
        self.menubar.add(self.view_item)

        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)

        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH,
                accel_group)
        self.refresh_item.set_sensitive(False)
        view_menu.add(self.refresh_item)

        self.share_item = gtk.MenuItem('_Share')
        self.menubar.add(self.share_item)

        share_menu = gtk.Menu()
        self.share_item.set_submenu(share_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        self.new_item.set_sensitive(False)
        share_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE,
                accel_group)
        self.delete_item.set_sensitive(False)
        share_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        self.edit_item.set_sensitive(False)
        share_menu.add(self.edit_item)

        self.wizard_item = gtk.MenuItem('_Wizard')
        self.menubar.add(self.wizard_item)

        wizard_menu = gtk.Menu()
        self.wizard_item.set_submenu(wizard_menu)

        self.new_share_wizard_item = \
            gtk.MenuItem(label='New Share Wizard')
        wizard_menu.add(self.new_share_wizard_item)

        self.help_item = gtk.MenuItem('_Help')
        self.menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT,
                accel_group)
        help_menu.add(self.about_item)

        # Toolbar
        self.toolbar = gtk.Toolbar()
        toplevel_vbox.pack_start(self.toolbar, False, False, 0)

        self.connect_button = gtk.ToolButton(gtk.STOCK_CONNECT)
        self.connect_button.set_is_important(True)
        self.connect_button.set_tooltip_text('Connect to a server')
        self.toolbar.insert(self.connect_button, 0)

        self.disconnect_button = gtk.ToolButton(gtk.STOCK_DISCONNECT)
        self.disconnect_button.set_is_important(True)
        self.disconnect_button.set_tooltip_text(
                                        'Disconnect from the server')
        self.toolbar.insert(self.disconnect_button, 1)

        sep = gtk.SeparatorToolItem()
        self.toolbar.insert(sep, 2)

        self.new_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_button.set_is_important(True)
        self.toolbar.insert(self.new_button, 3)

        self.edit_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.edit_button.set_is_important(True)
        self.toolbar.insert(self.edit_button, 4)

        self.delete_button = gtk.ToolButton(gtk.STOCK_DELETE)
        self.delete_button.set_is_important(True)
        self.toolbar.insert(self.delete_button, 5)

        sep = gtk.SeparatorToolItem()
        self.toolbar.insert(sep, 6)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_EXECUTE, 48)
        self.new_share_wizard_button = gtk.ToolButton(image,
                'New Share Wizard')
        self.new_share_wizard_button.set_is_important(True)
        self.toolbar.insert(self.new_share_wizard_button, 7)

        self.new_button.set_tooltip_text('Add a new Share')
        self.edit_button.set_tooltip_text('Edit a Share')
        self.delete_button.set_tooltip_text('Delete a Share')

        # Share-page
        self.share_notebook = gtk.Notebook()
        toplevel_vbox.pack_start(self.share_notebook, True, True, 0)

        main_hbox = gtk.HBox()
        self.share_notebook.append_page(main_hbox,
                gtk.Label('Share Management'))

        # Share listing on left side
        rvbox = gtk.VBox()
        main_hbox.pack_start(rvbox, True, True, 0)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC,
                                        gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        rvbox.pack_start(scrolledwindow, True, True, 2)

        self.shares_tree_view = gtk.TreeView()
        scrolledwindow.add(self.shares_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title('')
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property('pixbuf',
                              gtk.gdk.pixbuf_new_from_file_at_size(
                              self.share_icon_filename,22, 22))
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)

        column = gtk.TreeViewColumn()
        column.set_title('Name')
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, 'text', 0)

        column = gtk.TreeViewColumn()
        column.set_title('Share Type')
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, 'text', 1)

        column = gtk.TreeViewColumn()
        column.set_title('Comment')
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, 'text', 2)

        column = gtk.TreeViewColumn()
        column.set_title('Path')
        column.set_resizable(True)
        column.set_sort_column_id(3)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, 'text', 3)

        self.shares_store = gtk.ListStore(gobject.TYPE_STRING,
                gobject.TYPE_STRING, gobject.TYPE_STRING,
                gobject.TYPE_STRING)
        self.shares_store.set_sort_column_id(0,
                gtk.SORT_ASCENDING)
        self.shares_tree_view.set_model(self.shares_store)

        hbox = gtk.HBox()
        rvbox.pack_start(hbox, False, False, 0)

        self.show_all_share_checkbox = \
            gtk.CheckButton('Show Hidden Shares')
        hbox.pack_end(self.show_all_share_checkbox, False, False,
                      0)
        self.show_all_share_checkbox.set_tooltip_text(
                    'Enable or disable the visiblity of hidden shares')
        self.show_all_share_checkbox.set_active(False)
        self.show_all_share_checkbox.connect('toggled',
                self.toggle_share_view_visiblity, None)

        ### Right active widget :

        vbox = gtk.VBox()
        main_hbox.pack_start(vbox, False, False, 0)

        self.shareinfo_frame = gtk.Frame()
        self.active_pane_frame_label = gtk.Label()
        self.active_pane_frame_label.set_use_markup(True)
        self.active_pane_frame_label.set_markup(
                                        '<b> No Share Selected </b>')
        self.shareinfo_frame.set_label_widget(
                                        self.active_pane_frame_label)
        vbox.pack_start(self.shareinfo_frame, False, True, 0)
        self.shareinfo_frame.set_border_width(5)

        table = gtk.Table(1, 2)
        table.set_border_width(5)
        table.set_row_spacings(2)
        table.set_col_spacings(6)

        self.shareinfo_frame.add(table)

        label = gtk.Label('Please Slect a Share First')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 0, 1,gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)


        label = gtk.Label(' ' * 55)
        label.set_alignment(1, 0.5)
        table.attach(label, 1, 2, 0, 1, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        hbox = gtk.HBox()
        vbox.pack_end(hbox, False, False, 0)

        table = gtk.Table(3, 6, True)
        hbox.pack_start(table, False, True, 0)

        self.active_frame_new_button = gtk.Button('New')
        self.active_frame_new_button.set_tooltip_text('Add a New Share')
        table.attach(self.active_frame_new_button, 2, 3, 1, 2,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_frame_edit_button = gtk.Button('Edit')
        self.active_frame_edit_button.set_tooltip_text(
                                                'Edit Current Share')
        table.attach(self.active_frame_edit_button, 3, 4, 1, 2,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_frame_delete_button = gtk.Button('Delete')
        self.active_frame_delete_button.set_tooltip_text(
                                                'Delete Current Share')
        table.attach(self.active_frame_delete_button, 4, 5, 1, 2,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        # Server Info Page
        hbox = gtk.HBox(True)
        self.share_notebook.append_page(hbox,
                gtk.Label('Share Server Info'))

        vbox = gtk.VBox()
        hbox.pack_start(vbox, True, True, 0)
        self.srvinfo_frame = gtk.Frame()
        self.srv_info_label = gtk.Label('<b>Share Server Details</b>')
        self.srv_info_label.set_use_markup(True)
        self.srvinfo_frame.set_label_widget(self.srv_info_label)
        vbox.pack_start(self.srvinfo_frame, False, True, 0)
        self.srvinfo_frame.set_border_width(5)

        table = gtk.Table(10, 2)
        table.set_border_width(5)
        table.set_row_spacings(3)
        table.set_col_spacings(6)
        self.srvinfo_frame.add(table)

        label = gtk.Label(' Target Platform OS  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_tos_label = gtk.Label()
        self.srvinfo_tos_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_tos_label, 1, 2, 1, 2,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' NetBIOS Name : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_name_label = gtk.Label()
        self.srvinfo_name_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_name_label, 1, 2, 2, 3,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Hidden  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_hidden_label = gtk.Label()
        self.srvinfo_hidden_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_hidden_label, 1, 2, 3, 4,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Comment  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_comment_label = gtk.Label()
        self.srvinfo_comment_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_comment_label, 1, 2, 4 ,5,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Version : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 5, 6, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_version_label = gtk.Label()
        self.srvinfo_version_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_version_label, 1, 2, 5, 6,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Server Type  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 6, 7, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_type_label = gtk.Label()
        self.srvinfo_type_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_type_label, 1, 2, 6, 7,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)


        label = gtk.Label(' User Path  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 7, 8, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_upath_label = gtk.Label()
        self.srvinfo_upath_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_upath_label, 1, 2, 7, 8,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)


        label = gtk.Label(' Timeout  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 8, 9, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_to_label = gtk.Label()
        self.srvinfo_to_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_to_label, 1, 2, 8, 9,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)


        label = gtk.Label(' Announce / Anndelta  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 9, 10, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.srvinfo_aa_label = gtk.Label()
        self.srvinfo_aa_label.set_alignment(0, 0.5)
        table.attach(self.srvinfo_aa_label, 1, 2, 9, 10,
                            gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)


        vbox = gtk.VBox()
        hbox.pack_start(vbox, True, True, 0)

        self.sd_frame = gtk.Frame()
        self.sd_frame.set_border_width(5)
        label = gtk.Label('<b> Shared Disks </b>')
        label.set_use_markup(True)
        self.sd_frame.set_label_widget(label)
        vbox.pack_start(self.sd_frame, False, False, 0)

        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        toplevel_vbox.pack_end(self.statusbar, False, False, 0)

        # signals/events

        self.connect('delete_event', self.on_self_delete)
        self.connect('key-press-event', self.on_key_press)

        self.connect_item.connect('activate',
                                  self.on_connect_item_activate)
        self.disconnect_item.connect('activate',
                self.on_disconnect_item_activate)
        self.quit_item.connect('activate', self.on_quit_item_activate)
        self.refresh_item.connect('activate',
                                  self.on_refresh_item_activate)
        self.about_item.connect('activate', self.on_about_item_activate)

        self.new_item.connect('activate', self.on_new_item_activate)
        self.delete_item.connect('activate',
                                 self.on_delete_item_activate)
        self.edit_item.connect('activate', self.on_edit_item_activate)
        self.new_share_wizard_item.connect('activate',
                self.on_new_item_activate, True)

        self.connect_button.connect('clicked',
                                    self.on_connect_item_activate)
        self.disconnect_button.connect('clicked',
                self.on_disconnect_item_activate)

        self.new_button.connect('clicked', self.on_new_item_activate)
        self.delete_button.connect('clicked',
                                   self.on_delete_item_activate)
        self.edit_button.connect('clicked', self.on_edit_item_activate)
        self.new_share_wizard_button.connect('clicked',
                self.on_new_item_activate, True)

        self.active_frame_new_button.connect('clicked',
                self.on_new_item_activate)
        self.active_frame_delete_button.connect('clicked',
                self.on_delete_item_activate)
        self.active_frame_edit_button.connect('clicked',
                self.on_edit_item_activate)

        self.shares_tree_view.get_selection().connect('changed',
                self.on_update_sensitivity)
        self.shares_tree_view.get_selection().connect('changed',
                self.on_switch_fill_active_pane)
        self.shares_tree_view.connect('button_press_event',
                self.on_shares_tree_view_button_press)

        self.share_notebook.connect('switch-page',
                                    self.on_notebook_switch_page)

        self.add_accel_group(accel_group)

############################################################################################################


def PrintUsage():
    print 'Usage: %s [OPTIONS]'\
         % str(os.path.split(__file__)[-1])
    print 'All options are optional. The user will be queried for additional information if needed.\n'
    print '  -s  --server\t\tspecify the server to connect to.'
    print '  -u  --user\t\tspecify the username.'
    print '  -p  --password\tThe password for the user.'
    print '''  -t  --transport\tTransport type.
\t\t\t\t0 for RPC, SMB, TCP/IP
\t\t\t\t1 for RPC, TCP/IP
\t\t\t\t2 for localhost.'''
    print '  -c  --connect-now\tSkip the connect dialog.'


def ParseArgs(argv):
    arguments = {}

    try:  # get arguments into a nicer format
        (opts, args) = getopt.getopt(argv, 'chu:s:p:t:', ['help',
                        'user=', 'server=', 'password=', 'connect-now',
                        'transport='])
    except getopt.GetoptError:
        PrintUsage()
        sys.exit(2)

    for (opt, arg) in opts:
        if opt in ('-h', '--help'):
            PrintUsage()
            sys.exit(0)
        elif opt in ('-s', '--server'):
            arguments.update({'server': arg})
        elif opt in ('-u', '--user'):
            arguments.update({'username': arg})
        elif opt in ('-p', '--password'):
            arguments.update({'password': arg})
        elif opt in ('-t', '--transport'):
            arguments.update({'transport_type': int(arg)})
        elif opt in ('-c', '--connect-now'):
            arguments.update({'connect_now': True})
    return arguments


if __name__ == '__main__':
    arguments = ParseArgs(sys.argv[1:])

    main_window = ShareWindow(**arguments)
    main_window.show_all()
    gtk.main()

