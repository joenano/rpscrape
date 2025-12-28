#!/usr/bin/env python

import argparse
import datetime
import os
import re
import sys

from collections import defaultdict
from lxml import etree, html
from pathlib import Path
from tqdm import tqdm
from typing import Any
from orjson import dumps
import tomli

from utils.cleaning import normalize_name
from utils.course import valid_meeting
from utils.header import RandomHeader
from utils.going import get_surface
from utils.lxml_funcs import find
from utils.network import get_request
from utils.profiles import get_profiles
from utils.region import get_region, valid_region
from utils.stats import Stats

from models.racecard import Racecard, Runner

random_header = RandomHeader()

MAX_DAYS = 2

RACE_TYPE = {
    'F': 'Flat',
    'X': 'Flat',
    'C': 'Chase',
    'H': 'Hurdle',
    'B': 'NH Flat',
    'W': 'NH Flat',
}

type Racecards = defaultdict[str, defaultdict[str, defaultdict[str, dict[str, Any]]]]


def load_field_config() -> dict[str, Any]:
    """Load field configuration from settings/racecard_fields.toml"""
    config_path = Path('../settings/racecard_fields.toml')
    
    if not config_path.exists():
        # Return default config (everything enabled)
        return {
            'data_collection': {
                'fetch_profiles': True,
                'fetch_stats': True,
                'fetch_quotes': True,
                'fetch_medical': True,
                'fetch_history': True,
            },
            'runner_fields': {},  # Empty means all fields
        }
    
    with open(config_path, 'rb') as f:
        config = tomli.load(f)
    
    # Handle presets
    if 'preset' in config and 'mode' in config['preset']:
        mode = config['preset']['mode']
        if mode == 'minimal':
            config['data_collection'] = {
                'fetch_profiles': False,
                'fetch_stats': False,
                'fetch_quotes': False,
                'fetch_medical': False,
                'fetch_history': False,
            }
            config['runner_fields'] = {
                'name': True, 'horse_id': True, 'number': True, 'draw': True,
                'age': True, 'jockey': True, 'jockey_id': True,
                'trainer': True, 'trainer_id': True, 'lbs': True,
                'form': True, 'rpr': True, 'ofr': True,
            }
        elif mode == 'standard':
            config['data_collection'] = {
                'fetch_profiles': True,
                'fetch_stats': True,
                'fetch_quotes': False,
                'fetch_medical': False,
                'fetch_history': False,
            }
    
    return config


def validate_days_range(value: str) -> int:
    try:
        days = int(value)
        if 1 <= days <= MAX_DAYS:
            return days
        raise argparse.ArgumentTypeError(
            f'Value must be an integer between 1 and {MAX_DAYS}. Got: {days}'
        )
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid value: '{value}'. Expected an integer.")


