#!/usr/bin/env python3
#
# Scrapes results and saves them in csv format

import os
import sys
import json
import requests
from lxml import html

def print_usage():
    print('\n'.join([
        'Usage:',
        '   rpscrape.py [-r|-c] [region|course] [-y] [year|range] [flat|jumps]',
        '',     
        'Example:',
        '   ./rpscrape.py -r ire -y 1999 -f',
        '   ./rpscrape.py -c 2 -y 2015-2018 --jumps',
        '   ./rpscrape.py -c all -r 1998-2018 --flat',
        '',
        'Flags:',
        '    -r, --region           Scrape a specific region',
        '    -c, --course           Scrape a specific course',
        '    -y, --year             Year or range of years to scrape',
        '    -f, --flat             Flat races only',
        '    -j, --jumps            Jump races only',

        '',
        'More info:',
        '    --regions              List all available region codes',
        '    --regions [search]     List regions matching search term',
        '    --courses              List all courses',
        '    --courses [search]     List courses matching search term',
        '    --courses-[region]     List courses in region - e.g --courses-ire',
        ''
    ]))
    sys.exit()


def get_courses(region='all'):
    with open('../courses/{}_course_ids'.format(region), 'r') as courses:
        yield ((course.split('-')[0].strip(), course.split('-')[1].strip()) for course in courses)
         

def get_course_name(code):
    if code.isalpha():
        return code
    else:
        courses = get_courses()
        for course in courses:
            for c in course:
                if c[0] == code:
                    return c[1].replace('()', '').replace(' ', '-')


def course_search(term):
    courses = get_courses()
    for course in courses:
        for c in course:
            if term.lower() in c.lower():
                print_course(c[0], c[1])
    sys.exit()


def print_course(key, course):
    if len(key) == 5:
        print('     CODE: {}| {}'.format(key, course))
    elif len(key) == 4:
        print('     CODE: {} | {}'.format(key, course))
    elif len(key) == 3:
        print('     CODE: {}  | {}'.format(key, course))
    elif len(key) == 2:
        print('     CODE: {}   | {}'.format(key, course))
    else:
        print('     CODE: {}    | {}'.format(key, course))


def print_courses(region='all'):
    courses = get_courses(region)
    for course in courses:
        for c in course:
            print_course(c[0], c[1])
    sys.exit()


def validate_course(course):
    courses = get_courses()
    return course in [c[0] for course in courses for c in course]


def x_y():
    import base64
    return base64.b64decode('aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb206NDQzL3Byb2ZpbGUvY291cnNlL2ZpbHRlci9yZXN1bHRz')\
    .decode('utf-8'), base64.b64decode('aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb20vcmVzdWx0cw==').decode('utf-8')


def get_regions():
    with open('../courses/_countries', 'r') as regions:
        return json.load(regions)


def region_search(term):
    regions = get_regions()
    for key, region in regions.items():
        if term.lower() in region.lower():
            print_region(key, region)
    sys.exit()


def print_region(key, region):
    if len(key) == 3:
        print('     CODE: {} | {}'.format(key, region))
    else:
        print('     CODE: {}  | {}'.format(key, region))


def print_regions():
    regions = get_regions()
    for key, region in regions.items():
        print_region(key, region)
    sys.exit()


def validate_region(region):
    regions = get_regions()
    return region in regions.keys()


def validate_years(years):
    for year in years:
        if year.isdigit() and int(year) > 1995 and int(year) < 2019:
            return True
    return False


def get_races(tracks, names, years, code,  xy):
    for track, name in zip(tracks, names):
        for year in years:
            r = requests.get('{}/{}/{}/{}/all-races'.format(xy[0], track, year, code), headers={"User-Agent": "Mozilla/5.0"})
            results = r.json()
            try:
                for result in results['data']['principleRaceResults']:
                    yield ('{}/{}/{}/{}/{}'.format(xy[1], track, name, result['raceDatetime'][:10], result['raceInstanceUid']))
            except TypeError:
                pass


