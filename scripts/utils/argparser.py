from argparse import ArgumentParser
from datetime import date
from typing import NamedTuple

from utils.region import (
    print_regions,
    valid_region,
    region_search,
)
from utils.course import (
    course_name,
    course_search,
    courses,
    print_courses,
    valid_course,
)
from utils.date import (
    check_date,
    get_dates,
    parse_years,
    valid_years,
)


class ParsedArgs(NamedTuple):
    dates: list[date]
    tracks: list[tuple[str, str]]
    years: list[str]
    region: str
    type: str


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

    def parse(self, argv: list[str]) -> ParsedArgs:
        args = self.parser.parse_args(argv)

        # ---------- informational commands ----------
        if args.regions is not None:
            if args.regions == '':
                print_regions()
            else:
                region_search(args.regions)
            raise SystemExit(0)

        if args.courses is not None:
            if args.courses == '':
                print_courses()
            elif valid_region(args.courses):
                print_courses(args.courses)
            else:
                course_search(args.courses)
            raise SystemExit(0)

        # ---------- validation ----------
        if args.region and args.course:
            self.parser.error('Choose either --region or --course, not both')

        dates: list[date] = []
        years: list[str] = []
        tracks: list[tuple[str, str]] = []

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

            region = args.region or 'all'
            if args.region and not valid_region(args.region):
                self.parser.error('Invalid region code')

            tracks = list(courses(region))

            return ParsedArgs(
                dates=dates,
                tracks=tracks,
                years=[],
                region=region,
                type=args.type,
            )

        # ---------- date mode ----------
        if args.date:
            if args.year:
                self.parser.error('--date and --year are incompatible')

            if not check_date(args.date):
                self.parser.error('Invalid date format')

            dates = get_dates(args.date)

            region = args.region or 'all'
            if args.region and not valid_region(args.region):
                self.parser.error('Invalid region code')

            tracks = list(courses(region))

            return ParsedArgs(
                dates=dates,
                tracks=tracks,
                years=[],
                region=region,
                type=args.type,
            )

        # ---------- year mode ----------
        if not args.year:
            self.parser.error('Either --date, --date-file, or --year is required')

        years = parse_years(args.year)
        if not years or not valid_years(years):
            self.parser.error('Invalid year or year range')

        # ---------- region ----------
        if args.region:
            if not valid_region(args.region):
                self.parser.error('Invalid region code')

            tracks = list(courses(args.region))
            region = args.region

        # ---------- course ----------
        elif args.course:
            if not valid_course(args.course):
                self.parser.error('Invalid course code')

            name = course_name(args.course)
            if not name:
                self.parser.error('Unknown course')

            tracks = [(args.course, name)]
            region = 'course'

        else:
            self.parser.error('Either --region or --course is required')

        return ParsedArgs(
            dates=[],
            tracks=tracks,
            years=years,
            region=region,
            type=args.type,
        )