def get_race_urls(dates: list[str], region: str | None = None) -> dict[str, list[tuple[str, str]]]:
    race_urls: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
    url_base = 'https://www.racingpost.com'

    for date in dates:
        url = f'https://www.racingpost.com/racecards/{date}'
        _, response = get_request(url)

        doc = html.fromstring(response.content)

        for meeting in doc.xpath('//section[@data-accordion-row]'):
            course = meeting.xpath(".//span[contains(@class, 'RC-accordion__courseName')]")[0]
            if valid_meeting(course.text_content().strip().lower()):
                for race in meeting.xpath(".//a[@class='RC-meetingItem__link js-navigate-url']"):
                    # If a region filter is provided, do a lightweight check against the
                    # runners JSON to determine the course region and skip non-matching races.
                    race_id = race.attrib['data-race-id']
                    href = race.attrib['href']

                    if region:
                        try:
                            status_runners, resp_runners = get_request(
                                f'{url_base}/profile/horse/data/cardrunners/{race_id}.json'
                            )
                        except Exception:
                            # On failure, skip this race
                            continue

                        if status_runners != 200:
                            continue

                        try:
                            runners = resp_runners.json().get('runners', {})
                            first = next(iter(runners.values()))
                            course_uid = first.get('courseUid')
                        except Exception:
                            continue

                        if not course_uid:
                            continue

                        if get_region(str(course_uid)) != region.upper():
                            continue

                    race_urls[date].append((race_id, href))

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
    stats: Stats | None,
    runners_json: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> list[Runner]:
    runners: list[Runner] = []
    runner_fields = config.get('runner_fields', {})
    data_opts = config.get('data_collection', {})
    
    # If runner_fields is empty, include all fields
    include_all = not runner_fields

    for runner_json in runners_json:
        profile = None
        if data_opts.get('fetch_profiles', True):
            try:
                profile = profiles[runner_json['horseUid']]
            except KeyError:
                print(f'Failed to find profile: {runner_json["horseUid"]} - {runner_json["horseName"]}')
                print(dumps(runner_json).decode('utf-8'))
                sys.exit(1)

        runner = Runner()
        runners.append(runner)

        # Helper to check if field should be included
        def should_include(field: str) -> bool:
            return include_all or runner_fields.get(field, False)

        if should_include('age'):
            runner.age = runner_json['horseAge']
        if should_include('breeder'):
            runner.breeder = normalize_name(runner_json['breederName'])
        if should_include('breeder_id'):
            runner.breeder_id = runner_json['breederUid']
        if should_include('claim'):
            runner.claim = runner_json['weightAllowanceLbs']
        if should_include('colour'):
            runner.colour = runner_json['horseColourCode']
        if should_include('comment'):
            runner.comment = runner_json['diomed']
        if should_include('dam'):
            runner.dam = normalize_name(runner_json['damName'])
        if should_include('dam_id'):
            runner.dam_id = runner_json['damId']
        if should_include('dam_region'):
            runner.dam_region = runner_json['damCountry']
        if should_include('damsire'):
            runner.damsire = normalize_name(runner_json['damsireName'])
        if should_include('damsire_id'):
            runner.damsire_id = runner_json['damsireId']
        if should_include('damsire_region'):
            runner.damsire_region = runner_json['damsireCountry']
        if should_include('dob'):
            runner.dob = runner_json['horseDateOfBirth'].split('T')[0]
        if should_include('draw'):
            runner.draw = runner_json['draw'] if runner_json['draw'] else None
        if should_include('form'):
            runner.form = (
                ''.join(f['formFigure'] for f in runner_json['figuresCalculated'])[::-1]
                if runner_json['figuresCalculated']
                else ''
            )
        if should_include('gelding_first_time'):
            runner.gelding_first_time = runner_json['geldingFirstTime']
        if should_include('headgear'):
            runner.headgear = runner_json['rpHorseHeadGearCode']
        if should_include('headgear_first'):
            runner.headgear_first = runner_json['firstTime']
        if should_include('horse_id'):
            runner.horse_id = runner_json['horseUid']
        if should_include('jockey'):
            runner.jockey = normalize_name(runner_json['jockeyName'])
        if should_include('jockey_allowance'):
            runner.jockey_allowance = runner_json['weightAllowanceLbs']
        if should_include('jockey_id'):
            runner.jockey_id = runner_json['jockeyUid']
        if should_include('last_run'):
            runner.last_run = runner_json['daysSinceLastRun']
        if should_include('lbs'):
            runner.lbs = runner_json['weightCarriedLbs']
        if should_include('name'):
            runner.name = normalize_name(runner_json['horseName'])
        if should_include('non_runner'):
            runner.non_runner = runner_json['nonRunner']
        if should_include('number'):
            runner.number = runner_json['startNumber']
        if should_include('ofr'):
            runner.ofr = runner_json['officialRatingToday'] if runner_json['officialRatingToday'] else None
        if should_include('owner'):
            runner.owner = normalize_name(runner_json['ownerName'])
        if should_include('owner_id'):
            runner.owner_id = runner_json['ownerUid']
        if should_include('profile') and profile:
            runner.profile = profile['profile']
        if should_include('region'):
            runner.region = runner_json['countryOriginCode']
        if should_include('reserve'):
            runner.reserve = runner_json['irishReserve']
        if should_include('rpr'):
            runner.rpr = runner_json['rpPostmark'] if runner_json['rpPostmark'] else None
        if should_include('sex') and profile:
            runner.sex = profile['horseSex']
        if should_include('sex_code'):
            runner.sex_code = runner_json['horseSexCode']
        if should_include('silk_path'):
            runner.silk_path = runner_json['silkImagePath']
        if should_include('silk_url'):
            runner.silk_url = f'https://www.rp-assets.com/svg/{runner_json["silkImagePath"]}.svg'
        if should_include('sire'):
            runner.sire = normalize_name(runner_json['sireName'])
        if should_include('sire_id'):
            runner.sire_id = runner_json['sireId']
        if should_include('sire_region'):
            runner.sire_region = runner_json['sireCountry']
        if should_include('spotlight'):
            runner.spotlight = runner_json['spotlight']
        if should_include('trainer'):
            runner.trainer = normalize_name(runner_json['trainerStylename'])
        if should_include('trainer_14_days') and profile:
            runner.trainer_14_days = profile['trainerLast14Days']
        if should_include('trainer_id'):
            runner.trainer_id = runner_json['trainerId']
        if should_include('trainer_location') and profile:
            runner.trainer_location = profile['trainerLocation']
        if should_include('trainer_rtf'):
            runner.trainer_rtf = runner_json['trainerRtf']
        if should_include('ts'):
            runner.ts = runner_json['rpTopspeed'] if runner_json['rpTopspeed'] else None
        if should_include('wind_surgery_first'):
            runner.wind_surgery_first = runner_json['windSurgeryFirstTime']
        if should_include('wind_surgery_second'):
            runner.wind_surgery_second = runner_json['windSurgerySecondTime']

        if should_include('stats') and stats:
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

        if should_include('prev_trainers') and data_opts.get('fetch_history', True) and profile and profile.get('previousTrainers'):
            runner.prev_trainers = [
                {
                    'trainer': normalize_name(trainer['trainerStyleName']),
                    'trainer_id': trainer['trainerUid'],
                    'change_date': trainer['trainerChangeDate'].split('T')[0],
                }
                for trainer in profile['previousTrainers']
            ]

        if should_include('prev_owners') and data_opts.get('fetch_history', True) and profile and profile.get('previousOwners'):
            runner.prev_owners = [
                {
                    'owner': normalize_name(owner['ownerStyleName']),
                    'owner_id': owner['ownerUid'],
                    'change_date': owner['ownerChangeDate'].split('T')[0],
                }
                for owner in profile['previousOwners']
            ]

        if should_include('medical') and data_opts.get('fetch_medical', True) and profile and profile.get('medical'):
            runner.medical = [
                {'date': med['medicalDate'].split('T')[0], 'type': med['medicalType']}
                for med in profile['medical']
            ]

        if should_include('quotes') and data_opts.get('fetch_quotes', True) and profile and profile.get('quotes'):
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

        if should_include('stable_tour') and data_opts.get('fetch_quotes', True) and profile and profile.get('stable_quotes'):
            runner.stable_tour = [
                {'horse': normalize_name(q['horseName']), 'horse_id': q['horseUid'], 'quote': q['notes']}
                for q in profile['stable_quotes']
            ]

    return runners


