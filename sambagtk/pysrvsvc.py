#!/usr/bin/python
# -*- coding: utf-8 -*-

#       pysrvsvc.py
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

""" srvsvc related dialogues"""

import gtk
import gobject
import os
import sys

from samba.dcerpc import srvsvc


class srvsvcConnectDialog(gtk.Dialog):

    """Connect Dialog"""

    def __init__(self, server, transport_type, username, password=''):

        super(srvsvcConnectDialog, self).__init__()

        self.server_address = server
        self.username = username
        self.password = password
        self.transport_type = transport_type

        self.create()
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_modal(True)

        self.update_sensitivity()
        self.about_dialog = gtk.AboutDialog()

    def create(self):
        self.set_title('Connect to Samba Share Server')
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)
        self.set_decorated(True)

        self.vbox.set_spacing(5)

        # artwork TODO remove post decession
        
        self.artwork = gtk.VBox()

        self.samba_image_filename = os.path.join(sys.path[0], 'images',
                'samba-logo-small.png')
        self.samba_image = gtk.Image()
        self.samba_image.set_from_file(self.samba_image_filename)
        self.artwork.pack_start(self.samba_image, True, True, 0)

        label = gtk.Label('Opening Windows to A Wider World')
        box = gtk.HBox()
        box.pack_start(label, True, True, 0)
        self.artwork.pack_start(box, True, True, 0)

        label = gtk.Label('Samba Control Center')
        box = gtk.HBox()
        box.pack_start(label, True, True, 0)
        self.artwork.pack_start(box, True, True, 0)

        self.vbox.pack_start(self.artwork, False, True, 0)
        
        ########################### end of artwork TODO :

        # server frame

        self.server_frame = gtk.Frame('Server')
        self.vbox.pack_start(self.server_frame, False, True, 0)

        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)

        label = gtk.Label(' Server address: ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        self.server_address_entry.set_tooltip_text(
                                        'Enter the Server Address')
        table.attach(self.server_address_entry, 1, 2, 0, 1,
                gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(' Username: ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        self.username_entry.set_tooltip_text('Enter your Username')
        table.attach(self.username_entry, 1, 2, 1, 2,
                gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(' Password: ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL,
                        gtk.FILL | gtk.EXPAND, 0, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_text(self.password)
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        self.password_entry.set_tooltip_text('Enter your Password')
        table.attach(self.password_entry, 1, 2, 2, 3,
                gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        # transport frame
        
        self.transport_frame = gtk.Frame(' Transport type ')
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)

        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None,
                'RPC over SMB over TCP/IP ')
        self.rpc_smb_tcpip_radio_button.set_tooltip_text(
                                'ncacn_np type : Recomended (default)')
        # Default according MS-SRVS specification

        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type
                 == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)

        self.rpc_tcpip_radio_button = \
            gtk.RadioButton(self.rpc_smb_tcpip_radio_button,
                            'RPC over TCP/IP')
        self.rpc_tcpip_radio_button.set_tooltip_text('ncacn_ip_tcp type'
                )
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)

        self.localhost_radio_button = \
            gtk.RadioButton(self.rpc_tcpip_radio_button, 'Localhost')
        self.localhost_radio_button.set_tooltip_text('ncalrpc type')  # # MS-SRVS specification
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)

        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button('Cancel', gtk.STOCK_CANCEL)
        self.cancel_button.set_tooltip_text('Cancel and Quit')
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.connect_button = gtk.Button('Connect', gtk.STOCK_CONNECT)
        self.connect_button.set_flags(gtk.CAN_DEFAULT)
        self.connect_button.set_tooltip_text('OK / Connect to Server')
        self.add_action_widget(self.connect_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)

        self.rpc_smb_tcpip_radio_button.connect('toggled',
                self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect('toggled',
                self.on_radio_button_toggled)
        self.localhost_radio_button.connect('toggled',
                self.on_radio_button_toggled)

    def get_server_address(self):
        if self.get_transport_type() is 2:
            return '127.0.0.1'
        return self.server_address_entry.get_text().strip()

    def get_username(self):
        return self.username_entry.get_text().strip()

    def get_password(self):
        return self.password_entry.get_text()

    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()
        self.server_address_entry.set_sensitive(server_required)

    def get_transport_type(self):
        if self.rpc_smb_tcpip_radio_button.get_active():
            return 0
        elif self.rpc_tcpip_radio_button.get_active():
            return 1
        elif self.localhost_radio_button.get_active():
            return 2
        else:
            return -1

    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()


class ShareAddEditDialog(gtk.Dialog):

    """
    Share add and edit dialog

    If 'edit_mode' is set to True then in Edit mode .
    Immutable fields are automatically greyed out.
    """

    def __init__(self, pipe_manager, share=None):
        """ Class initialiser """

        super(ShareAddEditDialog, self).__init__()
        self.pipe = pipe_manager
        self.islocal = self.pipe.islocal

        if share is None:
            self.edit_mode = 0
            self.share = self.pipe.get_share_object()
        else:
            self.edit_mode = 1
            self.share = share
        self.share_to_fields()
        self.create()
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_window_mode()
        self.set_modal(True)

    def set_window_mode(self):
        """ Deactivates a bunch of widgets in Edit mode """

        if self.edit_mode:
            self.share_name_entry.set_sensitive(False)
            self.stype_disktree_radio_button.set_sensitive(False)
            self.stype_printq_radio_button.set_sensitive(False)
            self.stype_ipc_radio_button.set_sensitive(False)
            self.sflag_temp_check_button.set_sensitive(False)
            self.sflag_hidden_check_button.set_sensitive(False)

    def get_stype_final(self):
        """ Calculates share type from base type and share flags """

        stype = self.stype
        if self.flags[0]:
            stype |= srvsvc.STYPE_TEMPORARY
        if self.flags[1]:
            stype |= -srvsvc.STYPE_HIDDEN
        return stype

    def validate_fields(self):
        """ Checks for some Errors"""

        if type(self) is ShareAddEditDialog:
            name = self.share_name_entry.get_text()
        elif type(self) is ShareWizardDialog:
            name = self.sname

        if len(name) == 0:
            return 'Share name may not be empty!'

        if not self.pipe.name_validate(name):
            return 'Invalid Share name'

        if not self.edit_mode:
            for share in self.pipe.share_list:
                if share.name == name:
                    return ' '.join(['A Share with the name : ',
                                    share.name, 'already exists!'])

        return None

    def toggle_pwd_visiblity(self, widget, Junk):
        """ Toggels Password visiblity"""

        mode = self.set_pw_visiblity.get_active()
        self.share_password_entry.set_visibility(mode)

    def share_to_fields(self):
        """ Gets values from the share . """

        self.sname = self.share.name
        self.stype = self.pipe.get_share_type_info(self.share.type,
                'base_type')
        self.flags = self.pipe.get_share_type_info(self.share.type,
                'flags')
        self.comment = self.share.comment
        self.max_users = self.share.max_users
        if self.share.password is None:
            self.password = ''
        else:
            self.password = self.share.password
        self.path = self.share.path

    def fields_to_gui(self):
        """ Used to reset the gui fields from share fields on apply"""

        self.share_name_entry.set_text(self.sname)
        self.share_comment_entry.set_text(self.comment)
        self.share_password_entry.set_text(self.password)

        self.stype_disktree_radio_button.set_active(self.stype
                 == srvsvc.STYPE_DISKTREE)
        self.stype_printq_radio_button.set_active(self.stype
                 == srvsvc.STYPE_PRINTQ)
        self.stype_ipc_radio_button.set_active(self.stype
                 == srvsvc.STYPE_IPC)

        self.sflag_temp_check_button.set_active(self.flags[0])
        self.sflag_hidden_check_button.set_active(self.flags[1])

        if self.islocal:
            self.file_button.set_current_folder(self.path)
        else:
            self.file_entry.set_text(self.path)
        self.max_users_spinbox.set_value(self.max_users)

    def collect_fields(self):
        """ Collects fields from the GUI and saves in class variables """

        self.sname = self.share_name_entry.get_text()
        self.comment = self.share_comment_entry.get_text()
        self.password = self.share_password_entry.get_text()
        
        # Now to handle the share type resolution
        if self.stype_disktree_radio_button.get_active():
            self.stype = srvsvc.STYPE_DISKTREE
        elif self.stype_printq_radio_button.get_active():
            self.stype = srvsvc.STYPE_PRINTQ
        else:
            self.stype = srvsvc.STYPE_IPC
        # check flags
        self.flags = [False, False]
        if self.sflag_temp_check_button.get_active():
            self.flags[0] = True
        if self.sflag_hidden_check_button.get_active():
            self.flags[1] = True
        if self.islocal:
            self.path = self.file_button.get_filename()
        else:
            self.path = self.path_entry.get_text()
        self.max_users = self.max_users_spinbox.get_value_as_int()

    def fields_to_share(self):
        """ Modify a share type 502 object from the fields collected """

        self.collect_fields()
        self.share.name = self.sname
        self.share.type = self.get_stype_final()
        self.share.comment = self.comment
        self.share.max_users = self.max_users
        self.share.password = self.password
        self.share.path = self.pipe.fix_path_format(self.path)

    def create(self):
        """ Create the window """

        self.set_title(' '.join([(' New Share', ' Edit Share : '
                       )[self.edit_mode], self.sname]))
        self.icon_name = ['network-folder', 'network-printer', 'network'
                          , 'network-pipe'][self.stype]
        self.icon_filename = os.path.join(sys.path[0], 'images',
                ''.join([self.icon_name, '.png']))
        self.set_icon_from_file(self.icon_filename)
        self.vbox.set_spacing(3)
        self.set_border_width(5)
        self.set_decorated(True)
        self.set_resizable(False)
        
        # artwork
        self.desc_box = gtk.HBox()
        self.vbox.pack_start(self.desc_box, False, True, 0)

        hbox = gtk.HBox()
        icon = gtk.Image()
        icon.set_from_file(self.icon_filename)

        hbox.pack_start(icon, False, True, 0)
        self.desc_box.pack_start(hbox, False, True, 0)

        hbox = gtk.HBox()
        label = gtk.Label()
        if self.edit_mode:
            label.set_markup('<b>%s</b>'
                              % ' '.join(['Editing The Share : ',
                             self.sname]))
        else:
            label.set_markup('<b>Add a New Share</b>')
        label.set_alignment(0.5, 0.5)
        hbox.pack_start(label, True, True, 0)
        self.desc_box.pack_start(hbox, True, True, 0)
        
        # main form box

        self.form_box = gtk.VBox()
        self.vbox.pack_start(self.form_box, True, True, 0)
        
        # Name , password and comment (npc) frame        
        frame = gtk.Frame()
        label = gtk.Label('<b>Name and Comment</b>')
        label.set_use_markup(True)
        frame.set_label_widget(label)
        self.form_box.pack_start(frame, True, True, 0)
        frame.set_border_width(5)

        table = gtk.Table(4, 2)
        table.set_border_width(5)
        table.set_row_spacings(1)
        table.set_col_spacings(6)

        frame.add(table)

        label = gtk.Label(' Share Name : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        self.share_name_entry = gtk.Entry()
        self.share_name_entry.set_tooltip_text('Enter the Share Name')
        self.share_name_entry.set_text(self.sname)
        self.share_name_entry.set_activates_default(True)

		# dcesrv_srvsvc name check does this but just to reduce chances of an error limit max length
        if self.flags[1]:
            self.share_name_entry.set_max_length(12)
        else:
            self.share_name_entry.set_max_length(80)
        table.attach(self.share_name_entry, 1, 2, 0, 1,
                    gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(' Comment  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        self.share_comment_entry = gtk.Entry()
        self.share_comment_entry.set_max_length(48)  # max allowed is 48 MS-SRVS
        self.share_comment_entry.set_activates_default(True)
        self.share_comment_entry.set_text(self.comment)
        self.share_comment_entry.set_tooltip_text('Add a Comment or Description of the Share, Will default to share_type description'
                )
        table.attach(self.share_comment_entry, 1, 2, 1, 2,
                    gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(' Password  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        self.share_password_entry = gtk.Entry()
        self.share_password_entry.set_activates_default(True)
        self.share_password_entry.set_text(self.password)
        self.share_password_entry.set_visibility(False)
        self.share_password_entry.set_tooltip_text(
                                                'Set a Share Password')
        table.attach(self.share_password_entry, 1, 2, 2, 3,
                    gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)


        self.set_pw_visiblity = gtk.CheckButton('Visible')
        self.set_pw_visiblity.set_tooltip_text('Enable or disable the password visiblity'
                )
        self.set_pw_visiblity.set_active(False)
        self.set_pw_visiblity.connect('toggled',
                self.toggle_pwd_visiblity, None)
        table.attach(self.set_pw_visiblity, 1, 2, 3, 4, gtk.SHRINK,
                            gtk.FILL, 0, 0)

        # Share frame
        frame = gtk.Frame()
        label = gtk.Label('<b>Share Type</b>')
        label.set_use_markup(True)
        frame.set_label_widget(label)

        self.form_box.pack_start(frame, True, True, 0)

        table = gtk.Table(1, 2, True)
        frame.add(table)

        # Base Share Types
        vbox = gtk.VBox()
        vbox.set_border_width(5)
        table.attach(vbox, 0, 1, 0, 1, gtk.FILL | gtk.EXPAND,
                                        gtk.FILL | gtk.EXPAND, 1, 1)

        # Radio buttons
        self.stype_disktree_radio_button = gtk.RadioButton(None,
                'Disktree')
        self.stype_disktree_radio_button.set_tooltip_text(
                            'Disktree (folder) type Share. Default')
        self.stype_disktree_radio_button.set_active(self.stype
                 == srvsvc.STYPE_DISKTREE)
        vbox.pack_start(self.stype_disktree_radio_button)

        self.stype_printq_radio_button = \
            gtk.RadioButton(self.stype_disktree_radio_button,
                            'Print Queue')
        self.stype_printq_radio_button.set_tooltip_text(
                                                'Shared Print Queue')
        self.stype_printq_radio_button.set_active(self.stype
                 == srvsvc.STYPE_PRINTQ)
        # vbox.pack_start(self.stype_printq_radio_button)
        # deactivating this option until samba4 is fixed TODO activate once base is fixed

        self.stype_ipc_radio_button = \
            gtk.RadioButton(self.stype_printq_radio_button, 'IPC ')
        self.stype_ipc_radio_button.set_tooltip_text(
                        'Shared Interprocess Communication Pipe (IPC).')
        self.stype_ipc_radio_button.set_active(self.stype
                 == srvsvc.STYPE_IPC)
		#vbox.pack_start(self.stype_ipc_radio_button)
        #deactivating this option until samba4 is fixed TODO activate once base is fixed
        
        # Special Share Flags
        vbox = gtk.VBox()
        vbox.set_border_width(5)
        table.attach(vbox, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND,
                                    gtk.FILL | gtk.EXPAND, 1, 1)

        # Check buttons
        self.sflag_temp_check_button = gtk.CheckButton('Temporary')
        self.sflag_temp_check_button.set_tooltip_text(
                                            'Make share Temporary')
        self.sflag_temp_check_button.set_active(self.flags[0])
        vbox.pack_start(self.sflag_temp_check_button)

        self.sflag_hidden_check_button = gtk.CheckButton('Hidden ')
        self.sflag_hidden_check_button.set_tooltip_text(
                                                'Make share hidden.')
        self.sflag_hidden_check_button.set_active(self.flags[1])
        vbox.pack_start(self.sflag_hidden_check_button)

        # Path frame
        frame = gtk.Frame()
        label = gtk.Label('<b>Path</b>')
        label.set_use_markup(True)
        frame.set_label_widget(label)
        self.form_box.pack_start(frame, True, True, 0)
        frame.set_border_width(5)

        table = gtk.Table(1, 2)
        table.set_col_spacings(6)
        frame.add(table)

        label = gtk.Label('Share path : ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,
                                    gtk.FILL | gtk.EXPAND, 0, 0)
                                    
        # FIXME may need another parameter to select type of selctor in combination with local
        # eg selecting a ipc / printer may be easier with a path

        if self.islocal:
            self.file_button = gtk.FileChooserButton('Browse')
            self.file_button.set_current_folder(self.path)
            self.file_button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
            self.file_button.set_tooltip_text(
                                        'Select the folder to share')
            table.attach(self.file_button, 1, 2, 0, 1, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        else:
            self.file_entry = gtk.Entry()
            self.file_entry.set_text(self.path)
            self.file_entry.set_tooltip_text('Path to the folder to share'
                    )
            table.attach(self.file_entry, 1, 2, 0, 1, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        # max users frame
        
        frame = gtk.Frame()
        label = gtk.Label('<b>Max Users</b>')
        label.set_use_markup(True)
        frame.set_label_widget(label)
        self.form_box.pack_start(frame, True, True, 0)
        frame.set_border_width(5)

        table = gtk.Table(1, 2)
        table.set_col_spacings(6)
        frame.add(table)

        label = gtk.Label(' Max Users : ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,
                            gtk.FILL | gtk.EXPAND, 0, 0)

        # adjustment for max users spinbox
        self.max_users_adjustment = gtk.Adjustment(self.max_users, 1,
                0xFFFFFFFF, 1, 5)

        self.max_users_spinbox = \
            gtk.SpinButton(self.max_users_adjustment)
        self.max_users_spinbox.set_numeric(True)
        self.max_users_spinbox.set_tooltip_text('Max Users for the Share'
                )
        table.attach(self.max_users_spinbox, 1, 2, 0, 1,
                        gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        # action area
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button('Cancel', gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.apply_button = gtk.Button('Apply', gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(self.edit_mode)
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)

        self.ok_button = gtk.Button('OK', gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)


class DeleteDialog(gtk.Dialog):

    """ The delete dialog """

    def __init__(self, pipe_manager, share=None):
        """ Class initialiser """

        super(DeleteDialog, self).__init__()
        self.pipe = pipe_manager
        self.set_modal(True)

        if share is None:
            raise KeyError('Non existant Share cannot be deleted')

        self.share = share

        # resolving some types that are required for gtk dialog creation
        
        self.stype = self.pipe.get_share_type_info(self.share.type,
                'base_type')
        self.flags = self.pipe.get_share_type_info(self.share.type,
                'flags')
        self.generic_typestring = \
            self.pipe.get_share_type_info(self.share.type, 'typestring')
        self.desc = self.pipe.get_share_type_info(self.share.type,
                'desc')

        self.create()
        self.set_position(gtk.WIN_POS_CENTER)

    def create(self):
        """ Create the window """

        self.set_title(' '.join([' Delete Share', self.share.name]))
        self.icon_name = ['network-folder', 'network-printer', 'network'
                          , 'network-pipe'][self.stype]
        self.icon_filename = os.path.join(sys.path[0], 'images',
                ''.join([self.icon_name, '.png']))
        self.set_icon_from_file(self.icon_filename)
        self.vbox.set_spacing(3)
        self.set_border_width(5)
        self.set_decorated(True)
        self.set_resizable(False)

        #artwork
        self.desc_box = gtk.HBox()
        self.vbox.pack_start(self.desc_box, False, True, 0)

        hbox = gtk.HBox()
        icon = gtk.Image()
        icon.set_from_file(self.icon_filename)

        hbox.pack_start(icon, False, True, 0)
        self.desc_box.pack_start(hbox, False, True, 0)

        hbox = gtk.HBox()
        label = gtk.Label()
        label.set_text(
            'You are deleting the share with the following properties')
        label.set_alignment(0, 0.5)
        hbox.pack_start(label, True, True, 0)
        self.desc_box.pack_start(hbox, True, True, 0)

        # main form box
        self.form_box = gtk.VBox()
        self.vbox.pack_start(self.form_box, True, True, 0)

        frame = gtk.Frame()
        label = gtk.Label('<b> Share Details</b>')
        label.set_use_markup(True)
        frame.set_label_widget(label)
        self.form_box.pack_start(frame, True, True, 0)
        frame.set_border_width(5)

        table = gtk.Table(11, 2)
        table.set_border_width(5)
        table.set_row_spacings(2)
        table.set_col_spacings(6)

        frame.add(table)

        label = gtk.Label(' Share Name  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(self.share.name)
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 0, 1, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Comment  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(self.share.comment)
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 1, 2, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Path  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(self.share.path)
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 2, 3, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Password  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        if self.share.password:
            label = gtk.Label('Share Password Enabled')
        else:
            label = gtk.Label('Share Password Disabled')
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 3, 4, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label('<b> Share Type</b>')
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Generic Typestring  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 5, 6, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(self.generic_typestring)
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 5, 6, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Type Description  : ')  # spaces for Gui align do not change
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 6, 7, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(self.desc)
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 6, 7, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)


        label = gtk.Label()
        label.set_markup('<b> Special Flags </b>')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 7, 8, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Temporary  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 8, 9, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(str(self.flags[0]))
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 8, 9, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Hidden  : ')  # spaces for Gui align do not change
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 9, 10, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(str(self.flags[1]))
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 9, 10, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Max Users  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 10, 11, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(self.share.max_users)
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 10, 11, gtk.FILL,
            gtk.FILL | gtk.EXPAND, 0, 0)

        box = gtk.VBox(3)
        label = gtk.Label('Are yous sure you want to delete the share ?'
                          )
        label.set_alignment(0.5, 0.5)
        box.pack_start(label, True, True, 0)
        warning = '(Please Note this is an irreversable action)'
        label = gtk.Label('<span foreground="red">%s</span>' % warning)
        label.set_use_markup(True)
        label.set_alignment(0.5, 0.5)
        box.pack_start(label, True, True, 0)
        box.set_border_width(5)

        self.vbox.pack_start(box, True, True, 0)

        # action area
        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button('Cancel', gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.ok_button = gtk.Button('Delete', gtk.STOCK_OK)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)


class ShareWizardDialog(ShareAddEditDialog):

    def create(self):

        self.page = 0
        self.set_default_size(400, 275)

        self.main_box = gtk.VBox()
        self.vbox.pack_start(self.main_box, True, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        samba_image_filename = os.path.join(sys.path[0], 'images',
                'samba-logo-small.png')
        samba_image = gtk.Image()
        samba_image.set_from_file(samba_image_filename)
        vbox.pack_end(samba_image, False, True, 0)
        self.main_box.pack_start(vbox, False, True, 0)

        vbox = gtk.VBox()
        self.main_box.pack_start(vbox, True, True, 0)

        frame = gtk.Frame()
        frame.set_border_width(10)
        vbox.pack_start(frame, True, True, 0)

        self.data_box = gtk.VBox()
        self.data_box.set_border_width(5)
        frame.add(self.data_box)

        self.title_label = gtk.Label()
        self.title_label.set_alignment(0.05, 0.5)
        self.data_box.pack_start(self.title_label, False, True, 1)

        self.info_label = gtk.Label()
        self.info_label.set_alignment(.15, 0.5)
        self.data_box.pack_start(self.info_label, False, True, 0)

        self.fields_box = gtk.VBox()
        self.data_box.pack_start(self.fields_box, True, True, 3)

        # create all entities do not attach them so as to that they are refrenced
        # name
        self.share_name_entry = gtk.Entry()
        self.share_name_entry.set_tooltip_text('Enter the Share Name')
        self.share_name_entry.set_text(self.sname)

        # dcesrv_srvsvc name check does this but just to reduce chances of an error limit max length
        if self.flags[1]:
            self.share_name_entry.set_max_length(12)
        else:
            self.share_name_entry.set_max_length(80)

        # comment
        self.share_comment_entry = gtk.Entry()
        self.share_comment_entry.set_max_length(48)  # max allowed is 48 MS-SRVS
        self.share_comment_entry.set_activates_default(True)
        self.share_comment_entry.set_text(self.comment)
        self.share_comment_entry.set_tooltip_text(
                        'Add a Comment or Description of the Share. \
                                Will default to share_type description')

        # password
        self.share_password_entry = gtk.Entry()
        self.share_password_entry.set_activates_default(True)
        self.share_password_entry.set_text(self.password)
        self.share_password_entry.set_tooltip_text(
                                                'Set a Share Password')

        # For radio buttons we define other fields on the fly as these
        # are lost on parent removal , and cause errors on draw .
        # Radio buttons
        self.stype_disktree_radio_button = gtk.RadioButton(None,
                'Disktree')
        self.stype_printq_radio_button = \
            gtk.RadioButton(self.stype_disktree_radio_button,
                            'Print Queue')
        self.stype_ipc_radio_button = \
            gtk.RadioButton(self.stype_printq_radio_button, 'IPC ')

        self.sflag_temp_check_button = gtk.CheckButton('Temporary')
        self.sflag_hidden_check_button = gtk.CheckButton('Hidden ')

        # path
        if self.islocal:
            self.file_button = gtk.FileChooserButton('Browse')
        else:
            self.file_entry = gtk.Entry()

        # max_users
        self.max_users_adjustment = gtk.Adjustment(self.max_users, 1,
                0xFFFFFFFF, 1, 5)

        self.max_users_spinbox = \
            gtk.SpinButton(self.max_users_adjustment)
        self.max_users_spinbox.set_numeric(True)
        self.max_users_spinbox.set_tooltip_text(
                                            'Max Users for the Share')

        self.action_area.set_layout(gtk.BUTTONBOX_CENTER)

        self.cancel_button = gtk.Button('Cancel', gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.prev_button = gtk.Button(stock=gtk.STOCK_GO_BACK)
        self.prev_button.connect('clicked', self.update_fields, -1)
        self.action_area.pack_start(self.prev_button, False, False, 10)

        self.next_button = gtk.Button(stock=gtk.STOCK_GO_FORWARD)
        self.next_button.connect('clicked', self.update_fields, +1)
        self.action_area.pack_start(self.next_button, False, False, 0)

        self.ok_button = gtk.Button('OK', gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)
        self.update_fields(None, 0)

    def update_fields(self, widget, change):
        self.collect_fields()
        self.page += change
        for widget in self.fields_box.get_children():
            self.fields_box.remove(widget)

        if self.page == 0:
            self.title_label.set_markup(
                            '<b>Welcome to the New Share Wizard</b>')
            self.info_label.set_text(' ')

            label = gtk.Label('Please press next to continue.')
            label.set_alignment(0, 0.5)
            self.fields_box.pack_start(label, False, True, 0)
            self.fields_box.show_all()
            self.prev_button.set_sensitive(False)
            self.next_button.set_sensitive(True)
            self.ok_button.set_sensitive(False)

            self.fields_box.show_all()
        elif self.page == 1:

            self.title_label.set_markup('<b>Name and Password</b>')
            self.info_label.set_text('Please enter a valid name and password (optional) for your share.'
                    )
            self.prev_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.ok_button.set_sensitive(False)
            if self.sname is not None:
                self.share_name_entry.set_text(self.sname)
            if self.password is not None:
                self.share_comment_entry.set_text(self.password)

            table = gtk.Table(2, 2, True)
            table.set_border_width(5)
            table.set_row_spacings(2)
            table.set_col_spacings(6)

            label = gtk.Label('* Share Name : ')
            label.set_alignment(1, 0.5)

            table.attach(label, 0, 1, 0, 1, gtk.FILL,
                                    gtk.FILL | gtk.EXPAND, 0, 0)
            table.attach(self.share_name_entry, 1, 2, 0, 1,
                        gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

            label = gtk.Label('  Share Password : ')
            label.set_alignment(1, 0.5)

            table.attach(label, 0, 1, 1, 2, gtk.FILL,
                                    gtk.FILL | gtk.EXPAND, 0, 0)
            table.attach(self.share_password_entry, 1, 2, 1, 2,
                        gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

            self.fields_box.pack_start(table, False, True, 0)
            self.fields_box.show_all()
        elif self.page == 2:

            self.title_label.set_markup('<b>Comment and Max Users </b>')
            self.info_label.set_text(
               'Please enter a  comment(optional) and select max users')
            self.prev_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.ok_button.set_sensitive(False)
            if self.comment is not None:
                self.share_comment_entry.set_text(self.comment)
            self.max_users_spinbox.set_value(self.max_users)

            table = gtk.Table(2, 2, True)
            table.set_border_width(5)
            table.set_row_spacings(2)
            table.set_col_spacings(6)

            label = gtk.Label('  Share Comment :')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, 0, 1, gtk.FILL,
                                gtk.FILL | gtk.EXPAND, 0, 0)
            table.attach(self.share_comment_entry, 1, 2, 0, 1,
                        gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

            label = gtk.Label('  Max Users : ')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, 1, 2, gtk.FILL,
                                    gtk.FILL | gtk.EXPAND, 0, 0)
            table.attach(self.max_users_spinbox, 1, 2, 1, 2,
                        gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

            self.fields_box.pack_start(table, False, True, 0)
            self.fields_box.show_all()
        elif self.page == 3:

            self.title_label.set_markup('<b>Share Type Options</b>')
            self.info_label.set_text('Please select your share type options.'
                    )
            self.prev_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.ok_button.set_sensitive(False)

            self.stype_disktree_radio_button = gtk.RadioButton(None,
                    'Disktree')
            self.stype_disktree_radio_button.set_tooltip_text('Disktree (folder) type Share. Default'
                    )
            self.stype_disktree_radio_button.set_active(self.stype
                     == srvsvc.STYPE_DISKTREE)

            self.stype_printq_radio_button = \
                gtk.RadioButton(self.stype_disktree_radio_button,
                                'Print Queue')
            self.stype_printq_radio_button.set_tooltip_text('Shared Print Queue'
                    )
            self.stype_printq_radio_button.set_active(self.stype
                     == srvsvc.STYPE_PRINTQ)

            self.stype_ipc_radio_button = \
                gtk.RadioButton(self.stype_printq_radio_button, 'IPC ')
            self.stype_ipc_radio_button.set_tooltip_text(
                        'Shared Interprocess Communication Pipe (IPC).')
            self.stype_ipc_radio_button.set_active(self.stype
                     == srvsvc.STYPE_IPC)

            self.sflag_temp_check_button = gtk.CheckButton('Temporary')
            self.sflag_temp_check_button.set_tooltip_text(
                                                'Make share Temporary')
            self.sflag_temp_check_button.set_active(self.flags[0])

            self.sflag_hidden_check_button = gtk.CheckButton('Hidden ')
            self.sflag_hidden_check_button.set_tooltip_text(
                                                'Make share hidden.')
            self.sflag_hidden_check_button.set_active(self.flags[1])

            hbox = gtk.HBox(True, 10)

            vbox = gtk.VBox()
            vbox.set_border_width(5)

            vbox.pack_start(self.stype_disktree_radio_button, True,
                            True, 3)
            vbox.pack_start(self.stype_printq_radio_button, True, True,
                            3)
            vbox.pack_start(self.stype_ipc_radio_button, True, True, 3)
            hbox.pack_start(vbox, True, True, 0)

            vbox = gtk.VBox()
            vbox.set_border_width(5)

            vbox.pack_start(self.sflag_temp_check_button, True, True, 3)
            vbox.pack_start(self.sflag_hidden_check_button, True, True,
                            3)

            hbox.pack_start(vbox, True, True, 0)

            self.fields_box.pack_start(hbox, True, True, 0)
            self.fields_box.show_all()
        else:

            self.title_label.set_markup('<b>Path</b>')
            if self.islocal:
                self.info_label.set_text('Please select a valid path.')
            else:
                self.info_label.set_text('Please enter valid path.')
            self.prev_button.set_sensitive(True)
            self.next_button.set_sensitive(False)
            self.ok_button.set_sensitive(True)

            if self.islocal:
                self.file_button = gtk.FileChooserButton('Browse')
                if self.path is not None:
                    self.file_button.set_current_folder(self.path)
                else:
                    self.file_button.set_current_folder('.')
                self.file_button.set_action(
                                 gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
                self.file_button.set_tooltip_text(
                                         'Select the folder to share')
            else:
                self.file_entry = gtk.Entry()
                if self.path is not None:
                    self.file_entry.set_text(self.path)
                else:
                    self.file_entry.set_text('')
                self.file_entry.set_tooltip_text(
                                        'Path to the folder to share')

            table = gtk.Table(1, 2, True)
            table.set_border_width(5)
            table.set_row_spacings(2)
            table.set_col_spacings(6)

            label = gtk.Label('  Path     : ')
            label.set_alignment(1, 0.5)
            table.attach(label, 0, 1, 0, 1, gtk.FILL,
                                gtk.FILL | gtk.EXPAND, 0, 0)
            if self.islocal:
                table.attach(self.file_button, 1, 2, 0, 1, gtk.FILL,
                                gtk.FILL | gtk.EXPAND, 0, 0)
            else:
                table.attach(self.file_entry, 1, 2, 0, 1, gtk.FILL,
                                gtk.FILL | gtk.EXPAND, 0, 0)

            self.fields_box.pack_start(table, False, True, 0)
            self.fields_box.show_all()

    def collect_fields(self):
        """ Custom collect fields from the GUI and saves in class variables which is page specific. """

        if self.page == 0:
            pass
        elif self.page == 1:

            self.sname = self.share_name_entry.get_text()
            self.password = self.share_password_entry.get_text()
        elif self.page == 2:

            self.comment = self.share_comment_entry.get_text()
            self.max_users = self.max_users_spinbox.get_value_as_int()
        elif self.page == 3:

            if self.stype_disktree_radio_button.get_active():
                self.stype = srvsvc.STYPE_DISKTREE
            elif self.stype_printq_radio_button.get_active():
                self.stype = srvsvc.STYPE_PRINTQ
            else:
                self.stype = srvsvc.STYPE_IPC

            self.flags = [False, False]
            if self.sflag_temp_check_button.get_active():
                self.flags[0] = True
            if self.sflag_hidden_check_button.get_active():
                self.flags[1] = True
        else:

            if self.islocal:
                self.path = self.file_button.get_filename()
            else:
                self.path = self.path_entry.get_text()


