#!/usr/bin/python
# -*- coding: utf-8 -*-

""" srvsvc related dialogues"""

import gtk
import gobject
import os
import sys


class srvsvcConnectDialog(gtk.Dialog):

    """Connect Dialog"""

    def __init__(
        self,
        server,
        transport_type,
        username,
        password='',
        ):
        super(srvsvcConnectDialog, self).__init__()

        self.server_address = server
        self.username = username
        self.password = password
        self.transport_type = transport_type

        self.create()

        self.update_sensitivity()

    def create(self):
        self.set_title('Connect to Samba Share Server')
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)

        self.vbox.set_spacing(5)

        # artwork
        
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

        # server frame
        
        self.server_frame = gtk.Frame('Server')
        self.vbox.pack_start(self.server_frame, False, True, 0)

        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)

        label = gtk.Label(' Server address: ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        self.server_address_entry.set_tooltip_text('Enter the Server Address')
        table.attach(self.server_address_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(' Username: ')
        label.set_alignment(0, 0.5)
        table.attach(label,0,1,1,2,gtk.FILL,gtk.FILL | gtk.EXPAND,0,0)

        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        self.username_entry.set_tooltip_text('Enter your Username')
        table.attach(self.username_entry,1,2,1,2,gtk.FILL | gtk.EXPAND,gtk.FILL | gtk.EXPAND,1,1)
        label = gtk.Label(' Password: ')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_text(self.password)
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        self.password_entry.set_tooltip_text('Enter your Password')
        table.attach(self.password_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        # transport frame
        
        self.transport_frame = gtk.Frame(' Transport type ')
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)

        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None,
                'RPC over SMB over TCP/IP ')
        self.rpc_smb_tcpip_radio_button.set_tooltip_text('ncacn_np type : Recomended (default)'
                )  # # according MS-SRVS specification
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type
                 == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)

        self.rpc_tcpip_radio_button = \
            gtk.RadioButton(self.rpc_smb_tcpip_radio_button,
                            'RPC over TCP/IP')
        self.rpc_tcpip_radio_button.set_tooltip_text('ncacn_ip_tcp type')
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
            return self.server_address_entry.get_text().strip()

    def get_username(self):
            return self.username_entry.get_text().strip()

    def get_password(self):
            return self.password_entry.get_text()

    def update_sensitivity(self):
            server_required = \
                not self.localhost_radio_button.get_active()
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

    """ Share add and edit dialog 
 
 If 'edit_mode' is set to True then in Edit mode .
 Immutable fields are automatically greyed out.
  """

    def __init__(self, pipe_manager, share=None):
        """ Class initialiser """
        super(ShareAddEditDialog, self).__init__()
        self.pipe = pipe_manager
        if share is None :
            self.edit_mode = 0
            
		else :
            self.edit_mode =  1
            self.share = share
        

    def  create(self):
        """ Create the window """
        self.set_title([" New Share"," Edit Share : "][self.edit_mode]+ " " + self.share.name)
        self.set_border_width(5)
        if edit_mode:
            self.share_category = 1 + self.pipe.translate_types(share.type)[2] 
        else :
            self.share_category = 0
        self.icon_name = ["network","network-folder","network-printer","network","network-pipe"][self.share_category] 
        self.icon_filename = os.path.join(sys.path[0], "images", (self.icon_name+'.png'))
        self.set_icon_from_file(self.icon_filename)
        
        #artwork
        self.desc_box= gtk.HBox()
        
        self.desc_icon_box = gtk.HBox()
        self.desc_icon_box_image =  gtk.Image()
        self.desc_icon_box_image.set_from_file(self.icon_filename)
        
        self.desc_icon_box.pack_start(self.desc_icon_box_image, True, True, 0)
        self.desc_box.pack_start(self.desc_icon_box,False, True, 0)
        
        
        self.desc_text_box = gtk.HBox()
        self.desc_label = gtk.Label()
        if edit_mode :
            self.desc_label.set_text("Edit The Share")
            
    

        
