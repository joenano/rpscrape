#!/bin/bash
yesterday="$(date +"%Y/%m/%d" -date "1 day ago")"  
echo "yesterday date: $yesterday"
countries=("$@")
for country in "${countries[@]}"; do
	./run_rpscrape_script.sh "$yesterday" "$country"
done
