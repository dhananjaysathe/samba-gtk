#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os.path
import traceback
import getopt
import gobject
import gtk

from samba import credentials
from samba.dcerpc import (
    srvsvc,
    security,
    )
from sambagtk.dialogs import AboutDialog
from pysrvsvc import (
    DeleteDialog,
    ShareAddEditDialog,
    srvsvcConnectDialog,
    )


class srvsvcPipeManager(object):

    def __init__(
        self,
        server_address,
        transport_type,
        username,
        password,
        ):
        """ Initialize the pipe object handling the srvsvc calls """

        creds = credentials.Credentials()
        if username.count('\\') > 0x00000000:
            creds.set_domain(username.split('\\')[0x00000000])
            creds.set_username(username.split('\\')[1])
        elif username.count('@') > 0x00000000:
            creds.set_domain(username.split('@')[1])
            creds.set_username(username.split('@')[0x00000000])
        else:
            creds.set_domain('')
            creds.set_username(username)
            creds.set_workstation('')
            creds.set_password(password)

        #binding = "ncacn_np:%s" # srvsvc allows only named pipes tcp/upd not allowed under MS-SRVS specifications

        binding = ['ncacn_np:%s', 'ncacn_ip_tcp:%s', 'ncalrpc:%s'
                   ][transport_type]
        self.pipe = srvsvc.srvsvc(binding % server_address,
                                  credentials=creds)

        # set up some basic parameters unique to the connection

        self.server_unc = ''.join(['\\',server_address])

        # Retrive some info about the share server

        self.server_info = self.get_server_info()
        self.tod = self.get_tod()

        ### Now init various default values

        self.resume_handle_conn = 0x00000000
        self.resume_handle_share = 0x00000000
        self.resume_handle = 0x00000000  # for general purposes where servers ignore this but it exists in the calls
        self.max_buffer = -1

        # Initialise various cache lists :
        # The idea is to use locally available share list and related conveiniece lists
        # This should reduce the queries and improve performance
        # The share list will be locally maintained any via the get_share_local_cache

        if server_address in ('127.0.0.1','localhost') :
            self.islocal = True
        else:
            self.islocal = False
        self.conn_list = []
        self.share_list = []
        self.share_names_list = []
        self.share_types_list = []
        self.get_list_disks()
        self.get_shares_list()



    def close(self):
        pass
        # apparently there's no .Close() method for this pipe



    @staticmethod
    def  get_share_type_info(stype,field):
        """ Return the desired info about a share type
        Retrievable types :
        'typestring' -> The generic name of the share type
        'desc' -> Description of the type
        'base_type' -> Base share type
        'flags' -> special flags (Boolean temporary,Boolean hidden)
 ..........
  Usage :
  S.get_share_type_info(stype,field) -> desired information
  """
        base_dict = {
            srvsvc.STYPE_DISKTREE : {
                        'typestring' :'STYPE_DISKTREE',
                        'desc' : 'Disktree (Folder) Share'
                        },

            srvsvc.STYPE_PRINTQ : {
                        'typestring' :'STYPE_PRINTQ',
                        'desc' : 'Print Queue Share'
                        },

            srvsvc.STYPE_DEVICE : {
                        'typestring' :'STYPE_DEVICE',
                        'desc' : 'Device Share'
                        },

            srvsvc.STYPE_IPC : {
                        'typestring' :'STYPE_IPC',
                        'desc' : 'IPC Share'
                        }
                    }

        flag_temp = False
        flag_hidden = False
        if stype & srvsvc.STYPE_TEMPORARY:
               flag_temp = True
        if stype & srvsvc.STYPE_HIDDEN:
               flag_hidden = True

        if flag_temp is True and flag_hidden is False :
               stype_base = stype -  srvsvc.STYPE_TEMPORARY
               stype_typestring = ''.join([base_dict[stype_base]['typestring'],'_TEMPORARY'])
               stype_desc = ' '.join(['Temporary',base_dict[stype_base]['desc'] ])

        elif flag_temp is False and flag_hidden is True :
                 stype_base = stype +  srvsvc.STYPE_HIDDEN
                 stype_typestring = ''.join([base_dict[stype_base]['typestring'],'_HIDDEN'])
                 stype_desc = ' '.join(['Hidden',base_dict[stype_base]['desc'] ])

        elif flag_temp is True and flag_hidden is True :
                 stype_base = stype -  srvsvc.STYPE_TEMPORARY +  srvsvc.STYPE_HIDDEN
                 stype_typestring = ''.join([base_dict[stype_base]['typestring'],'_TEMPORARY_HIDDEN'])
                 stype_desc = ' '.join(['Temporary Hidden',base_dict[stype_base]['desc'] ])
        else:
            stype_base = stype
            stype_typestring = base_dict[stype_base]['typestring']
            stype_desc = base_dict[stype_base]['desc']

        stype_info_dict = {'typestring':stype_typestring,
                            'desc':stype_desc,
                            'base_type':stype_base,
                            'flags':(flag_temp,flag_hidden)
                            }

        return stype_info_dict[field]




    def fix_path_format(self,path=''):
        """ Fixes and checks the given path to make it in tthe correct format

  Convert the unix path to relavant Info Struct path for samba share object
  It also checks for validity of path if it is local.
  To be used for distktree (Files not IPC etc) type shares.
  Usage :
  S.fix_path_format(path= "") -> path

  """
        if self.islocal :
            if os.path.exists(path):
                path = os.path.realpath(path)  # gets canonical path
            else:
                raise OSError

            if path.startswith('/'):
                path = path.replace('/', '\\')
                path = ''.join(['C:',path])
                path = unicode(path)
            elif path.startswith('C:'):
                path = unicode(path)
            else:
                raise TypeError('Invalid path Argument')
        return path



    # NOT supported yet
    def get_connections(
        self,
        level = 1,
        max_buffer = -1,
        ):
        """ DO NOT USE : UNSUPPORTED BY SAMBA-4 YET
  """
        self.conn_list = []
        info_ctr = srvsvc.NetConnInfoCtr()
        info_ctr.level = level   #
        (no_ent,info_ctr,resume_handle) = \
            self.pipe.NetConnEnum(server_unc,
                                 self.server_info_basic.path,
                                 info_ctr,max_buffer,
                                 self.resume_handle_conn)
        for i in info_ctr.ctr.array :
            self.conn_list.append(i)



    def modify_share(self,share=None):
        """ Modifies share 502 object.

  Usage:
  S.modify_share(self,share)-> parm_error

  """
        if share is None:
            raise KeyError("Non existant Share cannot be modified")

        parm_error = 0x00000000
        name = share.name
        parm_error = self.pipe.NetShareSetInfo(self.server_unc, name,
                502, share, parm_error)
        return parm_error



    def  get_shares_list(self):
        """ Updates the share list of the pipe object .
        It first tries to list all shares if that fails it falls back to list standard shares """
        try:
            self.list_shares_all()
            self.all_listable = True
        except:
            self.list_shares()
            self.all_listable = False



    def list_shares(self):
        """ Gets a list of all (not hidden/special)active shares and update the share and share_name list.

  Usage:
  Recomended do not USE , use get list
  S.list_shares() -> None
  """
        self.share_list = []
        self.share_names_list = []
        self.share_types_list = []
        info_ctr = srvsvc.NetShareInfoCtr()
        info_ctr.level = 502
        (info_ctr, totalentries, self.resume_handle_share) = \
            self.pipe.NetShareEnum(self.server_unc, info_ctr,
                                   self.max_buffer,
                                   self.resume_handle_share)
        self.share_list = info_ctr.ctr.array
        for i in self.share_list:
            self.share_names_list.append(i.name)
            self.share_types_list.append(i.type)



    def list_shares_all(self):
        """ Gets a list of all (including hiden/special)active shares and update the share and share_name list.

  Usage:
  S.list_shares() -> None
  """
        self.share_list = []
        self.share_names_list = []
        self.share_types_list = []
        info_ctr = srvsvc.NetShareInfoCtr()
        info_ctr.level = 502
        (info_ctr, totalentries, self.resume_handle_share) = \
            self.pipe.NetShareEnumAll(self.server_unc, info_ctr,
                self.max_buffer, self.resume_handle_share)
        self.share_list = info_ctr.ctr.array
        for i in self.share_list:
            self.share_names_list.append(i.name)
            self.share_types_list.append(i.type)



    def add_share(self, share=None):
        """Adds a share with a given name and type
  This uses a share info 502 object.
  Should be followed by modify_share to complete the addition of the share.

  Usage :
  S.add_share(self,share=None) -> parm_error

  """
        if share is None :
            raise KeyError("Illegal to add an Empty Share ")
        # Uses the default 502 share info
        parm_error = 0x00000000
        parm_error = self.pipe.NetShareAdd(self.server_unc, 502, share,
                parm_error)
        return parm_error



    def get_share_info_local(self, name=''):
        """ Gets share info for a share with a particular name from local cache lists.

  Usage:
  S.get_share_info_local(self,name= \"\") -> sahre_info (502 type)
  """
        name = unicode(name)
        for i in self.share_names_list:
            if name is i:
                return share_list[i.index()]



    def get_share_info_rpc(self, name=''):
        """ Gets share info for a share with a particular name from the rpc server.

  Usage:
  S.get_share_info_local(self,name= \"\") -> sahre_info (502 type)
  """
        name = unicode(name)
        info = self.pipe.NetShareGetInfo(self.server_unc, name, 502)
        return info



    def  get_server_info(self):
        """ Gets type 102 server info .

 Usage:
 S.get_server_info() -> server_info
 """
        server_info=self.pipe.NetSrvGetInfo(self.server_unc, 102)
        return server_info



    def delete_share(self, name=''):
        """ Delete a share with the given name.

  Usage:
  S.delete_share (self,name= \"\") -> Boolean indicating success or faliure ,[error object]
  """

        reserved = None
        name = unicode(name)
        self.pipe.NetShareDel(self.server_unc, name, reserved)



    # NOT supported yet
    def remove_persistance(self, name=''):
        """ Removes persistance of a share .

  Usage: UNSUPPORTED YET
  ........
  """

        reserved = None  # to figure out what type python accepts maybee int or str
        name = unicode(name)
        self.pipe.NetShareDelSticky(self.server_unc, name, reserved)



    def get_share_type(self, name=''):
        """ Returns type of share code
  uses local cache for now as the rpc server in samba4 does not support it yet
  ........
  Usage:
  S.update_tod()
  """

        name = unicode(name)
        for i in self.share_names_list:
            if name is i:
                stype = share_types_list[i.index()]
            else:
                raise KeyError
        return stype



    def get_file_security(
        self,
        secdesc,
        filename='',
        filepath='',
        ):
        """ Returns a security descriptor buffer of a file .
  Filepath must be full path relative to basepath of share's path.

  Usage:
  s.get_file_security(self,secdesc,sharename="",filepath= "")-> sd_buf
  """

        filename = unicode(filename)
        sd_buf = self.pipe.NetGetFileSecurity(self.server_unc, share,
                filename, secdesc)  # FIXME secdesc....
        return sd_buf



    def get_tod(self):
        """ Updates Time and date (TOD) Info of the pipe object.
  ........
  Usage:
  update_tod() -> tod info object
  """

        tod_info = self.pipe.NetRemoteTOD(self.server_unc)
        return tod_info



    def set_file_security(
        self,
        secdesc,
        sd_buf,
        sharename='',
        filepath='',
        ):
        """ Sets the security  of a file .
  Filepath must be full path relative to basepath of share's path.

  Usage:
  S.set_file_security (self,secdesc,sd_buf,sharename= "",filepath= "s") -> Boolean succes,[error]
  """

        sharename = unicode(sharename)
        self.pipe.NetSetFileSecurity(self.server_unc, share, filename,
                secdesc, sd_buf)  # FIXME secdesc,sd_buf



    @staticmethod
    def get_platform_info(platform_id,field):
        """ Return the desired field.
        Retrievable types :
        'typestring' : The generic name of the platform type
        'desc' : Description of the type

  Usage:
  S.get_platform_string(platform_id,field)-> desired_field
  """

        os_dict = {
            srvsvc.PLATFORM_ID_DOS: {'typestring':'PLATFORM_ID_DOS','desc':'DOS'},
            srvsvc.PLATFORM_ID_OS2: {'typestring':'PLATFORM_ID_OS2','desc':'OS2'},
            srvsvc.PLATFORM_ID_NT: {'typestring':'PLATFORM_ID_NT','desc':'Windows NT or a newer'},
            srvsvc.PLATFORM_ID_NT: {'typestring':'PLATFORM_ID_OSF','desc':'OSF/1'},
            srvsvc.PLATFORM_ID_VMS: {'typestring':'PLATFORM_ID_VMS','desc':'VMS'},
            }
        return os_dict[platform_id][field]


    def get_share_object (
        self,
        name= "",
        stype= 0,
        comment= '',
        max_users=0xFFFFFFFF,
        password= '',
        path= '',
        #permissions= None,
        sd_buf= None
        ):
        """ Gets a 502 type share object.
  Usage:
  S.get_share_object(self,name= "",comment= "",max_users= 0xFFFFFFFF,password= "",path= "",permissions= None,sd_buf=None) -> share (502 type share object)
  """
        share = srvsvc.NetShareInfo502()

        share.comment = unicode(comment)
        share.name = unicode(name)
        share.type = stype
        share.current_users = 0x00000000
        share.max_users= max_users
        share.password = password
        share.path = path # As a result path validation needs to be done separately while insertion
        share.permissions = 0 #None
        share.sd_buf =  security.sec_desc_buf()

        return share



    def  name_validate(self,name,flags):
        """ Validate a Given Share Name .
        Returns True for a given share name and false for a invalid one .
        It does so gracefully without raising a exception. Thus validating  name cleanly
 .....
  Usage :
  S.name_validate(name,flags) -> Boolean Indicating Validity
  """
        try:
            self.pipe.NetNameValidate(self.server_unc, name, 9, flags)
            return True
        except:
            return False




    def get_list_disks(self):
        """ Returns a list of disk names on the system.
  In samaba rpc server these are hard coded .
  Refreshes Disk list of the pipe object.
............
  Usage:
  S.get_list_disks()-> None
  """

        disk_info = srvsvc.NetDiskInfo()
        self.disks_list = []
        (disk_info, totalentries, self.resume_handle) = \
            self.pipe.NetDiskEnum(self.server_unc, 0x00000000,
                                  disk_info, 26, self.resume_handle)
        for i in disk_info.disks:
            if i.disk != '':  # disk lists returns a blank entry not of consequence to the program
                self.disks_list.append(i.disk)




