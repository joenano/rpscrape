import awswrangler as wr
import boto3
import pandas as pd
import time
import os
import pyarrow

from apscheduler.schedulers.background import BackgroundScheduler

from RPScraper.settings import PROJECT_DIR, S3_BUCKET, AWS_GLUE_DB, AWS_GLUE_TABLE, SCHEMA_COLUMNS, \
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

df_all_dir = f'{PROJECT_DIR}/tmp/df_all.csv'


def append_to_pdataset(local_path, mode='a', header=False, index=False):
    try:
        df = pd.read_parquet(local_path)
        df['pos'] = df['pos'].astype(str)
        df['pattern'] = df['pattern'].astype(str)
        df['prize'] = df['prize'].astype(str)
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].apply(lambda x: x.year)
        df = df[list(SCHEMA_COLUMNS.keys())]
        df.to_csv(df_all_dir, mode=mode, header=header, index=index)
    except pyarrow.lib.ArrowInvalid as e:
        print(f"Loading parquet file failed. \nFile path: {local_path}. \nError: {e}")


def upload_local_files_to_dataset(folder='data'):
    scheduler2 = BackgroundScheduler()
    # Get all files currently in S3
    folders = os.listdir(f"{PROJECT_DIR}/{folder}/")
    folders = [f for f in folders if 'DS_Store' not in f and '.keep' not in f]
    for country in folders:
        files = os.listdir(f"{PROJECT_DIR}/{folder}/{country}/")
        files = [f for f in files if 'DS_Store' not in f and '.keep' not in f]
        # Download / Upload the first file manually with overwrite
        filename = f"{PROJECT_DIR}/{folder}/{files[0]}"
        append_to_pdataset(filename, mode='w', header=True)
        files = files[1:]
        for file in files:
            filename = f"{PROJECT_DIR}/s3_data/{file.split('/')[-1]}"
            print(filename)
            scheduler2.add_job(func=append_to_pdataset, kwargs={"local_path": filename},
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
        wr.s3.to_parquet(df, path=f's3://{S3_BUCKET}/datasets/', dataset=True,
                         dtype=SCHEMA_COLUMNS, mode='overwrite', boto3_session=session,
                         database=AWS_GLUE_DB, table=AWS_GLUE_TABLE, partition_cols=['year'])
        print(f"Uploaded data to parquet dataset")


if __name__ == '__main__':
    upload_local_files_to_dataset()
