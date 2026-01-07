import subprocess

from pathlib import Path
from curl_cffi.requests import get


class Update:
    def __init__(self):
        self.root_dir: Path = Path.cwd().parent
        self.api_url: str = 'https://api.github.com/repos/joenano/rpscrape/commits/master'

    def local_hash(self) -> str:
        return subprocess.check_output(
            ('git', 'rev-parse', 'HEAD'), cwd=self.root_dir, text=True
        ).strip()

    def remote_hash(self) -> str:
        resp = get(self.api_url, headers={'User-Agent': 'update-check'})
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
