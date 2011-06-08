import datetime
import gtk
import os
import sys

class Task(object):

    def __init__(self, command, id):
        self.command = command
        self.id = id
        self.job_time = 0
        self.days_of_month = 0
        self.days_of_week = 0
        self.run_periodically = False
        self.non_interactive = False

    def get_scheduled_index(self):
        if (self.days_of_month == 0x7FFFFFFF): # daily schedule
            return 0
        elif (self.days_of_week > 0): # weekly schedule
            return 1
        else: # monthly schedule
            return 2

    def get_time(self):
        time = self.job_time / 1000 # get rid of milliseconds
        seconds = int(time % 60)

        time /= 60 # get rid of seconds
        minutes = int(time % 60)

        time /= 60 # get rid of minutes
        hour = int(time % 24)

        return (hour, minutes, seconds)

    def set_time(self, hour, minutes, seconds):
        h_ms = int(hour * 60 * 60 * 1000)
        m_ms = int(minutes * 60 * 1000)
        s_ms = int(seconds * 1000)

        self.job_time = h_ms + m_ms + s_ms

    def get_scheduled_days_of_week(self):
        dow_list = []

        for day_no in xrange(0, 7):
            if (self.days_of_week & (2 ** day_no)):
                dow_list.append(day_no)

        return dow_list

    def get_scheduled_days_of_month(self):
        dom_list = []

        for day_no in xrange(0, 31):
            if (self.days_of_month & (2 ** day_no)):
                dom_list.append(day_no)

        return dom_list

    def set_scheduled_days_of_week(self, dow_list):
        self.days_of_week = 0x00

        for day_no in dow_list:
            self.days_of_week |= (2 ** day_no)

    def set_scheduled_days_of_month(self, dom_list):
        self.days_of_month = 0x00000000

        for day_no in dom_list:
            self.days_of_month |= (2 ** day_no)

    def get_scheduled_description(self):
        if (self.days_of_week == 0x00 and self.days_of_month == 0x00000000):
            return "Not scheduled."

        (hour, minutes, seconds) = self.get_time()
        index = self.get_scheduled_index()

        at_str = "%02d:%02d" % (hour, minutes)

        if (self.run_periodically):
            if (index == 0): # daily schedule
                every_str = "every day"
            elif (index == 1): # weekly schedule
                dow_str = ""
                for day_no in self.get_scheduled_days_of_week():
                    dow_str += Task.get_day_of_week_name(day_no) + ", "

                # eliminate the last comma
                dow_str = dow_str.rstrip(", ")

                every_str = "every " + dow_str + " of every week"
            else: # monthly schedule
                dom_str = ""
                for day_no in self.get_scheduled_days_of_month():
                    dom_str += Task.get_day_of_month_name(day_no) + ", "

                # eliminate the last comma
                dom_str = dom_str.rstrip(", ")

                every_str = "every " + dom_str + " of every month"
        else:
            if (index == 0): # daily schedule
                next_str = "once"
            elif (index == 1): # weekly schedule
                next_str = "next " + self.get_day_of_week_name(self.get_scheduled_days_of_week()[0])
            else:
                next_str = "next " + self.get_day_of_month_name(self.get_scheduled_days_of_month()[0]) + " of the month"

        sw_str = "starting with " + str(datetime.date.today())

        if (self.run_periodically):
            return "At " + at_str + ", " + every_str + ", " + sw_str + "."
        else:
            return "At " + at_str + ", " + next_str + ", " + sw_str + "."

    @staticmethod
    def get_day_of_week_name(day_no):
        DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]

        return DAYS_OF_WEEK[day_no]

    @staticmethod
    def get_day_of_month_name(day_no):
        if day_no == 0:
            return "1st"
        elif day_no == 1:
            return "2nd"
        elif day_no == 2:
            return "3rd"
        else:
            return str(day_no + 1) + "th"

    def list_view_representation(self):
        return [str(self.id), self.command, self.get_scheduled_description()]

