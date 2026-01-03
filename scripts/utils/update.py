import subprocess

from pathlib import Path
from curl_cffi.requests import get


class Update:
    def __init__(self):
        self.root_dir: Path = Path.cwd().parent
        self.api_url: str = 'https://api.github.com/repos/joenano/rpscrape/commits/master'

    def available(self):
        try:
            # Check if local master is behind origin/master
            subprocess.run(
                ['git', 'fetch', 'origin', 'master'],
                cwd=self.root_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'master..origin/master'],
                cwd=self.root_dir,
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                behind_count = int(result.stdout.decode('utf-8').strip())
                return behind_count > 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass
        return False

    def remote_hash(self) -> str:
        resp = get(self.api_url, headers={'User-Agent': 'update-check'}, timeout=2)
        resp.raise_for_status()
        data = resp.json()
        return data['sha']

    def available(self) -> bool:
        return self.local_hash() != self.remote_hash()

    def pull_latest(self) -> bool:
        return (
            subprocess.run(
                ('git', 'pull', '--ff-only', 'origin', 'master'),
                cwd=self.root_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
