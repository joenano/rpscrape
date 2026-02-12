from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestKey:
    scope_kind: str
    scope_value: str
    race_type: str
    filename: str

    def scoped_dir(self) -> Path:
        return Path(self.scope_kind, self.scope_value)

    def typed_dir(self) -> Path:
        return Path(self.scope_kind, self.scope_value, self.race_type)


@dataclass(frozen=True)
class Paths:
    output: Path
    progress: Path
    urls: Path
    betfair: Path


def build_paths(
    request: RequestKey,
    gzip_output: bool = False,
) -> Paths:
    project_root = Path(__file__).resolve().parents[2]

    data_root = project_root / 'data'
    cache_root = project_root / '.cache'

    ext = '.csv.gz' if gzip_output else '.csv'

    output = data_root / request.typed_dir() / f'{request.filename}{ext}'
    progress = cache_root / 'progress' / request.typed_dir() / f'{request.filename}.progress'
    urls = cache_root / 'urls' / request.scoped_dir() / f'{request.filename}.csv'
    betfair = cache_root / 'betfair' / f'{request.filename}.csv'

    for path in (output, progress, urls, betfair):
        path.parent.mkdir(parents=True, exist_ok=True)

    return Paths(
        output=output,
        progress=progress,
        urls=urls,
        betfair=betfair,
    )
