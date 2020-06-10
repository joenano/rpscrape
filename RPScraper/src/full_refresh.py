# Downloads all files from rpscrape and stores them in the data folder

import datetime as dt
import subprocess
import os
import awswrangler as wr
import boto3

from apscheduler.schedulers.background import BlockingScheduler

from RPScraper.src.utils.general import upload_csv_to_s3
from RPScraper.settings import PROJECT_DIR, S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

use_files_in_s3 = False

if use_files_in_s3:
    # Get a list of all files in S3 currently
    session = boto3.session.Session(aws_access_key_id=AWS_ACCESS_KEY_ID,
                                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    folder_dir = f's3://{S3_BUCKET}/data/'
    files = wr.s3.list_objects(folder_dir, boto3_session=session)
    file_names = [f.split(folder_dir)[1] for f in files]
else:
    file_names = []

# Define scheduler to run jobs
scheduler = BlockingScheduler()


def run_rpscrape(country, date):
    subprocess.call(f'echo "-d {date} {country}" | python3 rpscrape.py', shell=True)
    print(f'Finished scraping {country} - {date}')
    # upload_csv_to_s3(country, date)


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
        s3_file_name = f"{country}_{str(day).replace('/', '-')}.parquet"
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
        else:
            print(f"{s3_file_name} exists remotely")


scheduler.start()
