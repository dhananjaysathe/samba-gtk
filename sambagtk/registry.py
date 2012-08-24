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

"""Registry-related dialogs."""

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Pango

import os
import string
import sys

from samba.dcerpc import misc
from sambagtk.dialogs import ConnectDialog


class RegistryValue(object):

    def __init__(self, name, type, data, parent):
        self.name = name
        self.type = type
        self.data = data
        self.parent = parent

    def get_absolute_path(self):
        if self.parent is None:
            return self.name
        else:
            return self.parent.get_absolute_path() + "\\" + self.name

    def get_data_string(self):
        interpreted_data = self.get_interpreted_data()

        if interpreted_data is None or len(self.data) == 0:
            return "(value not set)"
        elif self.type in (misc.REG_SZ, misc.REG_EXPAND_SZ):
            return interpreted_data
        elif self.type == misc.REG_BINARY:
            return "".join(["%02X" % byte for byte in interpreted_data])
        elif self.type == misc.REG_DWORD:
            return "0x%08X" % (interpreted_data)
        elif self.type == misc.REG_DWORD_BIG_ENDIAN:
            return "0x%08X" % (interpreted_data)
        elif self.type == misc.REG_MULTI_SZ:
            return " ".join(interpreted_data)
        elif self.type == misc.REG_QWORD:
            return "0x%016X" % (interpreted_data)
        else:
            return str(interpreted_data)

    def get_interpreted_data(self):
        if self.data is None:
            return None

        if self.type in (misc.REG_SZ, misc.REG_EXPAND_SZ):
            result = ""

            index = 0
            while (index + 1 < len(self.data)): #The +1 ensures that the whole char is valid. Corrupt keys can otherwise cause exceptions
                word = ((self.data[index + 1] << 8) + self.data[index])
                if word != 0:
                    result += unichr(word)
                index += 2

            return result
        elif self.type == misc.REG_BINARY:
            return self.data
        elif self.type == misc.REG_DWORD:
            result = 0L

            if len(self.data) < 4:
                return 0L

            for i in xrange(4):
                result = (result << 8) + self.data[3 - i]

            return result
        elif self.type == misc.REG_DWORD_BIG_ENDIAN:
            result = 0L

            if len(self.data) < 4:
                return 0L

            for i in xrange(4):
                result = (result << 8) + self.data[i]

            return result
        elif self.type == misc.REG_MULTI_SZ:
            result = []
            string = ""

            if len(self.data) == 0:
                return []

            index = 0
            while (index < len(self.data)):
                word = ((self.data[index + 1] << 8) + self.data[index])
                if word == 0:
                    result.append(string)
                    string = ""
                else:
                    string += unichr(word)

                index += 2

            result.pop() # remove last systematic empty string

            return result
        elif self.type == misc.REG_QWORD:
            result = 0L

            if len(self.data) < 8:
                return 0L

            for i in xrange(8):
                result = (result << 8) + self.data[7 - i]

            return result
        else:
            return self.data

    def set_interpreted_data(self, data):
        del self.data[:]

        if data is None:
            self.data = None
        elif self.type in (misc.REG_SZ, misc.REG_EXPAND_SZ):
            for uch in data:
                word = ord(uch)
                self.data.append(int(word & 0x00FF))
                self.data.append(int((word >> 8) & 0x00FF))
        elif self.type == misc.REG_BINARY:
            self.data = []
            for elem in data:
                self.data.append(int(elem))
        elif self.type == misc.REG_DWORD:
            for i in xrange(4):
                self.data.append(int(data >> (8 * i) & 0xFF))
        elif self.type == misc.REG_DWORD_BIG_ENDIAN:
            for i in xrange(3, -1, -1):
                self.data.append(int(data >> (8 * i) & 0xFF))
        elif self.type == misc.REG_MULTI_SZ:
            index = 0

            for string in data:
                for uch in string:
                    word = ord(uch)
                    self.data.append(int(word & 0x00FF))
                    self.data.append(int((word >> 8) & 0x00FF))

                self.data.append(0)
                self.data.append(0)

            self.data.append(0)
            self.data.append(0)
        elif self.type == misc.REG_QWORD:
            for i in xrange(8):
                self.data.append(int(data >> (8 * i) & 0xFF))
        else:
            self.data = data

    def list_view_representation(self):
        return [self.name, RegistryValue.get_type_string(self.type),
                self.get_data_string(), self]

    @staticmethod
    def get_type_string(type):
        type_strings = {
            misc.REG_SZ:"String",
            misc.REG_BINARY:"Binary Data",
            misc.REG_EXPAND_SZ:"Expandable String",
            misc.REG_DWORD:"32-bit Number (little endian)",
            misc.REG_DWORD_BIG_ENDIAN:"32-bit Number (big endian)",
            misc.REG_MULTI_SZ:"Multi-String",
            misc.REG_QWORD:"64-bit Number (little endian)"
            }

        return type_strings[type]


class RegistryKey(object):

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.handle = None

    def get_absolute_path(self):
        if self.parent is None:
            return self.name
        else:
            return self.parent.get_absolute_path() + "\\" + self.name

    def get_root_key(self):
        if self.parent is None:
            return self
        else:
            return self.parent.get_root_key()

    def list_view_representation(self):
        return [self.name, self]


