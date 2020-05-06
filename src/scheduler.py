import datetime as dt
import subprocess
import pandas as pd
import os
import awswrangler as wr

from src.s3_tools import list_files
from src.utils import clean_data

PROJECT_DIR = os.environ['PROJECT_DIR']
S3_BUCKET = os.environ['BUCKET_NAME']

files = list_files(bucket=S3_BUCKET, prefix='')
# Remove folder name from the list of returned objects
if len(files) > 1:
    files = files[1:]
    file_names = [f.get('Key') for f in files]
else:
    file_names = []

from apscheduler.schedulers.background import BlockingScheduler

scheduler = BlockingScheduler()


def run_rpscrape(country, date):
    subprocess.call(f'echo "-d {date} {country}" | python3 rpscrape.py', shell=True)
    print(f'Finished scraping {country} - {date}')
    upload_csv_to_s3(country, date)


def upload_csv_to_s3(country, date):
    file_name = f"{str(date).replace('/', '_')}"
    df = pd.read_csv(f"{PROJECT_DIR}/data/{country}/{file_name}.csv")
    if len(df) > 0 and df is not None:
        # Apply some preprocessing steps
        df = clean_data(df, country)
        new_file_name = f"{country}_{file_name.replace('_', '-')}"
        s3_path = f"s3://{S3_BUCKET}/{new_file_name}.parquet"
        wr.s3.to_parquet(df,s3_path)
        print(f"Finished uploading to S3 {country} - {date}")
        os.remove(f"{PROJECT_DIR}/data/{country}/{file_name}.csv")
        print(f"Finished clean up {country} - {date}")


date_today = dt.datetime.today().date()
start_date = date_today - dt.timedelta(days=round(364.25*10))
print(f"Start date: {start_date}")
end_date = date_today - dt.timedelta(days=1)
print(f"End date: {end_date}")

# Get the countries we want
countries = ["gb", "ire"]
# Find the number of days between the start and end dates
delta = end_date - start_date
dates = list()
for country in countries:
    for i in range(delta.days + 1):
        day = (start_date + dt.timedelta(days=i)).strftime(format='%Y/%m/%d')
        s3_file_name = f"{country}_{str(day).replace('/', '-')}"
        local_file_path = f"{PROJECT_DIR}/data/{country}/{str(day).replace('/', '_')}.csv"
        print(local_file_path)
        exists_locally = os.path.exists(local_file_path)
        exists_remotely = True if s3_file_name in file_names else False
        if not exists_remotely:
            if exists_locally:
                print(f'{country}/{day} exists locally but not on S3, uploading local file..')
                upload_csv_to_s3(country, day)
            else:
                scheduler.add_job(id=str(hash(f"{day}_{country}")), func=run_rpscrape, name=f"{country}-{day}",
                                  kwargs={'country': country, 'date': day}, replace_existing=True,
                                  misfire_grace_time=99999999999)


scheduler.start()
