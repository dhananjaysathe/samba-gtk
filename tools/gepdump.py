#   Unix SMB/CIFS implementation.
#   GTK+ Endpoint Mapper frontend
#   
#   Copyright (C) Jelmer Vernooij 2004
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#   
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#   
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# 
# * Show: 
# *  - RPC statistics
# *  - Available interfaces
# *   - Per interface: available endpoints
# *   - Per interface auth details
#

import gtk
import samba.gtk
from samba.dcerpc import mgmt, epmapper

protocol_names = {
    epmapper.EPM_PROTOCOL_UUID: "UUID",
    epmapper.EPM_PROTOCOL_NCACN: "NCACN",
    epmapper.EPM_PROTOCOL_NCALRPC: "NCALRPC",
    epmapper.EPM_PROTOCOL_NCADG: "NCADG",
    epmapper.EPM_PROTOCOL_IP: "IP",
    epmapper.EPM_PROTOCOL_TCP: "TCP",
    epmapper.EPM_PROTOCOL_NETBIOS: "NetBIOS",
    epmapper.EPM_PROTOCOL_SMB: "SMB",
    epmapper.EPM_PROTOCOL_PIPE: "PIPE",
    epmapper.EPM_PROTOCOL_UNIX_DS: "Unix",
}

def get_protocol_name(protocol):
    return protocol_names.get(protocol, "Unknown")