class TaskEditDialog(gtk.Dialog):

    def __init__(self, task = None):
        super(TaskEditDialog, self).__init__()

        if (task is None):
            self.brand_new = True
            self.task = Task("", -1)
        else:
            self.brand_new = False
            self.task = task

        self.disable_signals = True

        self.create()

        if (not self.brand_new):
            self.task_to_values()
        self.update_sensitivity()
        self.update_captions()

        self.disable_signals = False

    def create(self):
        self.set_title(["Edit task", "New task"][self.brand_new])
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "crontab.png"))
        self.set_resizable(False)
        self.set_size_request(500, -1)


        # scheduled description label

        self.scheduled_label = gtk.Label()
        self.scheduled_label.set_line_wrap(True)
        self.scheduled_label.set_padding(10, 10)
        self.vbox.pack_start(self.scheduled_label, True, True, 0)

        separator = gtk.HSeparator()
        self.vbox.pack_start(separator, False, True, 10)


        # command
        hbox = gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)

        label = gtk.Label("Command:")
        hbox.pack_start(label, False, True, 5)

        self.command_entry = gtk.Entry()
        self.command_entry.set_activates_default(True)
        hbox.pack_start(self.command_entry, True, True, 5)

        separator = gtk.HSeparator()
        self.vbox.pack_start(separator, False, True, 10)

        table = gtk.Table(2, 3)
        table.set_border_width(5)
        table.set_row_spacings(5)
        table.set_col_spacings(5)
        self.vbox.pack_start(table, True, True, 0)

        label = gtk.Label("Schedule Task:")
        table.attach(label, 0, 1, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)

        label = gtk.Label("Start Time:")
        table.attach(label, 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)

        table.attach(gtk.Label(), 2, 3, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)

        self.scheduled_combo = gtk.combo_box_new_text()
        self.scheduled_combo.append_text("Daily")
        self.scheduled_combo.append_text("Weekly")
        self.scheduled_combo.append_text("Monthly")
        self.scheduled_combo.set_active(0)
        table.attach(self.scheduled_combo, 0, 1, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)

        hbox = gtk.HBox()
        table.attach(hbox, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 10, 0)

        self.hour_spin_button = gtk.SpinButton()
        self.hour_spin_button.set_range(0, 23)
        self.hour_spin_button.set_numeric(True)
        self.hour_spin_button.set_increments(1, 1)
        self.hour_spin_button.set_width_chars(2)
        hbox.pack_start(self.hour_spin_button, True, True, 0)

        label = gtk.Label(":")
        hbox.pack_start(label, False, False, 0)

        self.minute_spin_button = gtk.SpinButton()
        self.minute_spin_button.set_range(0, 59)
        self.minute_spin_button.set_numeric(True)
        self.minute_spin_button.set_increments(1, 1)
        self.minute_spin_button.set_width_chars(2)
        hbox.pack_start(self.minute_spin_button, True, True, 0)

        table.attach(gtk.Label(), 2, 3, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)

        table = gtk.Table(2, 2)
        self.vbox.pack_start(table, True, True, 5)


        # weekly stuff

        self.weekly_label = gtk.Label(" Run weekly on: ")
        table.attach(self.weekly_label, 0, 1, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_border_width(5)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        table.attach(scrolledwindow, 0, 1, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 5, 5)

        self.weekly_tree_view = gtk.TreeView()
        self.weekly_tree_view.set_size_request(0, 150)
        self.weekly_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.weekly_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Checked")
        self.weekly_toggle_renderer = gtk.CellRendererToggle()
        column.pack_start(self.weekly_toggle_renderer, True)
        self.weekly_tree_view.append_column(column)
        column.add_attribute(self.weekly_toggle_renderer, "active", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Day")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.weekly_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        self.weekly_store = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        self.weekly_tree_view.set_model(self.weekly_store)

        self.weekly_store.append([False, "Monday"])
        self.weekly_store.append([False, "Tuesday"])
        self.weekly_store.append([False, "Wednesday"])
        self.weekly_store.append([False, "Thursday"])
        self.weekly_store.append([False, "Friday"])
        self.weekly_store.append([False, "Saturday"])
        self.weekly_store.append([False, "Sunday"])


        # monthly stuff

        self.monthly_label = gtk.Label(" Run monthly on the: ")
        table.attach(self.monthly_label, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_border_width(5)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        table.attach(scrolledwindow, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 5, 5)

        self.monthly_tree_view = gtk.TreeView()
        self.monthly_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.monthly_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Checked")
        self.monthly_toggle_renderer = gtk.CellRendererToggle()
        column.pack_start(self.monthly_toggle_renderer, True)
        self.monthly_tree_view.append_column(column)
        column.add_attribute(self.monthly_toggle_renderer, "active", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Day")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.monthly_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        self.monthly_store = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        self.monthly_tree_view.set_model(self.monthly_store)

        for day_no in xrange(0, 31):
            self.monthly_store.append([False, Task.get_day_of_month_name(day_no)])

        self.run_periodically_check = gtk.CheckButton("Repeating schedule (run periodically)")
        self.run_periodically_check.connect("toggled", self.on_update_captions)
        self.vbox.pack_start(self.run_periodically_check, False, True, 5)

        self.non_interactive_check = gtk.CheckButton("Don't interact with the logged-on user")
        self.vbox.pack_start(self.non_interactive_check, False, True, 5)


        # dialog buttons

        self.action_area.set_layout(gtk.BUTTONBOX_END)

        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new task
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)

        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)


        # signals/events

        self.scheduled_combo.connect("changed", self.on_update_sensitivity)
        self.scheduled_combo.connect("changed", self.on_update_captions)
        self.weekly_toggle_renderer.connect("toggled", self.on_renderer_toggled, self.weekly_store)
        self.monthly_toggle_renderer.connect("toggled", self.on_renderer_toggled, self.monthly_store)
        self.hour_spin_button.connect("value-changed", self.on_update_captions)
        self.minute_spin_button.connect("value-changed", self.on_update_captions)

    def check_for_problems(self):
        if (len(self.command_entry.get_text().strip()) == 0):
            return "Please specify a command."

        index = self.scheduled_combo.get_active()
        last_active_row = None

        if (index == 1): # weekly schedule
            for row in self.weekly_store:
                if (row[0]):
                    last_active_row = row
                    break
            if (last_active_row is None):
                return "You need to select at least one day of the week, for a weekly schedule."
        elif (index == 2): # monthly schedule
            for row in self.monthly_store:
                if (row[0]):
                    last_active_row = row
                    break
            if (last_active_row is None):
                return "You need to select at least one day of the month, for a monthly schedule."

        return None

    def update_sensitivity(self):
        index = self.scheduled_combo.get_active()

        self.weekly_label.set_sensitive(index == 1) # weekly
        self.monthly_label.set_sensitive(index == 2) # monthly

        self.weekly_tree_view.set_sensitive(index == 1) # weekly
        self.monthly_tree_view.set_sensitive(index == 2) # monthly

    def update_captions(self):
        self.values_to_task()
        self.scheduled_label.set_text(self.task.get_scheduled_description())

        if (self.run_periodically_check.get_active()):
            self.weekly_label.set_label(" Run weekly on: ")
            self.monthly_label.set_label(" Run monthly on the: ")

            self.weekly_toggle_renderer.set_property("radio", False)
            self.monthly_toggle_renderer.set_property("radio", False)
        else:
            self.weekly_label.set_label(" Run on next: ")
            self.monthly_label.set_label(" Run on the next: ")

            self.weekly_toggle_renderer.set_property("radio", True)
            self.monthly_toggle_renderer.set_property("radio", True)

            # make sure there's exactly one checked item when working with radios
            first_active_row = None
            for row in self.weekly_store:
                if (row[0]):
                    if (first_active_row is not None):
                        row[0] = False
                    else:
                        first_active_row = row
            if (first_active_row is None):
                self.weekly_store[0][0] = True

            # make sure there's exactly one checked item when working with radios
            first_active_row = None
            for row in self.monthly_store:
                if (row[0]):
                    if (first_active_row is not None):
                        row[0] = False
                    else:
                        first_active_row = row
            if (first_active_row is None):
                self.monthly_store[0][0] = True

        # needed for an immediate visual update
        self.weekly_tree_view.queue_draw()
        self.monthly_tree_view.queue_draw()

    def task_to_values(self):
        if (self.task is None):
            raise Exception("task not set")

        self.scheduled_label.set_text(self.task.get_scheduled_description())
        self.command_entry.set_text(self.task.command)

        (hour, minutes, seconds) = self.task.get_time()

        self.hour_spin_button.set_value(hour)
        self.minute_spin_button.set_value(minutes)

        index = self.task.get_scheduled_index()
        self.scheduled_combo.set_active(index)
        if (index == 1): # weekly schedule
            for day_no in self.task.get_scheduled_days_of_week():
                self.weekly_store[day_no][0] = True
        elif (index == 2): # monthly schedule
            for day_no in self.task.get_scheduled_days_of_month():
                self.monthly_store[day_no][0] = True

        self.run_periodically_check.set_active(self.task.run_periodically)
        self.non_interactive_check.set_active(self.task.non_interactive)

    def values_to_task(self):
        if (self.task is None):
            raise Exception("task not set")

        self.task.command = self.command_entry.get_text()

        self.task.set_time(self.hour_spin_button.get_value(), self.minute_spin_button.get_value(), 0)

        index = self.scheduled_combo.get_active()

        self.task.set_scheduled_days_of_week([])
        self.task.set_scheduled_days_of_month([])

        if (index == 0): # daily schedule
            dom_list = []
            for day_no in xrange(0, 31):
                dom_list.append(day_no)
            self.task.set_scheduled_days_of_month(dom_list)
        elif (index == 1): # weekly schedule
            dow_list = []
            for day_no in xrange(0, 7):
                if (self.weekly_store[day_no][0]):
                    dow_list.append(day_no)
            self.task.set_scheduled_days_of_week(dow_list)
        elif (index == 2): # monthly schedule
            dom_list = []
            for day_no in xrange(0, 31):
                if (self.monthly_store[day_no][0]):
                    dom_list.append(day_no)
            self.task.set_scheduled_days_of_month(dom_list)

        self.task.run_periodically = self.run_periodically_check.get_active()
        self.task.non_interactive = self.non_interactive_check.get_active()

    def on_renderer_toggled(self, widget, path, store):
        if (self.disable_signals):
            return

        if (widget.get_radio()):
            for row in store:
                row[0] = False
            store[path][0] = True
        else:
            store[path][0] = not store[path][0]

        self.update_captions()

    def on_update_sensitivity(self, widget):
        if (self.disable_signals):
            return

        self.update_sensitivity()

    def on_update_captions(self, widget):
        if (self.disable_signals):
            return

        self.update_captions()


class ATSvcConnectDialog(gtk.Dialog):

    def __init__(self, server, transport_type, username, password):
        super(ATSvcConnectDialog, self).__init__()

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
        self.rpc_tcpip_radio_button.set_sensitive(False)
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)

        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_sensitive(False)
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



