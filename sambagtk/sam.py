# Samba GTK+ frontends
#
# Copyright (C) 2010 Sergio Martins <sergio97@gmail.com>
# Copyright (C) 2012 Jelmer Vernooij <jelmer@samba.org>
# Copyright (C) 2012 Dhananjay Sathe <dhananjaysathe@gmail.com>
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

from gi.repository import Gtk
from gi.repository import GObject
from sambagtk.dialogs import ConnectDialog

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


class UserEditDialog(Gtk.Dialog):

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
        self.set_title(" ".join([("Edit user", "New user"
                                        )[self.brand_new],self.user.username]))
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0],"images", "user.png"))
        self.set_modal(True)
        self.set_resizable(False)
        self.set_decorated(True)

        notebook = Gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)

        grid = Gtk.Grid ()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        notebook.append_page(grid, Gtk.Label('User'))

        label = Gtk.Label("Username",xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 0, 1, 1)

        label = Gtk.Label("Full name",xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 1, 1, 1)

        label = Gtk.Label("Password",xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 2, 1, 1)

        label = Gtk.Label("Password",xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 3, 1, 1)

        label = Gtk.Label("Confirm password",xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 4, 1, 1)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_activates_default(True)
        self.username_entry.set_max_length(20) #This is the length limit for usernames
        grid.attach(self.username_entry, 1, 0, 1, 1)

        self.fullname_entry = Gtk.Entry()
        self.fullname_entry.set_activates_default(True)
        grid.attach(self.fullname_entry, 1, 1, 1, 1)

        self.description_entry = Gtk.Entry()
        self.description_entry.set_activates_default(True)
        grid.attach(self.description_entry, 1, 2, 1, 1)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        grid.attach(self.password_entry, 1, 3, 1, 1)

        self.confirm_password_entry = Gtk.Entry()
        self.confirm_password_entry.set_visibility(False)
        self.confirm_password_entry.set_activates_default(True)
        grid.attach(self.confirm_password_entry, 1, 4, 1, 1)

        self.must_change_password_check = Gtk.CheckButton(
                                    "_User Must Change Password at Next Logon")
        self.must_change_password_check.set_active(self.brand_new)
        grid.attach(self.confirm_password_entry, 1, 5, 1, 1)

        self.cannot_change_password_check = Gtk.CheckButton(
        "User Cannot ChangePassword")
        grid.attach(self.must_change_password_check, 1, 6, 1, 1)

        self.password_never_expires_check = Gtk.CheckButton(
                                                    "Password Never Expires")
        grid.attach(self.password_never_expires_check, 1, 7, 1, 1)

        self.account_disabled_check = Gtk.CheckButton("Account Disabled")
        self.account_disabled_check.set_active(self.brand_new)
        grid.attach(self.account_disabled_check, 1, 8, 1, 1)

        self.account_locked_out_check = Gtk.CheckButton("Account Locked Out")
        grid.attach(self.account_locked_out_check, 1, 9, 1, 1)


        hbox = Gtk.HBox(False, 5)
        notebook.append_page(hbox, Gtk.Label('Groups'))

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_property("shadow_type",Gtk.ShadowType.IN)
        hbox.pack_start(scrolledwindow, True, True, 0)

        self.existing_groups_tree_view = Gtk.TreeView()
        scrolledwindow.add(self.existing_groups_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("Existing groups")
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.existing_groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.existing_groups_store = Gtk.ListStore(GObject.TYPE_STRING)
        self.existing_groups_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.existing_groups_tree_view.set_model(self.existing_groups_store)

        vbox = Gtk.VBox(True, 0)
        hbox.pack_start(vbox, True, True, 0)

        self.add_group_button = Gtk.Button("Add", Gtk.STOCK_ADD)
        vbox.pack_start(self.add_group_button, False, False, 0)

        self.del_group_button = Gtk.Button("Remove", Gtk.STOCK_REMOVE)
        vbox.pack_start(self.del_group_button, False, False, 0)

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_property("shadow_type",Gtk.ShadowType.IN)
        hbox.pack_start(scrolledwindow, True, True, 0)

        self.available_groups_tree_view = Gtk.TreeView()
        scrolledwindow.add(self.available_groups_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("Available groups")
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.available_groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.available_groups_store = Gtk.ListStore(GObject.TYPE_STRING)
        self.available_groups_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.available_groups_tree_view.set_model(self.available_groups_store)

        vbox = Gtk.VBox(False, 0)
        notebook.append_page(vbox, Gtk.Label('Profile'))

        frame = Gtk.Frame()
        frame.set_label("User Profiles")
        frame.set_border_width(5)
        vbox.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        frame.add(grid)

        label = Gtk.Label("User Profile Path", xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 0, 1, 1)

        label = Gtk.Label("Logon Script Name", xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 1, 1, 1)

        self.profile_path_entry = Gtk.Entry()
        self.profile_path_entry.set_activates_default(True)
        grid.attach(self.profile_path_entry, 1, 1, 1, 1)

        self.logon_script_entry = Gtk.Entry()
        self.logon_script_entry.set_activates_default(True)
        grid.attach(self.logon_script_entry, 1, 1, 1, 1)

        frame = Gtk.Frame()
        frame.set_label("Home Directory")
        frame.set_border_width(5)
        vbox.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        frame.add(grid)

        label = Gtk.Label("Path", xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 0, 1, 1)

        self.homedir_path_entry = Gtk.Entry()
        self.homedir_path_entry.set_activates_default(True)
        grid.attach(self.homedir_path_entry, 1, 0, 1, 1)

        self.map_homedir_drive_check = Gtk.CheckButton("Map homedir to drive")
        grid.attach(self.map_homedir_drive_check, 0, 1, 1, 1)

        self.map_homedir_drive_combo = Gtk.ComboBoxText()
        grid.attach(self.map_homedir_drive_combo, 1, 1, 1, 1)

        for i in range(ord('Z') - ord('A') + 1):
            self.map_homedir_drive_combo.append_text(''.join([chr(i + ord('A')),
                                                                        ':']))


        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.apply_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.apply_button.set_can_default(True)
        self.apply_button.set_sensitive(not self.brand_new)
        self.add_action_widget(self.apply_button, Gtk.ResponseType.APPLY)

        self.ok_button = Gtk.Button("OK", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)


        # signals/events

        self.must_change_password_check.connect("toggled",
                                                    self.on_update_sensitivity)
        self.cannot_change_password_check.connect("toggled",
                                                    self.on_update_sensitivity)
        self.password_never_expires_check.connect("toggled",
                                                    self.on_update_sensitivity)
        self.account_disabled_check.connect("toggled",
                                                    self.on_update_sensitivity)
        self.account_locked_out_check.connect("toggled",
                                                    self.on_update_sensitivity)

        self.add_group_button.connect("clicked",
                                              self.on_add_group_button_clicked)
        self.del_group_button.connect("clicked",
                                              self.on_del_group_button_clicked)
        self.existing_groups_tree_view.get_selection().connect("changed",
                                                    self.on_update_sensitivity)
        self.available_groups_tree_view.get_selection().connect("changed",
                                                    self.on_update_sensitivity)
        self.map_homedir_drive_check.connect("toggled",
                                                    self.on_update_sensitivity)

    def check_for_problems(self):
        if (self.password_entry.get_text() != self.confirm_password_entry.get_text()):
            return "The password was not correctly confirmed. Please ensure that the password and confirmation match exactly."

        if len(self.username_entry.get_text()) == 0:
            return "Username may not be empty!"

        if self.brand_new:
            for user in self.pipe_manager.user_list:
                if user.username == self.username_entry.get_text():
                   return ''.join(["User \"",user.username,
                                                "\" already exists!"])

        return None

    def update_sensitivity(self):
        existing_selected = (self.existing_groups_tree_view.get_selection().count_selected_rows() > 0)
        available_selected = (self.available_groups_tree_view.get_selection().count_selected_rows() > 0)

        if (self.password_never_expires_check.get_active() or
            self.cannot_change_password_check.get_active()):
            self.must_change_password_check.set_sensitive(False)
        else:
            self.must_change_password_check.set_sensitive(True)
        self.cannot_change_password_check.set_sensitive(
                            not self.must_change_password_check.get_active())
        self.password_never_expires_check.set_sensitive(
                            not self.must_change_password_check.get_active())

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

        self.map_homedir_drive_combo.set_sensitive(
                                    self.map_homedir_drive_check.get_active())

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
        (model, iter) = \
                self.existing_groups_tree_view.get_selection().get_selected()
        if (iter is None):
            return

        group_name = model.get_value(iter, 0)
        self.available_groups_store.append([group_name])
        self.existing_groups_store.remove(iter)

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()


class GroupEditDialog(Gtk.Dialog):

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
        self.set_title(" ".join([("Edit group", "New group")[self.brand_new]
                                                        ,self.thegroup.name]))
        self.set_border_width(5)
        self.set_icon_from_file(
                            os.path.join(sys.path[0], "images", "group.png"))
        self.set_modal(True)
        self.set_resizable(False)
        self.set_decorated(True)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        self.vbox.pack_start(grid, True, True, 0)

        label = Gtk.Label("Name", xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 0, 1, 1)

        label = Gtk.Label("Description", xalign =0 , yalign = 0.5)
        grid.attach(label, 0, 1, 1, 1)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_activates_default(True)
        grid.attach(self.name_entry, 1, 0, 1, 1)

        self.description_entry = Gtk.Entry()
        self.description_entry.set_activates_default(True)
        grid.attach(self.description_entry, 1, 1, 1, 1)

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.apply_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.apply_button.set_can_default(True)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new group
        self.add_action_widget(self.apply_button, Gtk.ResponseType.APPLY)

        self.ok_button = Gtk.Button("OK", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)


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


class SAMConnectDialog(ConnectDialog):

    def __init__(self, server, transport_type, username, password):

        super(SAMConnectDialog, self).__init__(
                    server, transport_type, username, password)
        self.set_title('Connect to Samba SAM Server')

    def mod_create(self):
        self.domains_frame = Gtk.Frame()
        self.domains_frame.set_no_show_all(True)
        self.domains_frame.set_label(" Domain ")
        self.vbox.pack_start(self.domains_frame, False, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        self.domains_frame.add(grid)

        label = Gtk.Label("Select domain: ", xalign=0, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        self.domain_combo_box = Gtk.ComboBoxText()
        grid.attach(self.domain_combo_box, 1, 0, 1, 1)

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

    def get_domain_index(self):
        return self.domain_combo_box.get_active()



