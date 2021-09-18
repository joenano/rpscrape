#!/usr/bin/env python3

import aiohttp
import argparse
import asyncio
from datetime import date, timedelta, datetime
import json
from lxml import html
import os
from re import search
import requests
import sys
import toml


class Completer:
    def __init__(self, options):
        self.options = sorted(options)
        self.matches = []

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            return self.matches[state]
        except IndexError:
            return None


def options(opt='help'):
    opts = "\n".join(
        [
            "       regions              List all available region codes",
            "       regions [search]     Search for specific country code",
            "",
            "       courses              List all courses",
            "       courses [search]     Search for specific course",
            "       courses [region]     List courses in region - e.g courses ire",
            "",
            "       -d, date             Scrape race by date - e.g -d 2019/12/17 gb",
        ]
    )

    if opt == 'help' or opt == '?':
        print("\n".join(
            [
                "  Usage:",
                "       ~$ ./rpscrape.py"
                "       [rpscrape]> [region|course] [year|range] [flat|jumps]",
                "",
                "       Regions have alphabetic codes.",
                "       Courses have numeric codes.",
                "",
                "  Examples:",
                "       [rpscrape]> ire 1999 flat",
                "       [rpscrape]> gb 2015-2018 jumps",
                "       [rpscrape]> 533 1998-2018 flat",
                "",
                "  Options:",
                "{}".format(opts),
                "",
                "  More info:",
                "       help            Show help",
                "       options         Show options",
                "       cls, clear      Clear screen",
                "       q, quit, exit   Quit",
                "",
            ]
        ))
    else:
        print(opts)


def substr_match(s, lst):
    return any(x.lower() in s.lower() for x in lst)


def get_region(course_id):
    courses = json.load(open('../courses/_courses', 'r'))
    courses.pop('all')

    for region, course in courses.items():
        for id in course.keys():
            if id == course_id:
                return region.upper()


def courses(code='all'):
    courses = json.load(open('../courses/_courses', 'r'))
    
    for id, course in courses[code].items():
        yield id, course


def course_name(code):
    if code.isalpha():
        return code
    for course in courses():
        if course[0] == code:
            return course[1].replace(' ', '-')


def course_search(term):
    for course in courses():
        if term.lower() in course[1].lower():
            print_course(course[0], course[1])


def print_course(code, course):
    print(f'     CODE: {code}{" " * (6 - len(code))}|  {course}')


def print_courses(code='all'):
    for course in courses(code):
        print_course(course[0], course[1])


def valid_course(code):
    return code in [course[0] for course in courses()]


def x_y():
    from base64 import b64decode
    return b64decode(
        'aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb206NDQzL3Byb2ZpbGUvY291cnNlL2ZpbHRlci9yZXN1bHRz'
    ).decode('utf-8'), b64decode('aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb20vcmVzdWx0cw==').decode('utf-8')


def regions():
    return json.load(open('../courses/_regions', 'r'))


def region_search(term):
    for code, region in regions().items():
        if term.lower() in region.lower():
            print_region(code, region)


def print_region(code, region):
    print(f'     CODE: {code}{" " * (5 - len(code))}|  {region}')


def print_regions():
    for code, region in regions().items():
        print_region(code, region)


def valid_region(code):
    return code in regions().keys()


def valid_years(years):
    if years:
        return all(year.isdigit() and 1987 <= int(year) <= int(datetime.today().year) for year in years)

    return False


def valid_date(date):
    if len(date.split('/')) == 3:
        try:
            year, month, day = [int(x) for x in date.split('/')]
            return 1987 <= year <= int(datetime.today().year) and 0 < month <= 12 and 0 < day <= 31
        except ValueError:
            return False

    return False


def check_date(date):
    if '-' in date and len(date.split('-')) < 3:
        return valid_date(date.split('-')[0]) and valid_date(date.split('-')[1])

    return valid_date(date)


def fraction_to_decimal(fractions):
    decimal = []
    for fraction in fractions:
        if fraction == '' or fraction == 'No Odds' or fraction == '&':
            decimal.append('')
        elif 'evens' in fraction.lower() or fraction.lower() == 'evs':
            decimal.append('2.00')
        else:
            decimal.append('{0:.2f}'.format(float(fraction.split('/')[0]) / float(fraction.split('/')[1]) + 1.00))

    return decimal


def convert_date(date):
    dmy = date.split('-')
    return dmy[0] + '-' + dmy[1] + '-' + dmy[2]


def distance_to_decimal(dist):
    return (
        dist.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75').replace('snk', '0.2')
        .replace('nk', '0.3').replace('sht-hd', '0.1').replace('shd', '0.1').replace('hd', '0.2')
        .replace('nse', '0.05').replace('dht', '0').replace('dist', '30')
    )


