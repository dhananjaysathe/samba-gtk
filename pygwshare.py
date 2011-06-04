#!/usr/bin/python

#commented out relevant decessions , will be removed later 


from samba import credentials
from samba.dcerpc import (
    srvsvc,
    security,
    lsa,
    )
    
from sambagtk.sam import (
    User,
    Group,
    )
    
from sambagtk.dialogs import (
    AboutDialog,
    )
    
import os.path
    
#from coherence.extern.log.log import level
    
class srvsvcPipeManager(object) :
	
	def __init__(self, server_address, transport_type, username, password):
			""" Initialize the pipe hndling the srvsvc calls """
			creds = credentials.Credentials()
			if (username.count("\\") > 0):
				creds.set_domain(username.split("\\")[0])
				creds.set_username(username.split("\\")[1])
			elif (username.count("@") > 0):
				creds.set_domain(username.split("@")[1])
				creds.set_username(username.split("@")[0])
			else:
				creds.set_domain("")
				creds.set_username(username)
			creds.set_workstation("")
			creds.set_password(password)

			#binding = "ncacn_np:%s" # srvsvc allows only named pipes tcp/upd not allowed
			# How ever it worked in python console on localhost. Needs testing
			
			binding = ["ncacn_np:%s", "ncacn_ip_tcp:%s", "ncalrpc:%s"][transport_type]
			self.pipe = srvsvc.srvsvc(binding % (server_address), credentials = creds)
			
			# set up some basic parameters unique to the connection
			
			self.server_unc = '\\'+server_address
			self.server_info_basic = self.pipe.NetSrvGetInfo(self.server_unc,102) # basic user info object of type 102
			self.tod = self.pipe.NetRemoteTOD(self.server_unc)
			# both the above types are standard types as define in the SRVS specification
			### Now init various default values
			
			self.resume_handle_conn = 0x00000000
			self.resume_handle_share = 0x00000000
			self.max_buffer = -1
			
			# Initialise various cache lists :
			# The idea is to use locally available share list and related conveiniece lists
			# This should reduce the queries and improve performance
			# The share list will be locally maintained any via the get_share_local_cache
			
			self.conn_list = []
			self.share_list = []
			self.share_names_list = []
			self.share_types_list = []
						

			
		
		 
	def close(self):
			pass 
			# apparently there's no .Close() method for this pipe
    
