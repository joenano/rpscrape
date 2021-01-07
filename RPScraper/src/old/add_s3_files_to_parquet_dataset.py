# After running full_refresh.py, this script downloads the S3 files and
# uploads them to a parquet dataset, then runs glue.

import awswrangler as wr
import boto3
import time

from apscheduler.schedulers.background import BackgroundScheduler

from RPScraper.settings import PROJECT_DIR, S3_BUCKET
from RPScraper.src.utils.s3_tools import download_from_s3
from RPScraper.src.upload_data_to_s3 import upload_local_files_to_dataset, append_to_pdataset
from RPScraper.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

download = True
upload = True

if download:
    scheduler = BackgroundScheduler()

    # Get all files currently in S3
    files = wr.s3.list_objects(f's3://{S3_BUCKET}/data/', boto3_session=session)
    files = [f for f in files if '.parquet' in f]

    for file in files:
        filename = f"{PROJECT_DIR}/s3_data/{file.split('/')[-1]}"
        print(filename)
        scheduler.add_job(
            func=download_from_s3,
            kwargs={'local_path': filename, 's3_path': file.split(f's3://{S3_BUCKET}/')[1], 'bucket': S3_BUCKET,
                    'session': session},
            id=f"{file.split('/')[-1]}_download", replace_existing=True, misfire_grace_time=9999999999)

    scheduler.start()
    time.sleep(1)
    while len(scheduler._pending_jobs) > 0:
        print(f"Jobs left: {len(scheduler._pending_jobs)}")
    scheduler.shutdown()

# Upload the local files to a parquet dataset
if upload:
    upload_local_files_to_dataset(folder='s3_data')