class ShareWindow(gtk.Window):
    """ Share management interface window """

    def __init__ (self, info_callback=None, server="", username="", password="",
            transport_type=0,connect_now=False):
        super(ShareWindow, self).__init__()

        # It's nice to have this info saved when a user wants to reconnect
        self.server_address = server
        self.username = username
        self.transport_type = transport_type

        self.create()
        self.pipe_manager = None
        self.active_page_index = 0

        self.set_status("Disconnected.")
        self.on_connect_item_activate(None, server, transport_type, username, password, connect_now)

        # This is used so the parent program can grab the server info after
        # we've connected.
        if info_callback is not None:
            info_callback(server=self.server_address, username=self.username,
                    transport_type=self.transport_type)

    def connected(self):
        return self.pipe_manager is not None

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)


    def fill_active_pane(self,share):
        """ Fills sthe active left pane """
        if share is None:
            self.active_pane_frame_label.set_markup('<b>No Share Selected</b>')
            self.active_window_name_label.set_text("-NA-")
            self.active_window_comment_label.set_text("-NA-")
            self.active_window_path_label.set_text("-NA-")
            self.active_window_password_label.set_text("-NA-")
            self.active_window_tstring_label.set_text("-NA-")
            self.active_window_tdesc_label.set_text("-NA-")
            self.active_window_tflag_label.set_text("-NA-")
            self.active_window_hflag_label.set_text("-NA-")
            self.active_window_maxusr_label.set_text("-NA-")
        else:
            self.active_pane_frame_label.set_markup('<b>Selected Share Details</b>')
            stype = self.share.type
            self.active_window_name_label.set_text(self.share.name)
            self.active_window_comment_label.set_text(self.share.comment)
            self.active_window_path_label.set_text(self.share.path)
            self.active_window_password_label.set_text(self.share.password)
            self.active_window_tstring_label.set_text(self.pipe_manager.get_share_type_info(stype,'typestring'))
            self.active_window_tdesc_label.set_text(self.pipe_manager.get_share_type_info(stype,'desc'))
            flag_set = self.pipe_manager.get_share_type_info(stype,'flags')
            self.active_window_tflag_label.set_text(str(flag_set[0]))
            self.active_window_hflag_label.set_text(str(flag_set[1]))
            self.active_window_maxusr_label.set_text(self.share.max_users)

    def create(self):
        # main window
        self.set_title("Share Management Interface")
        #self.set_default_size(800, 600)
        self.icon_filename = os.path.join(sys.path[0], "images", "network.png")
        self.share_icon_filename = os.path.join(sys.path[0], "images", "network.png")
        self.set_icon_from_file(self.icon_filename)
        self.set_position(gtk.WIN_POS_CENTER)

        accel_group = gtk.AccelGroup()
        self.vbox = gtk.VBox(False, 0)
        self.add(self.vbox)

        # menu
        self.menubar = gtk.MenuBar()
        self.vbox.pack_start(self.menubar, False, False, 0)

        self.file_item = gtk.MenuItem("_File")
        self.menubar.add(self.file_item)

        file_menu = gtk.Menu()
        self.file_item.set_submenu(file_menu)

        self.connect_item = gtk.ImageMenuItem(gtk.STOCK_CONNECT, accel_group)
        file_menu.add(self.connect_item)

        self.disconnect_item = gtk.ImageMenuItem(gtk.STOCK_DISCONNECT, accel_group)
        self.disconnect_item.set_sensitive(False)
        file_menu.add(self.disconnect_item)

        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        file_menu.add(menu_separator_item)

        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)

        self.view_item = gtk.MenuItem("_View")
        self.menubar.add(self.view_item)

        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)

        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        self.refresh_item.set_sensitive(False)
        view_menu.add(self.refresh_item)

        self.share_item = gtk.MenuItem("_Share")
        self.menubar.add(self.share_item)

        share_menu = gtk.Menu()
        self.share_item.set_submenu(share_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        self.new_item.set_sensitive(False)
        share_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        self.delete_item.set_sensitive(False)
        share_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        self.edit_item.set_sensitive(False)
        share_menu.add(self.edit_item)

        self.help_item = gtk.MenuItem("_Help")
        self.menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT, accel_group)
        help_menu.add(self.about_item)

        # toolbar
        self.toolbar = gtk.Toolbar()
        self.vbox.pack_start(self.toolbar, False, False, 0)

        self.connect_button = gtk.ToolButton(gtk.STOCK_CONNECT)
        self.connect_button.set_is_important(True)
        self.connect_button.set_tooltip_text("Connect to a server")
        self.toolbar.insert(self.connect_button, 0)

        self.disconnect_button = gtk.ToolButton(gtk.STOCK_DISCONNECT)
        self.disconnect_button.set_is_important(True)
        self.disconnect_button.set_tooltip_text("Disconnect from the server")
        self.toolbar.insert(self.disconnect_button, 1)

        sep = gtk.SeparatorToolItem()
        self.toolbar.insert(sep, 2)

        self.new_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_button.set_is_important(True)
        #self.new_button.set_tootip_text("New Share")
        self.toolbar.insert(self.new_button, 3)

        self.edit_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.edit_button.set_is_important(True)
        #self.edit_button.set_tootip_text("Edit Share")
        self.toolbar.insert(self.edit_button, 4)

        self.delete_button = gtk.ToolButton(gtk.STOCK_DELETE)
        self.delete_button.set_is_important(True)
        #self.delete_button.set_tootip_text("Delete Share")
        self.toolbar.insert(self.delete_button, 5)

        #share-page
        self.share_notebook = gtk.Notebook()
        self.vbox.pack_start(self.share_notebook, True, True, 0)

        hbox = gtk.HBox()
        self.share_notebook.append_page(hbox, gtk.Label("Share Management"))

        vpane = gtk.VPaned()
        hbox.add(vpane)

        ### left active widget :
        vbox = gtk.VBox(5)
        vpane.add1(vbox)

        frame = gtk.Frame()
        self.active_pane_frame_label = gtk.Label()
        self.active_pane_frame_label.set_use_markup(True)
        self.active_pane_frame_label.set_markup('<b>Selected Share Details</b>')
        frame.set_label_widget(self.active_pane_frame_label)
        vbox.pack_start(frame, True, True, 0)
        frame.set_border_width(5)

        table = gtk.Table(11,2)
        table.set_border_width(5)
        table.set_row_spacings(2)
        table.set_col_spacings(6)

        frame.add(table)

        label = gtk.Label(' Share Name  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_name_label = gtk.Label()
        self.active_window_name_label.set_alignment(0, 0.5)
        table.attach(self.active_window_name_label, 1, 2, 0, 1, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Comment  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_comment_label = gtk.Label()
        self.active_window_comment_label.set_alignment(0, 0.5)
        table.attach(self.active_window_comment_label, 1, 2, 1, 2, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Path  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_path_label = gtk.Label()
        self.active_window_path_label.set_alignment(0, 0.5)
        table.attach(self.active_window_path_label, 1, 2, 2, 3, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Password  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_password_label = gtk.Label()
        self.active_window_password_label.set_alignment(0, 0.5)
        table.attach(self.active_window_password_label, 1, 2, 3, 4, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label('<b>Share Type</b>')
        label.set_use_markup(True)
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Generic Typestring  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 5, 6, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_tstring_label = gtk.Label()
        self.active_window_tstring_label.set_alignment(0, 0.5)
        table.attach(self.active_window_tstring_label, 1, 2, 5, 6, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Type Description  : ') #spaces for Gui align do not change
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 6, 7, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_tdesc_label = gtk.Label()
        self.active_window_tdesc_label.set_alignment(0, 0.5)
        table.attach(self.active_window_tdesc_label, 1, 2, 6, 7, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label()
        label.set_markup('<b> Special Flags </b>')
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 7, 8, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Temporary  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 8, 9, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_tflag_label = gtk.Label()
        self.active_window_tflag_label.set_alignment(0, 0.5)
        table.attach(self.active_window_tflag_label, 1, 2, 8, 9, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Hidden  : ') #spaces for Gui align do not change
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 9, 10, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_hflag_label = gtk.Label()
        self.active_window_hflag_label.set_alignment(0, 0.5)
        table.attach(self.active_window_hflag_label, 1, 2, 9, 10, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        label = gtk.Label(' Max Users  : ')
        label.set_alignment(1, 0.5)
        table.attach(label, 0, 1, 10, 11, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        self.active_window_maxusr_label = gtk.Label()
        self.active_window_maxusr_label.set_alignment(0, 0.5)
        table.attach(self.active_window_maxusr_label, 1, 2, 10, 11, gtk.FILL,gtk.FILL | gtk.EXPAND, 0, 0)

        hbox = gtk.HBox()
        vbox.pack_start(hbox,True,True,0)

        button = gtk.Button("New")
        hbox.pack_start(button,True,True,0)

        button = gtk.Button("Edit")
        hbox.pack_start(button,True,True,0)

        button = gtk.Button("Delete")
        hbox.pack_start(button,True,True,0)

        # shares listing on right side

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        vpane.add2(scrolledwindow)

        self.shares_tree_view = gtk.TreeView()
        scrolledwindow.add(self.shares_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("")
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("pixbuf", gtk.gdk.pixbuf_new_from_file_at_size(self.share_icon_filename, 22, 22))
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Type")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        column = gtk.TreeViewColumn()
        column.set_title("Description")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        column = gtk.TreeViewColumn()
        column.set_title("Path")
        column.set_resizable(True)
        column.set_sort_column_id(3)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.shares_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)

        self.shares_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.shares_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.shares_tree_view.set_model(self.shares_store)

        #
        hbox = gtk.HBox()
        self.share_notebook.append_page(hbox, gtk.Label("Share Server Info"))

        label = gtk.Label('<b>Share Details</b>')
        label.set_use_markup(True)
        frame.set_label_widget(label)
        hbox.pack_start(frame, True, True, 0)
        frame.set_border_width(5)

        table = gtk.Table(11,2)
        table.set_border_width(5)
        table.set_row_spacings(2)
        table.set_col_spacings(6)




        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        self.vbox.pack_start(self.statusbar, False, False, 0)

############################################################################################################

def PrintUsage():
    print "Usage: %s [OPTIONS]" % (str(os.path.split(__file__)[-1]))
    print "All options are optional. The user will be queried for additional information if needed.\n"
    print "  -s  --server\t\tspecify the server to connect to."
    print "  -u  --user\t\tspecify the user."
    print "  -p  --password\tThe password for the user."
    print "  -t  --transport\tTransport type.\n\t\t\t\t0 for RPC, SMB, TCP/IP\n\t\t\t\t1 for RPC, TCP/IP\n\t\t\t\t2 for localhost."
    print "  -c  --connect-now\tSkip the connect dialog."
    #TODO: mention domain index. And maybe come up with a better way of handling it?

def ParseArgs(argv):
    arguments = {}

    try: #get arguments into a nicer format
        opts, args = getopt.getopt(argv, "chu:s:p:t:", ["help", "user=", "server=", "password=", "connect-now", "transport="])
    except getopt.GetoptError:
        PrintUsage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintUsage()
            sys.exit(0)
        elif opt in ("-s", "--server"):
            arguments.update({"server":arg})
        elif opt in ("-u", "--user"):
            arguments.update({"username":arg})
        elif opt in ("-p", "--password"):
            arguments.update({"password":arg})
        elif opt in ("-t", "--transport"):
            arguments.update({"transport_type":int(arg)})
        elif opt in ("-c", "--connect-now"):
            arguments.update({"connect_now":True})
    return (arguments)



if __name__ == "__main__":
    arguments = ParseArgs(sys.argv[1:]) #the [1:] ignores the first argument, which is the path to our utility

    main_window = ShareWindow(**arguments)
    main_window.show_all()
    gtk.main()
