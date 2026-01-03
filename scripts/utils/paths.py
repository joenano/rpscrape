from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class Paths:
    data_root: Path
    output: Path
    progress: Path
    urls: Path
    betfair: Path


def build_paths(
    folder_name: str,
    file_name: str,
    code: str | None,
    gzip_output: bool = False,
) -> Paths:
    project_root = Path('..')
    data_root = project_root / 'data'

    if code is None:
        output_dir = data_root / folder_name
    else:
        output_dir = data_root / folder_name / code

    output_dir.mkdir(parents=True, exist_ok=True)

    extension = '.csv.gz' if gzip_output else '.csv'
    output = output_dir / f'{file_name}{extension}'
    progress = output.with_suffix(output.suffix + '.progress')

    urls = data_root / 'urls' / f'{file_name}.csv'
    urls.parent.mkdir(parents=True, exist_ok=True)

    betfair = data_root / 'betfair' / f'{file_name}.csv'
    betfair.parent.mkdir(parents=True, exist_ok=True)

    return Paths(
        data_root=data_root,
        output=output,
        progress=progress,
        urls=urls,
        betfair=betfair,
    )
