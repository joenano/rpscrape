#!/usr/bin/env python

import argparse
import datetime
import os
import re
import sys

from collections import defaultdict
from lxml import etree, html
from tqdm import tqdm
from typing import Any
from orjson import OPT_NON_STR_KEYS, dumps

from utils.cleaning import normalize_name
from utils.course import valid_meeting
from utils.header import RandomHeader
from utils.going import get_surface
from utils.lxml_funcs import find
from utils.network import Persistent406Error, get_request
from utils.profiles import get_profiles
from utils.region import get_region
from utils.stats import Stats

from models.racecard import Racecard, Runner

random_header = RandomHeader()

RACE_TYPE = {'X': 'Flat', 'C': 'Chase', 'H': 'Hurdle', 'B': 'NH Flat', 'F': 'Flat'}


class LegacyKeywordError(Exception):
    def __init__(self, keyword: str) -> None:
        self.keyword: str = keyword
        super().__init__()


def check_legacy_keywords(value: str) -> str:
    if value.lower() in ('today', 'tomorrow'):
        raise LegacyKeywordError(value)
    return value


def handle_legacy_error(keyword: str):
    print('\nError: The API has changed.')
    print(f"The positional keyword '{keyword}' is no longer supported.")
    print('Use --day N or --days N instead.\n')
    print('./rpscrape.py today -> ./rpscrape.py --day 1')
    print('./rpscrape.py tomorrow -> ./rpscrape.py --day 2')
    print('today and tomorrow -> ./rpscrape.py --days 2')


def validate_days_range(value: str) -> int:
    try:
        days = int(value)
        if 1 <= days <= 2:
            return days
        raise argparse.ArgumentTypeError(f'Value must be an integer between 1 and 2. Got: {days}')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid value: '{value}'. Expected an integer.")


def get_race_urls(dates: list[str]) -> dict[str, list[tuple[str, str]]]:
    race_urls: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)

    for date in dates:
        url = f'https://www.racingpost.com/racecards/{date}'
        try:
            _, response = get_request(url)
        except Persistent406Error as err:
            print('Failed to get race urls.')
            print(err)
            sys.exit(1)

        doc = html.fromstring(response.content)

        for meeting in doc.xpath('//section[@data-accordion-row]'):
            course = meeting.xpath(".//span[contains(@class, 'RC-accordion__courseName')]")[0]
            if valid_meeting(course.text_content().strip().lower()):
                for race in meeting.xpath(".//a[@class='RC-meetingItem__link js-navigate-url']"):
                    race_urls[date].append((race.attrib['data-race-id'], race.attrib['href']))

    return dict(race_urls)


def get_pattern(race_name: str):
    regex_group = r'(\(|\s)((G|g)rade|(G|g)roup) (\d|[A-Ca-c]|I*)(\)|\s)'
    match = re.search(regex_group, race_name)

    if match:
        pattern = f'{match.groups()[1]} {match.groups()[4]}'.title()
        return pattern.title()

    if any(x in race_name.lower() for x in {'listed race', '(listed'}):
        return 'Listed'

    return ''


def parse_age_and_rating(doc: html.HtmlElement) -> tuple[str | None, str | None]:
    raw = find(doc, 'span', 'RC-header__rpAges')
    parts = raw.strip('()').split()
    age = parts[0] if len(parts) > 0 else None
    rating = parts[1] if len(parts) > 1 else None
    return age, rating


def parse_field_size(doc: html.HtmlElement) -> int | None:
    raw = find(doc, 'div', 'RC-headerBox__runners').lower()
    if 'runners:' in raw:
        segment = raw.split('runners:', 1)[1]
        return int(segment.split('(')[0].strip())
    return None


def parse_going(doc: html.HtmlElement) -> str:
    raw = find(doc, 'div', 'RC-headerBox__going').lower()
    going = raw.split('going:', 1)[1].strip().title() if 'going:' in raw else ''
    return going


def parse_prize(doc: html.HtmlElement) -> str | None:
    raw = find(doc, 'div', 'RC-headerBox__winner').lower()
    if 'winner:' in raw:
        return raw.split('winner:', 1)[1].strip()
    return None


