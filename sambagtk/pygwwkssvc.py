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

from sambagtk.wkssvc import (wkssvcConnectDialog , DeleteDialog)


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

        (info_ctr, totalentries, self.resume_handle_users) = \
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

    def unjoin_domain(self,server_address, username, password):
        # TODO test this !
        #unjoin_flags = wkssvc.WKSSVC_JOIN_FLAGS_xxx | wkssvc.WKSSVC_JOIN_FLAGS_xxx
        encrypted_password = get_encrypted_password_buff(password)
        self.pipe.NetrUnjoinDomain2(server_name, username,
                                    encrypted_password, unjoin_flags)



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

    def update_sensitivity(self):

        connected = self.pipe_manager is not None
        selected = self.get_selected_domain() is not None

        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)

        self.join_domain_item.set_sensitive(connected)
        self.unjoin_domain_item.set_sensitive(connected and selected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)

        self.join_domain_button.set_sensitive(connected)
        self.unjoin_domain_button.set_sensitive(connected and selected)


    def on_update_sensitivity(self, widget):
        self.update_sensitivity()

    def on_refresh_item_activate(self, widget):
        self.refresh_domains_view()
        self.set_status('Successfully Refreshed Domains List.')



    def run_new_join_dialog(self):
        dialog = DomainJoinDialog()
        while True:
            response_id = dialog.run()

            if response_id in [Gtk.ResponseType.OK,
                               Gtk.ResponseType.APPLY]:

                dialog.collect_fields()

                if response_id == Gtk.ResponseType.OK:
                    dialog.hide()
                    break
            else:
                dialog.hide()
                return None
        required_data = {}
        required_data["server_address"] = dialog.server_address
        required_data["domain_name"] = dialog.domain_name
        required_data["machine_name"] = dialog.machine_name
        required_data["username"] = dialog.username
        required_data["password"] = dialog.password

        return required_data

    def on_join_item_activate(self, widget):

        required_data = self.run_new_join_dialog()
        self.pipe_manager.join_domian()

        if required_data is None:
            self.set_status('Join canceled.')
            return

        try:
            self.pipe_manager.join_domian(required_data.get(server_address),
                                        required_data.get(domain_name),
                                        required_data.get(machine_name),
                                        required_data.get(username),
                                        required_data.get(password))
            self.set_status("Successfully joined domian \'%s\'."
                             % required_data.get(domain_name))
        except RuntimeError, re:
            msg = 'Failed to join domian: %s.' % re.args[1]
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(Gtk.MessageType.ERROR,
                                        Gtk.ButtonsType.OK, msg)
        except Exception, ex:
            msg = 'Failed to join domain: %s.' % str(ex)
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(Gtk.MessageType.ERROR,
                                        Gtk.ButtonsType.OK, msg)

        self.refresh_domains_view()

    def refresh_domains_view(self):
        if not self.connected():
            return None

        (model, paths) = \
            self.domains_tree_view.get_selection().get_selected_rows()
        self.domains_store.clear()
        #TODO : Implement this logic
        #self.pipe_manager.get_domains list()


    def on_unjoin_item_activate(self,widget):
        domain_name = self.get_selected_domain()
        #confirm deletion
        response = self.run_delete_dialog(domain_name)
        if response in [Gtk.ResponseType.OK, Gtk.ResponseType.APPLY]:

            try:
                # TODO : Implement this logic
                #self.pipe_manager.unjoin_domain()
                self.set_status("Successfully unjoined domain \'%s\'."
                                 % domain_name)
            except RuntimeError, re:

                msg = 'Failed to unjoin domain: %s.'\
                     % re.args[1]
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(Gtk.MessageType.ERROR,
                                        Gtk.ButtonsType.OK, msg)
            except Exception, ex:
                msg = 'Failed to unjoin domain: %s.' % str(ex)
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK, msg)

            self.refresh_domains_view()


    def get_selected_domain(self):
        if not self.connected():
            return None

        (model, iter) = \
            self.domains_tree_view.get_selection().get_selected()
        if iter is None:  # no selection
            return None
        else:
            domain_name = model.get_value(iter, 0)
            return domain_name

    def on_disconnect_item_activate(self, widget):
        if self.pipe_manager is not None:
            self.pipe_manager.close()
            self.pipe_manager = None
            self.wkst_info = None
        self.set_status('Disconnected.')

    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_F5:
            self.on_refresh_item_activate(None)
        elif event.keyval == Gdk.KEY_Delete:
            self.on_delete_item_activate(None)

    def on_self_delete(self, widget, event):
        if self.pipe_manager is not None:
            self.on_disconnect_item_activate(self.disconnect_item)

        Gtk.main_quit()
        return False

    def create(self):
        # main window
        self.set_title('Samba-Gtk Workstation Management Interface')
        self.set_default_size(800, 600)
        self.icon_filename = os.path.join(sys.path[0], 'images'
                , 'network.png')
        self.icon_pixbuf = \
            GdkPixbuf.Pixbuf.new_from_file(self.icon_filename)
        self.set_icon(self.icon_pixbuf)

        accel_group = Gtk.AccelGroup()
        toplevel_vbox = Gtk.VBox(False, 0)
        self.add(toplevel_vbox)

         # menu
        self.menubar = Gtk.MenuBar()
        toplevel_vbox.pack_start(self.menubar, False, False, 0)

        self.file_item = Gtk.MenuItem.new_with_mnemonic('_File')
        self.menubar.add(self.file_item)

        file_menu = Gtk.Menu()
        self.file_item.set_property("submenu",file_menu)

        self.connect_item = Gtk.ImageMenuItem.new_from_stock(
                                                Gtk.STOCK_CONNECT, accel_group)
        self.connect_item.set_always_show_image(True)
        file_menu.add(self.connect_item)

        self.disconnect_item = Gtk.ImageMenuItem.new_from_stock(
                                             Gtk.STOCK_DISCONNECT, accel_group)
        self.disconnect_item.set_sensitive(False)
        self.disconnect_item.set_always_show_image(True)
        file_menu.add(self.disconnect_item)

        menu_separator_item = Gtk.SeparatorMenuItem()
        menu_separator_item.set_property("sensitive",False)
        file_menu.add(menu_separator_item)

        self.quit_item = Gtk.ImageMenuItem.new_from_stock(
                                                   Gtk.STOCK_QUIT, accel_group)
        self.quit_item.set_always_show_image(True)
        file_menu.add(self.quit_item)

        self.view_item = Gtk.MenuItem.new_with_mnemonic('_View')
        self.menubar.add(self.view_item)

        view_menu = Gtk.Menu()
        self.view_item.set_property("submenu",view_menu)

        self.refresh_item = Gtk.ImageMenuItem.new_from_stock(
                                                Gtk.STOCK_REFRESH, accel_group)
        self.refresh_item.set_sensitive(False)
        self.refresh_item.set_always_show_image(True)
        view_menu.add(self.refresh_item)

        self.joins_item = Gtk.MenuItem.new_with_mnemonic('_Joins')
        self.menubar.add(self.joins_item)

        joins_menu = Gtk.Menu()
        self.joins_item.set_submenu(joins_menu)

        self.join_domain_item = Gtk.ImageMenuItem.new_from_stock(
                                                    Gtk.STOCK_CONNECT, accel_group)
        self.join_domain_item.set_sensitive(False)
        self.join_domain_item.set_always_show_image(True)
        joins_menu.add(self.join_domain_item)

        self.unjoin_domain_item = Gtk.ImageMenuItem.new_from_stock(
                                                 Gtk.STOCK_DISCONNECT, accel_group)
        self.unjoin_domain_item.set_sensitive(False)
        self.unjoin_domain_item.set_always_show_image(True)
        joins_menu.add(self.unjoin_domain_item)

        self.help_item = Gtk.MenuItem.new_with_mnemonic('_Help')
        self.menubar.add(self.help_item)

        help_menu = Gtk.Menu()
        self.help_item.set_property("submenu",help_menu)

        self.about_item = Gtk.ImageMenuItem.new_from_stock(
                                                  Gtk.STOCK_ABOUT, accel_group)
        self.about_item.set_always_show_image(True)
        help_menu.add(self.about_item)

        # Toolbar
        self.toolbar = Gtk.Toolbar()
        toplevel_vbox.pack_start(self.toolbar, False, False, 0)

        self.connect_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CONNECT)
        self.connect_button.set_is_important(True)
        self.connect_button.set_tooltip_text('Connect to a server')
        self.toolbar.insert(self.connect_button, 0)

        self.disconnect_button = Gtk.ToolButton.new_from_stock(
                                                         Gtk.STOCK_DISCONNECT)
        self.disconnect_button.set_is_important(True)
        self.disconnect_button.set_tooltip_text('Disconnect from the server')
        self.toolbar.insert(self.disconnect_button, 1)

        sep = Gtk.SeparatorToolItem()
        self.toolbar.insert(sep, 2)

        self.join_domain_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CONNECT)
        self.join_domain_button.set_text("Join Domain")
        self.join_domain_button.set_is_important(True)
        self.join_domain_button.set_tooltip_text('Join a new Domain')
        self.toolbar.insert(self.join_domain_button, 3)

        self.unjoin_domain_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_DISCONNECT)
        self.unjoin_domain_button.set_text("Unjoin Domain")
        self.unjoin_domain_button.set_is_important(True)
        self.unjoin_domain_button.set_tooltip_text('Unjoin Domain')
        self.toolbar.insert(self.unjoin_domain_button, 4)

        # domains list

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_property("shadow_type",Gtk.ShadowType.IN)
        toplevel_vbox.pack_start(scrolledwindow, True, True, 0)

        self.domains_tree_view = Gtk.TreeView()
        scrolledwindow.add(self.domains_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title('')
        renderer = Gtk.CellRendererPixbuf()
        renderer.set_property('pixbuf',
                              GdkPixbuf.Pixbuf.new_from_file_at_size(
                              self.icon_filename,22, 22))
        column.pack_start(renderer, True)
        self.domains_tree_view.append_column(column)

        column = Gtk.TreeViewColumn()
        column.set_title('Name')
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.domains_tree_view.append_column(column)
        column.add_attribute(renderer, 'text', 0)

        # may need a few more columns

        self.domains_store = Gtk.ListStore(GObject.TYPE_STRING)
        self.domains_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.domains_tree_view.set_model(self.domains_store)

        # status bar
        self.statusbar = Gtk.Statusbar()
        toplevel_vbox.pack_start(self.statusbar, False, False, 0)

        # signals/events

        self.connect("delete_event", self.on_self_delete)
        self.connect("key-press-event", self.on_key_press)

        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate",
                                            self.on_disconnect_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)

        self.join_domain_item.connect("activate", self.on_join_item_activate)
        self.unjoin_domain_item.connect("activate",
                                               self.on_unjoin_item_activate)

        self.about_item.connect("activate", self.on_about_item_activate)

        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked",
                                            self.on_disconnect_item_activate)

        self.join_domain_button.connect('clicked', self.on_new_item_activate)
        self.unjoin_domain_button.connect('clicked',self.on_delete_item_activate)

        self.domains_tree_view.get_selection().connect("changed",
                                                self.on_update_sensitivity)
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

    main_window = WkssvcWindow(**arguments)
    main_window.show_all()
    Gtk.main()
