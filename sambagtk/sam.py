# Samba GTK+ frontends
#
# Copyright (C) 2010 Sergio Martins <sergio97@gmail.com>
# Copyright (C) 2011 Jelmer Vernooij <jelmer@samba.org>
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
#

"""SAM-related dialogs."""

import gtk
import gobject

import os
import sys


class User(object):

    def __init__(self, username, fullname, description, rid):
        self.username = username
        self.fullname = fullname
        self.description = description
        self.rid = rid

        self.password = ""
        self.must_change_password = True
        self.cannot_change_password = False
        self.password_never_expires = False
        self.account_disabled = False
        self.account_locked_out = False
        self.group_list = []
        self.profile_path = ""
        self.logon_script = ""
        self.homedir_path = ""
        self.map_homedir_drive = -1

    def list_view_representation(self):
        return [self.username, self.fullname, self.description, self.rid]


class Group(object):

    def __init__(self, name, description, rid):
        self.name = name
        self.description = description
        self.rid = rid

    def list_view_representation(self):
        return [self.name, self.description, self.rid]


class UserEditDialog(gtk.Dialog):

    def __init__(self, pipe_manager, user=None):
        super(UserEditDialog, self).__init__()

        if (user is None):
            self.brand_new = True
            self.user = User("", "", "", 0)
        else:
            self.brand_new = False
            self.user = user

        self.pipe_manager = pipe_manager
        self.create()

        self.user_to_values()
        self.update_sensitivity()

    def create(self):
        self.set_title(["Edit user", "New user"][self.brand_new] + " " + self.user.username)
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "user.png"))

        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)

        table = gtk.Table (10, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)

        label = gtk.Label("Username")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Full name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Password")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Confirm password")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 0, 0)

        self.username_entry = gtk.Entry()
        self.username_entry.set_activates_default(True)
        self.username_entry.set_max_length(20) #This is the length limit for usernames
        table.attach(self.username_entry, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.fullname_entry = gtk.Entry()
        self.fullname_entry.set_activates_default(True)
        table.attach(self.fullname_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.description_entry = gtk.Entry()
        self.description_entry.set_activates_default(True)
        table.attach(self.description_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 3, 4, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.confirm_password_entry = gtk.Entry()
        self.confirm_password_entry.set_visibility(False)
        self.confirm_password_entry.set_activates_default(True)
        table.attach(self.confirm_password_entry, 1, 2, 4, 5, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.must_change_password_check = gtk.CheckButton("_User Must Change Password at Next Logon")
        self.must_change_password_check.set_active(self.brand_new)
        table.attach(self.must_change_password_check, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        self.cannot_change_password_check = gtk.CheckButton("User Cannot Change Password")
        table.attach(self.cannot_change_password_check, 1, 2, 6, 7, gtk.FILL, 0, 0, 0)

        self.password_never_expires_check = gtk.CheckButton("Password Never Expires")
        table.attach(self.password_never_expires_check, 1, 2, 7, 8, gtk.FILL, 0, 0, 0)

        self.account_disabled_check = gtk.CheckButton("Account Disabled")
        self.account_disabled_check.set_active(self.brand_new)
        table.attach(self.account_disabled_check, 1, 2, 8, 9, gtk.FILL, 0, 0, 0)

        self.account_locked_out_check = gtk.CheckButton("Account Locked Out")
        table.attach(self.account_locked_out_check, 1, 2, 9, 10, gtk.FILL, 0, 0, 0)

        notebook.set_tab_label(notebook.get_nth_page(0), gtk.Label("Main"))

        hbox = gtk.HBox(False, 5)
        notebook.add(hbox)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        hbox.pack_start(scrolledwindow, True, True, 0)

        self.existing_groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.existing_groups_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Existing groups")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.existing_groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.existing_groups_store = gtk.ListStore(gobject.TYPE_STRING)
        self.existing_groups_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.existing_groups_tree_view.set_model(self.existing_groups_store)

        vbox = gtk.VBox(True, 0)
        hbox.pack_start(vbox, True, True, 0)

        self.add_group_button = gtk.Button("Add", gtk.STOCK_ADD)
        vbox.pack_start(self.add_group_button, False, False, 0)

        self.del_group_button = gtk.Button("Remove", gtk.STOCK_REMOVE)
        vbox.pack_start(self.del_group_button, False, False, 0)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        hbox.pack_start(scrolledwindow, True, True, 0)

        self.available_groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.available_groups_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Available groups")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.available_groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.available_groups_store = gtk.ListStore(gobject.TYPE_STRING)
        self.available_groups_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.available_groups_tree_view.set_model(self.available_groups_store)

        notebook.set_tab_label(notebook.get_nth_page(1), gtk.Label("Groups"))

        vbox = gtk.VBox(False, 0)
        notebook.add(vbox)

        frame = gtk.Frame("User Profiles")
        frame.set_border_width(5)
        vbox.pack_start(frame, True, True, 0)

        table = gtk.Table(2, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        frame.add(table)

        label = gtk.Label("User Profile Path")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Logon Script Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.profile_path_entry = gtk.Entry()
        self.profile_path_entry.set_activates_default(True)
        table.attach(self.profile_path_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.logon_script_entry = gtk.Entry()
        self.logon_script_entry.set_activates_default(True)
        table.attach(self.logon_script_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        frame = gtk.Frame("Home Directory")
        frame.set_border_width(5)
        vbox.pack_start(frame, True, True, 0)

        table = gtk.Table(2, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        frame.add(table)

        label = gtk.Label("Path")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.homedir_path_entry = gtk.Entry()
        self.homedir_path_entry.set_activates_default(True)
        table.attach(self.homedir_path_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.map_homedir_drive_check = gtk.CheckButton("Map homedir to drive")
        table.attach(self.map_homedir_drive_check, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.map_homedir_drive_combo = gtk.combo_box_new_text()
        table.attach(self.map_homedir_drive_combo, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)

        for i in range(ord('Z') - ord('A') + 1):
            self.map_homedir_drive_combo.append_text(chr(i + ord('A')) + ':')

        notebook.set_tab_label(notebook.get_nth_page(2), gtk.Label("Profile"))

        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new user
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)

        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)


        # signals/events

        self.must_change_password_check.connect("toggled", self.on_update_sensitivity)
        self.cannot_change_password_check.connect("toggled", self.on_update_sensitivity)
        self.password_never_expires_check.connect("toggled", self.on_update_sensitivity)
        self.account_disabled_check.connect("toggled", self.on_update_sensitivity)
        self.account_locked_out_check.connect("toggled", self.on_update_sensitivity)

        self.add_group_button.connect("clicked", self.on_add_group_button_clicked)
        self.del_group_button.connect("clicked", self.on_del_group_button_clicked)
        self.existing_groups_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.available_groups_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.map_homedir_drive_check.connect("toggled", self.on_update_sensitivity)

    def check_for_problems(self):
        if (self.password_entry.get_text() != self.confirm_password_entry.get_text()):
            return "The password was not correctly confirmed. Please ensure that the password and confirmation match exactly."

        if len(self.username_entry.get_text()) == 0:
            return "Username may not be empty!"

        if self.brand_new:
            for user in self.pipe_manager.user_list:
                if user.username == self.username_entry.get_text():
                    return "User \"" + user.username + "\" already exists!"

        return None

    def update_sensitivity(self):
        existing_selected = (self.existing_groups_tree_view.get_selection().count_selected_rows() > 0)
        available_selected = (self.available_groups_tree_view.get_selection().count_selected_rows() > 0)

        if (self.password_never_expires_check.get_active() or
            self.cannot_change_password_check.get_active()):
            self.must_change_password_check.set_sensitive(False)
        else:
            self.must_change_password_check.set_sensitive(True)
        self.cannot_change_password_check.set_sensitive(not self.must_change_password_check.get_active())
        self.password_never_expires_check.set_sensitive(not self.must_change_password_check.get_active())

        # It is possible that many of these options are turned on at the same
        # time, even though they shouldn't be
        if self.must_change_password_check.get_active():
            self.must_change_password_check.set_sensitive(True)
        if self.password_never_expires_check.get_active():
            self.password_never_expires_check.set_sensitive(True)
        if self.cannot_change_password_check.get_active():
            self.cannot_change_password_check.set_sensitive(True)

        self.add_group_button.set_sensitive(available_selected)
        self.del_group_button.set_sensitive(existing_selected)

        self.map_homedir_drive_combo.set_sensitive(self.map_homedir_drive_check.get_active())

    def user_to_values(self):
        if self.user is None:
            raise Exception("user not set")

        self.username_entry.set_text(self.user.username)
        self.username_entry.set_sensitive(len(self.user.username) == 0)
        self.fullname_entry.set_text(self.user.fullname)
        self.description_entry.set_text(self.user.description)
        self.must_change_password_check.set_active(self.user.must_change_password)
        self.cannot_change_password_check.set_active(self.user.cannot_change_password)
        self.password_never_expires_check.set_active(self.user.password_never_expires)
        self.account_disabled_check.set_active(self.user.account_disabled)
        self.account_locked_out_check.set_active(self.user.account_locked_out)
        self.profile_path_entry.set_text(self.user.profile_path)
        self.logon_script_entry.set_text(self.user.logon_script)
        self.homedir_path_entry.set_text(self.user.homedir_path)

        if (self.user.map_homedir_drive != -1):
            self.map_homedir_drive_check.set_active(True)
            self.map_homedir_drive_combo.set_active(self.user.map_homedir_drive)
            self.map_homedir_drive_combo.set_sensitive(True)
        else:
            self.map_homedir_drive_check.set_active(False)
            self.map_homedir_drive_combo.set_active(-1)
            self.map_homedir_drive_combo.set_sensitive(False)

        self.existing_groups_store.clear()
        for group in self.user.group_list:
            self.existing_groups_store.append([group.name])

        self.available_groups_store.clear()
        for group in self.pipe_manager.group_list:
            if (not group in self.user.group_list):
                self.available_groups_store.append([group.name])

    def values_to_user(self):
        if self.user is None:
            raise Exception("user not set")

        self.user.username = self.username_entry.get_text()
        self.user.fullname = self.fullname_entry.get_text()
        self.user.description = self.description_entry.get_text()
        self.user.password = (None, self.password_entry.get_text())[len(self.password_entry.get_text()) > 0]
        self.user.must_change_password = self.must_change_password_check.get_active()
        self.user.cannot_change_password = self.cannot_change_password_check.get_active()
        self.user.password_never_expires = self.password_never_expires_check.get_active()
        self.user.account_disabled = self.account_disabled_check.get_active()
        self.user.account_locked_out = self.account_locked_out_check.get_active()
        self.user.profile_path = self.profile_path_entry.get_text()
        self.user.logon_script = self.logon_script_entry.get_text()
        self.user.homedir_path = self.homedir_path_entry.get_text()

        if (self.map_homedir_drive_check.get_active()) and (self.map_homedir_drive_combo.get_active() != -1):
            self.user.map_homedir_drive = self.map_homedir_drive_combo.get_active()
        else:
            self.user.map_homedir_drive = -1

        del self.user.group_list[:]

        iter = self.existing_groups_store.get_iter_first()
        while (iter is not None):
            value = self.existing_groups_store.get_value(iter, 0)
            self.user.group_list.append([group for group in self.pipe_manager.group_list if group.name == value][0])
            iter = self.existing_groups_store.iter_next(iter)

    def on_add_group_button_clicked(self, widget):
        (model, iter) = self.available_groups_tree_view.get_selection().get_selected()
        if (iter is None):
            return

        group_name = model.get_value(iter, 0)
        self.existing_groups_store.append([group_name])
        self.available_groups_store.remove(iter)

    def on_del_group_button_clicked(self, widget):
        (model, iter) = self.existing_groups_tree_view.get_selection().get_selected()
        if (iter is None):
            return

        group_name = model.get_value(iter, 0)
        self.available_groups_store.append([group_name])
        self.existing_groups_store.remove(iter)

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()


class GroupEditDialog(gtk.Dialog):

    def __init__(self, pipe_manager, group = None):
        super(GroupEditDialog, self).__init__()

        if group is None:
            self.brand_new = True
            self.thegroup = Group("", "", 0)
        else:
            self.brand_new = False
            self.thegroup = group

        self.pipe_manager = pipe_manager
        self.create()

        if not self.brand_new:
            self.group_to_values()

    def create(self):
        self.set_title(["Edit group", "New group"][self.brand_new] + " " + self.thegroup.name)
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "group.png"))

        table = gtk.Table (2, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        self.vbox.pack_start(table, True, True, 0)

        label = gtk.Label("Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.name_entry = gtk.Entry()
        self.name_entry.set_activates_default(True)
        table.attach(self.name_entry, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.description_entry = gtk.Entry()
        self.description_entry.set_activates_default(True)
        table.attach(self.description_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new group
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)

        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)


    def check_for_problems(self):
        if len(self.name_entry.get_text()) == 0:
            return "Name may not be empty!"

        if self.brand_new:
            for group in self.pipe_manager.group_list:
                if group.name == self.name_entry.get_text():
                    return "Choose another group name, this one already exists!"

        return None

    def group_to_values(self):
        if (self.thegroup is None):
            raise Exception("group not set")

        self.name_entry.set_text(self.thegroup.name)
        self.name_entry.set_sensitive(len(self.thegroup.name) == 0)
        self.description_entry.set_text(self.thegroup.description)

    def values_to_group(self):
        if self.thegroup is None:
            raise Exception("group not set")

        self.thegroup.name = self.name_entry.get_text()
        self.thegroup.description = self.description_entry.get_text()


class SAMConnectDialog(gtk.Dialog):

    def __init__(self, server, transport_type, username, password = ""):
        super(SAMConnectDialog, self).__init__()

        self.server_address = server
        self.transport_type = transport_type
        self.username = username
        self.password = password
        self.domains = None

        self.create()

        self.update_sensitivity()

    def create(self):
        self.set_title("Connect to SAM server")
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)
        self.set_decorated(True)

        # server frame

        self.vbox.set_spacing(5)

        self.artwork = gtk.VBox()

        self.samba_image_filename = os.path.join(sys.path[0],'images',
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

        self.server_frame = gtk.Frame("Server")
        self.vbox.pack_start(self.server_frame, False, True, 0)

        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)

        label = gtk.Label(" Server address: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        table.attach(self.server_address_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(" Username: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        table.attach(self.username_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)

        label = gtk.Label(" Password: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_text(self.password)
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)


        # transport frame

        self.transport_frame = gtk.Frame(" Transport type ")
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)

        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None, "RPC over SMB over TCP/IP ")
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)

        self.rpc_tcpip_radio_button = gtk.RadioButton(self.rpc_smb_tcpip_radio_button, "RPC over TCP/IP")
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)

        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)


        # domain frame

        self.domains_frame = gtk.Frame(" Domain ")
        self.domains_frame.set_no_show_all(True)
        self.vbox.pack_start(self.domains_frame, False, True, 0)

        table = gtk.Table(1, 2)
        table.set_border_width(5)
        self.domains_frame.add(table)

        label = gtk.Label("Select domain: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)

        self.domain_combo_box = gtk.combo_box_new_text()
        table.attach(self.domain_combo_box, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)


        # dialog buttons

        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.connect_button = gtk.Button("Connect", gtk.STOCK_CONNECT)
        self.connect_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.connect_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)


        # signals/events

        self.rpc_smb_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.localhost_radio_button.connect("toggled", self.on_radio_button_toggled)

    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()

        self.server_address_entry.set_sensitive(server_required)

    def set_domains(self, domains, domain_index=-1):
        if domains is not None:
            self.server_frame.set_sensitive(False)
            self.transport_frame.set_sensitive(False)

            self.domains_frame.set_no_show_all(False)
            self.domains_frame.show_all()
            self.domains_frame.set_no_show_all(True)
            self.domain_combo_box.get_model().clear()
            for domain in domains:
                self.domain_combo_box.append_text(domain)

            if domain_index != -1:
                self.domain_combo_box.set_active(domain_index)
        else:
            self.server_frame.set_sensitive(True)
            self.transport_frame.set_sensitive(True)
            self.domains_frame.hide_all()

    def get_server_address(self):
        return self.server_address_entry.get_text().strip()

    def get_transport_type(self):
        if self.rpc_smb_tcpip_radio_button.get_active():
            return 0
        elif self.rpc_tcpip_radio_button.get_active():
            return 1
        elif self.localhost_radio_button.get_active():
            return 2
        else:
            return -1

    def get_username(self):
        return self.username_entry.get_text().strip()

    def get_password(self):
        return self.password_entry.get_text()

    def get_domain_index(self):
        return self.domain_combo_box.get_active()

    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()


