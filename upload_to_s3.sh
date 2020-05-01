# Set AWS credentials and S3 paramters
AWS_KEY=""
AWS_SECRET=""
S3_BUCKET="rpscrape"
S3_BUCKET_PATH="data"

# You don't need Fog in Ruby or some other library to upload to S3 -- shell works perfectly fine
# This is how I upload my new Sol Trader builds (http://soltrader.net)
# Based on a modified script from here: http://tmont.com/blargh/2014/1/uploading-to-s3-in-bash

S3KEY="AKIATUMWGOXOAT6GEHYO"
S3SECRET="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" # pass these in

function putS3
{
  path=$1
  file=$2
  aws_path=$3
  bucket='rpscrape'
  date=$(date +"%a, %d %b %Y %T %z")
  acl="x-amz-acl:public-read"
  content_type='text/csv'
  string="PUT\n\n$content_type\n$date\n$acl\n/$bucket$aws_path$file"
  signature=$(echo -en "${string}" | openssl sha1 -hmac "${S3SECRET}" -binary | base64)
  curl -X PUT -T "$path/$file" \
    -H "Host: $bucket.s3.amazonaws.com" \
    -H "Date: $date" \
    -H "Content-Type: $content_type" \
    -H "$acl" \
    -H "Authorization: AWS ${S3KEY}:$signature" \
    "https://$bucket.s3.amazonaws.com$aws_path$file"
}


# set the path based on the first argument
echo "Path: $1"
countries=("gb" "ire")

for country in "${countries[@]}"; do
  echo "Uploading data for $country"
  full_path=$1/$country
  if [ -d "$full_path" ]; then
    echo "Path to country folder: $full_path"
    for file in "$full_path"/*; do
      echo "Uploading: $file"
      putS3 "$full_path" "${file##*/}" "/data/$country"
    done
  else
    echo "$full_path dosent exist, skipping"
  fi
done

