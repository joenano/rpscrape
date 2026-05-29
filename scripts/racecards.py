#!/usr/bin/env python

import argparse
import datetime
import os
import sys
import tomli

from collections import defaultdict
from dotenv import load_dotenv
from functools import partial
from lxml import html
from pathlib import Path
from orjson import dumps, loads
from tqdm import tqdm
from typing import Any

from utils.cleaning import clean_string
from utils.network import NetworkClient
from utils.profiles import get_profiles
from utils.region import valid_region
from utils.stats import Stats
from models.racecard import Racecard, Runner

_ = load_dotenv()


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
            'data_collection': {'fetch_profiles': False, 'fetch_stats': False, 'max_days': 2},
            'field_groups': {},  # Empty means all groups enabled
        }

    with open(config_path, 'rb') as f:
        config = tomli.load(f)

    return config


def validate_days_range(value: str, max_days: int) -> int:
    try:
        days = int(value)
        if 1 <= days <= max_days:
            return days
        raise argparse.ArgumentTypeError(
            f'Value must be an integer between 1 and {max_days}. Got: {days}'
        )
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid value: '{value}'. Expected an integer.")


def get_meetings(
    client: NetworkClient, dates: list[str], region: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    meetings: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    url = 'https://www.racingpost.com/api/racing/meetings/?date='

    for date in dates:
        status, response = client.get(url + date)

        if status != 200:
            print(f'Failed to get racecards for {date} (status: {status})')
            continue

        for meeting in response.json()['meetings']:
            if region and meeting['venueCountryCode'].lower() != region.lower():
                continue

            meetings[date].append(meeting)

    return dict(meetings)


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
    meetings: list[dict[str, Any]],
    date: str,
    config: dict[str, Any],
    client: NetworkClient,
) -> Racecards:
    racecards: Racecards = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    data_opts: dict[str, Any] = config.get('data_collection', {})
    fetch_profiles: bool = data_opts.get('fetch_profiles', False)
    fetch_stats: bool = data_opts.get('fetch_stats', False)

    for meeting in tqdm(
        meetings,
        desc=date,
        bar_format='{desc}: {percentage:3.0f}% |{bar:49}| {n}/{total} ETA {remaining}',
        ncols=91,
    ):
        course_id = meeting['venueUid']
        course_key = meeting['courseKey']

        for race in meeting['races']:
            race_id = race['raceId']

            url_base = 'https://www.racingpost.com'
            url_racecard = f'{url_base}/racecards/{course_id}/{course_key}/{date}/{race_id}/'
            url_runners = f'{url_base}/profile/horse/data/cardrunners/{race_id}.json'

            status_racecard, resp_racecard = client.get(url_racecard)
            status_runners, resp_runners = client.get(url_runners)

            if status_racecard != 200 or status_runners != 200:
                print('Failed to get racecard data.')
                print(f'status: {status_racecard} url: {url_racecard}')
                print(f'status: {status_runners} url: {url_runners}')
                continue

            try:
                runners_map = resp_runners.json()['runners']
                runners_json = list(runners_map.values())
            except (KeyError, IndexError, ValueError):
                print('Failed to parse JSON for runners.')
                print(f'url: {url_runners}')
                continue

            doc = html.fromstring(resp_racecard.content)
            json_string = doc.get_element_by_id('__NEXT_DATA__').text_content()

            try:
                data = loads(json_string)['props']['pageProps']['initialState']
                meeting_meta = data['meetings']['byDate'][date]['races']['byRaceId'][race_id]
                race_meta = data['racePage']['data']['race']
                runners = data['racePage']['data']['runners']
            except KeyError:
                print('Failed to get racecard data.')
                print(f'Invalid JSON at URL: {url_racecard}')
                continue

            profiles: dict[str, dict[str, Any]] = {}
            if fetch_profiles:
                profile_hrefs = [r['horseUrl'] for r in runners]
                profile_urls = [
                    f'https://www.racingpost.com{a.split("#")[0]}/form' for a in profile_hrefs
                ]
                profiles = get_profiles(client, profile_urls)

            stats = None
            if fetch_stats:
                status, resp = client.get(
                    f'https://www.racingpost.com/api/racing/free-stats-tab/?raceId={race_id}&date={date}'
                )
                if status == 200:
                    stats = Stats(resp.json())

            racecard: Racecard = Racecard()

            racecard.href = url_racecard
            racecard.race_id = int(race_id)
            racecard.date = date

            racecard.off_time = race_meta['startTime']

            racecard.course_id = course_id
            racecard.course = race_meta['courseStyleName']

            racecard.course_detail = race_meta['straightRoundJubileeCode']
            racecard.course_info = data['racePage']['data']['courseInfo']

            if racecard.course == 'Belmont At The Big A':
                racecard.course_id = 255
                racecard.course = 'Aqueduct'

            racecard.region = meeting['venueCountryCode']

            racecard.race_name = race['raceTitle']
            racecard.race_type = race['raceType']

            racecard.distance_f = race_meta['distanceFurlongs']
            racecard.distance_y = race_meta['distanceYards']
            racecard.distance = meeting_meta['displayDistance']

            racecard.pattern = race_meta['raceGroupDesc']
            racecard.race_class = race['raceClass']
            racecard.age_band = race['ageRestriction']
            racecard.rating_band = race['ratingBand']

            racecard.prizes = [{str(x['position_no']): x['prize_sterling']} for x in race_meta['prizes']]
            racecard.prize = race_meta['totalPrizeMoney']['total_prize_sterling']
            racecard.prize_winner = race_meta['formattedTotalPrizeMoney']

            racecard.field_size = race['numberOfRunners']

            racecard.handicap = race['isHandicap']
            racecard.going = race['going']
            racecard.surface = race['surfaceType']
            racecard.category = race['category']

            racecard.runners = parse_runners(stats, runners_json, profiles, config)

            assert racecard.region is not None
            assert racecard.course is not None
            assert racecard.off_time is not None

            racecards[racecard.region][racecard.course][racecard.off_time] = racecard.to_dict()

    return racecards