class RegValueEditDialog(Gtk.Dialog):

    def __init__(self, reg_value, type):
        super(RegValueEditDialog, self).__init__()

        if reg_value is None:
            self.brand_new = True
            self.reg_value = RegistryValue("", type, [], None)
        else:
            self.brand_new = False
            self.reg_value = reg_value

        self.disable_signals = False
        self.ascii_cursor_shift = 0 # because moving the cursor in some functions has no effect, we need to keep this value and apply it at the right time
        self.hex_cursor_shift = 0

        self.create()
        self.reg_value_to_values()

    def create(self):
        self.set_title(["Edit registry value", "New registry value"]
                      [self.brand_new])
        self.set_border_width(5)

        self.icon_registry_number_filename = os.path.join(sys.path[0],
                                            "images", "registry-number.png")
        self.icon_registry_string_filename = os.path.join(sys.path[0],
                                            "images", "registry-string.png")
        self.icon_registry_binary_filename = os.path.join(sys.path[0],
                                            "images", "registry-binary.png")

        self.set_resizable(True)
        self.set_decorated(True)
        self.set_modal(True)

        # value name
        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)

        label = Gtk.Label("Value name:")
        hbox.pack_start(label, False, True, 10)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_activates_default(True)
        self.name_entry.set_sensitive(self.brand_new)
        hbox.pack_start(self.name_entry, True, True, 10)

        separator = Gtk.HSeparator()
        self.vbox.pack_start(separator, False, True, 5)

        # data
        frame = Gtk.Frame()
        frame.set_label(" Value data: ")
        self.vbox.pack_start(frame, True, True, 10)

        self.type_notebook =Gtk.Notebook()
        self.type_notebook.set_border_width(5)
        self.type_notebook.set_show_tabs(False)
        self.type_notebook.set_show_border(False)
        frame.add(self.type_notebook)

        # string type page
        self.string_data_entry = Gtk.Entry()
        self.string_data_entry.set_activates_default(True)
        self.type_notebook.append_page(self.string_data_entry,Gtk.Label("String"))


        # binary type page
        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.ALWAYS)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.NONE)
        self.type_notebook.append_page(scrolledwindow,Gtk.Label("Binary"))

        hbox = Gtk.HBox()
        scrolledwindow.add_with_viewport(hbox)

        self.binary_data_addr_text_view = Gtk.TextView()
        self.binary_data_addr_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.binary_data_addr_text_view.set_editable(False)
        self.binary_data_addr_text_view.modify_font(Pango.FontDescription(
                                                                    "mono 10"))
        self.binary_data_addr_text_view.set_size_request(60, -1)
        hbox.pack_start(self.binary_data_addr_text_view, False, False, 0)

        self.binary_data_hex_text_view = Gtk.TextView()
        self.binary_data_hex_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.binary_data_hex_text_view.set_accepts_tab(False)
        self.binary_data_hex_text_view.modify_font(Pango.FontDescription(
                                                             "mono bold 10"))
        self.binary_data_hex_text_view.set_size_request(275, -1)
        hbox.pack_start(self.binary_data_hex_text_view, False, False, 0)

        self.binary_data_ascii_text_view = Gtk.TextView()
        self.binary_data_ascii_text_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        #self.binary_data_ascii_text_view.set_editable(False)
        self.binary_data_ascii_text_view.modify_font(Pango.FontDescription(
                                                                    "mono 10"))
        self.binary_data_ascii_text_view.set_accepts_tab(False)
        self.binary_data_ascii_text_view.set_size_request(100, -1)
        hbox.pack_start(self.binary_data_ascii_text_view, False, False, 0)


        # number type page
        hbox = Gtk.HBox()
        self.type_notebook.append_page(hbox,Gtk.Label("Number"))

        self.number_data_entry = Gtk.Entry()
        self.number_data_entry.set_activates_default(True)
        hbox.pack_start(self.number_data_entry, True, True, 5)

        self.number_data_dec_radio = \
                    Gtk.RadioButton.new_with_label_from_widget(None, "Decimal")
        hbox.pack_start(self.number_data_dec_radio, False, True, 5)

        self.number_data_hex_radio = \
                                Gtk.RadioButton.new_with_label_from_widget(
                                   self.number_data_dec_radio, "Hexadecimal")
        hbox.pack_start(self.number_data_hex_radio, False, True, 5)

        self.number_data_hex_radio.set_active(True)

        # multi-string type page
        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.IN)
        self.type_notebook.append_page(scrolledwindow,Gtk.Label("Multi-String"))

        self.multi_string_data_text_view = Gtk.TextView()
        self.multi_string_data_text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        scrolledwindow.add(self.multi_string_data_text_view)

        # dialog buttons
        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.apply_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.apply_button.set_can_default(True)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new task
        self.add_action_widget(self.apply_button, Gtk.ResponseType.APPLY)

        self.ok_button = Gtk.Button("OK", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)

        # signals/events
        self.binary_data_hex_text_view.get_buffer().connect("changed",
                            self.on_binary_data_hex_text_view_buffer_changed)
        self.binary_data_hex_text_view.get_buffer().connect("insert-text",
                        self.on_binary_data_hex_text_view_buffer_insert_text)
        self.binary_data_hex_text_view.get_buffer().connect("delete-range",
                        self.on_binary_data_hex_text_view_buffer_delete_range)

        # Ascii text view callbacks. This view requires special attention to
        # facilitate the crazy editing it needs to do
        self.binary_data_ascii_text_view.get_buffer().connect("insert-text",
                        self.on_binary_data_ascii_text_view_buffer_insert_text) #manually handles inserting text
        self.binary_data_ascii_text_view.get_buffer().connect("delete-range",
                       self.on_binary_data_ascii_text_view_buffer_delete_range) #manually handles deleting text
        self.binary_data_ascii_text_view.get_buffer().connect("changed",
                            self.on_binary_data_ascii_text_view_buffer_changed)
        self.binary_data_ascii_text_view.connect("move-cursor",
                               self.on_binary_data_ascii_text_view_move_cursor)

        self.number_data_dec_radio.connect("toggled",
                                        self.on_number_data_dec_radio_toggled)
        self.number_data_hex_radio.connect("toggled",
                                        self.on_number_data_hex_radio_toggled)
        self.number_data_entry.connect("changed",
                                            self.on_number_data_entry_changed)

    def check_for_problems(self):
        if len(self.name_entry.get_text().strip()) == 0:
            return "Please specify a name."


        elif self.reg_value.type in [misc.REG_DWORD,
                                     misc.REG_DWORD_BIG_ENDIAN,
                                     misc.REG_QWORD]:
            number_str = self.number_data_entry.get_text()
            if len(number_str) == 0:
                return "Please enter a number."

            if self.number_data_dec_radio.get_active():
                try:
                    number = string.atoi(number_str, 10)
                except Exception:
                    return "Please enter a valid decimal number."
                else:
                    number_str_hex = "%X" % number

                    if self.reg_value.type in [misc.REG_DWORD,
                                            misc.REG_DWORD_BIG_ENDIAN]:
                        max_hex_len = 8
                    else:
                        max_hex_len = 16

                    if len(number_str_hex) > max_hex_len:
                        return "Please enter a smaller decimal number."
        return None

    def reg_value_to_values(self):
        if self.reg_value is None:
            raise Exception("registry value not set")

        self.name_entry.set_text(self.reg_value.name)

        if self.reg_value.type in [misc.REG_SZ, misc.REG_EXPAND_SZ]:
            self.set_icon_from_file(self.icon_registry_string_filename)
            self.set_size_request(430, 200)

            self.string_data_entry.set_text(
                                        self.reg_value.get_interpreted_data())
        elif self.reg_value.type == misc.REG_BINARY:
            self.set_icon_from_file(self.icon_registry_binary_filename)
            self.set_size_request(483, 400) #extra few pixels for the scroll bar

            self.binary_data_hex_text_view.get_buffer().set_text(
                               RegValueEditDialog.byte_array_to_hex(
                                    self.reg_value.get_interpreted_data(), 8))
            #self.on_binary_data_hex_text_view_buffer_changed(None) #this is already called with the statement above


        elif self.reg_value.type in [misc.REG_DWORD,
                                     misc.REG_DWORD_BIG_ENDIAN,
                                     misc.REG_QWORD]:
            self.set_icon_from_file(self.icon_registry_number_filename)
            self.set_size_request(430, 200)

            if self.reg_value.type == misc.REG_QWORD:
                self.number_data_entry.set_text("%016X" %
                                        self.reg_value.get_interpreted_data())
            else:
                self.number_data_entry.set_text("%08X" %
                                        self.reg_value.get_interpreted_data())

        elif self.reg_value.type == misc.REG_MULTI_SZ:
            self.set_icon_from_file(self.icon_registry_string_filename)
            self.set_size_request(430, 400)

            text = ""
            for line in self.reg_value.get_interpreted_data():
                text += line + "\n"

            self.multi_string_data_text_view.get_buffer().set_text(text)

    def values_to_reg_value(self):
        if self.reg_value is None:
            raise Exception("registry value not set")

        self.reg_value.name = self.name_entry.get_text()

        if self.reg_value.type in [misc.REG_SZ, misc.REG_EXPAND_SZ]:
            self.reg_value.set_interpreted_data(
                                            self.string_data_entry.get_text())

        elif self.reg_value.type == misc.REG_BINARY:
            buffer = self.binary_data_hex_text_view.get_buffer()
            text = buffer.get_text(buffer.get_start_iter(),
                                  buffer.get_end_iter(),True)
            self.reg_value.set_interpreted_data(
                                    RegValueEditDialog.hex_to_byte_array(text))

        elif self.reg_value.type in [misc.REG_DWORD,
                                     misc.REG_DWORD_BIG_ENDIAN,
                                     misc.REG_QWORD]:
            if self.number_data_dec_radio.get_active():
                self.reg_value.set_interpreted_data(string.atoi(
                                        self.number_data_entry.get_text(), 10))
            else:
                self.reg_value.set_interpreted_data(string.atoi(
                                      self.number_data_entry.get_text(), 0x10))

        elif self.reg_value.type == misc.REG_MULTI_SZ:
            lines = []
            line = ""

            buffer = self.multi_string_data_text_view.get_buffer()
            for ch in buffer.get_text(buffer.get_start_iter(),
                                     buffer.get_end_iter(),True):
                if ch != "\n":
                    line += ch
                else:
                    lines.append(line)
                    line = ""

            if len(line) > 0:
                lines.append(line)

            self.reg_value.set_interpreted_data(lines)

    def update_type_page_after_show(self):
        if self.reg_value.type == misc.REG_SZ:
            self.type_notebook.set_current_page(0)
            self.string_data_entry.grab_focus()
        if self.reg_value.type == misc.REG_EXPAND_SZ:
            self.type_notebook.set_current_page(0)
            self.string_data_entry.grab_focus()
        if self.reg_value.type == misc.REG_BINARY:
            self.type_notebook.set_current_page(1)
            self.binary_data_hex_text_view.grab_focus()
        if self.reg_value.type == misc.REG_DWORD:
            self.type_notebook.set_current_page(2)
            self.number_data_entry.grab_focus()
        if self.reg_value.type == misc.REG_DWORD_BIG_ENDIAN:
            self.type_notebook.set_current_page(2)
            self.number_data_entry.grab_focus()
        if self.reg_value.type == misc.REG_MULTI_SZ:
            self.type_notebook.set_current_page(3)
            self.multi_string_data_text_view.grab_focus()
        if self.reg_value.type == misc.REG_QWORD:
            self.type_notebook.set_current_page(2)
            self.number_data_entry.grab_focus()
        if self.brand_new:
            self.name_entry.grab_focus()

    def on_binary_data_hex_text_view_buffer_changed(self, widget):
        if self.disable_signals:
            return
        self.disable_signals = True

        hex_buffer = self.binary_data_hex_text_view.get_buffer() #this is the same as 'widget'
        ascii_buffer = self.binary_data_ascii_text_view.get_buffer()
        addr_buffer = self.binary_data_addr_text_view.get_buffer()

        insert_iter = hex_buffer.get_iter_at_mark(hex_buffer.get_insert())
        insert_char_offs = insert_iter.get_offset()
        #print "cursor at:", insert_char_offs

        text = hex_buffer.get_text(hex_buffer.get_start_iter(),
                                   hex_buffer.get_end_iter(),True)
        before_len = len(text)
        text = RegValueEditDialog.check_hex_string(text).strip()
        after_len = len(text)

        hex_buffer.set_text(text)
        ascii_buffer.set_text(RegValueEditDialog.hex_to_ascii(text))
        addr_buffer.set_text(RegValueEditDialog.hex_to_addr(text))

        #print "cursor now at:", insert_char_offs + (after_len - before_len)
        hex_buffer.place_cursor(hex_buffer.get_iter_at_offset(
                                insert_char_offs + self.hex_cursor_shift))
        self.hex_cursor_shift = 0
        self.disable_signals = False

    def on_binary_data_hex_text_view_buffer_insert_text(self, widget, iter,
                                                        text, length):
        """callback for text inserted into the hex field. \nThe purpose of this function is only to update the cursor"""
        if self.disable_signals:
            return
        self.disable_signals = True

        offset = iter.get_offset()
        whole_text = widget.get_text(widget.get_start_iter(),
                                    widget.get_end_iter(),True)

        #construct the final text
        final_text = ""
        for i in range(offset):
            final_text += whole_text[i]
        for ch in text:
            final_text += ch
        for i in range(offset, len(whole_text)):
            final_text += whole_text[i]
        final_text = self.check_hex_string(final_text)

        #here we properly adjust the cursor
        count = 0
        limit = len(final_text) #it could be that the user typed an invalid character, so we'll play it safe
        for i in range(offset, offset + length + count + 1): #go through the inserted characters and see if any have been replaced by white space
            if (i < limit) and ((final_text[i] == ' ') or
                                                     (final_text[i] == '\n')):
                count += 1
        self.hex_cursor_shift = count

        self.disable_signals = False

    def on_binary_data_hex_text_view_buffer_delete_range(self, widget,
                                                        start, end):
        """callback for text inserted into the hex field. \nThe purpose of this function is only to update the cursor"""
        if (self.disable_signals):
            return
        self.disable_signals = True

        text = widget.get_text(start, end)
        if (text == ' ') or (text == '\n'):
            #if the user deleted whitespace, they probably wanted to delete whatever was before it
            new_start = widget.get_iter_at_offset(start.get_offset() - 1)
            #widget.delete(new_start, start) #if this worked as expected, programming would be too easy :P

        self.disable_signals = False

    def on_binary_data_ascii_text_view_buffer_changed(self, widget):
        """this function formats the text in the ascii field whenever it's changed"""
        if (self.disable_signals):
            return

        self.disable_signals = True
        if widget is None:
            widget = self.binary_data_ascii_text_view.get_buffer()

        #stuff we need to move the cursor properly later
        cursor_iter = widget.get_iter_at_mark(widget.get_insert()) #insert means cursor, or "the insertion point" as gtk calls it
        cursor_offset = cursor_iter.get_offset()

        text = widget.get_text(widget.get_start_iter(),
                              widget.get_end_iter(),True)
        text = self.check_ascii_string(text)
        widget.set_text(text)

        #Calling this function below will translate the hex back into our ascii box, making errors easier to spot
        self.disable_signals = False
        self.on_binary_data_hex_text_view_buffer_changed(None)
        self.disable_signals = True

        #now that we've overwritten everything in the textbuffer, we have to put the cursor back in the same spot
        widget.place_cursor(widget.get_iter_at_offset(cursor_offset +
                                                     self.ascii_cursor_shift))
        self.ascii_cursor_shift = 0

        self.disable_signals = False

    def on_binary_data_ascii_text_view_buffer_insert_text(self, widget, iter,
                                                         text, length):
        if (self.disable_signals):
            return
        self.disable_signals = True
        if widget is None:
            widget = self.binary_data_ascii_text_view.get_buffer()

        #get stuff that we need
        offset = iter.get_offset()
        inclusive_text = widget.get_text(widget.get_start_iter(), iter, True)
        hex_pos = int(iter.get_offset() * 3) #because each ascii character is 2 hex characters, plus a space
        hex_pos -= inclusive_text.count('\n') * 2 #because '\n' counts as a character, but it doesn't take up 3 spaces in the hex string.
        hex_buffer = self.binary_data_hex_text_view.get_buffer()
        addr_buffer = self.binary_data_addr_text_view.get_buffer()
        hex_text = hex_buffer.get_text(hex_buffer.get_start_iter(),
                                       hex_buffer.get_end_iter(), True)

        #insert into hex_text up to the point where the new character was inserted
        new_hex = ""
        for ch in hex_text: #this works best because the hex_pos can be greater than len(hex_text) when inserting at the end
            if len(new_hex) >= hex_pos:
                break
            new_hex += ch
        #insert the new character(s)
        for i in range(length):
            new_hex += "%X" % ((ord(text[i]) >> 4) & 0x0F) #handle the upper 4 bits of the char
            new_hex += "%X " % (ord(text[i]) & 0x0F)       #handle the lower 4 bits of the char
        #insert the rest of the old characters into new_hex
        while hex_pos < len(hex_text):
            new_hex += hex_text[hex_pos]
            hex_pos += 1
        new_hex = self.check_hex_string(new_hex)

        #here we properly adjust the cursor
        final_text = self.hex_to_ascii(new_hex)
        count = 0
        for i in range(offset, offset + length + count): #go through the inserted characters and see if any have been replaced by '\n's
            if (final_text[i] == '\n'):
                count += 1
        hex_buffer.set_text(new_hex) #set the text
        self.ascii_cursor_shift = count #tell the on_changed() function to shift the cursor, since it has no effect if we call place_cursor() from here
        addr_buffer.set_text(self.hex_to_addr(new_hex)) #can't forget to update the address text!
        self.disable_signals = False

    def on_binary_data_ascii_text_view_buffer_delete_range(self, widget,
                                                          start, end):
        if (self.disable_signals):
            return
        self.disable_signals = True

        #get stuff that we need
        text = widget.get_text(start, end, True)
        beginning_text = widget.get_text(widget.get_start_iter(), start, True)
        inclusive_text = widget.get_text(widget.get_start_iter(), end, True)
        hex_buffer = self.binary_data_hex_text_view.get_buffer()
        addr_buffer = self.binary_data_addr_text_view.get_buffer()
        hex_text = hex_buffer.get_text(hex_buffer.get_start_iter(),
                                       hex_buffer.get_end_iter(),True)
        new_end_iter = None #this will tell us if any extra characters need to be deleted later

        if text == '\n': #we assume that the user pressed backspace and NOT delete. We don't get any indicator of which key was pressed so without adding another complex function, this is the best we can do
            new_end_iter = start #so later we can delete from a new start to the current start
            start = widget.get_iter_at_offset(start.get_offset() - 1) #also delete the character before the '\n'

        #Adjust the values for use in the hex field. this is basically the same as count('\n') + 1
        hex_start = int(start.get_offset() * 3) #because each ascii character is 2 hex characters, plus a space
        hex_start -= beginning_text.count('\n') * 2 #because '\n' counts as a character, but it doesn't take up 3 spaces in the hex string.
        hex_end = int(end.get_offset() * 3)
        hex_end -= inclusive_text.count('\n') * 2

        new_hex = ""
        #insert into hex_text up to the point where characters were deleted
        for i in range(hex_start):
            new_hex += hex_text[i]
        #insert the characters after the deleted characters. We simply ignore the deleted characters
        for i in range(hex_end, len(hex_text)):
            new_hex += hex_text[i]

        hex_buffer.set_text(RegValueEditDialog.check_hex_string(new_hex)) #set the text
        addr_buffer.set_text(RegValueEditDialog.hex_to_addr(new_hex)) #can't forget to update the address text!

        if (new_end_iter is not None):
            widget.delete(start, new_end_iter) #this causes a warning because of bad iterators! Makes no sense

        self.disable_signals = False

    def on_binary_data_ascii_text_view_move_cursor(self, textview, step_size,
                                                    count, extend_selection):
        """This function handles cursor movement. For now it only responds to text selection"""
        print "ext_sel", extend_selection
        #The following doesn't work... even if extend_selection is true, get_selection_bounds() still returns nothing