def main():
    if len(sys.argv) == 6:
        if sys.argv[1] == '-r' or sys.argv[1] == '--region':
            region = sys.argv[2].lower()
            if not validate_region(region):
                sys.exit(print('Invalid region code. Use --regions [search term] to find a valid code.\n'))
        elif sys.argv[1] == '-c' or sys.argv[1] == '--course':
            course = sys.argv[2]
            if not validate_course(course):
                sys.exit(print('Invalid course code. Use --courses [search term] to find a valid code.\n'))
        else:
            print_usage()

        if sys.argv[3] == '-y' or sys.argv[3] == '--year':
            if '-' in sys.argv[4]:
                years = [str(x) for x in range(int(sys.argv[4].split('-')[0]), int(sys.argv[4].split('-')[1]) + 1)]
            else:
                years = [sys.argv[4]]

            if not validate_years(years):
                sys.exit(print('Invalid year, must be in range 1996-2018.\n'))
        else:
            print_usage()

        if '-f' in sys.argv[5]:
            code = 'flat'
        elif '-j' in sys.argv[5]:
            code = 'jumps'
        else:
            sys.exit(print('Invalid racing code. For flat races use -f or --flat. For jump races use -j or --jumps.\n'))
    elif len(sys.argv) == 2:
        if sys.argv[1] == '--regions':
            print_regions()
        elif sys.argv[1] == '--courses':
            print_courses()
        elif '--courses-' in sys.argv[1]:
            if validate_region(sys.argv[1].split('-')[-1]):
                print_courses(sys.argv[1].split('-')[-1])
            else:
                sys.exit(print('Invalid region code. Use --regions [search term] to find a valid code.\n'))
        else:
            print_usage()
    elif len(sys.argv) == 3:
        if sys.argv[1] == '--regions':
            region_search(sys.argv[2])
        elif sys.argv[1] == '--courses':
            course_search(sys.argv[2])
    else:
        print_usage()

    if 'region' in locals():
        courses = get_courses(region)
        tracks = [c[0] for course in courses for c in course]
        names = [get_course_name(track) for track in tracks]
        scrape_target = region
    else:
        tracks = [course]
        names = [get_course_name(course)]
        scrape_target = course

    races = get_races(tracks, names, years, code, x_y())

    if not os.path.exists('../data'):
        os.makedirs('../data')

    with open('../data/{}-{}.csv'.format(get_course_name(scrape_target).lower(), sys.argv[4]), 'w') as csv:
        csv.write(('"date","time","race_name","class","band","distance","going","pos","draw","btn","name",'
            '"sp","age","weight","gear","jockey","trainer","or","ts","rpr","prize","comment"\n'))
            
        for race in races:
            r = requests.get(race, headers={'User-Agent': 'Mozilla/5.0'})
            doc = html.fromstring(r.content)

            try:
                date = doc.xpath("//span[@data-test-selector='text-raceDate']/text()")[0]
            except IndexError:
                date = 'not found'
            try:
                time = doc.xpath("//span[@data-test-selector='text-raceTime']/text()")[0]
            except IndexError:
                time = 'not found'

            try:
                race = doc.xpath("//h2[@class='rp-raceTimeCourseName__title']/text()")[0].strip().strip('\n').replace(',', ' ')
            except IndexError:
                race = 'not found'
            if '(Group 1)' in race:
                r_class = 'Group 1'
                race = race.replace('(Group 1)', '')
            elif '(Group 2)' in race:
                r_class = 'Group 2'
                race = race.replace('(Group 2)', '')
            elif '(Group 3)' in race:
                r_class = 'Group 3'
                race = race.replace('(Group 3)', '')
            elif '(Listed Race)' in race:
                r_class = 'Listed'
                race = race.replace('(Listed Race)', '')
            else:
                try:
                    r_class = doc.xpath("//span[@class='rp-raceTimeCourseName_class']/text()")[0].strip().strip('()')
                except:
                    r_class = 'not found'

            try:
                band = doc.xpath("//span[@class='rp-raceTimeCourseName_ratingBandAndAgesAllowed']/text()")[0].strip().strip('()')
            except:
                band = 'not found'
            if ',' in band:
                split_band = band.split(',')
                band = split_band[1]
                r_class = split_band[0]
            if '(Fillies)' in race:
                band = band + ' Fillies'
                race = race.replace('(Fillies)', '')
            elif 'Fillies' in race:
                band = band + ' Fillies'
            elif '(Colts & Geldings)' in race:
                band = band + ' Colts & Geldings'
                race = race.replace('(Colts & Geldings)', '')

            try:
                distance = doc.xpath("//span[@class='rp-raceTimeCourseName_distance']/text()")[0].strip()
            except IndexError:
                distance = 'not found'
            dist = ''.join([d.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75') for d in distance])

            try:
                going = doc.xpath("//span[@class='rp-raceTimeCourseName_condition']/text()")[0].strip()
            except IndexError:
                going ='not found'

            coms = doc.xpath("//tr[@class='rp-horseTable__commentRow ng-cloak']/td/text()")
            com = [x.strip().replace('  ', '').replace(',', ' -') for x in coms]
            possy = doc.xpath("//span[@data-test-selector='text-horsePosition']/text()")
            del possy[1::2]
            pos = [x.strip() for x in possy]
            prizes = doc.xpath("//div[@data-test-selector='text-prizeMoney']/text()")
            prize = [p.strip().replace(",", '') for p in prizes]
            try:
                del prize[0]
                for i in range(len(pos) - len(prize)):
                    prize.append('')
            except IndexError:
                prize = ['' for x in range(len(pos))]    
            draw = doc.xpath("//sup[@class='rp-horseTable__pos__draw']/text()")
            beaten = doc.xpath("//span[@class='rp-horseTable__pos__length']/span/text()")
            del beaten[1::2]
            btn = [b.strip().strip("[]").replace('¼', '.25').replace('½', '.5').replace('¾', '.75') for b in beaten]
            btn.insert(0, '')
            name = doc.xpath("//a[@data-test-selector='link-horseName']/text()")
            sp = doc.xpath("//span[@class='rp-horseTable__horse__price']/text()")
            jock = doc.xpath("//a[@data-test-selector='link-jockeyName']/text()")
            del jock[::2]
            trainer = doc.xpath("//a[@data-test-selector='link-trainerName']/text()")
            del trainer[::2]
            age = doc.xpath("//td[@data-test-selector='horse-age']/text()")
            _or = doc.xpath("//td[@data-ending='OR']/text()")
            ts = doc.xpath("//td[@data-ending='TS']/text()")
            rpr = doc.xpath("//td[@data-ending='RPR']/text()")
            st = doc.xpath("//span[@data-ending='st']/text()")
            lb = doc.xpath("//span[@data-ending='lb']/text()")
            wgt = [a.strip() +'-' + b.strip() for a, b in zip(st, lb)]
            headgear = doc.xpath("//td[contains(@class, 'rp-horseTable__wgt')]")
            gear = []
            for h in headgear:
                span = h.find('span[@class="rp-horseTable__headGear"]')
                if span is not None:
                    gear.append(span.text)
                else:
                    gear.append('')

            for p, pr, dr, bt, n, s, j, tr, a, o, t, rp, w, g, c in \
            zip(pos, prize, draw, btn, name, sp, jock, trainer, age, _or, ts, rpr, wgt, gear, com):
                csv.write('''{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'''
                    .format(date, time, race, r_class, band, dist, going, p.strip(), 
                            dr.strip().strip("()"),bt, n.strip(), s.strip(), a.strip(),
                            w,g.strip(), tr.strip(), j.strip(), o.strip(), t.strip(), rp.strip(), pr,c))


if __name__ == '__main__':
        main()
