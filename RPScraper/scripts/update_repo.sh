#!/bin/bash
if git remote show origin | grep -q 'local out of date'; then
    echo Updates found in main repo
    git fetch upstream
	git checkout master
	git merge upstream/master
	git push
else
    echo No updates found
fi
