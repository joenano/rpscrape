import datetime as dt
import pandas as pd
import awswrangler as wr
import os

from RPScraper.settings import PROJECT_DIR, S3_BUCKET


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
    if x == '-':
        return None
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
    """Perform all 'data cleansing' steps on raw RPScraper data
    """
    df = df_in.copy()
    # Make all columns lower case
    df.columns = [col.lower() for col in df_in.columns]
    # Add country
    df['country'] = country
    # Drop duplicates
    df = df.drop_duplicates()
    # Convert the 'Off' column into a time object
    df['off'] = df['off'].apply(lambda x: convert_off_to_readable_format(x))
    # Convert finish time from a time object to seconds
    df['time'] = df['time'].apply(lambda x: convert_finish_time_to_seconds(x))
    # Convert the time of horse that did not finish to None
    df = df.apply(lambda x: nullify_non_finishers(x), axis=1)
    # Create a unique identifier for each race
    df['id'] = df.apply(
        lambda x: hash(f"{x['date']}_{x['course']}_{x['off']}_{x['dist_m']}_{x['age_band']}"), axis=1)
    # Clean up horse name (remove the country indicator from the end and make lower case)
    df['horse_cleaned'] = df['horse_cleaned'].apply(lambda x: clean_horse_name(x))
    # Clean up dam name (remove the country indicator from the end and make lower case)
    df['dam_cleaned'] = df['dam'].apply(lambda x: clean_horse_name(x))
    # Clean up sire name (remove the country indicator from the end and make lower case)
    df['sire_cleaned'] = df['sire'].apply(lambda x: clean_horse_name(x))
    # Add dam and sire names to horse name to make it unique
    df['horse_cleaned'] = df.apply(lambda x: f"{x['horse_cleaned']}_{x['dam_cleaned']}_{x['sire_cleaned']}", axis=1)
    # Clean jockey name
    df['jockey_cleaned'] = df['jockey'].apply(lambda x: clean_name(x))
    # Clean trainer name
    df['trainer_cleaned'] = df['trainer'].apply(lambda x: clean_name(x))

    return df


def upload_csv_to_s3(country, date):
    file_name = f"{str(date).replace('/', '_')}"
    try:
        df = pd.read_csv(f"{PROJECT_DIR}/data/{country}/{file_name}.csv")
        if len(df) > 0 and df is not None:
            # Apply some preprocessing steps
            df = clean_data(df, country)
            df['pos'] = df['pos'].astype(str)
            df['pattern'] = df['pattern'].astype(str)
            df['prize'] = df['prize'].astype(str)
            df['date'] = pd.to_datetime(df['event_dt'])
            df['year'] = df['date'].apply(lambda x: x.year)
            # Upload to S3
            new_file_name = f"{country}_{file_name.replace('_', '-')}"
            s3_path = f"s3://{S3_BUCKET}/data/{new_file_name}.parquet"
            wr.s3.to_parquet(df, s3_path)
            # Upload to parquet dataset
            # wr.s3.to_parquet(df, path='s3://RPScraper/datasets/', dataset=True, database='finish-time-predict',
            #                  table='rpscrape', dtype=SCHEMA_COLUMNS, mode='append', boto3_session=session)
            print(f"Finished uploading to S3 {country} - {date}")
            os.remove(f"{PROJECT_DIR}/data/{country}/{file_name}.csv")
            print(f"Finished clean up {country} - {date}")
    except:
        print("Upload failed, the file was likely empty")
        os.remove(f"{PROJECT_DIR}/data/{country}/{file_name}.csv")
