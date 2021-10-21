from datetime import date, timedelta, datetime


def check_date(date):
    if '-' in date and len(date.split('-')) < 3:
        return valid_date(date.split('-')[0]) and valid_date(date.split('-')[1])
    
    return valid_date(date)


def convert_date(date):
    dmy = date.split('-')
    return dmy[0] + '-' + dmy[1] + '-' + dmy[2]


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


def parse_years(year_str):
    if '-' in year_str:
        try:
            return [str(x) for x in range(int(year_str.split('-')[0]), int(year_str.split('-')[1]) + 1)]
        except ValueError:
            return []
    else:
        return [year_str]


def valid_date(date):
    if len(date.split('/')) == 3:
        try:
            year, month, day = [int(x) for x in date.split('/')]
            return 1987 <= year <= int(datetime.today().year) and 0 < month <= 12 and 0 < day <= 31
        except ValueError:
            return False

    return False


def valid_years(years):
    if years:
        return all(year.isdigit() and 1987 <= int(year) <= int(datetime.today().year) for year in years)

    return False
