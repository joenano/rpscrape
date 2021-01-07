#!/bin/bash

array=( "$@" )
last_idx=$(( ${#array[@]} - 1 ))
date=${array[$last_idx]}
countries=${array[@]::${#array[@]}-1}

for country in $countries; do
  echo "Running $country"
	./scripts/run_rpscrape_script.sh "$date" "$country" || echo "Completed"
done