def pedigree_info(pedigrees):
    clean_name = lambda name: name.replace('.', ' ').replace('  ', ' ').replace(',', '')

    sires, dams, damsires = [], [], []

    for p in pedigrees:
        ped_info = p.findall('a')

        if '-' in p.text_content():
            if len(ped_info) > 0:
                sire = ped_info[0].text.strip()

                if '(' in sire:
                    sire = sire.split('(')[0].strip() + ' (' + sire.split('(')[1]
                else:
                    sire = sire + ' (GB)'
                sires.append(clean_name(sire))
            else:
                sires.append('')

            if len(ped_info) > 1:
                dam = ped_info[1].text.strip()
                dam_nat = ped_info[1].find('span').text

                if dam_nat is not None:
                    dam = dam + ' ' + dam_nat.strip()
                else:
                    dam = dam + ' (GB)'
                dams.append(clean_name(dam))
            else:
                dams.append('')

            if len(ped_info) > 2:
                damsire = ped_info[2].text.strip().strip('()')
                if damsire == 'Damsire Unregistered':
                    damsire = ''
                damsires.append(clean_name(damsire))
            else:
                damsires.append('')
        else:
            sires.append('')

            if len(ped_info) > 0:
                dam = ped_info[0].text.strip()
                dam_nat = ped_info[0].find('span').text

                if dam_nat is not None:
                    dam = dam + ' ' + dam_nat.strip()
                else:
                    dam = dam + ' (GB)'
                dams.append(clean_name(dam))
            else:
                dams.append('')

            if len(ped_info) > 1:
                damsire = ped_info[1].text.strip().strip('()')
                if damsire == 'Damsire Unregistered':
                    damsire = ''
                damsires.append(clean_name(damsire))
            else:
                damsires.append('')

    return sires, dams, damsires


def class_from_rating_band(rating_band, code):
    try:
        upper = int(rating_band.split('-')[1])
    except:
        return ''

    if code == 'flat':
        if upper >= 100:
            return 'Class 2'
        if upper >= 90:
            return 'Class 3'
        if upper >= 80:
            return 'Class 4'
        if upper >= 70:
            return 'Class 5'
        if upper >= 60:
            return 'Class 6'
        if upper >= 40:
            return 'Class 7'
    else:
        if upper >= 140:
            return 'Class 2'
        if upper >= 120:
            return 'Class 3'
        if upper >= 100:
            return 'Class 4'
        if upper >= 85:
            return 'Class 5'

    return ''


def clean_race_name(race):
    clean_race = lambda race, x, y = '': race.replace(x, '').replace(y, '').replace('()', '').replace('  ', ' ').strip()

    if 'Class' in race:
        if substr_match(race, ['class a', 'class 1']):
            return clean_race(race, 'Class A', 'Class 1')
        if substr_match(race, ['class b', 'class 2']):
            return clean_race(race, 'Class B', 'Class 2')
        if substr_match(race, ['class c', 'class 3']):
            return clean_race(race, 'Class C', 'Class 3')
        if substr_match(race, ['class d', 'class 4']):
            return clean_race(race, 'Class D', 'Class 4')
        if substr_match(race, ['class e', 'class 5']):
            return clean_race(race, 'Class E', 'Class 5')
        if substr_match(race, ['class f', 'class 6']):
            return clean_race(race, 'Class F', 'Class 6')
        if substr_match(race, ['class h', 'class 7']):
            return clean_race(race, 'Class H', 'Class 7')
        if 'Class G' in race:
            return clean_race(race, 'Class G')

        if 'Trusthouse Forte Mile Guaranteed Minimum Value £60000 (Group' in race:
            return race.replace(race, '(Group')

    if substr_match(race, ['Group', 'Grade']):
        if substr_match(race, ['Group 1', 'Grade 1']):
            return clean_race(race, 'Group 1', 'Grade 1')
        if substr_match(race, ['Group 2', 'Grade 2']):
            return clean_race(race, 'Group 2', 'Grade 2')
        if substr_match(race, ['Group 3', 'Grade 3']):
            return clean_race(race, 'Group 3', 'Grade 3')

    if 'Listed' in race:
        return clean_race(race, 'Listed Race', '(Listed)')

    return race


def try_get_class(race):
    if substr_match(race, ['class a', 'class 1']):
        return 'Class 1'
    if substr_match(race, ['class b', 'class 2']):
        return 'Class 2'
    if substr_match(race, ['class c', 'class 3']):
        return 'Class 3'
    if substr_match(race, ['class d', 'class 4']):
        return 'Class 4'
    if substr_match(race, ['class e', 'class 5']):
        return 'Class 5'
    if substr_match(race, ['class f', 'class 6']):
        return 'Class 6'
    if substr_match(race, ['class h', 'class 7']):
        return 'Class 7'
    if 'Class G' in race:
        return 'Class 6'
    if '(premier handicap)' in race:
        return 'Class 2'

    return ''


