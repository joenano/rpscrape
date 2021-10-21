import subprocess

from pathlib import Path

class Update:
    
    def __init__(self):
        self.root_dir = Path.cwd().split('/utils')[0]
    
    def available(self):
        if 'local out of date' in self.get_status().lower():
            return True
        return False
    
    def get_status(self):
        command = ['git', 'remote', 'show', 'origin']
        status = subprocess.check_output(command, cwd=self.root_dir)
        return status.decode('utf-8')

    def pull_latest(self):
        command = ['git', 'pull', 'origin', 'master']
        status = subprocess.check_output(command, cwd=self.root_dir)
        return status.decode('utf-8')
    
    def up_to_date(self):
        if 'up-to-date' in self.get_status():
            return True
