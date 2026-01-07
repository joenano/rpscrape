from argparse import ArgumentParser
from datetime import date
from typing import NamedTuple

from utils.paths import RequestKey

from utils.course import (
    course_name,
    course_search,
    courses,
    print_courses,
    valid_course,
)
from utils.date import (
    check_date,
    format_date,
    get_dates,
    parse_years,
    valid_years,
)
from utils.region import (
    print_regions,
    valid_region,
    region_search,
)


class ParsedRequest(NamedTuple):
    request: RequestKey
    dates: list[date]
    years: list[str]
    tracks: list[tuple[str, str]]
    race_type: str


class ParsedArgs(NamedTuple):
    dates: list[date]
    tracks: list[tuple[str, str]]
    years: list[str]
    region: str
    race_type: str


class ArgParser:
    def __init__(self):
        self.parser: ArgumentParser = ArgumentParser(prog='rpscrape')

        _ = self.parser.add_argument(
            '-d',
            '--date',
            help='Date or date range: YYYY/MM/DD or YYYY/MM/DD-YYYY/MM/DD',
        )
        _ = self.parser.add_argument(
            '-y',
            '--year',
            help='Year or range: YYYY or YYYY-YYYY',
        )
        _ = self.parser.add_argument(
            '-r',
            '--region',
            help='Region code (e.g. gb, ire)',
        )
        _ = self.parser.add_argument(
            '-c',
            '--course',
            help='Course numeric code',
        )
        _ = self.parser.add_argument(
            '-t',
            '--type',
            choices={'flat', 'jumps'},
            help='Race type',
        )
        _ = self.parser.add_argument(
            '--date-file',
            metavar='PATH',
            help='File containing dates, one per line (YYYY/MM/DD)',
        )

        # search / listing helpers
        _ = self.parser.add_argument(
            '--regions',
            nargs='?',
            const='',
            metavar='QUERY',
            help='List regions or search regions',
        )
        _ = self.parser.add_argument(
            '--courses',
            nargs='?',
            const='',
            metavar='QUERY|REGION',
            help='List courses, search courses, or list courses in region',
        )

    def parse(self, argv: list[str]) -> ParsedRequest:
        args = self.parser.parse_args(argv)

        # ---------- informational commands ----------
        if args.regions is not None:
            print_regions() if args.regions == '' else region_search(args.regions)
            raise SystemExit(0)

        if args.courses is not None:
            if args.courses == '':
                print_courses()
            elif valid_region(args.courses):
                print_courses(args.courses)
            else:
                course_search(args.courses)
            raise SystemExit(0)

        # ---------- mutual exclusion ----------
        if args.region and args.course:
            self.parser.error('Choose either --region or --course, not both')

        # ---------- scope ----------
        if args.course:
            if not valid_course(args.course):
                self.parser.error('Invalid course code')

            name = course_name(args.course)
            if not name:
                self.parser.error('Unknown course')

            scope_kind = 'course'
            scope_value = args.course
            tracks = [(args.course, name)]
        else:
            region = args.region or 'all'
            if args.region and not valid_region(args.region):
                self.parser.error('Invalid region code')

            scope_kind = 'region'
            scope_value = region
            tracks = list(courses(region))

        # ---------- race type ----------
        race_type = args.type or 'all'

        dates: list[date] = []
        years: list[str] = []

        # ---------- date-file mode ----------
        if args.date_file:
            if args.date or args.year:
                self.parser.error('--date-file cannot be used with --date or --year')

            try:
                with open(args.date_file, 'r', encoding='utf-8') as f:
                    raw_dates = [line.strip() for line in f if line.strip()]
            except OSError as e:
                self.parser.error(f'Unable to read dates file: {e}')

            for d in raw_dates:
                d = d.replace('-', '/')
                if not check_date(d):
                    self.parser.error(f'Invalid date in file: {d}')
                dates.extend(get_dates(d))

        # ---------- date mode ----------
        elif args.date:
            if args.year:
                self.parser.error('--date and --year are incompatible')

            if not check_date(args.date):
                self.parser.error('Invalid date format')

            dates = get_dates(args.date)

        # ---------- year mode ----------
        else:
            if not args.year:
                self.parser.error('Either --date, --date-file, or --year is required')

            years = parse_years(args.year)
            if not years or not valid_years(years):
                self.parser.error('Invalid year or year range')

        # ---------- enforce race type for year scraping ----------
        if years and not args.type:
            self.parser.error('--type is required when scraping by year')

        # ---------- filename identity ----------
        if dates:
            start = format_date(dates[0])
            end = format_date(dates[-1])
        else:
            start = f'{years[0]}'
            end = f'{years[-1]}'

        filename = start if start == end else f'{start}_{end}'

        request = RequestKey(
            scope_kind=scope_kind,
            scope_value=scope_value,
            race_type=race_type,
            filename=filename,
        )

        return ParsedRequest(
            request=request,
            dates=dates,
            years=years,
            tracks=tracks,
            race_type=race_type,
        )
