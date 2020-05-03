#!/bin/bash
cd scripts
python3 scheduler.py
cd ..

# set the path based on the first argument
echo "Uploading data to S3"
countries=("gb" "ire")
for country in "${countries[@]}"; do
  echo "Uploading data for $country"
  full_path=data/$country
  if [ -d "$full_path" ]; then
    echo "Path to country folder: $full_path"
    for file in "$full_path"/*; do
      echo "Copying file: $full_path/${file##*/} to s3://$bucket/data/$country"
      aws s3 cp $full_path/${file##*/} s3://$bucket/data/$country && rm $full_path/${file##*/}
    done
  else
    echo "$full_path dosent exist, skipping"
  fi
done
