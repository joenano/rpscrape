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

from utils.cleaning import clean_string
from utils.course import valid_meeting
from utils.header import RandomHeader
from utils.going import get_surface
from utils.lxml_funcs import find
from utils.network import NetworkClient
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
    """Load field configuration from settings/user_racecard_settings.toml or default_racecard_settings.toml"""
    user_config_path = Path('../settings/user_racecard_settings.toml')
    default_config_path = Path('../settings/default_racecard_settings.toml')

    # Try user config first, fallback to default
    config_path = user_config_path if user_config_path.exists() else default_config_path

    if not config_path.exists():
        # Return default config (everything enabled)
        return {
            'data_collection': {
                'fetch_profiles': False,
                'fetch_stats': False,
            },
            'field_groups': {},  # Empty means all groups enabled
        }

    with open(config_path, 'rb') as f:
        config = tomli.load(f)

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


def get_race_urls(
    client: NetworkClient, dates: list[str], region: str | None = None
) -> dict[str, list[tuple[str, str]]]:
    race_urls: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)

    for date in dates:
        url = f'https://www.racingpost.com/racecards/{date}'
        status, response = client.get(url)

        if status != 200 or not response.content:
            print(f'Failed to get racecards for {date} (status: {status})')
            continue

        doc = html.fromstring(response.content)

        for meeting in doc.xpath('//section[@data-accordion-row]'):
            course = meeting.xpath(".//span[contains(@class, 'RC-accordion__courseName')]")[0]
            if valid_meeting(course.text_content().strip().lower()):
                for race in meeting.xpath(".//a[@class='RC-meetingItem__link js-navigate-url']"):
                    race_id = race.attrib['data-race-id']
                    href = race.attrib['href']

                    if region:
                        course_id = href.split('/')[2]
                        if get_region(course_id) != region.upper():
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
    field_groups = config.get('field_groups', {})
    data_opts = config.get('data_collection', {})

    # If field_groups is empty, include all groups
    include_all_groups = not field_groups

    # Helper to check if a group should be included
    def should_include_group(group: str) -> bool:
        if include_all_groups:
            return True
        if group not in field_groups:
            raise KeyError(f'Unknown field group: {group}')
        return field_groups[group] is True

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

        # Core identification fields
        if should_include_group('core'):
            runner.name = clean_string(runner_json['horseName'])
            runner.horse_id = runner_json['horseUid']
            runner.number = runner_json['startNumber']
            runner.draw = runner_json['draw'] if runner_json['draw'] else None

        # Basic info
        if should_include_group('basic_info'):
            runner.age = runner_json['horseAge']
            runner.colour = runner_json['horseColourCode']
            runner.region = runner_json['countryOriginCode']
            runner.dob = runner_json['horseDateOfBirth'].split('T')[0]
            runner.sex_code = runner_json['horseSexCode']
            if profile:
                runner.sex = profile['horseSex']

        # Performance
        if should_include_group('performance'):
            runner.form = (
                ''.join(f['formFigure'] for f in runner_json['figuresCalculated'])[::-1]
                if runner_json['figuresCalculated']
                else ''
            )
            runner.rpr = runner_json['rpPostmark'] if runner_json['rpPostmark'] else None
            runner.ts = runner_json['rpTopspeed'] if runner_json['rpTopspeed'] else None
            runner.ofr = (
                runner_json['officialRatingToday'] if runner_json['officialRatingToday'] else None
            )
            runner.last_run = runner_json['daysSinceLastRun']

        # Jockey fields
        if should_include_group('jockey'):
            runner.jockey = clean_string(runner_json['jockeyName'])
            runner.jockey_id = runner_json['jockeyUid']
            runner.jockey_allowance = runner_json['weightAllowanceLbs']
            runner.claim = runner_json['weightAllowanceLbs']

        # Trainer fields
        if should_include_group('trainer'):
            runner.trainer = clean_string(runner_json['trainerStylename'])
            runner.trainer_id = runner_json['trainerId']
            runner.trainer_rtf = runner_json['trainerRtf']
            if profile:
                runner.trainer_location = profile['trainerLocation']
                runner.trainer_14_days = profile['trainerLast14Days']

        # Weight
        if should_include_group('weight'):
            runner.lbs = runner_json['weightCarriedLbs']

        # Equipment
        if should_include_group('equipment'):
            runner.headgear = runner_json['rpHorseHeadGearCode']
            runner.headgear_first = runner_json['firstTime']
            runner.gelding_first_time = runner_json['geldingFirstTime']
            runner.wind_surgery_first = runner_json['windSurgeryFirstTime']
            runner.wind_surgery_second = runner_json['windSurgerySecondTime']

        # Breeding
        if should_include_group('breeding'):
            runner.sire = clean_string(runner_json['sireName'])
            runner.sire_id = runner_json['sireId']
            runner.sire_region = runner_json['sireCountry']
            runner.dam = clean_string(runner_json['damName'])
            runner.dam_id = runner_json['damId']
            runner.dam_region = runner_json['damCountry']
            runner.damsire = clean_string(runner_json['damsireName'])
            runner.damsire_id = runner_json['damsireId']
            runner.damsire_region = runner_json['damsireCountry']
            runner.breeder = clean_string(runner_json['breederName'])
            runner.breeder_id = runner_json['breederUid']

        # Ownership
        if should_include_group('ownership'):
            runner.owner = clean_string(runner_json['ownerName'])
            runner.owner_id = runner_json['ownerUid']

        # Comments
        if should_include_group('comments'):
            runner.comment = runner_json['diomed']
            runner.spotlight = runner_json['spotlight']

        # Status
        if should_include_group('status'):
            runner.non_runner = runner_json['nonRunner']
            runner.reserve = runner_json['irishReserve']

        # Silk
        if should_include_group('silk'):
            runner.silk_path = runner_json['silkImagePath']
            runner.silk_url = f'https://www.rp-assets.com/svg/{runner_json["silkImagePath"]}.svg'

        # Profile data
        if should_include_group('profile') and profile:
            runner.profile = profile['profile']

        # Stats data
        if should_include_group('stats') and stats:
            horse_stats = (
                stats.horses[str(runner.horse_id)].to_dict()
                if str(runner.horse_id) in stats.horses
                else {}
            )
            jockey_stats = (
                stats.jockeys[str(runner.jockey_id)] if str(runner.jockey_id) in stats.jockeys else {}
            )
            trainer_stats = (
                stats.trainers[str(runner.trainer_id)]
                if str(runner.trainer_id) in stats.trainers
                else {}
            )
            runner.stats = {
                'horse': horse_stats,
                'jockey': jockey_stats,
                'trainer': trainer_stats,
            }

        # History data
        if should_include_group('history') and profile:
            if profile.get('previousTrainers'):
                runner.prev_trainers = [
                    {
                        'trainer': clean_string(trainer['trainerStyleName']),
                        'trainer_id': trainer['trainerUid'],
                        'change_date': trainer['trainerChangeDate'].split('T')[0],
                    }
                    for trainer in profile['previousTrainers']
                ]
            if profile.get('previousOwners'):
                runner.prev_owners = [
                    {
                        'owner': clean_string(owner['ownerStyleName']),
                        'owner_id': owner['ownerUid'],
                        'change_date': owner['ownerChangeDate'].split('T')[0],
                    }
                    for owner in profile['previousOwners']
                ]

        # Medical data
        if should_include_group('medical') and profile and profile.get('medical'):
            runner.medical = [
                {'date': med['medicalDate'].split('T')[0], 'type': med['medicalType']}
                for med in profile['medical']
            ]

        # Quotes data
        if should_include_group('quotes') and profile:
            if profile.get('quotes'):
                runner.quotes = [
                    {
                        'date': q['raceDate'].split('T')[0],
                        'horse': clean_string(q['horseStyleName']),
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
            if profile.get('stable_quotes'):
                runner.stable_tour = [
                    {
                        'horse': clean_string(q['horseName']),
                        'horse_id': q['horseUid'],
                        'quote': q['notes'],
                    }
                    for q in profile['stable_quotes']
                ]

    return runners


def scrape_racecards(
    race_urls: dict[str, list[tuple[str, str]]],
    date: str,
    config: dict[str, Any],
    client: NetworkClient,
) -> Racecards:
    races: Racecards = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    data_opts = config.get('data_collection', {})
    fetch_profiles = data_opts.get('fetch_profiles', False)
    fetch_stats = data_opts.get('fetch_stats', False)

    for race_id, href in tqdm(
        race_urls[date],
        desc=date,
        bar_format='{desc}: {percentage:3.0f}% |{bar:49}| {n}/{total} ETA {remaining}',
        ncols=91,
    ):
        url_base = 'https://www.racingpost.com'
        url_racecard = f'{url_base}{href}'
        url_runners = f'{url_base}/profile/horse/data/cardrunners/{race_id}.json'

        status_racecard, resp_racecard = client.get(url_racecard)
        status_runners, resp_runners = client.get(url_runners)

        if status_racecard != 200 or status_runners != 200:
            print('Failed to get racecard data.')
            print(f'status: {status_racecard} url: {url_racecard}')
            print(f'status: {status_runners} url: {url_runners}')
            continue

        # Optional stats request
        status_accordion = None
        resp_accordion = None
        if fetch_stats:
            url_accordion = f'{url_base}/racecards/data/accordion/{race_id}'
            status_accordion, resp_accordion = client.get(url_accordion)

        try:
            doc = html.fromstring(resp_racecard.content)
        except etree.ParserError:
            print('Failed to parse HTML for racecard.')
            print(f'url: {url_racecard}')
            continue

        doc_accordion = None
        if fetch_stats and status_accordion == 200 and resp_accordion is not None:
            try:
                doc_accordion = html.fromstring(resp_accordion.content)
            except etree.ParserError:
                doc_accordion = None

        try:
            runners_map = resp_runners.json()['runners']
            runners = list(runners_map.values())
            race_meta = runners[0]
        except (KeyError, IndexError, ValueError):
            print('Failed to parse JSON for runners.')
            print(f'url: {url_runners}')
            continue

        profiles: dict[str, dict[str, Any]] = {}
        if fetch_profiles:
            profile_hrefs = doc.xpath("//a[@data-test-selector='RC-cardPage-runnerName']/@href")
            profile_urls = [url_base + a.split('#')[0] + '/form' for a in profile_hrefs]
            profiles = get_profiles(profile_urls)

        race: Racecard = Racecard()

        race.href = url_racecard
        race.race_id = int(race_id)
        race.date = date

        race.off_time = datetime.datetime.fromisoformat(race_meta['raceDatetime']).strftime('%H:%M')

        race.course_id = race_meta['courseUid']
        race.course = find(doc, 'h1', 'RC-courseHeader__name')
        race.course_detail = find(doc, 'span', 'RC-header__straightRoundJubilee').strip('()')

        if race.course == 'Belmont At The Big A':
            race.course_id = 255
            race.course = 'Aqueduct'

        race.region = get_region(str(race.course_id))
        race.race_name = find(doc, 'span', 'RC-header__raceInstanceTitle')
        race.race_type = RACE_TYPE[race_meta['raceTypeCode']]

        race.distance_f = race_meta['distanceFurlongRounded']
        race.distance_y = race_meta['distanceYard']
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

        stats = Stats(doc_accordion) if doc_accordion is not None else None

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

    region = args.region.lower() if args.region else None

    if region and not valid_region(region):
        print(f'Invalid region: {args.region}')
        sys.exit(1)

    client = NetworkClient()

    race_urls = get_race_urls(client, dates, region)

    config = load_field_config()

    for date in race_urls:
        racecards = scrape_racecards(race_urls, date, config, client)

        with open(f'../racecards/{date}.json', 'w', encoding='utf-8') as f:
            _ = f.write(dumps(racecards).decode('utf-8'))


if __name__ == '__main__':
    main()