#        if (not extend_selection) or (self.disable_signals):
#            return
#        self.disable_signals = True
#
#        #get stuff we need
#        ascii_buffer = textview.get_buffer()
#        (start, end) = ascii_buffer.get_selection_bounds() #This function returns 2 iterators
#        hex_buffer = self.binary_data_hex_text_view.get_buffer()
#
#        hex_start = int(start.get_offset() * 3) #because each ascii character is 2 hex characters, plus a space
#        hex_start -= (hex_start/25) * 2 #because '\n' counts as a character, but it doesn't take up 3 spaces in the hex string.
#        hex_end = int(end.get_offset() * 3)
#        hex_end -= (hex_end/25) * 2
#        hex_buffer.select_range(hex_buffer.get_iter_at_offset(hex_start), hex_buffer.get_iter_at_offset(hex_end))
#
#        self.disable_signals = False

    def on_number_data_hex_radio_toggled(self, widget):
        if (not widget.get_active()):
            return

        if (self.reg_value.type == misc.REG_QWORD):
            digits = 16
        else:
            digits = 8

        number_str = self.number_data_entry.get_text()
        if (len(number_str) == 0):
            number_str = "0"

        number = string.atoi(number_str, 10)

        format = "%0" + str(digits) + "X"

        self.number_data_entry.set_text(format % number)

    def on_number_data_dec_radio_toggled(self, widget):
        if (not widget.get_active()):
            return

        if (self.reg_value.type == misc.REG_QWORD):
            digits = 16
        else:
            digits = 8

        number_str = self.number_data_entry.get_text()
        if (len(number_str) == 0):
            number_str = "0"

        number = string.atoi(number_str, 0x10)

        format = "%0" + str(digits) + "d"

        self.number_data_entry.set_text(format % number)

    def on_number_data_entry_changed(self, widget):
        old_text = self.number_data_entry.get_text()

        if (self.reg_value.type in [misc.REG_DWORD,misc.REG_DWORD_BIG_ENDIAN]):
            max_len = 8
        else:
            max_len = 16

        new_text = ""
        if (self.number_data_hex_radio.get_active()):
            for ch in old_text:
                if (ch in string.hexdigits):
                    new_text += ch
            if (len(new_text) > max_len):
                new_text = new_text[:max_len]

        else:
            for ch in old_text:
                if (ch in string.digits):
                    new_text += ch

        self.number_data_entry.set_text(new_text)


    @staticmethod
    def remove_string_white_space(str):
        return string.join(str.split(), "")

    @staticmethod
    def check_hex_string(old_string, line_length=8, remove_orphaned = False):
        new_string = ""
        length = 0
        insert_space = False
        for ch in old_string:
            if (ch in string.hexdigits):
                new_string += string.upper(ch)
                if (insert_space):
                    new_string += " "
                    length += 1
                insert_space = not insert_space

            if (length >= line_length):
                new_string += "\n"
                length = 0

        if (insert_space and remove_orphaned):
            new_string = new_string.strip()[:len(new_string) - 1]

        return new_string

    @staticmethod
    def check_ascii_string(string, line_length=8):
        new_string = ""
        digits = ""
        length = 0
        #insert a '\n' every line_length characters.
        for ch in string:
            if ch != '\n': #ignore carrage returns alreadys present
                new_string += ch
                length += 1
                if (length >= line_length):
                    new_string += "\n"
                    length = 0

        return new_string.strip()

    @staticmethod
    def hex_to_ascii(hex_string, line_length=8):
        ascii_string = ""

        digits = ""
        length = 0
        for ch in hex_string:
            if (ch in string.hexdigits):
                digits += ch

            if (len(digits) >= 2):
                new_chr = chr(string.atol(digits, 0x10))
                if (new_chr in (string.punctuation +
                                string.digits +
                                string.ascii_letters + ' ')): #We don't just use string.printables because that inclues '\n' and '\r' which we don't want to put into the ascii box
                    ascii_string += new_chr
                else:
                    ascii_string += "."
                length += 1
                digits = ""

            if (length >= line_length):
                ascii_string += "\n"
                length = 0

        return ascii_string

    @staticmethod
    def hex_to_addr(old_string, line_length=8):
        new_string = ""

        digits = ""
        length = 0
        addr = 0
        for ch in old_string:
            if (ch in string.hexdigits):
                digits += ch

            if (len(digits) >= 2):

                if (length % line_length) == 0:
                    new_string += "%04X\n" % addr
                    addr += line_length

                length += 1
                digits = ""

        return new_string

    @staticmethod
    def byte_array_to_hex(array, line_length=8):
        new_string = ""

        for byte in array:
            new_string += "%02x" % byte

        return RegValueEditDialog.check_hex_string(new_string,
                                                  line_length, False)

    @staticmethod
    def hex_to_byte_array(hex_string):
        array = []

        digits = ""
        for ch in hex_string:
            if (ch in string.hexdigits):
                digits += ch

            if (len(digits) >= 2):
                byte = string.atol(digits, 0x10)
                array.append(byte)
                digits = ""

        return array


