#!/usr/bin/env python3

import gzip
import os
import sys

from collections.abc import Callable
from datetime import date
from dotenv import load_dotenv
from lxml import html
from orjson import loads
from pathlib import Path
from typing import TextIO, TYPE_CHECKING

from utils.argparser import ArgParser
from utils.betfair import Betfair
from utils.date import format_date
from utils.network import NetworkClient
from utils.paths import Paths, build_paths
from utils.settings import Settings
from utils.update import Update

_ = load_dotenv()

settings = Settings()

if TYPE_CHECKING:
    from utils.betfair import Betfair

RACE_TYPES: dict[str, set[str]] = {
    'flat': {'Flat'},
    'jumps': {'Chase', 'Hurdle', 'NH Flat'},
}


def check_for_update() -> bool:
    update = Update()

    if not update.available():
        return False

    choice = input('Update available. Do you want to update? [y/N] ').strip().lower()
    if choice != 'y':
        return False

    success = update.pull_latest()
    print('Updated successfully.' if success else 'Failed to update.')
    return success


def sort_key(url: str) -> tuple[str, str, int]:
    parts = url.split('/')
    race_course = parts[5]
    race_date = parts[6]
    race_id = int(parts[7])
    return race_date, race_course, race_id


def get_race_urls(
    tracks: list[tuple[str, str]], years: list[str], code: str, client: NetworkClient
) -> list[str]:
    url_course_base = 'https://www.racingpost.com:443/profile/course/filter/results'
    url_result_base = 'https://www.racingpost.com/results'

    urls: set[str] = set()

    for course_id, course in tracks:
        for year in years:
            race_list_url = f'{url_course_base}/{course_id}/{year}/{code}/all-races'

            status, response = client.get(race_list_url)

            if status != 200:
                print(f'Failed to get race urls.\nStatus: {status}, URL: {race_list_url}')
                sys.exit(1)

            data = loads(response.text).get('data', {})
            races = data.get('principleRaceResults', [])

            if not races:
                continue

            for race in races:
                race_date = race['raceDatetime'][:10]
                race_id = race['raceInstanceUid']
                race_url = f'{url_result_base}/{course_id}/{course}/{race_date}/{race_id}'
                urls.add(race_url.replace(' ', '-').replace("'", ''))

    return sorted(urls, key=sort_key)


def get_race_urls_date(
    dates: list[date], tracks: list[tuple[str, str]], client: NetworkClient
) -> list[str]:
    urls: set[str] = set()
    course_ids: set[str] = {t[0] for t in tracks}

    for race_date in dates:
        url = f'https://www.racingpost.com/results/{race_date}'

        _, response = client.get(url)
        doc = html.fromstring(response.content)

        races = doc.xpath('//a[@data-test-selector="link-listCourseNameLink"]')
        for race in races:
            course_id = race.attrib['href'].split('/')[2]
            if course_id in course_ids:
                urls.add(f'https://www.racingpost.com{race.attrib["href"]}')

    return sorted(urls, key=sort_key)


def load_or_save_urls(path: Path, builder: Callable[[], list[str]]) -> list[str]:
    if path.exists():
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]

    urls = builder()
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text('\n'.join(urls))

    return urls


def prepare_betfair(
    race_urls: list[str],
    paths: Paths,
) -> 'Betfair | None':
    if not settings.toml or not settings.toml.get('betfair_data', False):
        return None

    from utils.betfair import Betfair

    print('Getting Betfair data...')

    if paths.betfair.exists():
        print('Using cached Betfair data')
        return Betfair.from_csv(paths.betfair)

    betfair = Betfair(race_urls)

    with open(str(paths.betfair), 'w') as f:
        fields = settings.toml.get('fields', {}).get('betfair', {})
        header = ','.join(['date', 'region', 'off', 'horse'] + list(fields.keys()))
        _ = f.write(header + '\n')

        for row in betfair.rows:
            values = ['' if v is None else str(v) for v in row.to_dict().values()]
            _ = f.write(','.join(values) + '\n')

    return betfair


def scrape_races(
    race_urls: list[str],
    paths: Paths,
    code: str,
    client: NetworkClient,
    file_writer: Callable[[str, bool], TextIO],
):
    from utils.race import Race, VoidRaceError

    betfair = prepare_betfair(
        race_urls=race_urls,
        paths=paths,
    )

    last_url = paths.progress.read_text().strip() if paths.progress.exists() else None

    if last_url:
        try:
            race_urls = race_urls[race_urls.index(last_url) + 1 :]
            print(f'Resuming after {last_url}')
        except ValueError:
            pass
    else:
        print('Scraping races')

    append = last_url is not None and paths.output.exists()

    with file_writer(str(paths.output), append=append) as f:
        if not append:
            _ = f.write(settings.csv_header + '\n')

        for url in race_urls:
            _, response = client.get(url)
            doc = html.fromstring(response.content)

            try:
                race = (
                    Race(client, url, doc, code, settings.fields, betfair.data)
                    if betfair
                    else Race(client, url, doc, code, settings.fields)
                )
            except VoidRaceError:
                continue

            allowed = RACE_TYPES.get(code)
            if allowed is not None and race.race_info.race_type not in allowed:
                continue

            for row in race.csv_data:
                _ = f.write(row + '\n')

            _ = paths.progress.write_text(url)

    print('Finished scraping.')
    print(f'OUTPUT_CSV={paths.output.resolve()}')


def writer_csv(file_path: str, append: bool = False) -> TextIO:
    return open(file_path, 'a' if append else 'w', encoding='utf-8')


def writer_gzip(file_path: str, append: bool = False) -> TextIO:
    mode = 'at' if append else 'wt'
    return gzip.open(file_path, mode, encoding='utf-8')


def main():
    if settings.toml is None:
        sys.exit()

    if settings.toml['auto_update']:
        _ = check_for_update()

    gzip_output = settings.toml.get('gzip_output', False)
    file_writer = writer_gzip if gzip_output else writer_csv

    parser = ArgParser()

    if len(sys.argv) <= 1:
        parser.parser.print_help()
        sys.exit(2)

    args = parser.parse(sys.argv[1:])

    email = os.getenv('EMAIL')
    auth_state = os.getenv('AUTH_STATE')
    access_token = os.getenv('ACCESS_TOKEN')

    client = NetworkClient(email=email, auth_state=auth_state, access_token=access_token)

    if args.dates != []:
        folder_name = f'dates/{args.region}'

        if len(args.dates) == 1:
            file_name = format_date(args.dates[0])
        else:
            file_name = f'{format_date(args.dates[0])}_{format_date(args.dates[-1])}'

        paths = build_paths(
            folder_name=folder_name,
            file_name=file_name,
            code=args.type,
            gzip_output=gzip_output,
        )

        race_urls = load_or_save_urls(
            paths.urls,
            lambda: get_race_urls_date(args.dates, args.tracks, client),
        )

    else:
        folder_name = args.region
        file_name = args.years[0] if len(args.years) == 1 else f'{args.years[0]}-{args.years[-1]}'

        paths = build_paths(
            folder_name=folder_name,
            file_name=file_name,
            code=args.type,
            gzip_output=gzip_output,
        )

        race_urls = load_or_save_urls(
            paths.urls,
            lambda: get_race_urls(args.tracks, args.years, args.type, client),
        )

    scrape_races(race_urls, paths, args.type, client, file_writer)


if __name__ == '__main__':
    main()