class EndpointBrowser(gtk.Window):

    def on_quit1_activate (self, menuitem):
        gtk.main_quit()

    def on_about1_activate(self, menuitem):
        aboutwin = samba.gtk.AboutDialog("gepdump")
        aboutwin.run()

    def add_epm_entry(self, annotation, t):
        bd = t.as_binding_string()
        store_eps.append((0, annotation, 1, str(bd), 2, t))

        for floor in t.floors:
            if floor.lhs.protocol == EPM_PROTOCOL_UUID:
                data = str(floor.get_lhs_data().uuid)
            else:
                data = floor.get_rhs_data()
            
            store_eps.append((0, get_protocol_name(floor.lhs.protocol), 1, data, -1))

    def refresh_eps(self):
        store_eps.clear()

        handle = None
        num_ents = max_ents = 10

        while num_ents == max_ents:
            (handle, num_ents, ents) = epmapper_pipe.Lookup(inquiry_type=0, 
                object=uuid, interface_id=iface, vers_option=0, 
                entry_handle=handle, max_ents=max_ents)
            for ent in ents:
                self.add_epm_entry(ent.annotation, ent.tower.tower)

    def on_refresh_clicked(self, btn):
        self.refresh_eps()

    def on_connect_clicked(self, btn):
        self._epmapper_pipe = gtk_connect_rpc_interface(lp_ctx, epmapper.epmapper)

        mnu_refresh.set_sensitive(True)

        refresh_eps()

        self._mgmt_pipe = mgmt.mgmt(self._epmapper_pipe)

    def on_eps_select(self, selection, model, path, path_currently_selected, data):
        # Do an InqStats call
        statistics = mgmt_pipe.inq_stats(max_count=MGMT_STATS_ARRAY_MAX_SIZE, 
                                         unknown=0)

        if statistics.count != MGMT_STATS_ARRAY_MAX_SIZE:
            raise Exception("Unexpected array size %d" % statistics.count)

        self._lbl_calls_in.set_text("%6d" % statistics[mgmt.MGMT_STATS_CALLS_IN])
        self._lbl_calls_out.set_text("%6d" % statistics[mgmt.MGMT_STATS_CALLS_OUT])
        self._lbl_pkts_in.set_text("%wd" % statistics[mgmt.MGMT_STATS_PKTS_IN])
        self._lbl_pkts_out.set_text("%6d" % statistics[mgmt.MGMT_STATS_PKTS_OUT])

        self._store_princ_names.clear()

        for i in range(100):
            princ_name = mgmt_pipe.inq_princ_name(authn_proto=i, princ_name_size=100)
            name = gensec_get_name_by_authtype(i)
            if name is not None:
                protocol = "%u (%s)" % (i, name)
            else:
                protocol = "%u" % i

            self._store_princ_names.append((0, protocol, 1, princ_name))

        return True

    def _create_mainwindow(self):
        accel_group = gtk.AccelGroup()

        self.set_title("Gtk+ Endpoint Mapper Viewer")

        vbox1 = gtk.VBox(False, 0)
        vbox1.show()
        self.add(vbox1)

        menubar1 = gtk.MenuBar()
        menubar1.show()
        vbox1.pack_start(menubar1, False, False, 0)

        menuitem1 = gtk_menu_item_new_with_mnemonic ("_File")
        menuitem1.show()
        menubar1.add(menuitem1)

        menuitem1_menu = gtk.Menu()
        menuitem1.set_submenu (menuitem1_menu)

        mnu_connect = gtk_menu_item_new_with_mnemonic ("_Connect")
        menuitem1_menu.add(mnu_connect)

        mnu_refresh = gtk_menu_item_new_with_mnemonic ("_Refresh")
        menuitem1_menu.add(mnu_refresh)
        gtk_widget_set_sensitive( mnu_refresh, false )

        quit1 = gtk_image_menu_item_new_from_stock ("gtk-quit", accel_group)
        menuitem1_menu.add(quit1)

        menuitem4 = gtk_menu_item_new_with_mnemonic ("_Help")
        menubar1.add (menuitem4)

        menuitem4_menu = gtk.Menu()
        menuitem4.set_submenu (menuitem4_menu)

        about1 = gtk_menu_item_new_with_mnemonic ("_About")
        menuitem4_menu.add(about1)

        hbox2 = gtk.HBox(False, 0)
        vbox1.add(hbox2)

        scrolledwindow1 = gtk.ScrolledWindow(None, None)
        hbox2.pack_start(scrolledwindow1, True, True, 0)

        tree_eps = gtk.TreeView()

        curcol = gtk.TreeViewColumn()
        gtk_tree_view_column_set_title(curcol, "Name")
        renderer = gtk.CellRendererText()
        gtk_tree_view_column_pack_start(curcol, renderer, true)

        tree_eps.append_column(curcol)
        gtk_tree_view_column_add_attribute(curcol, renderer, "text", 0)

        curcol = gtk.TreeViewColumn()
        gtk_tree_view_column_set_title(curcol, "Binding String")
        renderer = gtk.CellRendererText()
        gtk_tree_view_column_pack_start(curcol, renderer, true)
        gtk_tree_view_column_add_attribute(curcol, renderer, "text", 1)


        tree_eps.append_column(curcol)

        store_eps = gtk.TreeStore(3, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_POINTER)
        tree_eps.set_model(store_eps)

        scrolledwindow1.add (tree_eps)

        tree_eps.gtk_tree_view_get_selection().set_select_function(on_eps_select, None, None)

        vbox2 = gtk.VBox(False, 0)
        hbox2.add (vbox2)

        frame1 = gtk.Frame("Interface")
        vbox2.add (frame1)

        vbox3 = gtk.VBox(False, 0)
        frame1.add(vbox3)
        vbox3.add(lbl_iface_uuid = gtk.Label(""))
        vbox3.add(lbl_iface_version = gtk.Label(""))
        vbox3.add(lbl_iface_name = gtk.Label(""))

        frame1 = gtk.Frame("Statistics")
        vbox2.add(frame1)

        table_statistics = gtk.Table(4, 2, True)
        frame1.add(table_statistics)

        table_statistics.attach_defaults(gtk.Label("Calls In: "), 0, 1, 0, 1)
        lbl_calls_in = gtk.Label("")
        table_statistics.attach_defaults(lbl_calls_in, 1, 2, 0, 1)
        table_statistics.attach_defaults(gtk.Label("Calls Out: "), 0, 1, 1, 2)
        lbl_calls_out = gtk.Label("")
        table_statistics.attach_defaults(lbl_calls_out, 1, 2, 1, 2)
        table_statistics.attach_defaults(gtk.Label("Packets In: "), 0, 1, 2, 3)
        lbl_pkts_in = gtk.Label("")
        table_statistics.attach_defaults(lbl_pkts_in, 1, 2, 2, 3)
        table_statistics.attach_defaults(gtk.Label("Packets Out: "), 0, 1, 3, 4)
        lbl_pkts_out = gtk.Label("")
        table_statistics.attach_defaults(lbl_pkts_out, 1, 2, 3, 4)
        
        frame1 = gtk.Frame("Authentication")
        vbox2.add(frame1)

        self._treeview_princ_names = gtk.TreeView()

        curcol = gtk.TreeViewColumn()
        gtk_tree_view_column_set_title(curcol, "Protocol")
        renderer = gtk.CellRendererText()
        gtk_tree_view_column_pack_start(curcol, renderer, true)
        self._treeview_princ_names.append_column(curcol)
        gtk_tree_view_column_add_attribute(curcol, renderer, "text", 0)

        curcol = gtk.TreeViewColumn()
        gtk_tree_view_column_set_title(curcol, "Principal Name")
        curcol.pack_start(gtk.CellRendererText(), true)
        self._treeview_princ_names.append_column(curcol)
        gtk_tree_view_column_add_attribute(curcol, renderer, "text", 1)

        frame1.add(self._treeview_princ_names)

        self._store_princ_names = gtk.ListStore(4, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_POINTER)
        self._treeview_princ_names.set_model(self._store_princ_names)

        statusbar = gtk.StatusBar()
        vbox1.pack_start (statusbar, False, False, 0)

        quit1.connect("activate", self.on_quit1_activate)
        about1.connect("activate", on_about1_activate)
        mnu_connect.connect ("activate", self.on_connect_clicked)
        mnu_refresh.connect ("activate", self.on_refresh_clicked)

        self.add_accel_group (accel_group)


lp_ctx = loadparm_init(NULL)
lp_load_default(lp_ctx)

mainwin = EndpointBrowser()
mainwin.show_all()
gtk.main_loop()