def main() -> None:
    config = load_field_config()
    max_days = config.get('data_collection', {}).get('max_days', 2)

    parser = argparse.ArgumentParser(
        description='Scrape racecards for a single day or a range of days.',
        formatter_class=argparse.RawTextHelpFormatter,
    )

    flag_group = parser.add_mutually_exclusive_group()

    validate_with_limit = partial(validate_days_range, max_days=max_days)

    _ = flag_group.add_argument(
        '--day',
        type=validate_with_limit,
        help='Scrape a single specific day (N).',
        metavar='N',
    )

    _ = flag_group.add_argument(
        '--days',
        type=validate_with_limit,
        help='Scrape a range of days (N total).',
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
        (datetime.date.today() + datetime.timedelta(days=i)).isoformat() for i in range(max_days)
    ]

    if args.day:
        dates = [dates[args.day - 1]]
    elif args.days:
        dates = dates[: args.days]
    else:
        parser.print_usage(sys.stderr)
        print(f'\nError: Must specify a day (--day) or days (--days) (1-{max_days})')
        sys.exit(1)

    if not os.path.exists('../racecards'):
        os.makedirs('../racecards')

    region = args.region.lower() if args.region else None

    if region and not valid_region(region):
        print(f'Invalid region: {args.region}')
        sys.exit(1)

    client = NetworkClient(
        email=os.getenv('EMAIL'),
        access_token=os.getenv('ACCESS_TOKEN'),
    )

    meetings = get_meetings(client, dates, region)

    for date in meetings:
        racecards = scrape_racecards(meetings[date], date, config, client)

        with open(f'../racecards/{date}.json', 'w', encoding='utf-8') as f:
            _ = f.write(dumps(racecards).decode('utf-8'))


if __name__ == '__main__':
    main()
