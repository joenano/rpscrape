#!/bin/bash
# set the path based on the first argument
echo "Path: $1"
countries=("$2@")

for country in "${countries[@]}"; do
  echo "Uploading data for $country"
  full_path=$1/$country
  if [ -d "$full_path" ]; then
    echo "Path to country folder: $full_path"
    for file in "$full_path"/*; do
      echo "Uploading: $full_path/$file to s3://rpscrape/data/$country"
      docker run --rm -ti -v .aws amazon/aws-cli s3 cp "$full_path/$file" "s3://rpscrape/data/$country"
    done
  else
    echo "$full_path dosent exist, skipping"
  fi
done
