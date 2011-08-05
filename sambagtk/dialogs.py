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
#
import sys
import os.path

import gobject
import gtk

import samba

class AboutDialog(gtk.AboutDialog):

    def __init__(self, name, description, icon):
        super(AboutDialog, self).__init__()

        self.set_name(name)
        self.set_version(samba.version)
        self.set_logo(icon)
        self.set_copyright("Copyright \xc2\xa9 2010 Sergio Martins <Sergio97@gmail.com> Copyright \xc2\xa9 2011 Dhananjay Sathe <dhananjaysathe@gmail.com>")
        self.set_authors(["Sergio Martins <Sergio97@gmail.com>", "Calin Crisan <ccrisan@gmail.com>", "Dhananjay Sathe <dhananajaysathe@gmail.com>","Jelmer Vernooij <jelmer@samba.org>"])
        self.set_comments(description)
        self.set_wrap_license(True)
        self.set_license("""
This program is free software; you can redistribute it and/or modify 
it under the terms of the GNU General Public License as published by 
the Free Software Foundation; either version 3 of the License, or 
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
GNU General Public License for more details. 

You should have received a copy of the GNU General Public License 
along with this program. If not, see <http://www.gnu.org/licenses/>.""")
