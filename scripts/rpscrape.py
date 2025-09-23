#!/usr/bin/env python3

import gzip
import requests
import os
import sys

from dataclasses import dataclass

from lxml import html
from orjson import loads
from datetime import date

from utils.argparser import ArgParser
from utils.completer import Completer
from utils.header import RandomHeader
from utils.race import Race, VoidRaceError
from utils.settings import Settings
from utils.update import Update

from utils.course import course_name, courses
from utils.lxml_funcs import xpath

settings = Settings()
random_header = RandomHeader()


@dataclass
class RaceList:
    course_id: str
    course_name: str
    url: str


def check_for_update():
    update = Update()

    if update.available():
        choice = input('Update available. Do you want to update? Y/N ')
        if choice.lower() != 'y':
            return

        if update.pull_latest():
            print('Updated successfully.')
        else:
            print('Failed to update.')

        sys.exit()


def get_race_urls(tracks: list[tuple[str, str]], years: list[str], code: str) -> list[str]:
    url_course_base = 'https://www.racingpost.com:443/profile/course/filter/results'
    url_result_base = 'https://www.racingpost.com/results'
    urls: set[str] = set()

    for course_id, course in tracks:
        for year in years:
            race_list_url = f'{url_course_base}/{course_id}/{year}/{code}/all-races'
            race_list = RaceList(course_id, course, race_list_url)

            response = requests.get(race_list.url, headers=random_header.header())
            data = loads(response.text).get('data', {})
            races = data.get('principleRaceResults', [])

            for race in races:
                race_date = race['raceDatetime'][:10]
                race_id = race['raceInstanceUid']
                race_url = f'{url_result_base}/{race_list.course_id}/{race_list.course_name}/{race_date}/{race_id}'
                urls.add(race_url.replace(' ', '-').replace("'", ''))

    return sorted(urls)


def get_race_urls_date(dates: list[date], region: str) -> list[str]:
    urls: set[str] = set()
    course_ids: set[str] = {course[0] for course in courses(region)}

    for race_date in dates:
        url = f'https://www.racingpost.com/results/{race_date}'
        response = requests.get(url, headers=random_header.header())
        doc = html.fromstring(response.content)

        races = xpath(doc, 'a', 'link-listCourseNameLink')
        for race in races:
            course_id = race.attrib['href'].split('/')[2]
            if course_id in course_ids:
                urls.add(f'https://www.racingpost.com{race.attrib["href"]}')

    return sorted(urls)


def scrape_races(races, folder_name, file_name, file_extension, code, file_writer):
    out_dir = f'../data/{folder_name}/{code}'

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    file_path = f'{out_dir}/{file_name}.{file_extension}'

    with file_writer(file_path) as csv:
        csv.write(settings.csv_header + '\n')

        for url in races:
            r = requests.get(url, headers=random_header.header())
            doc = html.fromstring(r.content)

            try:
                race = Race(url, doc, code, settings.fields)
            except VoidRaceError:
                continue

            if code == 'flat':
                if race.race_info['type'] != 'Flat':
                    continue
            elif code == 'jumps':
                if race.race_info['type'] not in {'Chase', 'Hurdle', 'NH Flat'}:
                    continue

            for row in race.csv_data:
                csv.write(row + '\n')

        print(
            f'Finished scraping.\n{file_name}.{file_extension} saved in rpscrape/{out_dir.lstrip("../")}'
        )


def writer_csv(file_path: str):
    return open(file_path, 'w', encoding='utf-8')


def writer_gzip(file_path: str):
    return gzip.open(file_path, 'wt', encoding='utf-8')


def main():
    if settings.toml is None:
        sys.exit()

    if settings.toml['auto_update']:
        check_for_update()

    file_extension = 'csv'
    file_writer = writer_csv

    if settings.toml.get('gzip_output', False):
        file_extension = 'csv.gz'
        file_writer = writer_gzip

    parser = ArgParser()

    if len(sys.argv) > 1:
        args = parser.parse_args(sys.argv[1:])

        if args.date and args.region:
            folder_name = 'dates/' + args.region
            file_name = args.date.replace('/', '_')
            race_urls = get_race_urls_date(parser.dates, args.region)
        else:
            folder_name = args.region if args.region else course_name(args.course)
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