class RegKeyEditDialog(Gtk.Dialog):

    def __init__(self, reg_key):
        super(RegKeyEditDialog, self).__init__()

        if (reg_key is None):
            self.brand_new = True
            self.reg_key = RegistryKey("", None)

        else:
            self.brand_new = False
            self.reg_key = reg_key

        self.create()
        self.reg_key_to_values()

    def create(self):
        self.set_title(["Edit registry key", "New registry key"]
                      [self.brand_new])
        self.set_border_width(5)

        self.icon_registry_filename = os.path.join(sys.path[0],
                                    "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.set_resizable(False)
        self.set_decorated(True)
        self.set_modal(True)

        # value name

        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)

        label = Gtk.Label("Key name:")
        hbox.pack_start(label, False, True, 10)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_activates_default(True)
        hbox.pack_start(self.name_entry, True, True, 10)


        # dialog buttons

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.apply_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.apply_button.set_can_default(True)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new task
        self.add_action_widget(self.apply_button, Gtk.ResponseType.APPLY)

        self.ok_button = Gtk.Button("OK", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)


        # signals/events

    def check_for_problems(self):
        if (len(self.name_entry.get_text().strip()) == 0):
            return "Please specify a name."

        return None

    def reg_key_to_values(self):
        if (self.reg_key is None):
            raise Exception("registry key not set")

        self.name_entry.set_text(self.reg_key.name)

    def values_to_reg_key(self):
        if (self.reg_key is None):
            raise Exception("registry key not set")

        self.reg_key.name = self.name_entry.get_text()


