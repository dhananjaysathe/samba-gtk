#!/usr/bin/python2
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

from gi.repository import Gtk
from gi.repository import GObject
import os
import sys
from sambagtk.dialogs import ConnectDialog

from samba.dcerpc import srvsvc


class srvsvcConnectDialog(ConnectDialog):

    def __init__(self, server, transport_type, username, password):

        super(srvsvcConnectDialog, self).__init__(
                    server, transport_type, username, password)
        self.set_title('Connect to Samba Share Server')




class ShareAddEditDialog(Gtk.Dialog):

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

        title = ' '.join([(' New Share', ' Edit Share : '
                       )[self.edit_mode], self.sname])
        self.icon_name = ['network-folder', 'network-printer', 'network'
                          , 'network-pipe'][self.stype]
        self.icon_filename = os.path.join(sys.path[0], 'images',
                ''.join([self.icon_name, '.png']))
        self.set_icon_from_file(self.icon_filename)
        self.vbox.set_spacing(3)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title(title)
        self.set_border_width(5)
        self.set_resizable(False)
        self.set_decorated(True)
        self.set_modal(True)

        # artwork
        self.desc_box = Gtk.HBox()
        self.vbox.pack_start(self.desc_box, False, True, 0)

        hbox = Gtk.HBox()
        icon = Gtk.Image()
        icon.set_from_file(self.icon_filename)

        hbox.pack_start(icon, False, True, 0)
        self.desc_box.pack_start(hbox, False, True, 0)

        hbox = Gtk.HBox()
        label = Gtk.Label(xalign=0.5, yalign=0.5)
        if self.edit_mode:
            label.set_markup('<b>%s</b>'
                              % ' '.join(['Editing The Share : ',
                             self.sname]))
        else:
            label.set_markup('<b>Add a New Share</b>')
        hbox.pack_start(label, True, True, 0)
        self.desc_box.pack_start(hbox, True, True, 0)

        # main form box

        self.form_box = Gtk.VBox()
        self.vbox.pack_start(self.form_box, True, True, 0)

        # Name , password and comment (npc) frame
        frame = Gtk.Frame()
        label = Gtk.Label('<b>Name and Comment</b>')
        label.set_property("use-markup",True)
        frame.set_label_widget(label)
        frame.set_border_width(5)
        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_row_spacing(2)
        grid.set_column_spacing(6)
        frame.add(grid)

        label = Gtk.Label(' Share Name : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        self.share_name_entry = Gtk.Entry()
        self.share_name_entry.set_text(self.sname)
        self.share_name_entry.set_activates_default(True)
        self.share_name_entry.set_tooltip_text(
            'Enter Name of the Share')
        # dcesrv_srvsvc name check does this but just to reduce chances of an error limit max length
        if self.flags[1]:
            self.share_name_entry.set_max_length(12)
        else:
            self.share_name_entry.set_max_length(80)
        grid.attach(self.share_name_entry, 1, 0, 1, 1)

        label = Gtk.Label(' Comment  : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 1, 1, 1)

        self.share_comment_entry = Gtk.Entry()
        self.share_comment_entry.set_property("max-length",48)
        self.share_comment_entry.set_text(self.comment)
        self.share_comment_entry.set_activates_default(True)
        self.share_comment_entry.set_tooltip_text(
            'Add a Comment or Description of the Share')
        grid.attach(self.share_comment_entry,  1, 1, 1, 1)

        label = Gtk.Label(' Password  : ',xalign=1, yalign=0.5)
        grid.attach(label, 0, 2, 1, 1)

        self.share_password_entry = Gtk.Entry()
        self.share_password_entry.set_text(self.password)
        self.share_password_entry.set_activates_default(True)
        self.share_password_entry.set_visibility(False)
        self.share_password_entry.set_tooltip_text(
                                        'Set a Share Password')
        grid.attach(self.share_password_entry, 1, 2, 1, 1)


        self.set_pw_visiblity = Gtk.CheckButton('Visible')
        self.set_pw_visiblity.set_property("active",False)
        self.set_pw_visiblity.set_tooltip_text(
                            'Enable or disable the password visiblity')
        self.set_pw_visiblity.connect('toggled',
                self.toggle_pwd_visiblity, None)
        grid.attach(self.set_pw_visiblity, 1, 3, 1, 1)

        # Share frame
        frame = Gtk.Frame()
        label = Gtk.Label('<b>Share Type</b>')
        label.set_property("use-markup",True)
        frame.set_property("label-widget",label)

        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_property("row-homogeneous",True)
        frame.add(grid)

        # Base Share Types
        vbox = Gtk.VBox()
        vbox.set_property("border-width",5)
        grid.attach(vbox, 0, 0, 1, 1)

        # Radio buttons
        self.stype_disktree_radio_button = \
            Gtk.RadioButton.new_with_label_from_widget(None,'Disktree')
        self.stype_disktree_radio_button.set_tooltip_text(
                            'Disktree (folder) type Share. Default')
        self.stype_disktree_radio_button.set_active(
                                    self.stype == srvsvc.STYPE_DISKTREE)
        vbox.pack_start(self.stype_disktree_radio_button, True, True, 0)

        self.stype_printq_radio_button = \
            Gtk.RadioButton.new_with_label_from_widget(
                        self.stype_disktree_radio_button,'Print Queue')
        self.stype_printq_radio_button.set_properties(
                            "tooltip-text",'Shared Print Queue',
                            "active",self.stype == srvsvc.STYPE_PRINTQ)
        # vbox.pack_start(self.stype_printq_radio_button, True, True, 0)
        # deactivating this option until samba4 is fixed TODO activate once base is fixed

        self.stype_ipc_radio_button = \
            Gtk.RadioButton(self.stype_printq_radio_button, 'IPC ')
        self.stype_ipc_radio_button.set_properties(
          "tooltip-text",'Shared Interprocess Communication Pipe (IPC)',
          "active",self.stype == srvsvc.STYPE_IPC)
        #vbox.pack_start(self.stype_ipc_radio_button, True, True, 0)
        #deactivating this option until samba4 is fixed TODO activate once base is fixed

        # Special Share Flags
        vbox = Gtk.VBox()
        vbox.set_property("border-width",5)
        grid.attach(vbox, 1, 0, 1, 1)

        # Check buttons
        self.sflag_temp_check_button = Gtk.CheckButton('Temporary')
        self.sflag_temp_check_button.set_property(
                                                "active",self.flags[0])
        self.sflag_temp_check_button.set_tooltip_text(
                                                'Make share Temporary')
        vbox.pack_start(self.sflag_temp_check_button, True, True, 0)

        self.sflag_hidden_check_button = Gtk.CheckButton('Hidden ')
        self.sflag_hidden_check_button.set_property(
                                                "active",self.flags[1])
        self.sflag_hidden_check_button.set_tooltip_text(
                                                'Make share Hidden')
        vbox.pack_start(self.sflag_hidden_check_button, True, True, 0)

        # Path frame
        frame = Gtk.Frame()
        label = Gtk.Label('<b>Path</b>')
        label.set_property("use-markup",True)
        frame.set_label_widget(label)
        frame.set_border_width(5)
        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_property("column-spacing",6)
        frame.add(grid)

        label = Gtk.Label('Share path : ', xalign = 0, yalign= 0.5)
        grid.attach(label, 0, 0, 1, 1)

        # FIXME may need another parameter to select type of selctor in combination with local
        # eg selecting a ipc / printer may be easier with a path

        if self.islocal:
            self.file_button = Gtk.FileChooserButton('Browse')
            self.file_button.set_current_folder(self.path)
            self.file_button.set_property(
                        "action",Gtk.FileChooserAction.SELECT_FOLDER)
            self.file_button.set_property("tooltip_text",
                                        'Select the folder to share')
            grid.attach(self.file_button, 1, 0, 1, 1)

        else:
            self.file_entry = Gtk.Entry()
            self.file_entry.set_property("text",self.path)
            self.file_entry.set_tooltip_text(
                                        'Path to the folder to share')
            grid.attach(self.file_button, 1, 0, 1, 1)

        # max users frame

        frame = Gtk.Frame()
        label = Gtk.Label('<b>Max Users</b>')
        label.set_property("use-markup",True)
        frame.set_label_widget(label)
        frame.set_border_width(5)
        self.form_box.pack_start(frame, True, True, 0)


        grid = Gtk.Grid()
        grid.set_property("column-spacing",6)
        frame.add(grid)

        label = Gtk.Label(' Max Users : ', xalign = 0, yalign= 0.5)
        grid.attach(label, 0, 0, 1, 1)

        # adjustment for max users spinbox
        self.max_users_adjustment = Gtk.Adjustment(self.max_users, 1,
                0xFFFFFFFF, 1, 5)

        self.max_users_spinbox = Gtk.SpinButton()
        self.max_users_spinbox.set_numeric(True)
        self.max_users_spinbox.set_adjustment(self.max_users_adjustment)
        self.max_users_spinbox.set_tooltip_text(
                                            'Max Users for the Share')
        grid.attach(self.max_users_spinbox, 1, 0, 1, 1)

        # action area

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button('Cancel', Gtk.STOCK_CANCEL)
        self.cancel_button.set_property("can-default",True)
        self.add_action_widget(self.cancel_button,
                                            Gtk.ResponseType.CANCEL)

        self.apply_button = Gtk.Button('Apply', Gtk.STOCK_APPLY)
        self.apply_button.set_property("sensitive",self.edit_mode)
        self.apply_button.set_property("can-default",True)
        self.add_action_widget(self.apply_button, Gtk.ResponseType.APPLY)

        self.ok_button = Gtk.Button('OK', Gtk.STOCK_OK)
        self.ok_button.set_property("can-default",True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_window_mode()


class DeleteDialog(Gtk.Dialog):

    """ The delete dialog """

    def __init__(self, pipe_manager, share=None):
        """ Class initialiser """

        super(DeleteDialog, self).__init__()
        self.pipe = pipe_manager


        if share is None:
            raise KeyError('Non existant Share cannot be deleted')

        self.share = share

        # resolving some types that are required for Gtk dialog creation

        self.stype = self.pipe.get_share_type_info(self.share.type,
                'base_type')
        self.flags = self.pipe.get_share_type_info(self.share.type,
                'flags')
        self.generic_typestring = \
            self.pipe.get_share_type_info(self.share.type, 'typestring')
        self.desc = self.pipe.get_share_type_info(self.share.type,
                'desc')

        self.create()

    def create(self):
        """ Create the window """

        title = ' '.join([' Delete Share', self.share.name])
        self.icon_name = ['network-folder', 'network-printer', 'network'
                          , 'network-pipe'][self.stype]
        self.icon_filename = os.path.join(sys.path[0], 'images',
                ''.join([self.icon_name, '.png']))
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

        hbox = Gtk.HBox()
        label = Gtk.Label(
            'You are deleting the share with the following properties',
            xalign=0, yalign=0.5)
        hbox.pack_start(label, True, True, 0)
        self.desc_box.pack_start(hbox, True, True, 0)

        # main form box
        self.form_box = Gtk.VBox()
        self.vbox.pack_start(self.form_box, True, True, 0)

        frame = Gtk.Frame()
        label = Gtk.Label('<b> Share Details</b>')
        label.set_property("use-markup",True)
        frame.set_label_widget(label)
        frame.set_border_width(5)
        self.form_box.pack_start(frame, True, True, 0)

        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_row_spacing(2)
        grid.set_column_spacing(6)
        frame.add(grid)

        label = Gtk.Label(' Share Name  : ', xalign=1, yalign=0.5)
        grid.attach(label, 0, 0, 1, 1)

        label = Gtk.Label(self.share.name, xalign=0, yalign=0.5)
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label(' Comment  : ', xalign=1, yalign=0.5)
        grid.attach(label, 0, 1, 1, 1)

        label = Gtk.Label(self.share.comment, xalign=0, yalign=0.5)
        grid.attach(label, 1, 1, 1, 1)

        label = Gtk.Label(' Path  : ', xalign=1, yalign=0.5)
        grid.attach(label, 0, 2, 1, 1)

        label = Gtk.Label(self.share.path, xalign=0, yalign=0.5)
        grid.attach(label, 1, 2, 1, 1)

        label = Gtk.Label(' Password  : ', xalign=1, yalign=0.5)
        grid.attach(label, 0, 3, 1, 1)

        if self.share.password:
            label = Gtk.Label('Share Password Enabled')
        else:
            label = Gtk.Label('Share Password Disabled')
        label.set_alignment(0, 0.5)
        grid.attach(label, 1, 3, 1, 1)

        label = Gtk.Label('<b> Share Type</b>', xalign=0, yalign=0.5)
        label.set_property("use-markup",True)
        grid.attach(label, 0, 4, 1, 1)


        label = Gtk.Label(' Generic Typestring  : ',xalign=1,yalign=0.5)
        grid.attach(label, 0, 5, 1, 1)

        label = Gtk.Label(self.generic_typestring, xalign=0, yalign=0.5)
        grid.attach(label, 1, 5, 1, 1)

        label = Gtk.Label(' Type Description  : ', xalign=1, yalign=0.5) # spaces for Gui align do not change
        grid.attach(label, 0, 6, 1, 1)

        label = Gtk.Label(self.desc, xalign=0, yalign=0.5)
        grid.attach(label, 1, 6, 1, 1)


        label = Gtk.Label('<b> Special Flags </b>',xalign=0, yalign=0.5)
        label.set_property("use-markup",True)
        grid.attach(label, 0, 7, 1, 1)

        label = Gtk.Label(' Temporary  : ',xalign=1,yalign=0.5)
        grid.attach(label, 0, 8, 1, 1)

        label = Gtk.Label(str(self.flags[0]), xalign=0, yalign=0.5)
        grid.attach(label, 1, 8, 1, 1)

        label = Gtk.Label(' Hidden  : ',xalign=1,yalign=0.5)
        grid.attach(label, 0, 9, 1, 1)

        label = Gtk.Label(str(self.flags[1]), xalign=0, yalign=0.5)
        grid.attach(label, 1, 9, 1, 1)

        label = Gtk.Label(' Max Users  : ',xalign=1,yalign=0.5)
        grid.attach(label, 0, 10, 1, 1)

        label = Gtk.Label(self.share.max_users, xalign=0, yalign=0.5)
        grid.attach(label, 1, 10, 1, 1)

        box = Gtk.VBox(3)
        label = Gtk.Label('Are yous sure you want to delete the share ?'
                          ,xalign = 0.5, yalign = 0.5)
        box.pack_start(label, True, True, 0)

        warning = '(Please Note this is an irreversable action)'
        label = Gtk.Label('<span foreground="red">%s</span>' % warning)
        label.set_use_markup(True)

        box.pack_start(label, True, True, 0)
        box.set_property("border-width",5)

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


class ShareWizardDialog(ShareAddEditDialog):

    def create(self):

        self.page = 0
        self.set_default_size(400, 275)

        self.main_box = Gtk.VBox()
        self.vbox.pack_start(self.main_box, True, True, 0)

        vbox = Gtk.VBox()
        vbox.set_property("border-width",5)
        samba_image_filename = os.path.join(sys.path[0], 'images',
                'samba-logo-small.png')
        samba_image = Gtk.Image()
        samba_image.set_from_file(samba_image_filename)
        vbox.pack_end(samba_image, False, True, 0)
        self.main_box.pack_start(vbox, False, True, 0)

        vbox = Gtk.VBox()
        self.main_box.pack_start(vbox, True, True, 0)

        frame = Gtk.Frame()
        frame.set_property("border-width",10)
        vbox.pack_start(frame, True, True, 0)

        self.data_box = Gtk.VBox()
        self.data_box.set_property("border-width",5)
        frame.add(self.data_box)

        self.title_label = Gtk.Label(xalign=0.05,yalign=0.5)
        self.data_box.pack_start(self.title_label, False, True, 1)

        self.info_label = Gtk.Label(xalign=0.15, yalign=0.5)
        self.data_box.pack_start(self.info_label, False, True, 0)

        self.fields_box = Gtk.VBox()
        self.data_box.pack_start(self.fields_box, True, True, 3)

        # create all entities do not attach them so as to that they are refrenced
        # name
        self.share_name_entry = Gtk.Entry()
        self.share_name_entry.set_text(self.sname)
        self.share_name_entry.set_activates_default(True)
        # dcesrv_srvsvc name check does this but just to reduce chances of an error limit max length
        if self.flags[1]:
            self.share_name_entry.set_max_length(12)
        else:
            self.share_name_entry.set_max_length(80)

        # comment
        self.share_comment_entry = Gtk.Entry()
        self.share_comment_entry.set_property("max-length",48)
        self.share_comment_entry.set_text(self.comment)
        self.share_comment_entry.set_activates_default(True)
        self.share_comment_entry.set_tooltip_text(
            'Add a Comment or Description of the Share,\
             Will default to share_type description')

        # password
        self.share_password_entry = Gtk.Entry()
        self.share_password_entry.set_text(self.password)
        self.share_password_entry.set_activates_default(True)
        self.share_password_entry.set_visibility(True)
        self.share_password_entry.set_tooltip_text(
                                        'Set a Share Password')


        # For radio buttons we define other fields on the fly as these
        # are lost on parent removal , and cause errors on draw .
        # Radio buttons
        self.stype_disktree_radio_button = \
            Gtk.RadioButton.new_with_label_from_widget(None,'Disktree')
        self.stype_printq_radio_button = \
            Gtk.RadioButton.new_with_label_from_widget(
                    self.stype_disktree_radio_button,'Print Queue')
        self.stype_ipc_radio_button = \
            Gtk.RadioButton.new_with_label_from_widget(
                        self.stype_printq_radio_button, 'IPC ')

        self.sflag_temp_check_button = Gtk.CheckButton('Temporary')
        self.sflag_hidden_check_button = Gtk.CheckButton('Hidden ')

        # path
        if self.islocal:
            self.file_button = Gtk.FileChooserButton('Browse')
        else:
            self.file_entry = Gtk.Entry()

        # max_users
        self.max_users_adjustment = Gtk.Adjustment(self.max_users, 1,
                0xFFFFFFFF, 1, 5)
        self.max_users_spinbox = Gtk.SpinButton()
        self.max_users_spinbox.set_numeric(True)
        self.max_users_spinbox.set_adjustment(self.max_users_adjustment)
        self.max_users_spinbox.set_tooltip_text(
                                            'Max Users for the Share')

        self.action_area.set_layout(Gtk.ButtonBoxStyle.CENTER)

        self.cancel_button = Gtk.Button('Cancel', Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.prev_button = Gtk.Button(stock=Gtk.STOCK_GO_BACK)
        self.prev_button.connect('clicked', self.update_fields, -1)
        self.action_area.pack_start(self.prev_button, False, False, 10)

        self.next_button = Gtk.Button(stock=Gtk.STOCK_GO_FORWARD)
        self.next_button.connect('clicked', self.update_fields, +1)
        self.action_area.pack_start(self.next_button, False, False, 0)

        self.ok_button = Gtk.Button('OK', Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)
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

            label = Gtk.Label('Please press next to continue.')
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

            grid = Gtk.Grid()
            grid.set_border_width(5)
            grid.set_row_spacing(2)
            grid.set_column_spacing(6)
            grid.set_row_homogeneous(True)

            label = Gtk.Label('* Share Name : ', xalign=1, yalign=0.5)
            grid.attach(label, 0, 0, 1, 1)
            grid.attach(self.share_name_entry, 1, 0, 1, 1)

            label = Gtk.Label('  Share Password : ', xalign=1, yalign=0.5)
            grid.attach(label, 0, 1, 1, 1)
            grid.attach(self.share_password_entry, 1, 1, 1, 1)

            self.fields_box.pack_start(grid, False, True, 0)
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


            grid = Gtk.Grid()
            grid.set_border_width(5)
            grid.set_row_spacing(2)
            grid.set_column_spacing(6)
            grid.set_row_homogeneous(True)

            label = Gtk.Label('  Share Comment :', xalign=1, yalign=0.5)
            grid.attach(label, 0, 0, 1, 1)
            grid.attach(self.share_comment_entry, 1, 0, 1, 1)

            label = Gtk.Label('  Max Users : ', xalign=1, yalign=0.5)
            grid.attach(label, 0, 1, 1, 1)
            grid.attach(self.max_users_spinbox, 1, 1, 1, 1)

            self.fields_box.pack_start(grid, False, True, 0)
            self.fields_box.show_all()

        elif self.page == 3:

            self.title_label.set_markup('<b>Share Type Options</b>')
            self.info_label.set_text(
                            'Please select your share type options.')
            self.prev_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.ok_button.set_sensitive(False)

            self.stype_disktree_radio_button = Gtk.RadioButton(None,
                    'Disktree')
            self.stype_disktree_radio_button.set_property(
                "tooltip-text",'Disktree (folder) type Share. Default')
            self.stype_disktree_radio_button.set_active(
                                    self.stype == srvsvc.STYPE_DISKTREE)

            self.stype_printq_radio_button = \
                Gtk.RadioButton(self.stype_disktree_radio_button,
                                'Print Queue')
            self.stype_printq_radio_button.set_property(
                            "tooltip-text",'Shared Print Queue')
            self.stype_printq_radio_button.set_active(
                                    self.stype == srvsvc.STYPE_PRINTQ)

            self.stype_ipc_radio_button = \
                Gtk.RadioButton(self.stype_printq_radio_button, 'IPC ')
            self.stype_ipc_radio_button.set_property("tooltip_text",
                        'Shared Interprocess Communication Pipe (IPC)')
            self.stype_ipc_radio_button.set_active(
                                        self.stype == srvsvc.STYPE_IPC)

            self.sflag_temp_check_button = Gtk.CheckButton('Temporary')
            self.sflag_temp_check_button.set_property(
                                 "tooltip_text",'Make share Temporary')
            self.sflag_temp_check_button.set_active(self.flags[0])

            self.sflag_hidden_check_button = Gtk.CheckButton('Hidden ')
            self.sflag_hidden_check_button.set_property(
                                   "tooltip_text",'Make share hidden.')
            self.sflag_hidden_check_button.set_active(self.flags[1])

            hbox = Gtk.HBox(True, 10)

            vbox = Gtk.VBox()
            vbox.set_property("border-width",5)

            vbox.pack_start(self.stype_disktree_radio_button, True,
                            True, 3)
            vbox.pack_start(self.stype_printq_radio_button, True, True,
                            3)
            vbox.pack_start(self.stype_ipc_radio_button, True, True, 3)
            hbox.pack_start(vbox, True, True, 0)

            vbox = Gtk.VBox()
            vbox.set_property("border-width",5)

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
                self.file_button = Gtk.FileChooserButton('Browse')
                if self.path is not None:
                    self.file_button.set_current_folder(self.path)
                else:
                    self.file_button.set_current_folder('.')
                self.file_button.set_property(
                           "action",Gtk.FileChooserAction.SELECT_FOLDER)
                self.file_button.set_tooltip-text(
                                        'Select the folder to share')
            else:
                self.file_entry = Gtk.Entry()
                if self.path is not None:
                    self.file_entry.set_text(self.path)
                else:
                    self.file_entry.set_text('')
                self.file_entry.set_property(
                           "tooltip_text",'Path to the folder to share')

            grid = Gtk.Grid()
            grid.set_border_width(5)
            grid.set_row_spacing(2)
            grid.set_column_spacing(6)
            grid.set_row_homogeneous(True)

            label = Gtk.Label('  Path     : ', xalign=1, yalign=0.5)
            grid.attach(label, 0, 0, 1, 1)
            if self.islocal:
                grid.attach(self.file_button,  1, 0, 1, 1)
            else:
                grid.attach(self.file_entry, 1, 0, 1, 1)

            self.fields_box.pack_start(grid, False, True, 0)
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


