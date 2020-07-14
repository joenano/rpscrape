import awswrangler as wr
import boto3
import pandas as pd
import time
import os
import pyarrow
import numpy as np

from apscheduler.schedulers.background import BackgroundScheduler

from RPScraper.settings import PROJECT_DIR, S3_BUCKET, AWS_GLUE_DB, AWS_GLUE_TABLE, SCHEMA_COLUMNS, \
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from RPScraper.src.utils.general import clean_data

session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

df_all_dir = f'{PROJECT_DIR}/tmp/df_all.csv'


def append_to_pdataset(local_path, folder, mode='a', header=False, index=False):
    try:
        if folder == 'data':
            df = pd.read_csv(local_path)
            if len(df) > 0:
                country = local_path.split('/')[-2]
                df = clean_data(df, country=country)
        elif folder == 's3_data':
            df = pd.read_parquet(local_path)
        if len(df) > 0:
            df['pos'] = df['pos'].astype(str)
            df['pattern'] = df['pattern'].astype(str)
            df['prize'] = df['prize'].astype(str)
            df['date'] = pd.to_datetime(df['date'])
            df['year'] = df['date'].apply(lambda x: x.year)
            df['id'] = df.apply(lambda x: hash(f"{x['country']}_{x['date']}_{x['name']}_{x['off']}"), axis=1)
            df = df[list(SCHEMA_COLUMNS.keys())]
            df.to_csv(df_all_dir, mode=mode, header=header, index=index)
            date = local_path.split('/')[-1].split('.')[0].replace('_', '-')
            file_name = f"{country}_{date}"
            wr.s3.to_parquet(df, f"s3://{S3_BUCKET}/data/{file_name}.parquet", boto3_session=session)
    except pyarrow.lib.ArrowInvalid as e:
        print(f"Loading parquet file failed. \nFile path: {local_path}. \nError: {e}")


def upload_local_files_to_dataset(folder='data', full_refresh=False):
    scheduler2 = BackgroundScheduler()
    # Get all files currently in S3
    folders = os.listdir(f"{PROJECT_DIR}/{folder}/")
    folders = [f for f in folders if 'DS_Store' not in f and '.keep' not in f
               and '.ipynb_checkpoints' not in f]
    print(f"Folders found: {folders}")
    for country in folders:
        files = os.listdir(f"{PROJECT_DIR}/{folder}/{country}/")
        files = [f for f in files if 'DS_Store' not in f and '.keep' not in f
                 and '.ipynb_checkpoints' not in f]
        # Download / Upload the first file manually with overwrite
        filename = f"{PROJECT_DIR}/{folder}/{country}/{files[0]}"
        append_to_pdataset(filename, mode='w', header=True, folder=folder)
        files = files[1:]
        for file in files:
            filename = f"{PROJECT_DIR}/{folder}/{country}/{file}"
            print(filename)
            scheduler2.add_job(func=append_to_pdataset, kwargs={"local_path": filename, "folder": folder},
                               id=f"{file.split('/')[-1]}_upload", replace_existing=True,
                               misfire_grace_time=999999999)
    scheduler2.start()
    time.sleep(1)
    print(f"Jobs left: {len(scheduler2._pending_jobs)}")
    time.sleep(1)
    while len(scheduler2._pending_jobs) > 0:
        print(f"Jobs left: {len(scheduler2._pending_jobs)}")
    scheduler2.shutdown()
    # Upload the dataframe to the /datasets/ directory in S3
    if os.path.exists(df_all_dir):
        df = pd.read_csv(df_all_dir)
        for key, value in SCHEMA_COLUMNS.items():
            if value == 'string':
                df[key] = df[key].astype(str)
                df[key] = df[key].fillna(pd.NA)
            elif value == 'int':
                df.loc[~df[key].isna(), key] = df.loc[~df[key].isna(), key].astype(np.int32)
                df[key] = df[key].fillna(pd.NA)
            elif value == 'double':
                df.loc[~df[key].isna(), key] = df.loc[~df[key].isna(), key].astype(np.float32)
                df[key] = df[key].fillna(pd.NA)
        wr.s3.to_parquet(df, path=f's3://{S3_BUCKET}/datasets/', dataset=True,
                         dtype=SCHEMA_COLUMNS, mode='overwrite' if full_refresh else 'append',
                         boto3_session=session, database=AWS_GLUE_DB, table=AWS_GLUE_TABLE,
                         partition_cols=['year'])
        print(f"Uploaded data to parquet dataset")


if __name__ == '__main__':
    upload_local_files_to_dataset(full_refresh=False)
