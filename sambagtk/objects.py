
import datetime

from samba.dcerpc import (
    misc,
    svcctl,
    )


class User(object):

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

    def list_view_representation(self):
        return [self.username, self.fullname, self.description, self.rid]


class Group(object):

    def __init__(self, name, description, rid):
        self.name = name
        self.description = description
        self.rid = rid

    def list_view_representation(self):
        return [self.name, self.description, self.rid]


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
