import awswrangler as wr
import boto3
import pandas as pd
import time
import os

from apscheduler.schedulers.background import BackgroundScheduler

from RPScraper.settings import PROJECT_DIR, S3_BUCKET, AWS_GLUE_DB, AWS_GLUE_TABLE, SCHEMA_COLUMNS

session = boto3.session.Session()


def append_to_pdataset(local_path, mode):
    df = pd.read_parquet(local_path)
    df['pos'] = df['pos'].astype(str)
    df['pattern'] = df['pattern'].astype(str)
    df['prize'] = df['prize'].astype(str)
    wr.s3.to_parquet(df, path=f's3://{S3_BUCKET}/datasets/', dataset=True,
                     dtype=SCHEMA_COLUMNS, mode=mode, boto3_session=session)
    print(f"Uploaded {local_path} to parquet dataset")
    os.remove(local_path)


def upload_local_files_to_dataset():
    scheduler2 = BackgroundScheduler()

    # Get all files currently in S3
    files = os.listdir(f"{PROJECT_DIR}/s3_data/")

    for file in files:
        filename = f"{PROJECT_DIR}/s3_data/{file.split('/')[-1]}"
        print(filename)
        scheduler2.add_job(
            func=append_to_pdataset, kwargs={"local_path": filename, 'mode': 'append'},
            id=f"{file.split('/')[-1]}_upload", replace_existing=True, misfire_grace_time=999999999)

    scheduler2.start()
    time.sleep(1)
    while len(scheduler2._pending_jobs) > 0:
        print(f"Jobs left: {len(scheduler2._pending_jobs)}")
    scheduler2.shutdown()

    # Run crawler
    print("Running crawler")
    res = wr.s3.store_parquet_metadata(
        path=f"s3://{S3_BUCKET}/datasets/",
        database=AWS_GLUE_DB,
        table=AWS_GLUE_TABLE,
        dataset=True
    )


if __name__ == '__main__':
    upload_local_files_to_dataset()