class RegRenameDialog(Gtk.Dialog):

    def __init__(self, reg_key, reg_value):
        super(RegRenameDialog, self).__init__()

        self.reg_key = reg_key
        self.reg_value = reg_value

        self.create()
        self.reg_to_values()

    def create(self):
        self.set_title(["Rename registry key", "Rename registry value"][self.reg_value is not None])
        self.set_border_width(5)

        self.icon_registry_filename = os.path.join(sys.path[0], "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.set_resizable(False)
        self.set_decorated(True)
        self.set_modal(True)


        # name

        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)

        label = Gtk.Label("Name:")
        hbox.pack_start(label, False, True, 10)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_activates_default(True)
        hbox.pack_start(self.name_entry, True, True, 10)


        # dialog buttons

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.apply_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.apply_button.set_can_default(True)
        self.add_action_widget(self.apply_button, Gtk.ResponseType.APPLY)

        self.ok_button = Gtk.Button("OK", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)


        # signals/events

    def check_for_problems(self):
        if (len(self.name_entry.get_text().strip()) == 0):
            return "Please specify a name."
        return None

    def reg_to_values(self):
        if (self.reg_key is None):
            self.name_entry.set_text(self.reg_value.name)
        else:
            self.name_entry.set_text(self.reg_key.name)

    def values_to_reg(self):
        if (self.reg_key is None):
            self.reg_value.name = self.name_entry.get_text()
        else:
            self.reg_key.name = self.name_entry.get_text()

