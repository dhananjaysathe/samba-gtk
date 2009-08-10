
import gtk;


class User:
    
    def __init__(self, username, fullname, description, rid):
        self.username = username
        self.fullname = fullname
        self.description = description
        self.rid = rid
        
        self.password = ""
        self.must_change_password = True
        self.cannot_change_password = False
        self.password_never_expires = False
        self.account_disabled = False
        self.account_locked_out = False
        self.group_list = []
        self.profile_path = ""
        self.logon_script = ""
        self.homedir_path = ""
        self.map_homedir_drive = -1
        
        None

    def list_view_representation(self):
        return [self.username, self.fullname, self.description, self.rid]


class Group:
    
    def __init__(self, name, description, rid):
        self.name = name
        self.description = description
        self.rid = rid
        
    def list_view_representation(self):
        return [self.name, self.description, self.rid]


class Service:
    
    STARTUP_TYPE_NORMAL = 0
    STARTUP_TYPE_AUTOMATIC = 1
    STARTUP_TYPE_DISABLED = 2
    
    def __init__(self, name, description, started, startup_type):
        self.name = name
        self.description = description
        self.started = started
        self.startup_type = startup_type
        
        self.start_params = ""
        self.path_to_exe = ""
        self.account = None # local system account
        self.account_password = ""
        self.allow_desktop_interaction = False
        self.hw_profile_list = [["Profile 1", True], ["Profile 2", False]]
        
    def list_view_representation(self):
        return [self.name, self.description, ["Stopped", "Started"][self.started], ["Normal", "Automatic", "Disabled"][self.startup_type]]


class RegistryValue:
    
    def __init__(self, name, type, data, parent):
        self.name = name
        self.type = type
        self.data = data
        self.parent = parent
        
    def list_view_representation(self):
        return [self.name, self.type, self.data]


class RegistryKey:
    
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        
    def list_view_representation(self):
        return [gtk.STOCK_DIRECTORY, self.name]


class Task:
    
    def __init__(self, command, id):
        self.command = command
        self.id = id
        self.job_time = 0
        self.days_of_month = 0
        self.days_of_week = 0
        self.run_periodically = False
        self.add_current_date = False
        self.non_interactive = False

    def list_view_representation(self):
        if (self.run_periodically):
            schedule = "Periodically, "
        else:
            schedule = "Once, "
        
        return [str(self.id), self.command, schedule]