def try_get_pattern(race, race_class):
    pattern = ''
    r_class = 'Class 1'

    if 'Forte Mile' in race and '(Group' in race:
        return r_class, 'Group 2'

    if 'Stakis Casinos Scottish Grand National Handicap Chase Class A Guaranteed Minimum Value £60000 Grade' in race:
        return r_class, pattern

    if race.endswith(' (Listed Race Grade'):
        return r_class, 'Listed'

    if '(Group' in race:
        try:
            pattern = search(r'(\(Grou..)\w+', race).group(0).strip('(')
        except AttributeError:
            pattern = search(r'(\(Grou.)\w+', race).group(0).strip('(')
        return r_class, pattern
    if '(Grade' in race:
        try:
            pattern = search(r'(\(Grad..)\w+', race).group(0).strip('(')
        except AttributeError:
            pattern = search(r'(\(Grad.)\w+', race).group(0).strip('(')
        return r_class, pattern
    if 'Grade' in race:
        return r_class, search(r'Grad..\w+', race).group(0)
    if '(Local Group 1)' in race:
        return r_class, 'Group 1'
    if '(Local Group 2)' in race:
        return r_class, 'Group 2'
    if '(Local Group 3)' in race:
        return r_class, 'Group 3'
    if '(Listed' in race or 'listed race' in race.lower():
        return r_class, 'Listed'

    return race_class, pattern


def try_get_race_type(race, race_dist):
    if race_dist >= 12:
        if substr_match(race, ['national hunt flat', 'nh flat race', 'mares flat race']):
            return 'NH Flat'
        if substr_match(race, ['inh bumper', ' sales bumper', 'kepak flat race', 'i.n.h. flat race']):
            return 'NH Flat'

        if substr_match(race, [' hurdle', '(hurdle)']):
            return 'Hurdle'
        if substr_match(race, [' chase', '(chase)', 'steeplechase', 'steeple-chase', 'steeplchase', 'steepl-chase']):
            return 'Chase'

    return ''


def sex_restricted(race):
    if substr_match(race, ['Entire Colts & Fillies', 'Colts & Fillies']):
        return 'C & F'
    elif substr_match(race, ['Fillies & Mares', 'Filles & Mares']):
        return 'F & M'
    elif substr_match(race, ['Fillies']):
        return 'F'
    elif substr_match(race, ['Colts & Geldings', 'Colts/Geldings', '(C & G)']):
        return 'C & G'
    elif '(Mares & Geldings)' in race:
        return 'M & G'
    elif 'Mares' in race:
        return 'M'
    else:
        return ''