class RegSearchDialog(Gtk.Dialog):

    def __init__(self):
        super(RegSearchDialog, self).__init__()

        self.warned = False

        self.create()

    def create(self):
        self.set_title("Search the registry")
        self.set_border_width(5)

        self.icon_registry_filename = os.path.join(sys.path[0], "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.set_resizable(False)
        self.set_decorated(True)
        self.set_modal(True)


        # name

        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)

        label = Gtk.Label("Search for: ")
        hbox.pack_start(label, False, True, 10)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_activates_default(True)
        hbox.pack_start(self.search_entry, True, True, 10)


        # options

        frame = Gtk.Frame()
        frame.set_label("Match:")
        self.vbox.pack_start(frame, False, True, 0)

        vbox = Gtk.VBox()
        vbox.set_border_width(4)
        frame.add(vbox)

        self.check_match_keys = Gtk.CheckButton("Keys")
        self.check_match_keys.set_active(True)
        vbox.pack_start(self.check_match_keys, False, False, 0)
        self.check_match_values = Gtk.CheckButton("Values")
        self.check_match_values.set_active(True)
        vbox.pack_start(self.check_match_values, False, False, 0)
        self.check_match_data = Gtk.CheckButton("Data")
        self.check_match_data.set_active(True)
        vbox.pack_start(self.check_match_data, False, False, 0)

        self.check_match_whole_string = Gtk.CheckButton("Match whole string only")
        self.vbox.pack_start(self.check_match_whole_string, False, False, 5)


        # dialog buttons

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.ok_button = Gtk.Button("Search", Gtk.STOCK_FIND)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.set_default_response(Gtk.ResponseType.OK)


        # signals/events

    def check_for_problems(self):
        if self.search_entry.get_text() == "":
            return ("You must enter text to search for!",Gtk.MessageType.ERROR)
        elif not ( self.check_match_data.get_active() and
                   not self.check_match_keys.get_active() and
                   not self.check_match_values.get_active()):
            errmsg = "You much select at least one of: keys, values, or data to search"
            return (errmsg, Gtk.MessageType.ERROR)
        elif not self.check_match_whole_string.get_active() and not self.warned:
            for ch in self.search_entry.get_text():
                if ch in string.punctuation:
                    self.warned = True
                    errmsg = "Search items should be separated by a space. Punctuation (such as commas) will be considered part of the search string.\n\nPress find again to continue anyways."
                    return (errmsg, Gtk.MessageType.INFO)

        return None

class RegPermissionsDialog(Gtk.Dialog):

    def __init__(self, users, permissions):
        super(RegPermissionsDialog, self).__init__()

        self.users = users
        self.permissions = permissions

        self.create()

        if users is not None:
            for user in users:
                self.user_store.append((user.username,
                                        user,))

    def create(self):
        self.set_title("Permissions")
        self.set_border_width(5)
        self.set_default_size(380, 480)

        self.icon_registry_filename = os.path.join(sys.path[0],
                                    "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.set_resizable(True)
        self.set_decorated(True)
        self.set_modal(True)



        # Groups/Users area

        vbox = Gtk.VBox()
        self.vbox.pack_start(vbox, True, True, 10)

        label = Gtk.Label("Users:", xalign = 0 , yalign =1 )
        vbox.pack_start(label, False, False, 0)

        hpaned = Gtk.HPaned()
        vbox.pack_start(hpaned, True, True, 0)

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.IN)
        hpaned.add1(scrolledwindow)

        self.user_tree_view = Gtk.TreeView()
        self.user_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.user_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("User")
        column.set_resizable(True)
        column.set_fixed_width(200)
        column.set_sort_column_id(0)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.user_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.user_store = Gtk.ListStore(GObject.TYPE_STRING,
                                       GObject.TYPE_PYOBJECT)
        self.user_tree_view.set_model(self.user_store)

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)

        padding = Gtk.HBox()
        hbox.pack_start(padding, True, True, 0)

        self.add_button = Gtk.Button("Add", Gtk.STOCK_ADD)
        hbox.pack_start(self.add_button, False, False, 2)

        self.remove_button = Gtk.Button("Remove", Gtk.STOCK_REMOVE)
        hbox.pack_start(self.remove_button, False, False, 2)



        #Permissions area

        vbox = Gtk.VBox()
        self.vbox.pack_start(vbox, True, True, 10)

        self.permissions_label = Gtk.Label(label="Permissions for UNKNOWN USER/GROUP:",
                                        xalign= 0, yalign= 1 )
        vbox.pack_start(self.permissions_label, False, False, 0)

        hpaned = Gtk.HPaned()
        vbox.pack_start(hpaned, True, True, 0)

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.IN)
        hpaned.add1(scrolledwindow)

        self.permissions_tree_view = Gtk.TreeView()
        scrolledwindow.add(self.permissions_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("Permission")
        column.set_resizable(True)
        column.set_min_width(160)
        column.set_sort_column_id(0)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        column = Gtk.TreeViewColumn()
        column.set_title("Allow")
        column.set_resizable(False)
        column.set_fixed_width(30)
        column.set_sort_column_id(1)
        renderer = Gtk.CellRendererToggle()
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)

        column = Gtk.TreeViewColumn()
        column.set_title("Deny")
        column.set_resizable(False)
        column.set_fixed_width(30)
        column.set_sort_column_id(2)
        renderer = Gtk.CellRendererToggle()
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)

        self.permissions_store = Gtk.ListStore(GObject.TYPE_STRING,
                                              GObject.TYPE_BOOLEAN,
                                              GObject.TYPE_BOOLEAN,
                                              GObject.TYPE_PYOBJECT)
        self.permissions_tree_view.set_model(self.permissions_store)

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)

        padding = Gtk.HBox()
        hbox.pack_start(padding, True, True, 0)

        self.advanced_button = Gtk.Button("Advanced")
        hbox.pack_start(self.advanced_button, False, False, 2)



        # dialog buttons

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.ok_button = Gtk.Button("Ok", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.ok_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.APPLY)

        self.set_default_response(Gtk.ResponseType.APPLY)




        # signals/events

        self.user_tree_view.get_selection().connect("changed",
                                    self.on_user_tree_view_selection_changed)
        self.add_button.connect("clicked", self.on_add_item_activate)
        self.remove_button.connect("clicked", self.on_remove_item_activate)

        #TODO: permission view data editing updates the store?
        self.advanced_button.connect("clicked", self.on_advanced_item_activate)

    def check_for_problems(self):
        #TODO: find problems?
        return None

    def on_user_tree_view_selection_changed(self, widget):
        self.permissions_store.clear()

        (iter, user) = self.get_selected_user()

        if (iter is not None):
            self.permissions_label.set_text('',join(["Permissions for ",
                                                    user.username,":"]))
            #TODO: update permissions view on selection changed
        else:
            self.permissions_label.set_text("")

    def on_add_item_activate(self, widget):
        #TODO: implement add user for permissions
        pass

    def on_remove_item_activate(self, widget):
        (iter, user) = self.get_selected_user()

        if (iter is not None):
            self.users.remove(user)
            self.user_store.remove(iter)
            #TODO: remove user permissions?

    def on_advanced_item_activate(self, widget):
        dialog = RegAdvancedPermissionsDialog(None, None)
        dialog.show_all()
        #TODO: handle advanced dialog
        dialog.run()
        dialog.hide_all()


    def get_selected_user(self):
        (model, iter) = self.user_tree_view.get_selection().get_selected()
        if (iter is None): # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 1))

