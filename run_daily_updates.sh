#!/bin/bash
yesterday="$(date +"%Y/%m/%d" -date "1 day ago")"  
./run_rpscrape_script.sh "$yesterday" "gb"
./upload_to_s3.sh