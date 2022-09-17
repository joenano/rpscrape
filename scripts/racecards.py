#!/usr/bin/env python3
import os
import requests
import sys

from collections import defaultdict
from datetime import datetime, timedelta
from lxml import html
from orjson import loads, dumps
from re import search

from utils.going import get_surface
from utils.header import RandomHeader
from utils.lxml_funcs import find
from utils.region import get_region


random_header = RandomHeader()


def clean_name(name):
    if name:
        return name.strip().replace("'", '').lower().title()
    else:
        return ''


def distance_to_furlongs(distance):
    dist = distance.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75')

    if 'm' in dist:
        if len(dist) > 2:
            dist = int(dist.split('m')[0]) * 8 + float(dist.split('m')[1].strip('f'))
        else:
            dist = int(dist.split('m')[0]) * 8
    else:
        dist = dist.strip('f')

    return float(dist)


def get_going_info(session, date):
    r = session.get(f'https://www.racingpost.com/non-runners/{date}', headers=random_header.header())
    doc = html.fromstring(r.content.decode())

    json_str = doc.xpath('//body/script')[0].text.replace('var __PRELOADED_STATE__ = ', '').strip().strip(';')

    going_info = defaultdict(dict)

    for course in loads(json_str):
        going, rail_movements = parse_going(course['going'])

        course_id = 0
        course_name = ''

        if course['courseName'] == 'Belmont At The Big A':
            course_id = 255
            course_name = 'Aqueduct'
        else:
            course_id = int(course['raceCardsCourseMeetingsUrl'].split('/')[2])
            course_name = course['courseName']

        going_info[course_id]['course'] = course_name
        going_info[course_id]['going'] = going
        going_info[course_id]['stalls'] = course['stallsPosition']
        going_info[course_id]['rail_movements'] = rail_movements
        going_info[course_id]['weather'] = course['weather']

    return going_info


def get_pattern(race_name):
    regex_group = '(\(|\s)((G|g)rade|(G|g)roup) (\d|[A-Ca-c]|I*)(\)|\s)'
    match = search(regex_group, race_name)

    if match:
        pattern = f'{match.groups()[1]} {match.groups()[4]}'.title()
        return pattern.title()

    if any(x in race_name.lower() for x in {'listed race', '(listed'}):
        return 'Listed'

    return ''


def get_race_type(doc, race, distance):
        race_type = ''
        fences = find(doc, 'div', 'RC-headerBox__stalls')

        if 'hurdle' in fences.lower():
            race_type = 'Hurdle'
        elif 'fence' in fences.lower():
            race_type = 'Chase'
        else:
            if distance >= 12:
                if any(x in race for x in {'national hunt flat', 'nh flat race', 'mares flat race'}):
                    race_type = 'NH Flat'
                if any(x in race for x in {'inh bumper', ' sales bumper', 'kepak flat race', 'i.n.h. flat race'}):
                    race_type = 'NH Flat'
                if any(x in race for x in {' hurdle', '(hurdle)'}):
                    race_type = 'Hurdle'
                if any(x in race for x in {' chase', '(chase)', 'steeplechase', 'steeple-chase', 'steeplchase', 'steepl-chase'}):
                    race_type = 'Chase'

        if race_type == '':
            race_type = 'Flat'

        return race_type


def get_race_urls(session, racecard_url):
    r = session.get(racecard_url, headers=random_header.header())
    doc = html.fromstring(r.content)

    race_urls = []

    for meeting in doc.xpath("//section[@data-accordion-row]"):
        course = meeting.xpath(".//span[contains(@class, 'RC-accordion__courseName')]")[0]
        if valid_course(course.text_content().strip().lower()):
            for race in meeting.xpath(".//a[@class='RC-meetingItem__link js-navigate-url']"):
                race_urls.append('https://www.racingpost.com' + race.attrib['href'])

    return sorted(list(set(race_urls)))


