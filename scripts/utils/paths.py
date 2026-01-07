from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestKey:
    scope_kind: str
    scope_value: str
    race_type: str
    filename: str

    def data_dir(self) -> Path:
        return Path(
            self.scope_kind,
            self.scope_value,
            self.race_type,
        )


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
    project_root = Path('..')
    data_root = project_root / 'data'
    cache_root = project_root / '.cache'

    ext = '.csv.gz' if gzip_output else '.csv'

    output = data_root / request.data_dir() / f'{request.filename}{ext}'
    output.parent.mkdir(parents=True, exist_ok=True)

    progress = output.with_suffix(output.suffix + '.progress')

    urls = cache_root / 'urls' / request.data_dir() / f'{request.filename}.csv'
    urls.parent.mkdir(parents=True, exist_ok=True)

    betfair = cache_root / 'betfair' / request.data_dir() / f'{request.filename}.csv'

    return Paths(
        output=output,
        progress=progress,
        urls=urls,
        betfair=betfair,
    )