def scrape_racecards(race_urls: dict[str, list[tuple[str, str]]], date: str, config: dict[str, Any]) -> Racecards:
    races: Racecards = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
    data_opts = config.get('data_collection', {})
    fetch_profiles = data_opts.get('fetch_profiles', True)
    fetch_stats = data_opts.get('fetch_stats', True)

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

        status_racecard, resp_racecard = get_request(url_racecard)
        status_runners, resp_runners = get_request(url_runners)
        status_accordion, resp_accordion = get_request(url_accordion)

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

        profiles = {}
        if fetch_profiles:
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

        race.course_detail = find(doc, 'span', 'RC-header__straightRoundJubilee').strip('()')

        if race.course == 'Belmont At The Big A':
            race.course_id = 255
            race.course = 'Aqueduct'

        race.region = get_region(str(race.course_id))

        race.race_name = find(doc, 'span', 'RC-header__raceInstanceTitle')

        race.race_type = RACE_TYPE[runner['raceTypeCode']]

        race.distance_f = runner['distanceFurlongRounded']
        race.distance_y = runner['distanceYard']
        race.distance_round = find(doc, 'strong', 'RC-header__raceDistanceRound')
        race.distance = find(doc, 'span', 'RC-header__raceDistance').strip('()')
        race.distance = race.distance or race.distance_round

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

        stats = Stats(doc_accordion) if fetch_stats else None

        race.runners = parse_runners(stats, runners, profiles, config)

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
        '--region',
        type=str,
        help="Region code to filter by (e.g., 'gb', 'ire').",
        metavar='CODE',
    )

    args = parser.parse_args()

    dates: list[str] = [
        (datetime.date.today() + datetime.timedelta(days=i)).isoformat() for i in range(MAX_DAYS)
    ]

    if args.day:
        dates = [dates[args.day - 1]]
    elif args.days:
        dates = dates[: args.days]
    else:
        parser.print_usage(sys.stderr)
        print(f'\nError: Must specify a day (--day) or days (--days) (1-{MAX_DAYS})')
        sys.exit(1)

    if not os.path.exists('../racecards'):
        os.makedirs('../racecards')

    # Validate and pass optional region filter
    region: str | None = None
    if hasattr(args, 'region') and args.region:
        region = args.region.lower()
        if not valid_region(region):
            print(f'Invalid region: {args.region}')
            sys.exit(1)

    race_urls = get_race_urls(dates, region)
    
    config = load_field_config()

    for date in race_urls:
        racecards = scrape_racecards(race_urls, date, config)

        with open(f'../racecards/{date}.json', 'w', encoding='utf-8') as f:
            _ = f.write(dumps(racecards).decode('utf-8'))


if __name__ == '__main__':
    main()