class RegAdvancedPermissionsDialog(Gtk.Dialog):
    def __init__(self, users, permissions):
        super(RegAdvancedPermissionsDialog, self).__init__()

        self.users = users
        self.permissions = permissions

        self.create()

        self.insert_test_values() #TODO: remove

        #update sensitivity
        self.on_auditing_tree_view_selection_changed(None)
        self.on_permissions_tree_view_selection_changed(None)

    def create(self):
        self.set_title("Permissions")
        self.set_border_width(5)
        self.set_resizable(True)
        self.set_decorated(True)
        self.set_modal(True)
        self.set_default_size(630, 490)

        self.icon_registry_filename = os.path.join(sys.path[0],
                                    "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.notebook = Gtk.Notebook()
        self.vbox.pack_start(self.notebook, True, True, 0)



        # Permissions tab

        hbox = Gtk.HBox() #hbox is for the padding on the left & right.
        self.notebook.append_page(hbox, Gtk.Label("Permissions"))

        vbox = Gtk.VBox()
        hbox.pack_start(vbox, True, True, 10)

        label = Gtk.Label("To view the details of special permissions entries, select it and then click Edit.\n",
                         xalign= 0 , yalign= 0)
        vbox.pack_start(label, False, False, 15)

        label = Gtk.Label(label="Permission entries:",xalign= 0 , yalign= 1)
        vbox.pack_start(label, False, False, 0)

        hpaned = Gtk.HPaned()
        vbox.pack_start(hpaned, True, True, 0)

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.IN)
        hpaned.add1(scrolledwindow)

        self.permissions_tree_view = Gtk.TreeView()
        scrolledwindow.add(self.permissions_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("Type")
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        column = Gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(1)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        column = Gtk.TreeViewColumn()
        column.set_title("Permission")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(2)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        column = Gtk.TreeViewColumn()
        column.set_title("Inherited from")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(3)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)

        column = Gtk.TreeViewColumn()
        column.set_title("Applies to")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(4)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.permissions_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 4)

        #Store contains: type (string), name (string), permission (string), inherited from (string), apply to (string, permissions (object)
        self.permissions_store = Gtk.ListStore(GObject.TYPE_STRING,
                                              GObject.TYPE_STRING,
                                              GObject.TYPE_STRING,
                                              GObject.TYPE_STRING,
                                              GObject.TYPE_STRING,
                                              GObject.TYPE_PYOBJECT)
        self.permissions_tree_view.set_model(self.permissions_store)

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)

        padding = Gtk.HBox()
        hbox.pack_start(padding, True, True, 0)

        self.add_button_permissions = Gtk.Button("Add", Gtk.STOCK_ADD)
        hbox.pack_start(self.add_button_permissions, False, False, 2)

        self.edit_button_permissions = Gtk.Button("Edit", Gtk.STOCK_EDIT)
        hbox.pack_start(self.edit_button_permissions, False, False, 2)

        self.remove_button_permissions = Gtk.Button("Remove", Gtk.STOCK_REMOVE)
        hbox.pack_start(self.remove_button_permissions, False, False, 2)

        check_area = Gtk.VBox()
        vbox.pack_start(check_area, False, False, 10)

        self.check_inherit_permissions = Gtk.CheckButton(
               "Inherit permissions from parents that apply to child objects.")
        check_area.pack_start(self.check_inherit_permissions, False, False, 0)

        hbox = Gtk.HBox()
        check_area.pack_start(hbox, False, False, 0)

        self.replace_child_permissions_button = Gtk.Button(
                                                "Replace child permissions")
        hbox.pack_start(self.replace_child_permissions_button, False, False, 0)



        # Auditing tab

        hbox = Gtk.HBox() #hbox is for the padding on the left & right.
        self.notebook.append_page(hbox, Gtk.Label("Auditing"))

        vbox = Gtk.VBox()
        hbox.pack_start(vbox, True, True, 10)

        label = Gtk.Label("To view the details of special auditing entries, select it and then click Edit.\n",
                         xalign= 0, yalign= 0)
        vbox.pack_start(label, False, False, 15)

        label = Gtk.Label("Auditing entries:", xalign= 0, yalign= 1)
        vbox.pack_start(label, False, False, 0)

        hpaned = Gtk.HPaned()
        vbox.pack_start(hpaned, True, True, 0)

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.IN)
        hpaned.add1(scrolledwindow)

        self.auditing_tree_view = Gtk.TreeView()
        scrolledwindow.add(self.auditing_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("Type")
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.auditing_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        column = Gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(1)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.auditing_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        column = Gtk.TreeViewColumn()
        column.set_title("Permission")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(2)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.auditing_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        column = Gtk.TreeViewColumn()
        column.set_title("Inherited from")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(3)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.auditing_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)

        column = Gtk.TreeViewColumn()
        column.set_title("Applies to")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(4)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.auditing_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 4)

        self.auditing_store = Gtk.ListStore(GObject.TYPE_STRING,
                                            GObject.TYPE_STRING,
                                            GObject.TYPE_STRING,
                                            GObject.TYPE_STRING,
                                            GObject.TYPE_STRING,
                                            GObject.TYPE_PYOBJECT)
        self.auditing_tree_view.set_model(self.auditing_store)

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)

        padding = Gtk.HBox()
        hbox.pack_start(padding, True, True, 0)

        self.add_button_auditing = Gtk.Button("Add", Gtk.STOCK_ADD)
        hbox.pack_start(self.add_button_auditing, False, False, 2)

        self.edit_button_auditing = Gtk.Button("Edit", Gtk.STOCK_EDIT)
        hbox.pack_start(self.edit_button_auditing, False, False, 2)

        self.remove_button_auditing = Gtk.Button("Remove", Gtk.STOCK_REMOVE)
        hbox.pack_start(self.remove_button_auditing, False, False, 2)

        check_area = Gtk.VBox()
        vbox.pack_start(check_area, False, False, 10)

        self.check_inherit_auditing = Gtk.CheckButton(
          "Inherit auditing options from parents that apply to child objects.")
        check_area.pack_start(self.check_inherit_auditing, False, False, 0)

        hbox = Gtk.HBox()
        check_area.pack_start(hbox, False, False, 0)

        self.replace_child_auditing_button = Gtk.Button(
                                            "Replace child auditing options")
        hbox.pack_start(self.replace_child_auditing_button, False, False, 0)





        # Ownership tab

        hbox = Gtk.HBox() #hbox is for the padding on the left & right.
        self.notebook.append_page(hbox, Gtk.Label(label="Ownership"))

        vbox = Gtk.VBox()
        hbox.pack_start(vbox, True, True, 10)


        label = Gtk.Label("You may take ownership of an object if you have the appropriate permissions.\n",
                         xalign= 0 , yalign= 0)
        vbox.pack_start(label, False, False, 15)

        label = Gtk.Label(label="Current owner of this item:",
                         xalign= 0 , yalign= 1)
        vbox.pack_start(label, False, False, 0)

        textview = Gtk.Entry()
        textview.set_editable(False)
        vbox.pack_start(textview, False, False, 0)

        label = Gtk.Label(label="Change owner to:",xalign= 0 , yalign= 1)
        vbox.pack_start(label, False, False, 0)

        hpaned = Gtk.HPaned()
        vbox.pack_start(hpaned, True, True, 0)

        scrolledwindow = Gtk.ScrolledWindow(None, None)
        scrolledwindow.set_shadow_type(Gtk.ShadowType.IN)
        hpaned.add1(scrolledwindow)

        self.owner_tree_view = Gtk.TreeView()
        self.owner_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.owner_tree_view)

        column = Gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_fixed_width(200)
        column.set_sort_column_id(0)
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        self.owner_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.owner_store = Gtk.ListStore(GObject.TYPE_STRING,
                                        GObject.TYPE_PYOBJECT)
        self.owner_tree_view.set_model(self.owner_store)

        self.check_replace_owner_child_objects = Gtk.CheckButton(
                                        "Replace ownership of child objects")
        vbox.pack_start(self.check_replace_owner_child_objects,False, False,10)



        # dialog buttons

        self.action_area.set_layout(Gtk.ButtonBoxStyle.END)

        self.cancel_button = Gtk.Button("Cancel", Gtk.STOCK_CANCEL)
        self.cancel_button.set_can_default(True)
        self.add_action_widget(self.cancel_button, Gtk.ResponseType.CANCEL)

        self.ok_button = Gtk.Button("Ok", Gtk.STOCK_OK)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.OK)

        self.ok_button = Gtk.Button("Apply", Gtk.STOCK_APPLY)
        self.ok_button.set_can_default(True)
        self.add_action_widget(self.ok_button, Gtk.ResponseType.APPLY)

        self.set_default_response(Gtk.ResponseType.APPLY)

        # TODO: Effective permissions

        # signals/events
        self.permissions_tree_view.get_selection().connect("changed",
                               self.on_permissions_tree_view_selection_changed)
        self.auditing_tree_view.get_selection().connect("changed",
                                  self.on_auditing_tree_view_selection_changed)

        self.add_button_permissions.connect("clicked",
                                        self.on_add_permissions_button_clicked)
        self.edit_button_permissions.connect("clicked",
                                       self.on_edit_permissions_button_clicked)
        self.remove_button_permissions.connect("clicked",
                                     self.on_remove_permissions_button_clicked)
        self.replace_child_permissions_button.connect("clicked",
                                    self.on_replace_permissions_button_clicked)
        self.add_button_auditing.connect("clicked",
                                           self.on_add_auditing_button_clicked)
        self.edit_button_auditing.connect("clicked",
                                          self.on_edit_auditing_button_clicked)
        self.remove_button_auditing.connect("clicked",
                                        self.on_remove_auditing_button_clicked)
        self.replace_child_auditing_button.connect("clicked",
                                       self.on_replace_auditing_button_clicked)

        self.check_inherit_permissions.connect("clicked",
                                     self.on_check_inherit_permissions_changed)
        self.check_inherit_auditing.connect("clicked",
                                        self.on_check_inherit_auditing_changed)



    def insert_test_values(self):
        #TODO: remove this function when no longer needed
        self.check_inherit_permissions.set_active(True)
        self.check_inherit_auditing.set_active(True)

        user = User("Foo Bar", "", "", 0)
        self.permissions_store.append(("Allow", user.username,
                    "Special Permissions", "Unicorns", "This key only", user))
        self.permissions_store.append(("Deny", "Pib", "Access to Playdoe",
                                  "HKEY_USERS", "This key and subkeys", user))

        self.auditing_store.append(("Deny", "Homer Simpson", "Double Rainbow",
                                  "HKEY_LOCAL_MACHINE\\made up key\\temp\\new",
                                  "This key and subkeys", user))
        self.auditing_store.append(("Allow", "Administrator",
                                    "Your Right to Party", "Earthworm Jim",
                                    "This key only", user))

    def get_selected_permission(self):
        (model, iter) = self.permissions_tree_view.get_selection().get_selected()
        if (iter is None): # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 1))

    def get_selected_audit(self):
        (model, iter) = self.auditing_tree_view.get_selection().get_selected()
        if iter is None: # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 1))

    def on_permissions_tree_view_selection_changed(self, widget):
        (iter, permission) = self.get_selected_permission()
        self.edit_button_permissions.set_sensitive(permission is not None)
        self.remove_button_permissions.set_sensitive(permission is not None)

    def on_auditing_tree_view_selection_changed(self, widget):
        (iter, audit) = self.get_selected_audit()
        self.edit_button_auditing.set_sensitive(audit is not None)
        self.remove_button_auditing.set_sensitive(audit is not None)

    def on_add_permissions_button_clicked(self, widget):
        #TODO: this
        pass

    def on_edit_permissions_button_clicked(self, widget):
        #TODO: this
        pass

    def on_remove_permissions_button_clicked(self, widget):
        (iter, permission) = self.get_selected_permission()
        if (iter is not None):
            self.permissions_store.remove(iter)

    def on_replace_permissions_button_clicked(self, widget):
        #TODO: this
        pass

    def on_add_auditing_button_clicked(self, widget):
        #TODO: this
        pass

    def on_edit_auditing_button_clicked(self, widget):
        #TODO: this
        pass

    def on_remove_auditing_button_clicked(self, widget):
        (iter, audit) = self.get_selected_audit()
        if (iter is not None):
            self.auditing_store.remove(iter)

    def on_replace_auditing_button_clicked(self, widget):
        #TODO: this
        pass

    def on_check_inherit_permissions_changed(self, widget):
        if widget.get_active():
            return
        #TODO: if no permissions are inherited

        message = "Unchecking this option means auditing options inherited from the parent object will be lost.\n\nDo you want to copy the inherited auditing options for this object?"
        message_box = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.QUESTION,
                                       Gtk.ButtonsType.YES_NO, message)
        response = message_box.run()
        message_box.hide()

        if (response == Gtk.ResponseType.YES):
            #TODO: copy permissions from the parent object
            pass
        elif (response == Gtk.ResponseType.NO):
            #TODO: delete all inherited permissions from the permissions store
            pass
        else:#probably Gtk.ResponseType.DELETE_EVENT (from pressing escape)
            widget.set_active(True)


    def on_check_inherit_auditing_changed(self, widget):
        if widget.get_active():
            return
        #TODO: if no permissions are inherited

        message = "Unchecking this option means auditing options inherited from the parent object will be lost.\n\nDo you want to copy the inherited auditing options for this object?"
        message_box = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                                       Gtk.MessageType.QUESTION,
                                       Gtk.ButtonsType.YES_NO, message)
        response = message_box.run()
        message_box.hide()

        if response == Gtk.ResponseType.YES:
            #TODO: copy auditing from the parent object
            pass
        elif response == Gtk.ResponseType.NO:
            #TODO: delete all inherited auditing from the permissions store
            pass
        else:#probably Gtk.ResponseType.DELETE_EVENT (from pressing escape)
            widget.set_active(True)


class WinRegConnectDialog(ConnectDialog):

    def __init__(self, server, transport_type, username, password):

        super(WinRegConnectDialog, self).__init__(
                    server, transport_type, username, password)
        self.set_title('Connect to Server')

