# Set up virutal environment
virtualenv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Add environment variables
export PROJECT_DIR=./
export S3_BUCKET=rpscrape
export AWS_GLUE_DB=finish-time-predict
export AWS_GLUE_TABLE=rpscrape
export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
# Run upload script
python ./src/upload_data_to_s3.py
