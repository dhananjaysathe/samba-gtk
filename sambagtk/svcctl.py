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

"""svcctl related dialogs."""

import gobject
import gtk
import os
import pango
import sys

from samba.dcerpc import svcctl

class Service(object):

    def __init__(self):
        self.name = ""
        self.display_name = ""
        self.description = ""

        self.state = svcctl.SVCCTL_STOPPED
        self.check_point = 0
        self.wait_hint = 0

        self.accepts_pause = False
        self.accepts_stop = False

        self.start_type = svcctl.SVCCTL_AUTO_START
        self.path_to_exe = ""
        self.account = None # local system account
        self.account_password = None # don't change
        self.allow_desktop_interaction = False

        self.start_params = ""
        #self.hw_profile_list = [["Profile 1", True], ["Profile 2", False]] TODO: implement hw_profiles functionality

        self.handle = -1

    @staticmethod
    def get_state_string(state):
        return {
            svcctl.SVCCTL_CONTINUE_PENDING: "Continue pending",
            svcctl.SVCCTL_PAUSE_PENDING: "Pause pending",
            svcctl.SVCCTL_PAUSED: "Paused",
            svcctl.SVCCTL_RUNNING: "Running",
            svcctl.SVCCTL_START_PENDING: "Start pending",
            svcctl.SVCCTL_STOP_PENDING: "Stop pending",
            svcctl.SVCCTL_STOPPED: "Stopped"
            }[state]

    @staticmethod
    def get_start_type_string(start_type):
        return {
            svcctl.SVCCTL_BOOT_START: "Start at boot",
            svcctl.SVCCTL_SYSTEM_START: "Start at system startup",
            svcctl.SVCCTL_AUTO_START: "Start automatically",
            svcctl.SVCCTL_DEMAND_START: "Start manually",
            svcctl.SVCCTL_DISABLED: "Disabled",
            }.get(start_type, "")

    def list_view_representation(self):
        return [self.name, self.display_name, self.description,
                Service.get_state_string(self.state),
                Service.get_start_type_string(self.start_type)]


