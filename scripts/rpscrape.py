#!/usr/bin/env python3

import gzip
import requests
import os
import sys

from dataclasses import dataclass

from lxml import html
from orjson import loads

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
        if choice.lower() != 'y': return

        if update.pull_latest():
            print('Updated successfully.')
        else:
            print('Failed to update.')

        sys.exit()


def get_race_urls(tracks, years, code):
    urls = set()

    url_course = 'https://www.racingpost.com:443/profile/course/filter/results'
    url_result = 'https://www.racingpost.com/results'

    race_lists = []

    for track in tracks:
        for year in years:
            race_list = RaceList(*track, f'{url_course}/{track[0].lower()}/{year}/{code}/all-races')
            race_lists.append(race_list)

    for race_list in race_lists:
        r = requests.get(race_list.url, headers=random_header.header())
        races = loads(r.text)['data']['principleRaceResults']

        if races:
            for race in races:
                race_date = race["raceDatetime"][:10]
                race_id = race["raceInstanceUid"]
                url = f'{url_result}/{race_list.course_id}/{race_list.course_name}/{race_date}/{race_id}'
                urls.add(url.replace(' ', '-').replace("'", ''))

    return sorted(list(urls))


def get_race_urls_date(dates, region):
    urls = set()

    days = [f'https://www.racingpost.com/results/{d}' for d in dates]

    course_ids = {course[0] for course in courses(region)}

    for day in days:
        r = requests.get(day, headers=random_header.header())
        doc = html.fromstring(r.content)

        races = xpath(doc, 'a', 'link-listCourseNameLink')

        for race in races:
            if race.attrib['href'].split('/')[2] in course_ids:
                urls.add('https://www.racingpost.com' + race.attrib['href'])

    return sorted(list(urls))


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

        print(f'Finished scraping.\n{file_name}.{file_extension} saved in rpscrape/{out_dir.lstrip("../")}')


def writer_csv(file_path):
    return open(file_path, 'w', encoding='utf-8')


def writer_gzip(file_path):
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

        if args.date:
            folder_name = 'dates/' + args.region
            file_name = args.date.replace('/', '_')
            races = get_race_urls_date(parser.dates, args.region)
        else:
            folder_name = args.region if args.region else course_name(args.course)
            file_name = args.year
            races = get_race_urls(parser.tracks, parser.years, args.type)

        scrape_races(races, folder_name, file_name, file_extension, args.type, file_writer)
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
                    races = get_race_urls_date(args['dates'], args['region'])
                else:
                    races = get_race_urls(args['tracks'], args['years'], args['type'])

                scrape_races(races, args['folder_name'], args['file_name'], file_extension, args['type'], file_writer)


if __name__ == '__main__':
    main()
