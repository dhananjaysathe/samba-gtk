#!/usr/bin/python
# -*- coding: utf-8 -*-

from samba import credentials
from samba.dcerpc import srvsvc
from sambagtk.dialogs import AboutDialog
import os.path


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

        self.server_unc = '\\' + server_address

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

        if server_address == '127.0.0.1':
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
               stype_typestring = base_dict[stype_base]['typestring'] + '_TEMPORARY'
               stype_desc = 'Temporary '+base_dict[stype_base]['desc']

        elif flag_temp is False and flag_hidden is True :
                 stype_base = stype +  srvsvc.STYPE_HIDDEN
                 stype_typestring = base_dict[stype_base]['typestring'] + '_HIDDEN'
                 stype_desc = 'Hidden '+base_dict[stype_base]['desc']

        elif flag_temp is True and flag_hidden is True :
                 stype_base = stype -  srvsvc.STYPE_TEMPORARY +  srvsvc.STYPE_HIDDEN
                 stype_typestring = base_dict[stype_base]['typestring'] + '_TEMPORARY_HIDDEN'
                 stype_desc = 'Temporary Hidden '+base_dict[stype_base]['desc']
        else:
            stype_base = stype
            stype_typestring = base_dict[stype_base]['typestring']
            stype_desc = base_dict[stype_base]['desc']

        final_properties = [('typestring',stype_typestring),
                            ('desc',stype_desc),
                            ('base',stype_base),
                            ('flags',(flag_temp,flag_hidden))
                            ]
                            
        stype_info_dict = dict(final_properties)
        
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
                path = 'C:' + path
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
            raise KeyError("Illegal to pass null share type.")

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
            if name == i:
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
            if name == i:
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
  S.set_file_security (self,secdesc,sd_buf,sharename= \"\",filepath= \"\") -> Boolean succes,[error]
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


    @staticmethod
    def get_share_object (
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
        share.path = self.fix_path_format(path)
        share.permissions = None
        share.sd_buf = sd_buf  # ### FIXME

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