def get_runners(session, profile_urls):
    runners = {}

    for url in profile_urls:
        r = session.get(url, headers=random_header.header())
        doc = html.fromstring(r.content)

        runner = {}

        try:
            json_str = doc.xpath('//body/script')[0].text.split('window.PRELOADED_STATE =')[1].split('\n')[0].strip().strip(';')
            js = loads(json_str)
        except IndexError:
            split = url.split('/')
            runner['horse_id'] = int(split[5])
            runner['name'] = split[6].replace('-', ' ').title()
            runner['broken_url'] = url
            runners[runner['horse_id']] = runner
            continue

        runner['horse_id'] = js['profile']['horseUid']
        runner['name'] = clean_name(js['profile']['horseName'])
        runner['dob'] = js['profile']['horseDateOfBirth'].split('T')[0]
        runner['age'] = int(js['profile']['age'].split('-')[0])
        runner['sex'] = js['profile']['horseSex']
        runner['sex_code'] = js['profile']['horseSexCode']
        runner['colour'] = js['profile']['horseColour']
        runner['region'] = js['profile']['horseCountryOriginCode']

        runner['breeder'] = js['profile']['breederName']
        runner['dam'] = clean_name(js['profile']['damHorseName'])
        runner['dam_region'] = js['profile']['damCountryOriginCode']
        runner['sire'] = clean_name(js['profile']['sireHorseName'])
        runner['sire_region'] = js['profile']['sireCountryOriginCode']
        runner['grandsire'] = clean_name(js['profile']['siresSireName'])
        runner['damsire'] = clean_name(js['profile']['damSireHorseName'])
        runner['damsire_region'] = js['profile']['damSireCountryOriginCode']

        runner['trainer'] = clean_name(js['profile']['trainerName'])
        runner['trainer_location'] = js['profile']['trainerLocation']
        runner['trainer_14_days'] = js['profile']['trainerLast14Days']

        runner['owner'] = clean_name(js['profile']['ownerName'])

        runner['prev_trainers'] = js['profile']['previousTrainers']

        if runner['prev_trainers']:
            prev_trainers = []

            for trainer in runner['prev_trainers']:
                prev_trainer = {}
                prev_trainer['trainer'] = trainer['trainerStyleName']
                prev_trainer['trainer_id'] = trainer['trainerUid']
                prev_trainer['change_date'] = trainer['trainerChangeDate'].split('T')[0]
                prev_trainers.append(prev_trainer)

            runner['prev_trainers'] = prev_trainers

        runner['prev_owners'] = js['profile']['previousOwners']

        if runner['prev_owners']:
            prev_owners = []

            for owner in runner['prev_owners']:
                prev_owner = {}
                prev_owner['owner'] = owner['ownerStyleName']
                prev_owner['owner_id'] = owner['ownerUid']
                prev_owner['change_date'] = owner['ownerChangeDate'].split('T')[0]
                prev_owners.append(prev_owner)

            runner['prev_owners'] = prev_owners

        if js['profile']['comments']:
            runner['comment'] = js['profile']['comments'][0]['individualComment']
            runner['spotlight'] = js['profile']['comments'][0]['individualSpotlight']
        else:
            runner['comment'] = None
            runner['spotlight'] = None

        if js['profile']['medical']:
            medicals = []

            for med in js['profile']['medical']:
                medical = {}
                medical['date'] = med['medicalDate'].split('T')[0]
                medical['type'] = med['medicalType']
                medicals.append(medical)

            runner['medical'] = medicals

        runner['quotes'] = None

        if js['quotes']:
            quotes = []

            for q in js['quotes']:
                quote = {}
                quote['date'] = q['raceDate'].split('T')[0]
                quote['horse'] = q['horseStyleName']
                quote['horse_id'] = q['horseUid']
                quote['race'] = q['raceTitle']
                quote['race_id'] = q['raceId']
                quote['course'] = q['courseStyleName']
                quote['course_id'] = q['courseUid']
                quote['distance_f'] = q['distanceFurlong']
                quote['distance_y'] = q['distanceYard']
                quote['quote'] = q['notes']
                quotes.append(quote)

            runner['quotes'] = quotes

        runner['stable_tour'] = None

        if js['stableTourQuotes']:
            quotes = []

            for q in js['stableTourQuotes']:
                quote = {}
                quote['horse'] = q['horseName']
                quote['horse_id'] = q['horseUid']
                quote['quote'] = q['notes']
                quotes.append(quote)

            runner['stable_tour'] = quotes

        runners[runner['horse_id']] = runner

    return runners


