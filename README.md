# rpscrape

Horse racing data has been hoarded by a few companies, enabling them to effectively extort the public for access to any worthwhile historical amount. Compared to other sports where historical data is easily and freely available to use and query as you please, racing data in most countries is far harder to come by and is often only available with subscriptions to expensive software.

The aim of this tool is to provide a way of gathering large amounts of historical results data at no cost.


#### Example data from Ascot 2018

![data](https://i.postimg.cc/7LncCDMG/data1.png)
![data](https://i.postimg.cc/SsQPC5DZ/data2.png)

## Install

```
~$ git clone https://github.com/4A47/rpscrape.git
```

If you don't have git installed you can download the folder [here](https://github.com/4A47/rpscrape/archive/master.zip).

## Requirements

You must have Python 3.6 or greater installed. You can download the latest Python release [here](https://www.python.org/downloads/).

In addition, the [Requests](http://docs.python-requests.org/en/master/) and [LXML](https://lxml.de/) python modules are needed, they can be installed using PIP(_included with Python_) with the following command.

```
~$ pip install requests lxml
```

## Usage

Run the program from the scripts folder:
```
~$ cd rpscrape/scripts
~$ ./rpscrape.py
```

on Windows:
```
> cd rpscrape/scripts
> python rpscrape.py
```

To scrape you must provide 3 options in the following format:
```
[rpscrape]> [region|course] [year|range] [code]
```

The first option can be either a region or a specific course.

Each region has a 2 or 3 letter code like "ire" for Ireland or "gb" for Great Britain. You can show the list of region codes with the following command:
```
[rpscrape]> regions
     CODE: mal | Malaysia
     CODE: mac | Macau
     CODE: gue | Guernsey
     CODE: ity | Italy
     CODE: swi | Switzerland
     CODE: tur | Turkey
     CODE: hk  | Hong Kong
     CODE: chi | Chile
     CODE: uae | United Arab Emirates
```

The other possibility for the first option is that of a specific course. Courses codes are numeric and up to 4 digits long. To view the course codes, use the courses option as shown in the following example.

```
[rpscrape]> courses
     CODE: 32   | Aintree
     CODE: 2    | Ascot
     CODE: 3    | Ayr
     CODE: 4    | Bangor
     CODE: 5    | Bath
     CODE: 6    | Beverley
     CODE: 7    | Brighton
     CODE: 8    | Carlisle
```

If you want to search for a specific region or course, add a search term as shown below.

```
[rpscrape]> regions france
    CODE: fr  | France
```

```
[rpscrape]> courses york
    CODE: 107  | York
    CODE: 1347 | York Aus
```

To list the courses from a specific region, add the region code like so:
 ```
[rpscrape]> courses ire
     CODE: 175  | Ballinrobe
     CODE: 176  | Bellewstown
     CODE: 177  | Clonmel
     CODE: 596  | Cork
     CODE: 178  | Curragh
     CODE: 180  | Down Royal
     CODE: 179  | Downpatrick
     CODE: 181  | Dundalk
 ```

The second option can be a year e.g "1999", or a range of years e.g "2005-2015".

The final option is the racing code and can either be "flat" or "jumps".


### Examples

The following example shows a request for flat races from Ireland in 2017.

```
[rpscrape]> ire 2017 flat
```

The next example shows a request for the last 2 years flat form in Great Britain.

```
[rpscrape]> gb 2017-2018 flat
```

The next example shows a request for the last 20 years jump form at Ascot(code: 2).
```
[rpscrape]> 2 1999-2018 jumps
```
Note: When scraping jumps data the year you enter is when the season started, i.e to get 2019 Cheltenham Festival data, you would use the year 2018.
```
[rpscrape]> 11 2018 jumps
```
In the above example, Cheltenham races from the season 2018-2019 are scraped, the 2018 Greatwood and the 2019 festival will be included but not the 2018 festival.


#### Options

```
regions              List all available region codes
regions [search]     Search for specific region code

courses              List all courses
courses [search]     Search for specific course
courses [region]     List courses in region - e.g courses ire

help                Show help
options             Show options
cls, clear          Clear screen
q, quit, exit       Quit
```

Tab complete for option keywords is available on Linux.


### Feature Requests
Feel free to post any ideas to improve or add more functionality in the issues and I will consider trying to implement them.
