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
    
from coherence.extern.log.log import level
    
class svcsrvPipeManager(object)
	
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
			binding = ["ncacn_np:%s", "ncacn_ip_tcp:%s", "ncalrpc:%s"][transport_type]# apparently it is allowed 
			# worked in python console on localhost need to test on more ip addresses			
			self.pipe = srvsvc.srvsvc(binding % (server_address), credentials = creds)
			
			# set up some basic parameters unique to the connection
			self.server_unc='\\'+server_address
			self.server_info_basic=self.pipe.NetSrvGetInfo(self.server_unc,102) # basic user info object of type 102
			# FIXME Not implemented Yet in samba4 >>>>
			###self.server_info_advanced=self.pipe.NetSrvGetInfo(self.server_unc,502) # more advanced server info of type 502
			self.tod=self.pipe.NetRemoteTOD(self.server_unc)
			# both the above types are standard types as define in the SRVS specification
			### Now init various default values
			self.resume_handle_conn=0x00000000
			self.resume_handle_share=0x00000000
			self.max_buffer=-1
      
		
		 
	def close(self):
			pass # apparently there's no .Close() method for this pipe
    
#conn enum is not supported 	
	"""def get_connections(self,level=1,self.max_buffer,path=self.server_info_basic.path)# max allowed mem buffer at '-1' 
			conn_list=[]
			info_ctr=srvsvc.NetConnInfoCtr()
			info_ctr.level=level   #   
			no_ent=self.pipe.NetConnEnum(server_unc,path,info_ctr,max_buffer,self.resume_handle_conn)
			for i in info_ctr.ctr.array :
				conn_list.append(i)
			return conn_list 
			#return no_ent,info_ctr,resume_handle 
   """
	def  translate_type_comment(stype,comment=0):
			""" Utility function translates share type from number to string and vice versa.
		It gives comments if comments flag is set to '1'"""
			typelist=(
			('STYPE_DISKTREE','Disk drive',0x00000000),
			('STYPE_PRINTQ','Print queue',0x00000001),
			('STYPE_DEVICE','Communication device',0x00000002),
			('STYPE_IPC','Interprocess communication (IPC)',0x00000003)
			)
			if isinstance(stype,str) :
				for i in typelist :
					if i[0]==stype:
						xlat_type=i[2]
						comm=i[1]
			if isinstance(stype,int) :
				for i in typelist :
					if i[2]==stype:
						xlat_type=i[0]
						comm=i[1]
			if comment == 1 :
				return comm
			else :
				return xlat_type
	
	
	def get_path_format(path="",islocal=0):
		""" Convert the unix path to relavant Info Struct path for samba share object 
		It also checks for validity of path if it is local."""
			if islocal == 1:
				if os.path.exists(path):
					path=os.path.realpath(path) # gets canonical path
				else :
					raise OSError
			if path.startswith('/'):
				path=path.replace('/','\\')
				path="C:"+path
				path=unicode(path)
										
			return path	
				
	
	def  alter_share(self,comment="",max_users=0xFFFFFFFF,name="",password="",path="",permissions=None,sd_buf,stype='STYPE_DISKTREE',flags="",islocal=0):
			""" alters share 502 object. """
			#chose default 502 type TODO inquire tru val defult type is mem share
			share=srvsvc.NetShareInfo502()
			if comment=""
				share.comment=translate_type_comment(stype,1)
			else : 
				share.comment=comment
			share.current_users=0
			share.name=name
			share.password=password
			share.path=get_path_format(path,islocal)
			share.permissions=None
			share.sd_buf=security 							#### ASKKKKKKKKK
			share.type=translate_type_comment(stype,0)
			if flags='STYPE_TEMPORARY':
				share.type |= 0x40000000
			elif flags='STYPE_SPECIAL' :
				share.type |= 0x80000000
			parm_error=0x00000000
			parm_error=self.pipe.NetShareSetInfo(self.server_unc,name, 502, share, parm_error)
			
	
	def   get_share_enum_cache(self)
			""" Gets a list of all active shares and update the share and share_name list. """
			self.share_list=[]
			self.share_names_list=[]
			self.share_types_list=[]
			info_ctr=srvsvc.NetShareInfoCtr()
			info_ctr.level=502
			(info_ctr, totalentries, resume_handle)=self.pipe.NetShareEnumAll(self.server_unc, info_ctr, self.max_buffer,self.resume_handle_share)
			self.share_list=info_ctr.ctr.array
			for i in self.share_list :
				self.share_names_list.append(i.name) 
				self.share_types_list.append(i.type) 
				
				
	def  add_share(self,name=""):
		#assume 502 share info
			""" Add a share with a given name of type share info 502"""
			share=srvsvc.NetShareInfo502()
			name=unicode(name)
			share.name=name
			parm_error=0x00000000
			parm_error=self.pipe.NetShareAdd(self.server_unc, 502, share, parm_error)
			
	
	def  get_share_info(self,name=""):
		""" Gets share info for a share with a particular name """
			name=unicode(name)
			# Proposing to use locally available share list 
			# This should improve reduce the queries and improve performance
			# The share list will be locally maintained any via the share enum
			#share=self.pipe.NetShareGetInfo(self.server_unc, name, 502)
			for i in self.share_names_list
				if name==i
					return share_list[i.index()]
			
	
	def delete_share (self,name=""):
		""" Delete a share with the given name. """
			reserved=0
			name=unicode(name)
			self.pipe.NetShareDel(self.server_unc, name, reserved)


	def remove_persistance (self,name=""):
		""" Removes persistance of a share """
			reserved=0
			name=unicode(name)
			self.pipe.NetShareDelSticky(self.server_unc, name, reserved)
		
	
	def get_share_type (self,name=""):
		""" Returns type of share code """
			name=unicode(name)
			
			# stype=self.pipe.NetShareCheck(self.server_unc,name)
			# not supported in samba 4 yet 
			# again new scheme where in local cache of share enum is used rather than a new rpc call
			
			for i in self.share_names_list
				if name==i
					return stype=share_types_list[i.index()]
	
	