#  conn enum is not supported yet DO Not Use	
#	def get_connections(self,level= 1,max_buffer=self.max_buffer,path= self.server_info_basic.path):
#			self.conn_list = []
#			info_ctr = srvsvc.NetConnInfoCtr()
#			info_ctr.level = level   #   
#			(no_ent,info_ctr,resume_handle) = self.pipe.NetConnEnum(server_unc,path,info_ctr,max_buffer,self.resume_handle_conn)
#			for i in info_ctr.ctr.array :
#				self.conn_list.append(i)
			 
			
   
	@staticmethod
	def  translate_types(stype,typeflags=""):
			""" Utility function translates share type from number to string and vice versa.It also accounts for typeflags
				returns the translated type , typeflags, and comment as list in that order
				
				If the int value of typeflag is given and the typeflags are specified they are used to generate 
				compatible int format output .
				Usage :
				translate_types(stype, typeflags="")-> (stype_converted,typeflags,stype_comments)
				
			"""
			typelist = (
			('STYPE_DISKTREE',0x00000000,' Disk drive'),
			('STYPE_PRINTQ',0x00000001,' Print queue'),
			('STYPE_DEVICE',0x00000002,' Communication device'),
			('STYPE_IPC',0x00000003,' Interprocess communication (IPC)')
			)
			advanced_types = (
			('STYPE_TEMPORARY',0x40000000,' Temporary resource'),
			('STYPE_SPECIAL',0x80000000,' Special Resource'),
			('STYPE_BOTH',0x40000000 | 0x80000000, ' Temporary and Special')
			)
			if isinstance(stype,str) :
				for i in typelist :
					if i[0] == stype:
						stype_int = i[1]
						stype_comm = i[2]
				if typeflags != "" :
					for i in advanced_types :
						if i[0] == typeflags:
							stype_int |= -i[1]
							stype_comm += i[2]
			
				return stype_int,typeflags,stype_comm				
		
		# Now handle the special flags get them from int if present, (passed flags are ignored and reset
						
			if isinstance(stype,int) and typeflags == '':
				if -(0x80000000 |0x40000000 ) <= stype < -0x80000000:	
					typeflags = 'STYPE_BOTH'
					stype += (0x80000000 |0x40000000 )
				elif -0x80000000 <= stype < -0x40000000:
					typeflags = 'STYPE_SPECIAL'
					stype += 0x80000000
				elif -0x40000000 <= stype < 0:
					typeflags = 'STYPE_SPECIAL'
					stype += 0x40000000	
				for i in typelist :
					if i[1] == stype:
						stype_str = i[0]
						stype_comm = i[1]
			
				return stype_str,typeflags,stype_comments
		
			if isinstance(stype,int) and typeflags != '' and stype >= 0:
				stype_int = stype
				if i in advanced_types:
					if i[0] == typeflags:
						stype_int |= -i[1]
						stype_comm = i[2] + 'attribute added'
						#can be used as an addon comment
			
				return stype_int,typeflags,stype_comments
	
	
	@staticmethod
	def fix_path_format(path= "",islocal= 0):
			""" Convert the unix path to relavant Info Struct path for samba share object 
			It also checks for validity of path if it is local.
			To be used for distktree (Files not IPC etc) type shares.
			"""
			if islocal == 1:
				if os.path.exists(path):
					path = os.path.realpath(path) # gets canonical path
				else :
					raise OSError
			if path.startswith('/'):
				path = path.replace('/','\\')
				path = "C:"+path
				path = unicode(path)
			else :
				raise TypeError							
			return path	
				
	
	def  modify_share(self,comment= "",max_users= 0xFFFFFFFF,password= "",path= "",permissions= None,sd_buf=None,islocal= 0):
			""" Modifies share 502 object. """
			
			# FIXME sd_buf needs to be fixed 
			self.get_share_local_cache()
			share=self.get_share_info(name)
			if comment != "" :
				share.comment = comment
			share.max_users= max_users
			share.current_users = 0
			share.password = password
			share.path = self.fix_path_format(path,islocal)
			share.permissions = None
			share.sd_buf = security 							#### FIXME
			parm_error = 0x00000000
			parm_error = self.pipe.NetShareSetInfo(self.server_unc,name, 502, share, parm_error)
			
	
	def   get_share_local_cache(self) :
			""" Gets a list of all active shares and update the share and share_name list. """
			self.share_list = []
			self.share_names_list = []
			self.share_types_list = []
			info_ctr = srvsvc.NetShareInfoCtr()
			info_ctr.level = 502
			(info_ctr, totalentries, resume_handle) = self.pipe.NetShareEnumAll(self.server_unc, info_ctr, self.max_buffer,self.resume_handle_share)
			self.share_list = info_ctr.ctr.array
			for i in self.share_list :
				self.share_names_list.append(i.name) 
				self.share_types_list.append(i.type) 
				
				
	def  add_share(self,name= "",stype= 'STYPE_DISKTREE',typeflags=""):
		# Uses the default 502 share info
			""" Add a share with a given name of type share info 502 with no parameters except name.
			Should be followed by modify_share to complete the addition of the share."""
			share = srvsvc.NetShareInfo502()
			name = unicode(name)
			share.name = name
			share.type,typeflags,share.comment = translate_types(stype,typeflags)
			parm_error = 0x00000000
			parm_error = self.pipe.NetShareAdd(self.server_unc, 502, share, parm_error)
			
	
	def  get_share_info(self,name= ""):
			""" Gets share info for a share with a particular name """
			name = unicode(name)
			for i in self.share_names_list :
				if name == i :
					return share_list[i.index()]
			
	
	def delete_share (self,name= ""):
			""" Delete a share with the given name. """
			reserved = None
			name = unicode(name)
			self.pipe.NetShareDel(self.server_unc, name, reserved)


	def remove_persistance (self,name= ""):
			""" Removes persistance of a share """
			reserved = None
			name = unicode(name)
			self.pipe.NetShareDelSticky(self.server_unc, name, reserved)
		
	
	def get_share_type (self,name= ""):
			""" Returns type of share code """
			name = unicode(name)
			for i in self.share_names_list :
				if name == i :
					stype =share_types_list[i.index()]
			return stype
	
		
	def  update_tod(self):
			""" Updates Time and date (TOD) Info """
			self.tod = self.pipe.NetRemoteTOD(self.server_unc)
			
				
