#!/bin/bash
yesterday="$(date +"%Y/%m/%d" -date "1 day ago")"  
countries = ("$2@")
for country in "${countries[@]}"; do
	./run_rpscrape_script.sh "$yesterday" "$country"
done
