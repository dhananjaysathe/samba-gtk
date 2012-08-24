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

from sambagtk.dialogs import ConnectDialog

""" wkssvc related dialogues"""


class wkssvcConnectDialog(ConnectDialog):

    def __init__(self, server, transport_type, username, password):

        super(wkssvcConnectDialog, self).__init__(
                    server, transport_type, username, password)
        self.set_title('Connect to Samba Server')


class DomainJoinDialog(Gtk.Dialog):

    def __init__(self):
        """ Class initialiser """

        super(JoinDomainDialog, self).__init__()
        self.create()

    def toggle_pwd_visiblity(self, widget, Junk):
        """ Toggels Password visiblity"""

        mode = self.set_pw_visiblity.get_active()
        self.password_entry.set_visibility(mode)

    def collect_fields(self):
        """ Collects fields from the GUI and saves in class variables """

        self.server_address = self.server_address_entry.get_text().strip()
        self.domain_name = self.domain_name_entry.get_text().strip()
        self.machine_name = self.machine_name_entry.get_text().strip()
        self.username = self.username_entry.get_text().strip()
        self.password = self.password_entry.get_text().strip()


    def create(self):
        """ Create the window """

        self.icon_name = 'network'
        self.icon_filename = os.path.join(sys.path[0], 'images',
                ''.join([self.icon_name, '.png']))
        self.set_icon_from_file(self.icon_filename)
        self.vbox.set_spacing(3)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title('Join a Domain')
        self.set_border_width(5)
        self.set_resizable(False)
        self.set_decorated(True)
        self.set_modal(True)

        # main form box
        self.form_box = Gtk.VBox()
        self.vbox.pack_start(self.form_box, True, True, 0)

        # Domain & Machine Names Frame
        frame = Gtk.Frame()
        label = Gtk.Label('<b>Domain Details</b>')
        label.set_property("use-markup",True)
        frame.set_label_widget(label)
        frame.set_border_width(5)
        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_row_spacing(2)
        grid.set_column_spacing(6)
        frame.add(grid)

        label = Gtk.Label(' Server Address : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        self.server_address_entry = Gtk.Entry()
        self.server_address_entry.set_text(self.sname)
        self.server_address_entry.set_activates_default(True)
        self.server_address_entry.set_tooltip_text(
            'Enter destination server address.')
        grid.attach(self.server_address_entry, 1, 0, 1, 1)

        label = Gtk.Label(' Domain Name : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 1, 1, 1)

        self.domain_name_entry = Gtk.Entry()
        self.domain_name_entry.set_text(self.sname)
        self.domain_name_entry.set_activates_default(True)
        self.domain_name_entry.set_tooltip_text(
            'Enter name of the domain you wish to join.')
        grid.attach(self.domain_name_entry, 1, 1, 1, 1)

        label = Gtk.Label(' Machine Name  : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 2, 1, 1)

        self.machine_name_entry = Gtk.Entry()
        self.machine_name_entry.set_text(self.comment)
        self.machine_name_entry.set_activates_default(True)
        self.machine_name_entry.set_tooltip_text(
            'Enter the NetBIOS /Hostname of the Machine in the concerned domian .')
        grid.attach(self.machine_name_entry,  1, 2, 1, 1)

        # User Creds frame
        frame = Gtk.Frame()
        label = Gtk.Label('<b>User Credentials </b>')
        label.set_property("use-markup",True)
        frame.set_property("label-widget",label)

        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        frame.add(grid)

        label = Gtk.Label(' Username : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_text(self.sname)
        self.username_entry.set_activates_default(True)
        self.username_entry.set_tooltip_text('Enter the Username')
        grid.attach(self.username_entry, 1, 0, 1, 1)

        label = Gtk.Label(' Password  : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 1, 1, 1)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_text(self.password)
        self.password_entry.set_activates_default(True)
        self.password_entry.set_visibility(False)
        self.password_entry.set_tooltip_text('Enter the Password')
        grid.attach(self.password_entry, 1, 1, 1, 1)

        self.set_pw_visiblity = Gtk.CheckButton('Visible')
        self.set_pw_visiblity.set_property("active",False)
        self.set_pw_visiblity.set_tooltip_text(
                            'Toggle password visiblity')
        self.set_pw_visiblity.connect('toggled',
                self.toggle_pwd_visiblity, None)
        grid.attach(self.set_pw_visiblity, 1, 2, 1, 1)

        # action area

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button('Cancel', Gtk.STOCK_CANCEL)
        self.cancel_button.set_property("can-default",True)
        self.add_action_widget(self.cancel_button,
                                            Gtk.ResponseType.CANCEL)

        self.ok_button = Gtk.Button('OK', Gtk.STOCK_CONNECT)
        self.ok_button.set_property("can-default",True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_window_mode()

class DeleteDialog(Gtk.Dialog):

    """ The delete dialog """

    def __init__(self, pipe_manager, domain_name=None):
        """ Class initialiser """

        super(DeleteDialog, self).__init__()
        self.domain_name = domain_name
        self.create()

    def create(self):
        """ Create the window """

        title = ' '.join([' Unjoin Domain', self.domain_name])
        self.icon_filename = os.path.join(sys.path[0], 'images','network.png')
        self.set_icon_from_file(self.icon_filename)
        self.vbox.set_spacing(3)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_modal(True)
        self.set_title(title)
        self.set_border_width(5)
        self.set_resizable(False)
        self.set_decorated(True)


        #artwork
        self.desc_box = Gtk.HBox()
        self.vbox.pack_start(self.desc_box, False, True, 0)

        hbox = Gtk.HBox()
        icon = Gtk.Image()
        icon.set_from_file(self.icon_filename)

        hbox.pack_start(icon, False, True, 0)
        self.desc_box.pack_start(hbox, False, True, 0)

        # main form box
        self.form_box = Gtk.VBox()
        self.vbox.pack_start(self.form_box, True, True, 0)

        frame = Gtk.Frame()
        label = Gtk.Label('<b> Domain Details</b>')
        label.set_property("use-markup",True)
        frame.set_label_widget(label)
        frame.set_border_width(5)
        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_row_spacing(2)
        grid.set_column_spacing(6)
        frame.add(grid)

        label = Gtk.Label(' Domain Name  : ', xalign=1, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        label = Gtk.Label(self.domain_name, xalign=0, yalign=0.5)
        grid.attach(label, 1, 0, 1, 1)


        box = Gtk.VBox(3)
        label = Gtk.Label('Are yous sure you want to continue ?'
                          ,xalign = 0.5, yalign = 0.5)
        box.pack_start(label, True, True, 0)

        self.vbox.pack_start(box, True, True, 0)

        # action area
        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button('Cancel', Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.ok_button = Gtk.Button('Delete', Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)
