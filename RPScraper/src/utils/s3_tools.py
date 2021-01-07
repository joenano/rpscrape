import logging
import boto3
from botocore.exceptions import ClientError

# Create boto3 client to interact with S3
s3_client = boto3.client('s3')


def delete_from_s3(s3_path, bucket="betfair-exchange-qemtek"):
    """Delete a file from an S3 bucket
        :param bucket: S3 Bucket to use
        :param s3_path: Path inside S3 to store the data
        """
    try:
        s3_client.delete_object(bucket=bucket, key=s3_path)
    except ClientError as e:
        logging.error(e)
        print(e)


def upload_to_s3(local_path, s3_path, bucket="betfair-exchange-qemtek"):
    """Upload a file to an S3 bucket
        :param local_path: File to upload
        :param bucket: S3 Bucket to upload to
        :param s3_path: Path inside S3 to store the data
        """
    # Upload the file
    try:
        s3_client.upload_file(local_path, bucket, s3_path)
    except ClientError as e:
        logging.error(e)
        print(e)


def download_from_s3(local_path, s3_path, bucket="betfair-exchange-qemtek", session=None):
    """Download a file from an S3 bucket
        :param local_path: Path to save the file
        :param bucket: S3 Bucket to download from
        :param s3_path: S3 path
        """
    try:
        if session is not None:
            client = session.client('s3')
        else:
            client=s3_client
        client.download_file(Bucket=bucket, Key=s3_path, Filename=local_path)
        print(f"Download completed for {s3_path}")
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise


def move_file(source, destination, bucket="betfair-exchange-qemtek"):
    """Move a file from one location to another insidee an S3 bucket
        :param source: Source file destination
        :param destination: Directory of the new location
        :param bucket: S3 Bucket to use
        """
    try:
        # Copy object to new destination
        s3_client.copy_object(Bucket=bucket, CopySource=source, Key=destination)
        # Delete old file
        s3_client.delete_object(Bucket=bucket, Key=source)
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise


def list_files(prefix, bucket, session=None):
    """List files in specific S3 URL
        :param bucket: S3 Bucket to use
        :param prefix: S3 path"""

    def get_all_s3_objects(s3_client, **base_kwargs):
        continuation_token = None
        while True:
            list_kwargs = dict(MaxKeys=1000, **base_kwargs)
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token
            response = s3_client.list_objects_v2(**list_kwargs)
            yield from response.get('Contents', [])
            if not response.get('IsTruncated'):  # At the end of the list?
                break
            continuation_token = response.get('NextContinuationToken')
    if session is not None:
        client = session.client('s3')
    else:
        client = s3_client
    output = []
    for file in get_all_s3_objects(s3_client=client, Bucket=bucket, Prefix=prefix):
        output.append(file)
    return output
