#!/usr/bin/env python3

import gzip
import sys

from collections.abc import Callable
from pathlib import Path
from typing import TextIO
from lxml import html
from orjson import loads
from datetime import date

from utils.betfair import Betfair
from utils.argparser import ArgParser
from utils.completer import Completer
from utils.header import RandomHeader
from utils.network import Persistent406Error, get_request
from utils.race import Race, VoidRaceError
from utils.settings import Settings
from utils.update import Update

from utils.course import course_name, courses

settings = Settings()
random_header = RandomHeader()


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


def get_race_urls(tracks: list[tuple[str, str]], years: list[str], code: str) -> list[str]:
    url_course_base = 'https://www.racingpost.com:443/profile/course/filter/results'
    url_result_base = 'https://www.racingpost.com/results'
    urls: set[str] = set()

    for course_id, course in tracks:
        for year in years:
            race_list_url = f'{url_course_base}/{course_id}/{year}/{code}/all-races'

            try:
                status, response = get_request(race_list_url)
            except Persistent406Error as err:
                print('Failed to get race urls.')
                print(err)
                sys.exit(1)

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

    return sorted(urls)


def get_race_urls_date(dates: list[date], region: str) -> list[str]:
    urls: set[str] = set()
    course_ids: set[str] = {course[0] for course in courses(region)}

    for race_date in dates:
        url = f'https://www.racingpost.com/results/{race_date}'

        try:
            status, response = get_request(url)
        except Persistent406Error as err:
            print('Failed to get race urls.')
            print(err)
            sys.exit(1)

        if status != 200:
            print(f'Failed to get race urls.\nStatus: {status}, URL: {url}')
            sys.exit(1)

        doc = html.fromstring(response.content)

        races = doc.xpath('//a[@data-test-selector="link-listCourseNameLink"]')
        for race in races:
            course_id = race.attrib['href'].split('/')[2]
            if course_id in course_ids:
                urls.add(f'https://www.racingpost.com{race.attrib["href"]}')

    return sorted(urls)


def scrape_races(
    race_urls: list[str],
    folder_name: str,
    file_name: str,
    file_extension: str,
    code: str,
    file_writer: Callable[[str], TextIO],
):
    out_dir = Path('../data') / folder_name / code
    out_dir.mkdir(parents=True, exist_ok=True)

    file_path = out_dir / f'{file_name}.{file_extension}'

    betfair: Betfair | None = None

    if settings.toml and settings.toml.get('betfair_data', False):
        print('Getting Betfair data...')
        betfair = Betfair(race_urls)

        betfair_dir = Path('../data/betfair') / folder_name / code
        betfair_dir.mkdir(parents=True, exist_ok=True)

        with file_writer(str(betfair_dir / f'{file_name}.csv')) as f:
            betfair_fields = settings.toml.get('fields', {}).get('betfair', {})

            header = ','.join(['date', 'region', 'off', 'horse'] + list(betfair_fields.keys()))
            _ = f.write(header + '\n')

            for row in betfair.rows:
                values = ['' if v is None else str(v) for v in row.to_dict().values()]
                _ = f.write(','.join(values) + '\n')

    print('Scraping races...')

    with file_writer(str(file_path)) as f:
        _ = f.write(settings.csv_header + '\n')

        for url in race_urls:
            try:
                _, response = get_request(url)
            except Persistent406Error as err:
                print('Failed to get race.')
                print(err)
                sys.exit(1)

            doc = html.fromstring(response.content)

            try:
                if betfair:
                    race = Race(url, doc, code, settings.fields, betfair.data)
                else:
                    race = Race(url, doc, code, settings.fields)
            except VoidRaceError:
                continue

            if code == 'flat' and race.race_info.r_type != 'Flat':
                continue
            if code == 'jumps' and race.race_info.r_type not in {'Chase', 'Hurdle', 'NH Flat'}:
                continue

            for row in race.csv_data:
                _ = f.write(row + '\n')

    rel_path = file_path.relative_to('../')
    print(f'Finished scraping.\nData path: rpscrape/{rel_path}')


def writer_csv(file_path: str) -> TextIO:
    return open(file_path, 'w', encoding='utf-8')


def writer_gzip(file_path: str) -> TextIO:
    return gzip.open(file_path, 'wt', encoding='utf-8')


def main():
    if settings.toml is None:
        sys.exit()

    if settings.toml['auto_update']:
        _ = check_for_update()

    file_extension = 'csv'
    file_writer = writer_csv

    if settings.toml.get('gzip_output', False):
        file_extension = 'csv.gz'
        file_writer = writer_gzip

    parser = ArgParser()

    if len(sys.argv) > 1:
        args = parser.parse_args(sys.argv[1:])

        if args.date and args.region:
            folder_name = f'dates/{args.region}'
            file_name = args.date.replace('/', '_')
            race_urls = get_race_urls_date(parser.dates, args.region)
        else:
            folder_name = args.region or course_name(args.course)
            file_name = args.year
            race_urls = get_race_urls(parser.tracks, parser.years, args.type)

        scrape_races(race_urls, folder_name, file_name, file_extension, args.type, file_writer)
    else:
        if sys.platform == 'linux':
            import readline

            completions = Completer()
            readline.set_completer(completions.complete)
            readline.parse_and_bind('tab: complete')

        while True:
            args = input('[rpscrape]> ').lower().strip()
            args = parser.parse_args_interactive([arg.strip() for arg in args.split()])

            if args:
                if 'dates' in args:
                    race_urls = get_race_urls_date(args['dates'], args['region'])
                else:
                    race_urls = get_race_urls(args['tracks'], args['years'], args['type'])

                scrape_races(
                    race_urls,
                    args['folder_name'],
                    args['file_name'],
                    file_extension,
                    args['type'],
                    file_writer,
                )


if __name__ == '__main__':
    main()
