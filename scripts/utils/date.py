from datetime import date, timedelta, datetime


def check_date(date_str: str) -> bool:
    parts = date_str.split('-')
    if len(parts) == 2:
        return valid_date(parts[0]) and valid_date(parts[1])
    return valid_date(date_str)


def convert_date(date_str: str) -> str:
    parts = date_str.split('-')
    if len(parts) != 3:
        raise ValueError(f'Invalid date format: {date_str}')
    return '-'.join(parts[:3])


def format_date(d: date) -> str:
    return d.strftime('%Y_%m_%d')


def get_dates(date_str: str) -> list[date]:
    def parse(s: str) -> date:
        year, month, day = map(int, s.split('/'))
        return date(year, month, day)

    if '-' in date_str:
        start_str, end_str = date_str.split('-', 1)
        start_date, end_date = parse(start_str), parse(end_str)
        delta = (end_date - start_date).days
        return [start_date + timedelta(days=i) for i in range(delta + 1)]

    return [parse(date_str)]


def parse_years(years: str) -> list[str]:
    if '-' in years:
        try:
            start, end = map(int, years.split('-', 1))
            return [str(x) for x in range(start, end + 1)]
        except ValueError:
            return []

    return [years]


def valid_date(date_str: str) -> bool:
    if len(date_str.split('/')) == 3:
        try:
            year, month, day = [int(x) for x in date_str.split('/')]
            return 1987 <= year <= int(datetime.today().year) and 0 < month <= 12 and 0 < day <= 31
        except ValueError:
            return False

    return False


def valid_years(years: list[str]):
    if years:
        return all(year.isdigit() and 1987 <= int(year) <= int(datetime.today().year) for year in years)

    return False
