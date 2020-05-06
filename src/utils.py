import datetime as dt


def convert_off_to_readable_format(x):
    """Convert the 'Off' column into a time object"""

    if x[0:2] not in ['10', '11', '12']:
        x = '0' + x
    x = x + ' PM'
    return str(dt.datetime.strptime(x, '%I:%M %p').time())


def convert_finish_time_to_seconds(x):
    """Convert finish time from a time object to seconds
    """
    if not isinstance(x, str):
        return x
    if ':' in x[0:2]:
        x = '0' + x
    return float(x[0:2]) * 60 + float(x[3:5]) + float(x[6:8]) / 10


def clean_name(x, illegal_symbols="'$@#^(%*)._ ", append_with=None):
    x = str(x).lower().strip()
    while x[0].isdigit():
        x = x[1:]
    # Remove any symbols, including spaces
    for s in illegal_symbols:
        x = x.replace(s, "")
    if append_with is not None:
        x = f"{x}_{append_with}"
    return x


def clean_horse_name(x, illegal_symbols="'$@#^(%*) ", append_with=None):
    # Remove the country part
    x = ' '.join(x.split(' ')[:-1])
    x = clean_name(x, illegal_symbols=illegal_symbols, append_with=append_with)
    return x


def nullify_non_finishers(x):
    x['time'] = x['time'] if str(x['pos']).isdigit() else None
    return x


def clean_data(df_in, country):
    """Perform all 'data cleansing' steps on raw rpscrape data
    """
    df = df_in.copy()
    # Make all columns lower case
    df.columns = [col.lower() for col in df_in.columns]
    # Add country
    df['country'] = country
    # Drop duplicates
    df = df.drop_duplicates()
    df['off'] = df['off'].apply(lambda x: convert_off_to_readable_format(x))
    # Convert finish time from a time object to seconds
    df['time'] = df['time'].apply(lambda x: convert_finish_time_to_seconds(x))
    # Convert the time of horse that did not finish to 0
    df = df.apply(lambda x: nullify_non_finishers(x), axis=1)
    # Convert the 'Off' column into a time object
    df['id'] = df.groupby(['date', 'course', 'off']).ngroup()
    # Clean up horse name (remove the country indicator from the end and make lower case)
    df['horse_cleaned'] = df.apply(lambda x: clean_horse_name(x['horse'], append_with=x['country']), axis=1)
    # Clean jockey name
    df['jockey_clened'] = df['jockey'].apply(lambda x: clean_name(x))
    # Clean trainer name
    df['trainer_cleaned'] = df['trainer'].apply(lambda x: clean_name(x))
    return df