def parse_going(going_info):
    going = going_info
    rail_movements = ''

    if 'Rail movements' in going_info:
        going_info = going_info.replace('movements:', 'movements')
        rail_movements = [x.strip() for x in going_info.split('Rail movements')[1].strip().strip(')').split(',')]
        going = going_info.split('(Rail movements')[0].strip()

    return going, rail_movements


def parse_races(session, race_urls, date):
    races = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    going_info = get_going_info(session, date)

    for url in race_urls:
        r = session.get(url, headers=random_header.header())
        doc = html.fromstring(r.content)

        race = {}

        url_split = url.split('/')

        race['course'] = find(doc, 'h1', 'RC-courseHeader__name')

        if race['course'] == 'Belmont At The Big A':
            race['course_id'] = 255
            race['course'] = 'Aqueduct'
        else:
            race['course_id'] = int(url_split[4])

        race['race_id'] = int(url_split[7])
        race['date'] = url_split[6]
        race['off_time'] = find(doc, 'span', 'RC-courseHeader__time')
        race['race_name'] = find(doc, 'span', 'RC-header__raceInstanceTitle')
        race['distance_round'] = find(doc, 'strong', 'RC-header__raceDistanceRound')
        race['distance'] = find(doc, 'span', 'RC-header__raceDistance')
        race['distance'] = race['distance_round'] if not race['distance'] else race['distance'].strip('()')
        race['distance_f'] = distance_to_furlongs(race['distance_round'])
        race['region'] = get_region(str(race['course_id']))
        race['pattern'] = get_pattern(race['race_name'].lower())
        race['race_class'] = find(doc, 'span', 'RC-header__raceClass')
        race['race_class'] = race['race_class'].strip('()') if race['race_class'] else ''
        race['type'] = get_race_type(doc, race['race_name'].lower(), race['distance_f'])

        if not race['race_class']:
            if race['pattern']:
                race['race_class'] = 'Class 1'

        try:
            band = find(doc, 'span', 'RC-header__rpAges').strip('()').split()
            if band:
                race['age_band'] = band[0]
                race['rating_band'] = band[1] if len(band) > 1 else None
            else:
                race['age_band'] = None
                race['rating_band'] = None
        except AttributeError:
            race['age_band'] = None
            race['rating_band'] = None

        prize = find(doc, 'div', 'RC-headerBox__winner').lower()
        race['prize'] = prize.split('winner:')[1].strip() if 'winner:' in prize else None
        field_size = find(doc, 'div', 'RC-headerBox__runners').lower()
        if field_size:
            race['field_size'] = int(field_size.split('runners:')[1].split('(')[0].strip())
        else:
            race['field_size'] = ''

        try:
            race['going_detailed'] = going_info[race['course_id']]['going']
            race['rail_movements'] = going_info[race['course_id']]['rail_movements']
            race['stalls'] = going_info[race['course_id']]['stalls']
            race['weather'] = going_info[race['course_id']]['weather']
        except KeyError:
            race['going'] = None
            race['rail_movements'] = None
            race['stalls'] = None
            race['weather'] = None

        going = find(doc, 'div', 'RC-headerBox__going').lower()
        race['going'] = going.split('going:')[1].strip().title() if 'going:' in going else ''

        race['surface'] = get_surface(race['going'])

        profile_hrefs = doc.xpath("//a[@data-test-selector='RC-cardPage-runnerName']/@href")
        profile_urls = ['https://www.racingpost.com' + a.split('#')[0] + '/form' for a in profile_hrefs]

        runners = get_runners(session, profile_urls)

        for horse in doc.xpath("//div[contains(@class, ' js-PC-runnerRow')]"):
            horse_id = int(find(horse, 'a', 'RC-cardPage-runnerName', attrib='href').split('/')[3])

            if 'broken_url' in runners[horse_id]:
                sire = find(horse, 'a', 'RC-pedigree__sire').split('(')
                dam = find(horse, 'a', 'RC-pedigree__dam').split('(')
                damsire = find(horse, 'a', 'RC-pedigree__damsire').lstrip('(').rstrip(')').split('(')

                runners[horse_id]['sire'] = clean_name(sire[0])
                runners[horse_id]['dam'] = clean_name(dam[0])
                runners[horse_id]['damsire'] = clean_name(damsire[0])

                runners[horse_id]['sire_region'] = sire[1].replace(')', '').strip()
                runners[horse_id]['dam_region'] = dam[1].replace(')', '').strip()
                runners[horse_id]['damsire_region'] = damsire[1].replace(')', '').strip()

                runners[horse_id]['age'] = find(horse, 'span', 'RC-cardPage-runnerAge', attrib='data-order-age')

                sex = find(horse, 'span', 'RC-pedigree__color-sex').split()

                runners[horse_id]['colour'] = sex[0]
                runners[horse_id]['sex_code'] = sex[1].capitalize()

                runners[horse_id]['trainer'] = find(horse, 'a', 'RC-cardPage-runnerTrainer-name', attrib='data-order-trainer')

            runners[horse_id]['number'] = int(find(horse, 'span', 'RC-cardPage-runnerNumber-no', attrib='data-order-no'))

            try:
                runners[horse_id]['draw'] = int(find(horse, 'span', 'RC-cardPage-runnerNumber-draw', attrib='data-order-draw'))
            except ValueError:
                runners[horse_id]['draw'] = None

            runners[horse_id]['headgear'] = find(horse, 'span', 'RC-cardPage-runnerHeadGear')
            runners[horse_id]['headgear_first'] = find(horse, 'span', 'RC-cardPage-runnerHeadGear-first')

            try:
                runners[horse_id]['lbs'] = int(find(horse, 'span', 'RC-cardPage-runnerWgt-carried', attrib='data-order-wgt'))
            except ValueError:
                runners[horse_id]['lbs'] = None

            try:
                runners[horse_id]['ofr'] = int(find(horse, 'span', 'RC-cardPage-runnerOr', attrib='data-order-or'))
            except ValueError:
                runners[horse_id]['ofr'] = None

            try:
                runners[horse_id]['rpr'] = int(find(horse, 'span', 'RC-cardPage-runnerRpr', attrib='data-order-rpr'))
            except ValueError:
                runners[horse_id]['rpr'] = None

            try:
                runners[horse_id]['ts'] = int(find(horse, 'span', 'RC-cardPage-runnerTs', attrib='data-order-ts'))
            except ValueError:
                runners[horse_id]['ts'] = None

            claim = find(horse, 'span', 'RC-cardPage-runnerJockey-allowance')
            jockey = find(horse, 'a', 'RC-cardPage-runnerJockey-name', attrib='data-order-jockey')

            if jockey:
                runners[horse_id]['jockey'] = jockey if not claim else jockey + f'({claim})'
            else:
                runners[horse_id]['jockey'] = None

            try:
                runners[horse_id]['last_run'] = find(horse, 'div', 'RC-cardPage-runnerStats-lastRun')
            except TypeError:
                runners[horse_id]['last_run'] = None

            runners[horse_id]['form'] = find(horse, 'span', 'RC-cardPage-runnerForm')

            try:
                runners[horse_id]['trainer_rtf'] = find(horse, 'span', 'RC-cardPage-runnerTrainer-rtf')
            except TypeError:
                runners[horse_id]['trainer_rtf'] = None

        race['runners'] = [runner for runner in runners.values()]
        races[race['region']][race['course']][race['off_time']] = race

    return races


def valid_course(course):
    invalid = ['free to air', 'worldwide stakes', '(arab)']
    return all([x not in course for x in invalid])


def main():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in {'today', 'tomorrow'}:
        return print('Usage: ./racecards.py [today|tomorrow]')

    racecard_url = 'https://www.racingpost.com/racecards'

    date = datetime.today().strftime('%Y-%m-%d')

    if sys.argv[1].lower() == 'tomorrow':
        racecard_url += '/tomorrow'
        date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')

    session = requests.Session()

    race_urls = get_race_urls(session, racecard_url)
    races = parse_races(session, race_urls, date)

    if not os.path.exists('../racecards'):
        os.makedirs(f'../racecards')

    with open(f'../racecards/{date}.json', 'w', encoding='utf-8') as f:
        f.write(dumps(races).decode('utf-8'))


if __name__ == '__main__':
    main()