def parse_runners(
    stats: Stats,
    runners_json: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> list[Runner]:
    runners: list[Runner] = []

    for runner_json in runners_json:
        profile = profiles[runner_json['horseUid']]

        runner = Runner()
        runners.append(runner)

        runner.age = runner_json['horseAge']
        runner.breeder = normalize_name(runner_json['breederName'])
        runner.breeder_id = runner_json['breederUid']
        runner.claim = runner_json['weightAllowanceLbs']
        runner.colour = runner_json['horseColourCode']
        runner.comment = runner_json['diomed']
        runner.dam = normalize_name(runner_json['damName'])
        runner.dam_id = runner_json['damId']
        runner.dam_region = runner_json['damCountry']
        runner.damsire = normalize_name(runner_json['damsireName'])
        runner.damsire_id = runner_json['damsireId']
        runner.damsire_region = runner_json['damsireCountry']
        runner.dob = runner_json['horseDateOfBirth'].split('T')[0]
        runner.draw = runner_json['draw'] if runner_json['draw'] else None
        runner.form = (
            ''.join(f['formFigure'] for f in runner_json['figuresCalculated'])[::-1]
            if runner_json['figuresCalculated']
            else ''
        )
        runner.headgear = runner_json['rpHorseHeadGearCode']
        runner.headgear_first = runner_json['firstTime']
        runner.horse_id = runner_json['horseUid']
        runner.jockey = normalize_name(runner_json['jockeyName'])
        runner.jockey_allowance = runner_json['weightAllowanceLbs']
        runner.jockey_id = runner_json['jockeyUid']
        runner.last_run = runner_json['daysSinceLastRun']
        runner.lbs = runner_json['weightCarriedLbs']
        runner.name = normalize_name(runner_json['horseName'])
        runner.non_runner = runner_json['nonRunner']
        runner.number = runner_json['startNumber']
        runner.ofr = runner_json['officialRatingToday'] if runner_json['officialRatingToday'] else None
        runner.owner = normalize_name(runner_json['ownerName'])
        runner.owner_id = runner_json['ownerUid']
        runner.profile = profile['profile']
        runner.region = runner_json['countryOriginCode']
        runner.reserve = runner_json['irishReserve']
        runner.rpr = runner_json['rpPostmark'] if runner_json['rpPostmark'] else None
        runner.sex = profile['horseSex']
        runner.sex_code = runner_json['horseSexCode']
        runner.silk_path = runner_json['silkImagePath']
        runner.silk_url = f'https://www.rp-assets.com/svg/{runner.silk_path}.svg'
        runner.sire = normalize_name(runner_json['sireName'])
        runner.sire_id = runner_json['sireId']
        runner.sire_region = runner_json['sireCountry']
        runner.spotlight = runner_json['spotlight']
        runner.trainer = normalize_name(runner_json['trainerStylename'])
        runner.trainer_14_days = profile['trainerLast14Days']
        runner.trainer_id = runner_json['trainerId']
        runner.trainer_location = profile['trainerLocation']
        runner.trainer_rtf = runner_json['trainerRtf']
        runner.ts = runner_json['rpTopspeed'] if runner_json['rpTopspeed'] else None
        runner.wind_surgery_first = runner_json['windSurgeryFirstTime']
        runner.wind_surgery_second = runner_json['windSurgerySecondTime']

        horse_stats = (
            stats.horses[str(runner.horse_id)].to_dict() if str(runner.horse_id) in stats.horses else {}
        )

        jockey_stats = (
            stats.jockeys[str(runner.jockey_id)] if str(runner.jockey_id) in stats.jockeys else {}
        )

        trainer_stats = (
            stats.trainers[str(runner.trainer_id)] if str(runner.trainer_id) in stats.trainers else {}
        )

        runner.stats = {
            'horse': horse_stats,
            'jockey': jockey_stats,
            'trainer': trainer_stats,
        }

        if profile['previousTrainers']:
            runner.prev_trainers = [
                {
                    'trainer': normalize_name(trainer['trainerStyleName']),
                    'trainer_id': trainer['trainerUid'],
                    'change_date': trainer['trainerChangeDate'].split('T')[0],
                }
                for trainer in profile['previousTrainers']
            ]

        if profile['previousOwners']:
            runner.prev_owners = [
                {
                    'owner': normalize_name(owner['ownerStyleName']),
                    'owner_id': owner['ownerUid'],
                    'change_date': owner['ownerChangeDate'].split('T')[0],
                }
                for owner in profile['previousOwners']
            ]

        if profile['medical']:
            runner.medical = [
                {'date': med['medicalDate'].split('T')[0], 'type': med['medicalType']}
                for med in profile['medical']
            ]

        if profile['quotes']:
            runner.quotes = [
                {
                    'date': q['raceDate'].split('T')[0],
                    'horse': normalize_name(q['horseStyleName']),
                    'horse_id': q['horseUid'],
                    'race': q['raceTitle'],
                    'race_id': q['raceId'],
                    'course': q['courseStyleName'],
                    'course_id': q['courseUid'],
                    'distance_f': q['distanceFurlong'],
                    'distance_y': q['distanceYard'],
                    'quote': q['notes'],
                }
                for q in profile['quotes']
            ]

        if profile['stable_quotes']:
            runner.stable_tour = [
                {'horse': normalize_name(q['horseName']), 'horse_id': q['horseUid'], 'quote': q['notes']}
                for q in profile['stable_quotes']
            ]

    return runners


def scrape_racecards(
    race_urls: dict[str, list[tuple[str, str]]], date: str
) -> defaultdict[str, defaultdict[str, defaultdict[str, dict[str, Any]]]]:
    races: defaultdict[str, defaultdict[str, defaultdict[str, dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )

    for race_id, href in tqdm(
        race_urls[date],
        desc=date,
        bar_format='{desc}: {percentage:3.0f}% |{bar:49}| {n}/{total} ETA {remaining}',
        ncols=91,
    ):
        url_base = 'https://www.racingpost.com'
        url_racecard = f'{url_base}{href}'
        url_runners = f'{url_base}/profile/horse/data/cardrunners/{race_id}.json'
        url_accordion = f'{url_base}/racecards/data/accordion/{race_id}'

        try:
            status_racecard, resp_racecard = get_request(url_racecard)
            status_runners, resp_runners = get_request(url_runners)
            status_accordion, resp_accordion = get_request(url_accordion)
        except Persistent406Error as err:
            print(err)
            sys.exit(1)

        if any(status != 200 for status in (status_racecard, status_runners, status_accordion)):
            print('Failed to get racecard data.')
            print(f'status: {status_racecard} url: {url_racecard}')
            print(f'status: {status_runners} url: {url_runners}')
            print(f'status: {status_accordion} url: {url_accordion}')
            continue

        try:
            doc = html.fromstring(resp_racecard.content)
            doc_accordion = html.fromstring(resp_accordion.content)
        except etree.ParserError:
            print('Failed to parse HTML for racecard.')
            print(f'url: {url_racecard}')
            print(f'url: {url_accordion}')
            continue

        try:
            runners = resp_runners.json()['runners']
            runners = [r for r in runners.values()]
            runner = runners[0]
        except KeyError:
            print('Failed to parse JSON for runners.')
            print(f'url: {url_runners}')
            continue

        profile_hrefs = doc.xpath("//a[@data-test-selector='RC-cardPage-runnerName']/@href")
        profile_urls = [url_base + a.split('#')[0] + '/form' for a in profile_hrefs]

        profiles = get_profiles(profile_urls)

        race: Racecard = Racecard()

        race.href = url_racecard
        race.race_id = int(race_id)

        race.date = date
        date_str = runner['raceDatetime']
        race.off_time = datetime.datetime.fromisoformat(date_str).strftime('%H:%M')

        race.course_id = runner['courseUid']
        race.course = find(doc, 'h1', 'RC-courseHeader__name')

        if race.course == 'Belmont At The Big A':
            race.course_id = 255
            race.course = 'Aqueduct'

        race.region = get_region(str(race.course_id))

        race.race_name = find(doc, 'span', 'RC-header__raceInstanceTitle')

        if runner['raceTypeCode'] not in RACE_TYPE:
            print(runner['raceTypeCode'])
            print(race)
            sys.exit()
        race.race_type = RACE_TYPE[runner['raceTypeCode']]

        race.distance_f = runner['distanceFurlongRounded']
        race.distance_y = runner['distanceYard']
        race.distance_round = find(doc, 'strong', 'RC-header__raceDistanceRound')
        race.distance = find(doc, 'span', 'RC-header__raceDistance')
        race.distance = race.distance_round if not race.distance else race.distance.strip('()')

        race.pattern = get_pattern(race.race_name.lower())
        race.race_class = find(doc, 'span', 'RC-header__raceClass')
        race.race_class = race.race_class.replace('Class', '').strip('()').strip()
        race.race_class = int(race.race_class) if race.race_class.isdigit() else None
        race.race_class = 1 if not race.race_class and race.pattern else race.race_class

        race.age_band, race.rating_band = parse_age_and_rating(doc)
        race.prize = parse_prize(doc)
        race.field_size = parse_field_size(doc)

        race.handicap = race.rating_band is not None or 'handicap' in race.race_name.lower()

        race.going = parse_going(doc)
        race.surface = get_surface(race.going)

        stats = Stats(doc_accordion)

        race.runners = parse_runners(stats, runners, profiles)

        races[race.region][race.course][race.off_time] = race.to_dict()

    return races


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Scrape racecards for a single day or a range of days.',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    flag_group = parser.add_mutually_exclusive_group()

    _ = flag_group.add_argument(
        '--day',
        type=validate_days_range,
        help="Scrape a single specific day (N). E.g., '--day 2' scrapes the 2nd day.",
        metavar='N',
    )
    _ = flag_group.add_argument(
        '--days',
        type=validate_days_range,
        help="Scrape a range of days (N total). E.g., '--days 2' scrapes 2 days.",
        metavar='N',
    )

    _ = parser.add_argument(
        'legacy_input', nargs='?', type=check_legacy_keywords, help=argparse.SUPPRESS
    )

    try:
        args = parser.parse_args()
    except LegacyKeywordError as e:
        handle_legacy_error(e.keyword)
        sys.exit(2)

    dates: list[str] = [
        (datetime.date.today() + datetime.timedelta(days=i)).isoformat() for i in range(2)
    ]

    if args.day:
        dates = [dates[args.day - 1]]
    elif args.days:
        dates = dates[: args.days]
    else:
        parser.print_usage(sys.stderr)
        print('\nError: Must specify a day or days (1-2) to scrape using either --day or --days.')
        sys.exit(1)

    if not os.path.exists('../racecards'):
        os.makedirs('../racecards')

    race_urls = get_race_urls(dates)

    for date in race_urls:
        racecards = scrape_racecards(race_urls, date)

        with open(f'../racecards/{date}.json', 'w', encoding='utf-8') as f:
            _ = f.write(dumps(racecards).decode('utf-8'))


if __name__ == '__main__':
    main()
