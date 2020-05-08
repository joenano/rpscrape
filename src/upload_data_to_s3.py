import os

from src.utils import upload_csv_to_s3
from settings import PROJECT_DIR

countries = os.listdir(f"{PROJECT_DIR}/data")
files = list()
for country in countries:
    for file in os.listdir(f"{PROJECT_DIR}/{country}"):
        date = file[:-4]
        print(f'Uploading {country} - {date} to S3')
        upload_csv_to_s3(country, date)
