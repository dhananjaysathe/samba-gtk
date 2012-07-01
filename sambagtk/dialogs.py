# Samba GTK+ frontends
#
# Copyright (C) 2010 Sergio Martins <sergio97@gmail.com>
# Copyright (C) 2011 Jelmer Vernooij <jelmer@samba.org>
# Copyright (C) 2011 Dhananjay Sathe <dhananjaysathe@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk
from gi.repository import GdkPixbuf
import samba
import os
import sys
class AboutDialog(Gtk.AboutDialog):

    def __init__(self, name, description, icon):
        super(AboutDialog, self).__init__()

        license_text = \
"""
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>."""

        authors = ["Sergio Martins <Sergio97@gmail.com>",
                    "Calin Crisan <ccrisan@gmail.com>",
                    "Dhananjay Sathe <dhananajaysathe@gmail.com>",
                    "Jelmer Vernooij <jelmer@samba.org>"]
        copyright_text = "Copyright \xc2\xa9 2012 Dhananjay Sathe <dhananjaysathe@gmail.com>"

        self.set_property("program-name",name)
        self.set_property("logo",icon)
        self.set_property("version",samba.version)
        self.set_property("comments",description)
        self.set_property("wrap_license",True)
        self.set_property("license",license_text)
        self.set_property("authors",authors)
        self.set_property("copyright",copyright_text)
        if not self.get_logo():
            default_logo_file = os.path.join(sys.path[0], 'images',
                                                'samba-logo-small.png')
            icon_pixbuf = GdkPixbuf.Pixbuf.new_from_file(default_logo_file)
            self.set_logo(icon_pixbuf)


class ConnectDialog(Gtk.Dialog):

    """Connect Dialog"""

    def __init__(self, server, transport_type, username, password):

        super(ConnectDialog, self).__init__()

        self.server_address = server
        self.username = username
        self.password = password
        self.transport_type = transport_type
        self.domains = None #required for sam manager
        self.create()

        self.update_sensitivity()

    def mod_create(self):           #interface to modify the builtin create to extend the gui
        pass

    def create(self):
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_modal(True)
        self.set_border_width(5)
        self.set_icon_name(Gtk.STOCK_CONNECT)
        self.set_resizable(False)
        self.set_decorated(True)

        self.vbox.set_spacing(5)

        # artwork TODO remove post decession

        self.artwork = Gtk.VBox()

        self.samba_image_filename = os.path.join(sys.path[0], 'images',
                'samba-logo-small.png')
        self.samba_image = Gtk.Image()
        self.samba_image.set_from_file(self.samba_image_filename)
        self.artwork.pack_start(self.samba_image, True, True, 0)

        label = Gtk.Label('Opening Windows to A Wider World')
        box = Gtk.HBox()
        box.pack_start(label, True, True, 0)
        self.artwork.pack_start(box, True, True, 0)

        label = Gtk.Label('Samba Control Center')
        box = Gtk.HBox()
        box.pack_start(label, True, True, 0)
        self.artwork.pack_start(box, True, True, 0)

        self.vbox.pack_start(self.artwork, False, True, 0)

        ########################### end of artwork TODO :

        # server frame

        self.server_frame = Gtk.Frame()
        self.server_frame.set_property("label",' Server')
        self.vbox.pack_start(self.server_frame, False, True, 0)

        grid = Gtk.Grid()
        grid.set_property("border-width",5)
        self.server_frame.add(grid)

        label = Gtk.Label(' Server address: ',xalign=0, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        self.server_address_entry = Gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_property("activates-default",True)
        self.server_address_entry.set_property("tooltip-text",
                                        'Enter the Server Address')
        grid.attach(self.server_address_entry, 1, 0, 1, 1)

        label = Gtk.Label(' Username: ',xalign=0, yalign=0.5)
        grid.attach(label, 0, 1, 1, 1)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_property("activates-default",True)
        self.username_entry.set_property("tooltip-text",
                                            'Enter your Username')
        grid.attach(self.username_entry, 1, 1, 1, 1)

        label = Gtk.Label(' Password: ',xalign=0, yalign=0.5)
        grid.attach(label, 0, 2, 1, 1)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_text(self.password)
        self.password_entry.set_property("activates-default",True)
        self.password_entry.set_property("tooltip-text",
                                        'Enter your Password')
        self.password_entry.set_visibility(False)

        grid.attach(self.password_entry, 1, 2, 1, 1)

        # transport frame

        self.transport_frame = Gtk.Frame()
        self.transport_frame.set_property("label",' Transport type ')
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = Gtk.VBox()
        vbox.set_property("border-width",5)
        self.transport_frame.add(vbox)

        self.rpc_smb_tcpip_radio_button = \
                        Gtk.RadioButton.new_with_label_from_widget(None,
                'RPC over SMB over TCP/IP ')
        self.rpc_smb_tcpip_radio_button.set_tooltip_text(
                                'ncacn_np type : Recomended (default)')
        self.rpc_smb_tcpip_radio_button.set_active(
                                            self.transport_type == 0)   # Default according MS-SRVS specification
        vbox.pack_start(self.rpc_smb_tcpip_radio_button, True, True, 0)

        self.rpc_tcpip_radio_button = \
                        Gtk.RadioButton.new_with_label_from_widget(
                            self.rpc_smb_tcpip_radio_button,
                            'RPC over TCP/IP')
        self.rpc_tcpip_radio_button.set_tooltip_text(
                                                'ncacn_ip_tcp type')
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button, True, True, 0)

        self.localhost_radio_button = \
            Gtk.RadioButton.new_with_label_from_widget(
                            self.rpc_tcpip_radio_button, 'Localhost')
        self.localhost_radio_button.set_tooltip_text(
                                                'ncacn_ip_tcp type')
        self.localhost_radio_button.set_active(self.transport_type == 2) #  MS-SRVS specification
        vbox.pack_start(self.localhost_radio_button, True, True, 0)

        # dialog buttons
        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button('Cancel', Gtk.STOCK_CANCEL)
        self.cancel_button.set_tooltip_text('Cancel and Quit')
        self.add_action_widget(self.cancel_button,
                                            Gtk.ResponseType.CANCEL)

        self.connect_button = Gtk.Button('Connect', Gtk.STOCK_CONNECT)
        self.connect_button.set_can_default(True)
        self.cancel_button.set_tooltip_text('OK / Connect to Server')
        self.add_action_widget(self.connect_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)

        # signals/events

        self.rpc_smb_tcpip_radio_button.connect('toggled',
                                        self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect('toggled',
                                        self.on_radio_button_toggled)
        self.localhost_radio_button.connect('toggled',
                                        self.on_radio_button_toggled)
        self.mod_create()

    def get_server_address(self):
        if self.get_transport_type() is 2:
            return '127.0.0.1'
        return (self.server_address_entry.get_text().strip() or
                self.server_address )

    def get_username(self):
        return (self.username_entry.get_text().strip() or
                self.username)

    def get_password(self):
        return (self.password_entry.get_text() or
                self.password)

    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()
        self.server_address_entry.set_sensitive(server_required)

    def get_transport_type(self):
        if self.rpc_smb_tcpip_radio_button.get_active():
            return 0
        elif self.rpc_tcpip_radio_button.get_active():
            return 1
        else:
            return 2

    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()

