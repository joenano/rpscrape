# rpscrape - (BETA)

Big horse racing data has been hoarded by select companies enabling them to effectively extort the public by selling and renting it. Compared to other sports where data is in depth and freely available, racing data in most countries is not particularly in depth and is not available in large datasets.

The aim of this tool is to provide a way for gathering large amounts of results data free of charge.


#### Example data from Ascot 2018

![data](https://i.postimg.cc/7LncCDMG/data1.png)
![data](https://i.postimg.cc/SsQPC5DZ/data2.png)

## Install

```
~$ git clone https://github.com/4A47/rpscrape.git
```

If you dont have git installed you can download the folder [here](https://github.com/4A47/rpscrape/archive/master.zip).

## Usage
```
-$ rpscrape.py [-r|-c] [region|course] [-y] [year|range] [--flat|--jumps]
```

#### Flags

```
-r, --region           Scrape a specific region
-c, --course           Scrape a specific course
-y, --year             Specific year to scrape
-f, --flat             Flat races only
-j, --jumps            Jump races only
```
#### More Info

```
--regions              List all available region codes
--regions [search]     List regions matching search term
--courses              List all courses
--courses [search]     List courses matching search term
--courses-[region]     List courses in region - e.g --courses-ire
```

#### Options

The first option is that of a region(-r) or a course(-c).

Each region has a 2 or 3 letter code like ire for Ireland or gb for Great Britain. You can show the list of region codes with the following command:
```
~$ ./rpscrape.py --regions

     CODE: mal | Malaysia
     CODE: mac | Macau
     CODE: gue | Guernsey
     CODE: ity | Italy
     CODE: swi | Switzerland
     CODE: tur | Turkey
     CODE: hk  | Hong Kong
     CODE: chi | Chile
     CODE: per | Peru
     CODE: uae | United Arab Emirates

```

The other possibility for the first option is that of a specific course. To view the course codes, use the --courses options as shown in the following example.

```
~$ ./rpscrape.py --courses

     CODE: 32   | Aintree
     CODE: 2    | Ascot
     CODE: 3    | Ayr
     CODE: 4    | Bangor
     CODE: 5    | Bath
     CODE: 6    | Beverley
     CODE: 7    | Brighton
     CODE: 8    | Carlisle
     CODE: 9    | Cartmel
     CODE: 10   | Catterick

```

If you want to search for a specific region or course, add a search term after the --regions or --courses flag as shown below.

```
~$ ./rpscrape.py --regions france

    CODE: fr  | France

```

```
~$ ./rpscrape.py --courses york

    CODE: 107  | York
    CODE: 1347 | York Aus

```

To list the courses from a specific region, add the region code to the --courses flag like so:
 ```
~$ ./rpscrape.py --courses-ire

     CODE: 175  | Ballinrobe
     CODE: 176  | Bellewstown
     CODE: 177  | Clonmel
     CODE: 596  | Cork
     CODE: 178  | Curragh
     CODE: 180  | Down Royal
     CODE: 179  | Downpatrick
     CODE: 181  | Dundalk

 ```

You can also look directly at files found in the courses folder for this information

### Examples

The following example states that the results of flat races from Ireland in 2017 should be scraped(not scrapped for skulduggery as many have suggested).

```
~$ cd rpscrape/scripts
~$ ./rpscrape.py -r ire -y 2017 -f
```

The next example shows a request for the last 2 years flat form in Argentina because its 7am and you've just spent the last 4 hours doing your brains in Australia and you've got a penchant for some Argentinian dirt action to get you out of jail before work at 9.

```
~$ cd rpscrape/scripts
~$ ./rpscrape.py --region arg -y 2017-2018 --flat
```

The next example shows a request for the last 20 years flat form at Ascot(code: 2). There will be no jump examples, unfortunately for some, but suffice to say its as easy as changing the last flag to either -j or --jumps.

```
~$ cd rpscrape/scripts
~$ ./rpscrape.py --course 2 --year 1998-2018 --flat
```

### Known Issues

* Horses who finish pulled up/unseated/fell etc are not being recorded.