class ServiceEditDialog(gtk.Dialog):

    def __init__(self, service = None):
        super(ServiceEditDialog, self).__init__()

        if (service is None):
            self.brand_new = True
            self.service = Service()
        else:
            self.brand_new = False
            self.service = service

        self.create()

        if (not self.brand_new):
            self.service_to_values()
        self.update_sensitivity()

    def create(self):
        self.set_title("Edit service " + self.service.name)
        self.set_border_width(5)
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(sys.path[0], "images", "service.png"))
        self.set_icon(self.icon_pixbuf)
        self.set_resizable(False)
        self.set_size_request(450, 350)

        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)


        # general tab

        table = gtk.Table(6, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)

        label = gtk.Label("Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Display name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Path to executable")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Startup type")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Start parameters")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 5, 6, gtk.FILL, 0, 5, 0)

        self.name_label = gtk.Label()
        self.name_label.set_alignment(0, 0.5)
        table.attach(self.name_label, 1, 2, 0, 1, gtk.FILL, 0, 0, 5)

        self.display_name_entry = gtk.Entry()
        self.display_name_entry.set_editable(False)
        table.attach(self.display_name_entry, 1, 2, 1, 2, gtk.FILL, 0, 0, 5)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        scrolledwindow.set_size_request(0, 50)
        table.attach(scrolledwindow, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 5)

        self.description_text_view = gtk.TextView()
        self.description_text_view.set_editable(False)
        self.description_text_view.set_wrap_mode(gtk.WRAP_WORD)
        scrolledwindow.add(self.description_text_view)

        self.exe_path_entry = gtk.Entry()
        self.exe_path_entry.set_editable(False)
        table.attach(self.exe_path_entry, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)

        self.startup_type_combo = gtk.combo_box_new_text()
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_BOOT_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_SYSTEM_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_AUTO_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_DEMAND_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_DISABLED))
        table.attach(self.startup_type_combo, 1, 2, 4, 5, gtk.FILL, 0, 0, 0)

        self.start_params_entry = gtk.Entry()
        self.start_params_entry.set_activates_default(True)
        table.attach(self.start_params_entry, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        notebook.set_tab_label(notebook.get_nth_page(0), gtk.Label("General"))


        # log on tab

        table = gtk.Table(8, 3, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)

        self.local_account_radio = gtk.RadioButton(None, "_Local System account")
        table.attach(self.local_account_radio, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.allow_desktop_interaction_check = gtk.CheckButton("Allo_w service to interact with desktop")
        table.attach(self.allow_desktop_interaction_check, 0, 2, 1, 2, gtk.FILL, 0, 20, 0)

        self.this_account_radio = gtk.RadioButton(self.local_account_radio, "_This account:")
        table.attach(self.this_account_radio, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        self.account_entry = gtk.Entry()
        self.account_entry.set_activates_default(True)
        table.attach(self.account_entry, 1, 2, 2, 3, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Password:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 20, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_activates_default(True)
        self.password_entry.set_visibility(False)
        table.attach(self.password_entry, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Confirm password:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 20, 0)

        self.confirm_password_entry = gtk.Entry()
        self.confirm_password_entry.set_activates_default(True)
        self.confirm_password_entry.set_visibility(False)
        table.attach(self.confirm_password_entry, 1, 2, 4, 5, gtk.FILL, 0, 0, 0)


        # TODO: implement hw profiles functionality

        label = gtk.Label("You can enable or disable this service for the hardware profiles listed below :")
        #table.attach(label, 0, 3, 5, 6, 0, 0, 0, 5)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        #table.attach(scrolledwindow, 0, 3, 6, 7, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 0, 0)

        self.profiles_tree_view = gtk.TreeView()
        scrolledwindow.add(self.profiles_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Hardware profile")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.profiles_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Status")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.profiles_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        self.profiles_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.profiles_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.profiles_tree_view.set_model(self.profiles_store)

        hbox = gtk.HBox(2, False)
#        table.attach(hbox, 0, 1, 7, 8, 0, 0, 0, 0)

        self.enable_button = gtk.Button("Enable")
        hbox.pack_start(self.enable_button, False, False, 0)

        self.disable_button = gtk.Button("Disable")
        hbox.pack_start(self.disable_button, False, False, 0)

        notebook.set_tab_label(notebook.get_nth_page(1), gtk.Label("Log On"))

        # dialog buttons

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


        # signals/events

        self.local_account_radio.connect("toggled", self.on_local_account_radio_clicked)
        #self.profiles_tree_view.get_selection().connect("changed", self.on_profiles_tree_view_selection_changed)
        #self.enable_button.connect("clicked", self.on_enable_button_click)
        #self.disable_button.connect("clicked", self.on_disable_button_click)

    def check_for_problems(self):
        if (self.password_entry.get_text() != self.confirm_password_entry.get_text()) and self.this_account_radio.get_active():
            return "The password was not correctly confirmed. Please ensure that the password and confirmation match exactly."

        return None

    def update_sensitivity(self):
        local_account = self.local_account_radio.get_active()

        self.allow_desktop_interaction_check.set_sensitive(local_account)
        self.account_entry.set_sensitive(not local_account)
        self.password_entry.set_sensitive(not local_account)
        self.confirm_password_entry.set_sensitive(not local_account)

#        profile = self.get_selected_profile()
#        if (profile is None):
#            self.enable_button.set_sensitive(False)
#            self.disable_button.set_sensitive(False)
#        else:
#            self.enable_button.set_sensitive(not profile[1])
#            self.disable_button.set_sensitive(profile[1])

    def service_to_values(self):
        if (self.service is None):
            raise Exception("service not set")

        self.name_label.set_text(self.service.name)
        self.display_name_entry.set_text(self.service.display_name)
        self.description_text_view.get_buffer().set_text(self.service.description)
        self.exe_path_entry.set_text(self.service.path_to_exe)

        temp_dict = {svcctl.SVCCTL_BOOT_START:0, svcctl.SVCCTL_SYSTEM_START:1, svcctl.SVCCTL_AUTO_START:2, svcctl.SVCCTL_DEMAND_START:3, svcctl.SVCCTL_DISABLED:4}

        self.startup_type_combo.set_active(temp_dict[self.service.start_type])
        self.start_params_entry.set_text(self.service.start_params)

        if (self.service.account is None):
            self.local_account_radio.set_active(True)
            self.allow_desktop_interaction_check.set_active(self.service.allow_desktop_interaction)
        else:
            self.this_account_radio.set_active(True)
            self.account_entry.set_text(self.service.account)

            if (self.service.account_password is not None):
                self.password_entry.set_text(self.service.account_password)
                self.confirm_password_entry.set_text(self.service.account_password)

        #self.refresh_profiles_tree_view()

    def values_to_service(self):
        if (self.service is None):
            raise Exception("service not set")

        temp_dict = {0:svcctl.SVCCTL_BOOT_START, 1:svcctl.SVCCTL_SYSTEM_START, 2:svcctl.SVCCTL_AUTO_START, 3:svcctl.SVCCTL_DEMAND_START, 4:svcctl.SVCCTL_DISABLED}

        self.service.start_type = temp_dict[self.startup_type_combo.get_active()]
        self.service.start_params = self.start_params_entry.get_text()

        if (self.local_account_radio.get_active()):
            self.service.account = None
            self.service.account_password = None
            self.service.allow_desktop_interaction = self.allow_desktop_interaction_check.get_active()
        else:
            self.service.account = self.account_entry.get_text()
            self.service.account_password = self.password_entry.get_text()

#        del self.service.hw_profile_list[:]
#
#        iter = self.profiles_store.get_iter_first()
#        while (iter is not None):
#            name = self.profiles_store.get_value(iter, 0)
#            enabled = self.profiles_store.get_value(iter, 1)
#            self.service.hw_profile_list.append([name, [False, True][enabled == "Enabled"]])
#            iter = self.profiles_store.iter_next(iter)

#    def refresh_profiles_tree_view(self):
#        (model, paths) = self.profiles_tree_view.get_selection().get_selected_rows()
#
#        self.profiles_store.clear()
#        for profile in self.service.hw_profile_list:
#            self.profiles_store.append((profile[0], ["Disabled", "Enabled"][profile[1]]))
#
#        if (len(paths) > 0):
#            self.profiles_tree_view.get_selection().select_path(paths[0])

#    def get_selected_profile(self):
#        (model, iter) = self.profiles_tree_view.get_selection().get_selected()
#        if (iter is None): # no selection
#            return None
#        else:
#            name = model.get_value(iter, 0)
#            return [profile for profile in self.service.hw_profile_list if profile[0] == name][0]

    def on_local_account_radio_clicked(self, widget):
        self.update_sensitivity()

#    def on_enable_button_click(self, widget):
#        profile = self.get_selected_profile()
#        if (profile is None): # no selection
#            return
#
#        profile[1] = True
#        self.refresh_profiles_tree_view()
#
#    def on_disable_button_click(self, widget):
#        profile = self.get_selected_profile()
#        if (profile is None): # no selection
#            return
#
#        profile[1] = False
#        self.refresh_profiles_tree_view()
#
#    def on_profiles_tree_view_selection_changed(self, widget):
#        self.update_sensitivity()


class ServiceControlDialog(gtk.Dialog):

    def __init__(self, service, control):
        super(ServiceControlDialog, self).__init__()

        self.service = service
        self.control = control
        self.cancel_callback = None
        self.progress_speed = 0.1

        self.create()

    def create(self):
        self.set_title("Service Control")
        self.set_border_width(10)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "service.png"))
        self.set_resizable(False)
        self.set_size_request(400, 150)

        self.control_label = gtk.Label()
        self.control_label.set_markup("<b>" + ServiceControlDialog.get_control_string(self) + "</b> " + self.service.display_name + "...")
        self.control_label.set_padding(10, 10)
        self.control_label.set_ellipsize(pango.ELLIPSIZE_END)
        self.vbox.pack_start(self.control_label, False, True, 5)

        self.progress_bar = gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.vbox.pack_start(self.progress_bar, False, True, 5)


        # dialog buttons

        self.action_area.set_layout(gtk.BUTTONBOX_CENTER)

        self.close_button = gtk.Button("Close", gtk.STOCK_CLOSE)
        self.close_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.close_button, gtk.RESPONSE_CANCEL)

        self.set_default_response(gtk.RESPONSE_CANCEL)


        # signals/events

        self.close_button.connect("clicked", self.on_close_button_clicked)

    def get_control_string(self):
        if (self.control is None):
            return "Starting"
        elif (self.control == svcctl.SVCCTL_CONTROL_STOP):
            return "Stopping"
        elif (self.control == svcctl.SVCCTL_CONTROL_PAUSE):
            return "Pausing"
        elif (self.control == svcctl.SVCCTL_CONTROL_CONTINUE):
            return "Resuming"
        else:
            return ""

    def set_close_callback(self, close_callback):
        self.close_callback = close_callback

    def progress(self, to_the_end = False):
        fraction = self.progress_bar.get_fraction()

        if ((fraction + self.progress_speed >= 1.0) or to_the_end):
            self.progress_bar.set_fraction(1.0)
        else:
            self.progress_bar.set_fraction(fraction + self.progress_speed)

    def set_progress_speed(self, progress_speed):
        self.progress_speed = progress_speed

    def on_close_button_clicked(self, widget):
        if (self.close_callback is not None):
            self.close_callback()


class SvcCtlConnectDialog(gtk.Dialog):

    def __init__(self, server, transport_type, username, password):
        super(SvcCtlConnectDialog, self).__init__()

        self.server_address = server
        self.transport_type = transport_type
        self.username = username
        self.password = password

        self.create()

        self.update_sensitivity()

    def create(self):
        self.set_title("Connect to a server")
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)

        # server frame

        self.vbox.set_spacing(5)

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

        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None, "RPC over SMB over TCP/IP")
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)

        self.rpc_tcpip_radio_button = gtk.RadioButton(self.rpc_smb_tcpip_radio_button, "RPC over TCP/IP")
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)

        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)


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

    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()



