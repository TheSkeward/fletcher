from git import Repo
import os

# rorepo is a Repo instance pointing to the git-python repository.
# For all you know, the first argument to Repo is a path to the repository
# you want to work with
class VersionInfo:
    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.repo = Repo(dir_path)
        assert not self.repo.bare
    def latest_commit_log(self):
        head = self.repo.head       # the head points to the active branch/ref
        master = head.reference     # retrieve the reference the head points to
        log_offset = -1
        while not master.log()[log_offset].message.startswith('commit:'):
            log_offset = log_offset - 1
        return master.log()[log_offset].message.split(' ', 1)[1]

def status_command(message, client, args):
    global versioninfo
    return "Not much, just "+versioninfo.latest_commit_log()+". How about you?",

def autoload(ch):
    ch.add_command({
        'trigger': ['!status', 'what\'s up'],
        'function': status_command,
        'async': False, 'args_num': 0, 'args_name': [], 'description': 'Tell user about the status'
        })