def distance_to_furlongs(distance):
    dist = ''.join([d.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75') for d in distance])

    if 'm' in dist:
        if len(dist) > 2:
            dist = int(dist.split('m')[0]) * 8 + float(dist.split('m')[1].strip('f'))
        else:
            dist = int(dist.split('m')[0]) * 8
    else:
        dist = dist.strip('f')

    return float(dist)


def distance_to_metres(distance):
    dist = distance.lower()
    metres = 0

    if 'm' in dist:
        metres += int(dist.split('m')[0]) * 1609.34

    if 'f' in dist:
        metres += int(dist.split('f')[0][-1]) * 201.168

    if 'yds' in dist:
        if 'f' in dist:
            metres += int(dist.split('f')[1].strip('yds')) * .914
        elif 'm' in dist:
            metres += int(dist.split('m')[1].strip('yds')) * .914

    return round(metres)


def parse_years(year_str):
    if '-' in year_str:
        try:
            return [str(x) for x in range(int(year_str.split('-')[0]), int(year_str.split('-')[1]) + 1)]
        except ValueError:
            return []
    else:
        return [year_str]


def get_dates(date_str):
    if '-' in date_str:
        start_year, start_month, start_day = date_str.split('-')[0].split('/')
        end_year, end_month, end_day = date_str.split('-')[1].split('/')

        start_date = date(int(start_year), int(start_month), int(start_day))
        end_date = date(int(end_year), int(end_month), int(end_day))

        return [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    else:
        year, month, day = date_str.split('/')

        return [date(int(year), int(month), int(day))]


def get_race_urls(tracks, years, code, xy):
    urls = []
    for track in tracks:
        for year in years:
            r = requests.get(f'{xy[0]}/{track[0]}/{year}/{code}/all-races', headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                try:
                    results = r.json()
                    if results['data']['principleRaceResults'] == None:
                        print(f'No {code} race data for {course_name(track)} in {year}.')
                    else:
                        for result in results['data']['principleRaceResults']:
                            url = f'{xy[1]}/{track[0]}/{track[1]}/{result["raceDatetime"][:10]}/{result["raceInstanceUid"]}'
                            urls.append(url.replace(' ', '-').replace("'", ''))
                except:
                    pass
            else:
                print(f'Unable to access races from {course_name(track[0])} in {year}')

    return urls


def get_race_urls_async(tracks, years, code, xy):
    urls = []
    courses = []

    for track in tracks:
        for year in years:
            courses.append((track, f'{xy[0]}/{track[0]}/{year}/{code}/all-races'))

    races = asyncio.run(get_jsons(courses))

    for race in races:
        results = json.loads(race[1])['data']['principleRaceResults']

        if results:
            for result in results:
                url = f'{xy[1]}/{race[0][0]}/{race[0][1]}/{result["raceDatetime"][:10]}/{result["raceInstanceUid"]}'
                urls.append(url.replace(' ', '-').replace("'", ''))

    return urls


def get_race_urls_date(dates, region):
    urls = []

    days = [f'https://www.racingpost.com/results/{d}' for d in dates]
    docs = asyncio.run(get_documents(days))

    for doc in docs:
        race_links = doc[1].xpath('//a[@data-test-selector="link-listCourseNameLink"]')

        for race in race_links:
            if 'https://www.racingpost.com' + race.attrib['href'] not in urls:
                if race.attrib['href'].split('/')[2] in [course[0] for course in courses(region)]:
                    urls.append('https://www.racingpost.com' + race.attrib['href'])

    return urls


async def get_jsons(courses):
    session = get_session()
    ret = await asyncio.gather(*[get_json(course, session) for course in courses])
    await session.close()
    return ret


async def get_json(course, session):
    async with session.get(course[1]) as response:
        resp = await response.text()
        return (course[0], resp)


async def get_documents(urls):
    session = get_session()
    ret = await asyncio.gather(*[get_document(url, session) for url in urls])
    await session.close()
    return ret


async def get_document(url, session):
    async with session.get(url) as response:
        resp = await response.text()
        return (url, html.fromstring(resp))


def get_session():
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=50))
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    return session


def calculate_times(win_time, dist_btn, going, code, course, race_type):
    times = []

    if code == 'flat' or race_type == 'flat':
        if going == '':
            lps_scale = 6
        elif substr_match(going, ['firm', 'standard', 'fast', 'hard', 'slow', 'sloppy']):
            if 'southwell' in course.lower():
                lps_scale = 5
            else:
                lps_scale = 6
        elif 'Good' in going:
            if substr_match(going, ['soft', 'yielding']):
                lps_scale = 5.5
            else:
                lps_scale = 6
        elif substr_match(going, ['soft', 'heavy', 'yielding', 'holding']):
            lps_scale = 5
        else:
            lps_scale = 5
    else:
        if going == '':
            lps_scale = 5
        elif substr_match(going, ['firm', 'standard', 'hard', 'fast']):
            if 'southwell' in course.lower():
                lps_scale = 4
            else:
                lps_scale = 5
        elif 'Good' in going:
            if substr_match(going, ['soft', 'yielding']):
                lps_scale = 4.5
            else:
                lps_scale = 5
        elif substr_match(going, ['soft', 'heavy', 'yielding', 'slow', 'holding']):
            lps_scale = 4
        else:
            lps_scale = 5

    for dist in dist_btn:
        try:
            time = (win_time + (float(dist) / lps_scale))
            times.append('{}:{:2.2f}'.format(int(time // 60), time % 60))
        except ValueError:
            times.append('')

    return times


def clean(data):
    return [d.strip().replace('–', '').replace(',', '') for d in data]


def scrape_races(races, target, years, code):
    if not os.path.exists(f'../data/{code}/{target.lower()}/'):
        os.makedirs(f'../data/{code}/{target.lower()}/')

    with open(f'../data/{code}/{target.lower()}/{years}.csv', 'w', encoding='utf-8') as csv:

        csv.write(
            'Date,Region,Course,Off,Name,Type,Class,Pattern,Rating_Band,Age_Band,Sex_Rest,Dist,Dist_Y,Dist_M,Dist_F,'
            'Going,Num,Pos,Ran,Draw,Btn,Ovr_Btn,Horse,SP,Dec,Age,Sex,Wgt,Lbs,HG,Time,Jockey,Trainer,OR,RPR,TS,'
            'Prize,Sire,Dam,Damsire,Owner,Comment\n'
        )

        docs = asyncio.run(get_documents(races))

        for race in docs:
            doc = race[1]
            race = race[0]

            region = get_region(race.split('/')[4])
            course = race.split('/')[5]
            date = convert_date(race.split('/')[6])

            try:
                r_time = doc.xpath("//span[@data-test-selector='text-raceTime']/text()")[0]
            except IndexError:
                r_time = ''

            try:
                race_name = doc.xpath("//h2[@class='rp-raceTimeCourseName__title']/text()")[0].strip().strip('\n') \
                    .replace(',', ' ').replace('"', '').replace('\x80', '').replace('\\x80', '').replace('  ', ' ')
            except IndexError:
                race_name = ''

            try:
                race_class = doc.xpath("//span[@class='rp-raceTimeCourseName_class']/text()")[0].strip().strip('()')
            except IndexError:
                race_class = ''

            if race_class == '':
                race_class = try_get_class(race_name)

            try:
                race_class, pattern = try_get_pattern(race_name, race_class)
            except AttributeError:
                print('try_get_pattern error:')
                print('Race link: ', race)
                print('Race name: ', race_name)
                sys.exit()

            race_name = clean_race_name(race_name)
            race_name = clean_race_name(race_name)

            try:
                band = doc.xpath("//span[@class='rp-raceTimeCourseName_ratingBandAndAgesAllowed']/text()")[0].strip().strip('()')
            except:
                band = ''

            rating_band = ''
            age_band = ''

            if len(band.split(',')) > 1:
                for x in band.split(','):
                    if 'yo' in x:
                        age_band = x.strip()
                    elif '-' in x:
                        rating_band = x.strip()
            else:
                if 'yo' in band:
                    age_band = band.strip()
                elif '-' in band:
                    rating_band = band.strip()

            if race_class == '' and rating_band != '':
                race_class = class_from_rating_band(rating_band, code)

            sex_rest = sex_restricted(race_name)

            try:
                distance = doc.xpath("//span[@data-test-selector='block-distanceInd']/text()")[0].strip()
            except IndexError:
                distance = ''

            try:
                dist_y = doc.xpath("//span[@data-test-selector='block-fullDistanceInd']/text()")[0].strip().strip('()')
            except IndexError:
                dist_y = ''

            try:
                dist_f = distance_to_furlongs(distance)
            except ValueError:
                print('ERROR: distance_to_furlongs()')
                print('Race: ', race)
                sys.exit()

            dist_m = distance_to_metres(dist_y)

            if dist_m == 0:
                dist_m = round(dist_f * 201.168)

            dist_y = round(dist_m * 1.09361)
            dist_f = str(dist_f).replace('.0', '') + 'f'

            try:
                going = doc.xpath("//span[@class='rp-raceTimeCourseName_condition']/text()")[0].strip()
            except IndexError:
                going = ''

            race_type = ''

            if code == 'flat' and 'national hunt flat' not in race_name.lower():
                race_type = 'Flat'
            else:
                try:
                    if 'hurdle' in doc.xpath("//span[@class='rp-raceTimeCourseName_hurdles']/text()")[0].lower():
                        race_type = 'Hurdle'
                    elif 'fence' in doc.xpath("//span[@class='rp-raceTimeCourseName_hurdles']/text()")[0].lower():
                        race_type = 'Chase'
                except IndexError:
                    race_type = try_get_race_type(race_name.lower(), float(dist_f.strip('f')))

            if race_type == '':
                try_get_race_type(race_name.lower(), float(dist_f.strip('f')))

            if race_type == '':
                race_type = 'Flat'

            pedigrees = doc.xpath("//tr[@data-test-selector='block-pedigreeInfoFullResults']/td")
            sires, dams, damsires = pedigree_info(pedigrees)

            sex = []

            for x in pedigrees:
                try:
                    sex.append(x.text.strip().split()[1].upper())
                except IndexError:
                    sex.append(x.text.strip().upper())

            coms = doc.xpath("//tr[@class='rp-horseTable__commentRow ng-cloak']/td/text()")
            coms = [x.strip().replace('  ', '').replace(',', ' -').replace('\n', ' ').replace('\r', '') for x in coms]

            possy = doc.xpath("//span[@data-test-selector='text-horsePosition']/text()")
            del possy[1::2]
            pos = [x.strip() for x in possy]

            prizes = doc.xpath("//div[@data-test-selector='text-prizeMoney']/text()")
            prize = [p.strip().replace(",", '').replace('£', '') for p in prizes]
            
            try:
                del prize[0]
                [prize.append('') for i in range(len(pos) - len(prize))]
            except IndexError:
                prize = ['' for i in range(len(pos))]

            for i, p in enumerate(pos):
                if p == 'DSQ':
                    prize.insert(i, '')
                    prize.pop()

            draw = clean(doc.xpath("//sup[@class='rp-horseTable__pos__draw']/text()"))
            draw = [d.strip("()") for d in draw]

            btn = []
            ovr_btn = []

            for x in doc.xpath("//span[@class='rp-horseTable__pos__length']"):
                distances = x.findall('span')

                if len(distances) == 2:
                    if distances[0].text is None:
                        btn.append('0')
                    else:
                        btn.append(distances[0].text)
                    if distances[1].text is None:
                        ovr_btn.append('0')
                    else:
                        ovr_btn.append(distances[1].text.strip('[]'))
                else:
                    if distances[0].text is None:
                        btn.append('0')
                        ovr_btn.append('0')
                    else:
                        if distances[0].text == 'dht':
                            btn.append(distances[0].text)
                            try:
                                ovr_btn.append(ovr_btn[-1])
                            except IndexError:
                                ovr_btn.append(btn[-1])
                        else:
                            btn.append(distances[0].text)
                            ovr_btn.append(distances[0].text)

            try:
                btn = [distance_to_decimal(b) for b in btn]
            except AttributeError:
                print('btn error: ', race)
                sys.exit()

            ovr_btn = [distance_to_decimal(b) for b in ovr_btn]

            if len(ovr_btn) < len(pos):
                ovr_btn.extend(['' for x in range(len(pos) - len(ovr_btn))])

            if len(btn) < len(pos):
                btn.extend(['' for x in range(len(pos) - len(btn))])

            time_btn = []

            for x, y in zip(btn, ovr_btn):
                try:
                    if float(x) < .25:
                        time_btn.append(str(float(x) + float(y)))
                    else:
                        time_btn.append(y)
                except ValueError:
                    time_btn.append(y)

            numbers = [x.strip('.') for x in doc.xpath("//span[@class='rp-horseTable__saddleClothNo']/text()")]

            try:
                ran = doc.xpath(
                    "//span[@class='rp-raceInfo__value rp-raceInfo__value_black']/text()"
                )[0].replace('ran', '').strip('\n').strip()
            except IndexError:
                if possy[0].strip() == 'VOI':
                    continue
                ran = len(numbers)

            horse_nat = doc.xpath("//span[@class='rp-horseTable__horse__country']/text()")
            nats = []
            for nat in horse_nat:
                if nat.strip() == '':
                    nats.append('(GB)')
                else:
                    nats.append(nat.strip())

            names = clean(doc.xpath("//a[@data-test-selector='link-horseName']/text()"))

            profiles = doc.xpath("//a[@data-test-selector='link-horseName']/@href")
            profiles = [p.replace('/profile/horse/', '') for p in profiles]

            sps = clean(doc.xpath("//span[@class='rp-horseTable__horse__price']/text()"))
            sps = [x.replace('No Odds', '') for x in sps]

            jock = clean(doc.xpath("//a[@data-test-selector='link-jockeyName']/text()"))
            del jock[::2]

            trainer = clean(doc.xpath("//a[@data-test-selector='link-trainerName']/text()"))
            del trainer[1::2]
            del trainer[1::2]

            owners = doc.xpath("//a[@data-test-selector='link-silk']")
            owners = [x.attrib['href'].split('/')[-1].replace('-', ' ').title() for x in owners]

            silks = doc.xpath("//img[@class='rp-horseTable__silk']")
            silks = [s.attrib['src'] for s in silks]

            age = clean(doc.xpath("//td[@data-test-selector='horse-age']/text()"))
            age = [a.replace('-', '.') for a in age]

            _or = clean(doc.xpath("//td[@data-ending='OR']/text()"))
            ts = clean(doc.xpath("//td[@data-ending='TS']/text()"))
            rpr = clean(doc.xpath("//td[@data-ending='RPR']/text()"))

            st = doc.xpath("//span[@data-ending='st']/text()")
            lb = doc.xpath("//span[@data-ending='lb']/text()")
            wgt = [a.strip() + '-' + b.strip() for a, b in zip(st, lb)]
            lbs = [int(a.strip()) * 14 + int(b.strip()) for a, b in zip(st, lb)]

            headgear = doc.xpath("//td[contains(@class, 'rp-horseTable__wgt')]")
            gear = []
            for h in headgear:
                span = h.find('span[@class="rp-horseTable__headGear"]')
                if span is not None:
                    try:
                        gear.append(span.text + span[1].text.strip())
                    except:
                        gear.append(span.text)
                else:
                    gear.append('')

            info = doc.xpath('//div[@class="rp-raceInfo"]')[0].find('.//li').findall('.//span[@class="rp-raceInfo__value"]')

            times = []

            if len(info) == 3:
                winning_time = clean(info[1].text.split("("))[0].split()

                if winning_time[0] == '0.0.00s' or winning_time[0] == '0.00s':
                    try:
                        winning_time = info[1].text.split("(")[1].lower().replace('fast by', '').strip().strip(')').split()
                    except IndexError:
                        times = ['-' for i in range(len(pos))]

            elif len(info) == 2:
                winning_time = info[0].text.split("(")[0].split()

                if winning_time[0] == '0.0.00s' or winning_time[0] == '0.00s':
                    try:
                        winning_time = info[0].text.split("(")[1].lower().replace('fast by', '').strip().strip(')').split()
                    except IndexError:
                        times = ['-' for i in range(len(pos))]
            else:
                print(f'ERROR: (winning time) {date} {course_name} {r_time}.')

            if winning_time == [] or winning_time == ['standard', 'time']:
                times = ['-' for i in range(len(pos))]

            if not times:
                if len(winning_time) > 1:
                    try:
                        win_time = float(winning_time[0].replace("m", '')) * 60 + float(winning_time[1].strip("s"))
                    except ValueError:
                        print('ERROR: winning time')
                        print(race)
                        sys.exit()
                else:
                    try:
                        win_time = float(winning_time[0].strip("s"))
                    except ValueError:
                        print(f'ERROR: (winning time){winning_time[0]}.')
                        print(race)
                        sys.exit()

                times = calculate_times(win_time, time_btn, going, code, course, race_type)

            dec = fraction_to_decimal([sp.strip('F').strip('J').strip('C').strip() for sp in sps])

            race_name = race_name.replace("'", '')

            for num, p, pr, dr, bt, ovr_bt, name, nat, sp, dc, time, j, tr, a, s, o, rp, t, w, l, g, com, sire, dam, damsire, owner in \
                    zip(numbers, pos, prize, draw, btn, ovr_btn, names, nats, sps, dec, times, jock, trainer, age, sex, _or, rpr, ts,
                        wgt, lbs, gear, coms, sires, dams, damsires, owners):
                sire = sire.replace("'", '')
                dam = dam.replace("'", '')
                damsire = damsire.replace("'", '')
                j = j.replace("'", '')
                tr = tr.replace("'", '')
                com = com.replace('\n', '').strip()

                if not p.isnumeric() and p != 'DSQ':
                    time = '-'
                    sec = '-'
                    ovr_bt = '-'
                    bt = '-'

                csv.write((
                    f'{date},{region},{course},{r_time},{race_name},{race_type},{race_class},{pattern},'
                    f'{rating_band},{age_band},{sex_rest},{distance},{dist_y},{dist_m},{dist_f},'
                    f'{going},{num},{p},{ran},{dr},{bt},{ovr_bt},{name} {nat},{sp},{dc},{a},{s},{w},'
                    f'{l},{g},{time},{j},{tr},{o},{rp},{t},{pr},{sire},{dam},{damsire},{owner},{com}\n'
                ))

        print(f'\nFinished scraping. {years}.csv saved in rpscrape/data/{code}/{target.lower()}')


def parse_args(args=sys.argv):
    if len(args) == 1:
        if 'help' in args or 'options' in args or '?' in args:
            options(args[0])
        elif 'clear' in args or 'cls' in args or 'clr' in args:
            os.system('cls' if os.name == 'nt' else 'clear')
        elif 'quit' in args or 'q' in args or 'exit' in args:
            sys.exit()
        elif 'regions' in args:
            print_regions()
        elif 'courses' in args:
            print_courses()
    elif len(args) >= 2 and args[0].startswith('region'):
        region_search(' '.join(args[1:]))
    elif len(args) >= 2 and args[0].startswith('course'):
        if valid_region(args[1]):
            print_courses(args[1])
        else:
            course_search(' '.join(args[1:]))
    elif len(args) == 3:
        if args[0] == '-d' or args[0] == 'date':
            region_code = args[2]

            if not valid_region(region_code):
                return print('Invalid region.')

            if check_date(args[1]):
                dates = get_dates(args[1])
                races = get_race_urls_date(dates, region_code)
                scrape_races(races, region_code, args[1].replace('/', '_'), '')
            else:
                return print('Invalid date. Expected format: YYYY/MM/DD')
        else:
            if valid_region(args[0]):
                region = args[0]
            elif valid_course(args[0]):
                course_id = args[0]
            else:
                return print('Invalid course or region.')

            if 'jumps' in args or 'jump' in args or '-j' in args:
                code = 'jumps'
            elif 'flat' in args or '-f' in args:
                code = 'flat'
            else:
                return print('Invalid racing code. -f, flat or -j, jumps.')

            years = parse_years(args[1])
            current_year = int(datetime.today().year)

            if not valid_years(years):
                print(f'\nINVALID YEAR: must be in range 1988-{current_year}.\n')
                return

            if code == 'jumps':
                latest_valid_year = current_year - 1 if int(datetime.today().month) < 5 else current_year

                if int(years[-1]) > latest_valid_year:
                    print(f'\nINVALID YEAR: the latest jump season started in {latest_valid_year}.\n')
                    return

            scrape_target = region if 'region' in locals() else course_id

            if 'region' in locals():
                tracks = [course for course in courses(region)]
            else:
                tracks = [(course_id, course_name(course_id))]

            races = get_race_urls_async(tracks, years, code, x_y())

            scrape_races(races, course_name(scrape_target), args[1], code)

    else:
        options()


def check_for_update():
    try:
        from git import Repo, cmd

        if 'local out of date' in cmd.Git('..').execute(['git', 'remote', 'show', 'origin']).lower():
            x = input('Update available. Do you want to update? Y/N ')

            if x.lower() == 'y':
                Repo('..').remote(name='origin').pull()

                if 'up to date' in cmd.Git('..').execute(['git', 'remote', 'show', 'origin']).lower():
                    sys.exit(print('Updated successfully.'))
                else:
                    sys.exit(print('Failed to update.'))
    except ModuleNotFoundError:
        sys.exit(print('gitpython module not found.\n\nInstall with "pip3 install gitpython" or disable auto update in settings.'))


def main():
    try:
        settings = toml.load(open('../settings.toml', 'r'))
    except ValueError:
        print('Failed to parse settings.toml')
        settings = {'auto_update': True}

    if settings['auto_update']:
        check_for_update()

    if sys.version_info[0] == 3 and sys.version_info[1] >= 7 and sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument('-d', '--date',     type=str, metavar='', help='Date or date range in format YYYY/MM/DD e.g 2020/01/19-2020/05/01')
        parser.add_argument('-c', '--course',   type=str, metavar='', help='Numeric course code e.g 20')
        parser.add_argument('-r', '--region',   type=str, metavar='', help='Region code e.g ire')
        parser.add_argument('-y', '--year',     type=str, metavar='', help='Year or year range in format YYYY e.g 2018-2020')
        parser.add_argument('-t', '--type',     type=str, metavar='', help='Race type [flat/jumps]')
        args = parser.parse_args()

        if args.date and any([args.course, args.year, args.type]):
            print('Arguments not compatible with -d flag.\n\nFormat:\n\t\t-d YYYY/MM/DD -r [REGION CODE]\n\nExamples:\n\t\t-d 2020/01/19 -r gb\n')
            print('When scraping by date, if no region code is specified, all available races will be scraped by default.')
            sys.exit()

        if args.date:
            if not check_date(args.date):
                sys.exit(print('Invalid date.\n\nFormat:\n\t\tYYYY/MM/DD\n\t\tYYYY/MM/DD-YYYY/MM/DD\n\nExamples:\n\t\t2015/03/27\n\t\t2020/01/19-2020/05/01'))

            if args.region:
                if not valid_region(args.region):
                    sys.exit(print('Invalid region code.\n\nExamples:\n\t\t-r gb\n\t\t-r ire'))
                region = args.region
            else:
                region = 'all'

            dates = get_dates(args.date)
            races = get_race_urls_date(dates, region)
            scrape_races(races, region, args.date.replace('/', '_'), '')

            sys.exit()

        if args.course:
            if not valid_course(args.course):
                sys.exit(print('Invalid course code.\n\nExamples:\n\t\t-c 20\n\t\t-c 1083'))

        if args.region:
            if not valid_region(args.region):
                sys.exit(print('Invalid region code.\n\nExamples:\n\t\t-r gb\n\t\t-r ire'))

        years = parse_years(args.year) if args.year else []

        if not years or not valid_years(years):
            sys.exit(print('Invalid year.\n\nFormat:\n\t\tYYYY\n\nExamples:\n\t\t-y 2015\n\t\t-y 2012-2017'))

        if not args.type or args.type not in ['flat', 'jumps']:
            sys.exit(print('Invalid race type.\n\nMust be either flat or jumps.\n\nExamples:\n\t\t-t flat\n\t\t-t jumps'))

        if not args.course and not args.region:
            sys.exit(print('Must supply a course or region code.'))

        target = args.region if args.region else course_name(args.course)

        if args.region:
            tracks = [course for course in courses(args.region)]
        else:
            tracks = [(args.course, course_name(args.course))]

        # races = get_race_urls(tracks, years, args.type, x_y())
        races = get_race_urls_async(tracks, years, args.type, x_y())

        scrape_races(races, target, args.year, args.type)

        sys.exit()

    try:
        import readline
        completions = Completer(['courses', 'regions', 'options', 'help', 'quit', 'exit', 'clear', 'flat', 'jumps', 'date'])
        readline.set_completer(completions.complete)
        readline.parse_and_bind('tab: complete')
    except ModuleNotFoundError:  # windows
        pass

    while True:
        args = input('[rpscrape]> ').lower().strip()
        parse_args([arg.strip() for arg in args.split()])


if __name__ == '__main__':
    main()
