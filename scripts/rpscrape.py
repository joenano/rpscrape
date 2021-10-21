#!/usr/bin/env python3

import asyncio
import os
import sys

from orjson import loads

from utils.argparser import ArgParser
from utils.completer import Completer
from utils.race import Race, VoidRaceError
from utils.settings import Settings

from utils.async_funcs import get_documents, get_jsons
from utils.course import course_name, courses


settings = Settings()


def get_race_urls(tracks, years, code):
    urls = set()
    courses = []
    
    course_url = 'https://www.racingpost.com:443/profile/course/filter/results'
    result_url = 'https://www.racingpost.com/results'

    for track in tracks:
        for year in years:
            courses.append((track, f'{course_url}/{track[0]}/{year}/{code}/all-races'))

    races = asyncio.run(get_jsons(courses))

    for race in races:
        results = loads(race[1])['data']['principleRaceResults']

        if results:
            for result in results:
                url = f'{result_url}/{race[0][0]}/{race[0][1]}/{result["raceDatetime"][:10]}/{result["raceInstanceUid"]}'
                urls.add(url.replace(' ', '-').replace("'", ''))

    return sorted(list(urls))


def get_race_urls_date(dates, region):
    urls = set()

    days = [f'https://www.racingpost.com/results/{d}' for d in dates]
    docs = asyncio.run(get_documents(days))
    
    course_ids = {course[0] for course in courses(region)}
    
    for doc in docs:
        race_links = doc[1].xpath('//a[@data-test-selector="link-listCourseNameLink"]')

        for race in race_links:
            if race.attrib['href'].split('/')[2] in course_ids:
                urls.add('https://www.racingpost.com' + race.attrib['href'])

    return sorted(list(urls))


def scrape_races(races, folder_name, file_name, code):
    if not os.path.exists(f'../data/{folder_name}/{code}'):
        os.makedirs(f'../data/{folder_name}/{code}')

    with open(f'../data/{folder_name}/{code}/{file_name}.csv', 'w', encoding='utf-8') as csv:

        csv.write(settings.field_str + '\n')

        docs = asyncio.run(get_documents(races))

        for doc in docs:
            try:
                race = Race(doc, code, settings.fields)
            
                for row in race.csv_data:
                    csv.write(row + '\n')
                
            except VoidRaceError:
                continue

        print(f'Finished scraping.\n{file_name}.csv saved in rpscrape/data/{folder_name}/{code}')


def check_for_update():
    try:
        from git import Repo, cmd

        if 'local out of date' in cmd.Git('..').execute(['git', 'remote', 'show', 'origin']).lower():
            x = input('Update available. Do you want to update? Y/N ')

            if x.lower() == 'y':
                Repo('..').remote(name='origin').pull()

                if 'up to date' in cmd.Git('..').execute(['git', 'remote', 'show', 'origin']).lower():
                    print('Updated successfully.')
                    sys.exit()
                else:
                    print('Failed to update.')
                    sys.exit()
    except ModuleNotFoundError:
        print('gitpython module not found.\n\n'
              'Install: "pip3 install gitpython" or disable auto update in settings.')
        sys.exit()


def main():
    if not settings:
        sys.exit()
    
    if settings.toml['auto_update']:
        check_for_update()
    
    if sys.version_info[0] == 3 and sys.version_info[1] >= 7 and sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
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

        scrape_races(races, folder_name, file_name, args.type)
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
                    
                scrape_races(races, args['folder_name'], args['file_name'], args['type'])


if __name__ == '__main__':
    main()
