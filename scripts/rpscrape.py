#!/usr/bin/env python3

""" Scrapes results and saves them in csv format """

import json
from lxml import html
import os
from re import search
import requests
import sys
from time import sleep, strptime


class Completer:
    def __init__(self, options):
        self.options = sorted(options)

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            return self.matches[state]
        except IndexError:
            return None


def options(opt="help"):
    opts = "\n".join(
        [
            "       regions              List all available region codes",
            "       regions [search]     Search for specific country code",
            "",
            "       courses              List all courses",
            "       courses [search]     Search for specific course",
            "       courses [region]     List courses in region - e.g courses ire",
        ]
    )

    if opt == "help":
        print(
            "\n".join(
                [
                    "  Usage:",
                    "       ~$ ./rpscrape.py"
                    "       [rpscrape]> [region|course] [year|range] [flat|jumps]",
                    "",
                    "       Regions have alphabetic codes.",
                    "       Courses have numeric codes.",
                    "",
                    "  Examples:",
                    "       [rpscrape]> ire 1999 flat",
                    "       [rpscrape]> gb 2015-2018 jumps",
                    "       [rpscrape]> 533 1998-2018 flat",
                    "",
                    "  Options:",
                    "{}".format(opts),
                    "",
                    "  More info:",
                    "       help            Show help",
                    "       options         Show options",
                    "       cls, clear      Clear screen",
                    "       q, quit, exit   Quit",
                    "",
                ]
            )
        )
    else:
        print(opts)


def courses(code="all"):
    with open(f"../courses/{code}_course_ids", "r") as courses:
        for course in courses:
            yield (course.split('-')[0].strip(), ' '.join(course.split('-')[1::]).strip())


def course_name(code):
    if code.isalpha():
        return code
    for course in courses():
        if course[0] == code:
            return course[1].replace("()", "").replace(" ", "-")


def course_search(term):
    for course in courses():
        if term.lower() in course[1].lower():
            print_course(course[0], course[1])


def print_course(code, course):
    if len(code) == 5:
        print(f"     CODE: {code}| {course}")
    elif len(code) == 4:
        print(f"     CODE: {code} | {course}")
    elif len(code) == 3:
        print(f"     CODE: {code}  | {course}")
    elif len(code) == 2:
        print(f"     CODE: {code}   | {course}")
    else:
        print(f"     CODE: {code}    | {course}")


def print_courses(code="all"):
    for course in courses(code):
        print_course(course[0], course[1])


def valid_course(code):
    return code in [course[0] for course in courses()]


def x_y():
    from base64 import b64decode

    return b64decode(
        'aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb206NDQzL3Byb2ZpbGUvY291cnNlL2ZpbHRlci9yZXN1bHRz'
    ).decode('utf-8'), b64decode('aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb20vcmVzdWx0cw==').decode('utf-8')


def regions():
    with open("../courses/_countries", "r") as regions:
        return json.load(regions)


def region_search(term):
    for code, region in regions().items():
        if term.lower() in region.lower():
            print_region(code, region)


def print_region(code, region):
    if len(code) == 3:
        print(f"     CODE: {code} | {region}")
    else:
        print(f"     CODE: {code}  | {region}")


def print_regions():
    for code, region in regions().items():
        print_region(code, region)


def valid_region(code):
    return code in regions().keys()


def valid_years(years):
    if years:
        return all(year.isdigit() and int(year) > 1995 and int(year) < 2020 for year in years)
    else:
        return False


def fraction_to_decimal(fractions):
    decimal = []
    for fraction in fractions:
        if fraction == "" or fraction == "No Odds":
            decimal.append("")
        elif "evens" in fraction.lower() or fraction.lower() == "evs":
            decimal.append("2.00")
        else:
            decimal.append(
                "{0:.2f}".format(float(fraction.split("/")[0]) / float(fraction.split("/")[1]) + 1.00)
            )

    return decimal


def convert_date(date):
    dmy = date.split()
    mon = strptime(dmy[1], "%b").tm_mon

    if mon < 10:
        mon = str(0) + str(mon)

    if int(dmy[0]) < 10:
        dmy[0] = str(0) + str(dmy[0])

    new_date = dmy[2] + "-" + str(mon) + "-" + dmy[0]

    return new_date


def pedigree_info(pedigrees):
    sires, dams, damsires = [], [], []

    for p in pedigrees:
        ped_info = p.findall('a')

        if len(ped_info) > 0:
            sire = ped_info[0].text.strip()
            sire_nat = ped_info[0].tail.strip()
            if sire_nat != '-':
                sire = sire + ' ' + sire_nat.replace('-', '').strip()
            else:
                sire = sire + ' (GB)'

            sires.append(sire)
        else:
            sires.append('')

        if len(ped_info) > 1:
            dam = ped_info[1].text.strip()
            dam_nat = p.find('span').text
            if dam_nat is not None:
                dam = dam + ' ' + dam_nat.strip()
            else:
                dam = dam + ' (GB)'
            dams.append(dam)
        else:
            dams.append('')

        if len(ped_info) > 2:
            damsire = ped_info[2].text.strip().strip('()')
            if damsire == 'Damsire Unregistered':
                damsire = ''
            damsires.append(damsire)
        else:
            damsires.append('')

    return sires, dams, damsires


def race_info(race, race_class):
    r_class = ""
    r_name = str(race)

    if " Class A" in race:
        r_name = r_name.replace(" Class A", "")
        r_class = "Class 1"
    elif " Class B" in race:
        r_name = r_name.replace(" Class B", "")
        r_class = "Class 2"
    elif " Class C" in race:
        r_name = r_name.replace(" Class C", "")
        r_class = "Class 3"
    elif " Class D" in race:
        r_name = r_name.replace(" Class D", "")
        r_class = "Class 4"
    elif " Class E" in race:
        r_name = r_name.replace(" Class E", "")
        r_class = "Class 5"
    elif " Class F" in race:
        r_name = r_name.replace(" Class F", "")
        r_class = "Class 6"
    elif " Class G" in race:
        r_name = r_name.replace(" Class G", "")
        r_class = "Class 6"
    elif " Class H" in race:
        r_name = r_name.replace(" Class H", "")
        r_class = "Class 7"

    if "(Premier Handicap)" in race:
        r_class = "Class 2"
        return r_name, r_class
    elif "(Group" in race:
        r_class = search("(\(Grou..)\w+", race).group(0).strip("(")
        r_name = r_name.replace(f" ({r_class})", "")
        return r_name, r_class
    elif "(Grade" in race:
        r_class = search("(\(Grad..)\w+", race).group(0).strip("(")
        r_name = r_name.replace(f" ({r_class})", "")
        return r_name, r_class
    elif "Grade" in race:
        r_class = search("Grad..\w+", race).group(0)
        r_name = r_name.replace(f" {r_class}", "")
        return r_name, r_class
    elif "(Listed" in race:
        r_class = "Listed"
        r_name = r_name.replace(" (Listed Race)", "").replace("(Listed)", "")
        return r_name, r_class
    elif "Maiden" in race and race_class == "":
        r_class = "Class 5"
        return r_name, r_class

    return r_name, race_class


def band_info(band, race, race_class):
    info = band
    r_name = race
    r_class = race_class

    if "," in band:
        r_class = band.split(",")[0]
        info = info.split(",")[1]

    if ("(Entire Colts & Fillies)") in race or "(Colts & Fillies)" in race:
        info = info + " C & F"
        r_name = r_name.replace("(Entire Colts & Fillies)", "").replace(
            "(Colts & Fillies)", ""
        )
    elif "(Fillies & Mares)" in race:
        info = info + " F & M"
        r_name = r_name.replace("(Fillies & Mares)", "")
    elif "(Fillies)" in race or "Fillies" in race:
        info = info + " F"
        r_name = r_name.replace("(Fillies)", "")
    elif "(Colts & Geldings)" in race or "(C & G)" in race:
        info = info + " C & G"
        r_name = r_name.replace("(Colts & Geldings)", "").replace("(C & G)", "")
    elif "Mares" in race:
        info = info + " M"

    return info, r_name, r_class


def convert_distance(distance):
    dist = "".join(
        [d.strip().replace("¼", ".25").replace("½", ".5").replace("¾", ".75") for d in distance]
    )

    if "m" in dist:
        if len(dist) > 2:
            dist = int(dist.split("m")[0]) * 8 + float(dist.split("m")[1].strip("f"))
        else:
            dist = int(dist.split("m")[0]) * 8
    else:
        dist = dist.strip("f")

    return dist


def get_races(tracks, names, years, code, xy):
    races = []
    for track, name in zip(tracks, names):
        for year in years:
            r = requests.get(
                f"{xy[0]}/{track}/{year}/{code}/all-races",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                try:
                    results = r.json()
                    if results["data"]["principleRaceResults"] == None:
                        print(f"No {code} race data for {course_name(track)} in {year}.")
                    else:
                        for result in results["data"]["principleRaceResults"]:
                            races.append(
                                f'{xy[1]}/{track}/{name}/{result["raceDatetime"][:10]}/{result["raceInstanceUid"]}'
                            )
                except:
                    pass
            else:
                print(f"Unable to access races from {course_name(track)} in {year}")

    return races


def calculate_times(win_time, dist_btn, going, code, course):
    times = []
    if code == "flat":
        if (
            "Firm" in going
            or "Standard" in going
            or "Fast" in going
            or "Hard" in going
            or "Slow" in going
        ):
            if "southwell" in course.lower():
                lps_scale = 5
            else:
                lps_scale = 6
        elif "Good" in going:
            if "Soft" in going or "Yielding" in going:
                lps_scale = 5.5
            else:
                lps_scale = 6
        elif "Soft" in going or "Heavy" in going or "Yielding" in going:
            lps_scale = 5
    else:
        if "Firm" in going or "Standard" in going or "Hard" in going:
            if "southwell" in course.lower():
                lps_scale = 4
            else:
                lps_scale = 5
        elif "Good" in going:
            if "Soft" in going or "Yielding" in going:
                lps_scale = 4.5
            else:
                lps_scale = 5
        elif "Soft" in going or "Heavy" or "Yielding" in going:
            lps_scale = 4

    for dist in dist_btn:
        try:
            time = win_time + (float(dist) / lps_scale)
            times.append("{}:{:2.2f}".format(int(time // 60), time % 60))
        except ValueError:
            times.append("")

    return times


def clean(data):
    return [d.strip().replace("–", "") for d in data]


def scrape_races(races, target, years, code):
    if not os.path.exists("../data"):
        os.makedirs("../data")

    with open(
        f"../data/{target.lower()}-{years}_{code}.csv", "w", encoding="utf-8"
    ) as csv:
        csv.write(
            (
                '"date","course","time","race_name","class","band","dist(f)","dist(m)","going",'
                '"pos","draw","btn","horse_name","sp","dec","age","weight","lbs","gear","fin_time",'
                '"jockey","trainer","or","ts","rpr","prize(£)","sire","dam","damsire","comment"\n'
            )
        )

        for race in races:
            r = requests.get(race, headers={"User-Agent": "Mozilla/5.0"})
            while r.status_code == 403:
                sleep(5)
                r = requests.get(race, headers={"User-Agent": "Mozilla/5.0"})

            if r.status_code != 200:
                continue

            doc = html.fromstring(r.content)

            course_name = race.split("/")[5]
            try:
                date = doc.xpath("//span[@data-test-selector='text-raceDate']/text()")[0]
                date = convert_date(date)
            except IndexError:
                date = ""
            try:
                r_time = doc.xpath("//span[@data-test-selector='text-raceTime']/text()")[0]
            except IndexError:
                r_time = ""

            try:
                race = (
                    doc.xpath("//h2[@class='rp-raceTimeCourseName__title']/text()")[0]
                    .strip()
                    .strip("\n")
                    .replace(",", " ")
                    .replace('"', "")
                    .replace("\x80", "")
                )
            except IndexError:
                race = ""

            try:
                race_class = (
                    doc.xpath("//span[@class='rp-raceTimeCourseName_class']/text()")[0].strip().strip("()")
                )
            except:
                race_class = ""

            race, race_class = race_info(race, race_class)

            try:
                band = (
                    doc.xpath(
                        "//span[@class='rp-raceTimeCourseName_ratingBandAndAgesAllowed']/text()")[0].strip().strip("()")
                )
            except:
                band = ""
            band, race, race_class = band_info(band, race, race_class)

            try:
                distance = doc.xpath("//span[@class='rp-raceTimeCourseName_distance']/text()")[0].strip()
            except IndexError:
                distance = ""
            dist = convert_distance(distance)

            try:
                metres = round(float(dist) * 200)
            except ValueError:
                metres = ""
                print(f"ValueError: (dist to metres conversion) RACE: {r_time} {date}")

            try:
                going = doc.xpath("//span[@class='rp-raceTimeCourseName_condition']/text()")[0].strip()
            except IndexError:
                going = ""

            pedigrees = doc.xpath("//tr[@data-test-selector='block-pedigreeInfoFullResults']/td")
            sires, dams, damsires = pedigree_info(pedigrees)

            coms = doc.xpath("//tr[@class='rp-horseTable__commentRow ng-cloak']/td/text()")
            com = [x.strip().replace("  ", "").replace(",", " -") for x in coms]
            possy = doc.xpath("//span[@data-test-selector='text-horsePosition']/text()")
            del possy[1::2]
            pos = [x.strip() for x in possy]
            prizes = doc.xpath("//div[@data-test-selector='text-prizeMoney']/text()")
            prize = [p.strip().replace(",", "").replace("£", "") for p in prizes]
            try:
                del prize[0]
                for i in range(len(pos) - len(prize)):
                    prize.append("")
            except IndexError:
                prize = ["" for x in range(len(pos))]
            draw = clean(doc.xpath("//sup[@class='rp-horseTable__pos__draw']/text()"))
            draw = [d.strip("()") for d in draw]
            beaten = doc.xpath("//span[@class='rp-horseTable__pos__length']/span/text()")
            del beaten[1::2]
            btn = [
                b.strip()
                .strip("[]")
                .replace("¼", ".25")
                .replace("½", ".5")
                .replace("¾", ".75")
                .replace("snk", "0.3")
                .replace("nk", "0.33")
                .replace("shd", "0.2")
                .replace("hd", "0.25")
                .replace("nse", "0.1")
                .replace("dht", "0")
                for b in beaten
            ]
            btn.insert(0, "0")
            if len(btn) < len(pos):
                btn.extend(["" for x in range(len(pos) - len(btn))])

            name = clean(doc.xpath("//a[@data-test-selector='link-horseName']/text()"))
            sps = clean(doc.xpath("//span[@class='rp-horseTable__horse__price']/text()"))
            jock = clean(doc.xpath("//a[@data-test-selector='link-jockeyName']/text()"))
            del jock[::2]
            trainer = clean(doc.xpath("//a[@data-test-selector='link-trainerName']/text()"))
            del trainer[::2]
            age = clean(doc.xpath("//td[@data-test-selector='horse-age']/text()"))
            _or = clean(doc.xpath("//td[@data-ending='OR']/text()"))
            ts = clean(doc.xpath("//td[@data-ending='TS']/text()"))
            rpr = clean(doc.xpath("//td[@data-ending='RPR']/text()"))
            st = doc.xpath("//span[@data-ending='st']/text()")
            lb = doc.xpath("//span[@data-ending='lb']/text()")
            wgt = [a.strip() + "-" + b.strip() for a, b in zip(st, lb)]
            lbs = [int(a.strip()) * 14 + int(b.strip()) for a, b in zip(st, lb)]
            headgear = doc.xpath("//td[contains(@class, 'rp-horseTable__wgt')]")
            gear = []
            for h in headgear:
                span = h.find('span[@class="rp-horseTable__headGear"]')
                if span is not None:
                    gear.append(span.text)
                else:
                    gear.append("")

            info = doc.xpath('//div[@class="rp-raceInfo"]')[0].find('.//li').findall('.//span[@class="rp-raceInfo__value"]')

            if len(info) == 3:
                winning_time = clean(info[1].text.split("("))[0].split()
            elif len(info) == 2:
                winning_time = info[0].text.split("(")[0].split()
            else:
                print(f'ERROR: (winning time) {date} {course_name} {r_time}.')

            if len(winning_time) > 1:
                try:
                    win_time = float(winning_time[0].replace("m", "")) * 60 + float(winning_time[1].strip("s"))
                except ValueError:
                    print(f'ERROR: (winning time) {date} {course_name} {r_time}.')
            else:
                win_time = float(winning_time[0].strip("s"))

            times = calculate_times(win_time, btn, going, code, course_name)

            dec = fraction_to_decimal([sp.strip("F").strip("J").strip("C").strip() for sp in sps])

            for p, pr, dr, bt, n, sp, dc, time, j, tr, a, o, t, rp, w, l, g, c, sire, dam, damsire in zip \
            (pos, prize, draw, btn, name, sps, dec, times, jock, trainer, age, _or, ts, rpr, wgt, lbs, gear, com, sires, dams, damsires):
                csv.write(
                    (
                        f"{date},{course_name},{r_time},{race},{race_class},{band.strip()},{dist},{metres},{going},{p},{dr},{bt},{n},"
                        f"{sp},{dc},{a},{w},{l},{g},{time},{j},{tr},{o},{t},{rp},{pr},{sire},{dam},{damsire},{c}\n"
                    )
                )

        print(f"\nFinished scraping. {target.lower()}-{years}_{code}.csv saved in rpscrape/data")


def parse_args(args=sys.argv):
    if len(args) == 1:
        if "help" in args or "options" in args:
            options(args[0])
        elif "clear" in args:
            os.system("cls" if os.name == "nt" else "clear")
        elif "quit" in args or "q" in args or "exit" in args:
            sys.exit()
        elif "regions" in args:
            print_regions()
        elif "courses" in args:
            print_courses()
    elif len(args) == 2:
        if args[0] == "regions":
            region_search(args[1])
        elif args[0] == "courses":
            if valid_region(args[1]):
                print_courses(args[1])
            else:
                course_search(args[1])
    elif len(args) == 3:
        if valid_region(args[0]):
            region = args[0]
        elif valid_course(args[0]):
            course = args[0]
        else:
            return print("Invalid course or region.")

        if "jumps" in args or "jump" in args or "-j" in args:
            code = "jumps"
        elif "flat" in args or "-f" in args:
            code = "flat"
        else:
            return print("Invalid racing code. -f, flat or -j, jumps.")

        if "-" in args[1]:
            try:
                years = [str(x) for x in range(int(args[1].split("-")[0]), int(args[1].split("-")[1]) + 1)]
            except ValueError:
                return print("\nINVALID YEAR: must be in range 1996-2019.\n")
        else:
            years = [args[1]]
        if not valid_years(years):
            return print("\nINVALID YEAR: must be in range 1996-2019 for flat and 1996-2019 for jumps.\n")

        if code == "jumps":
            if int(years[-1]) > 2019:
                return print("\nINVALID YEAR: the latest jump season started in 2019.\n")

        if "region" in locals():
            tracks = [course[0] for course in courses(region)]
            names = [course_name(track) for track in tracks]
            scrape_target = region
            print(f"Scraping {code} results from {scrape_target} in {args[1]}...")
        else:
            tracks = [course]
            names = [course_name(course)]
            scrape_target = course
            print(f"Scraping {code} results from {course_name(scrape_target)} in {args[1]}...")

        races = get_races(tracks, names, years, code, x_y())
        scrape_races(races, course_name(scrape_target), args[1], code)
    else:
        options()


def main():
    if len(sys.argv) > 1:
        sys.exit(options())

    try:
        import readline

        completions = Completer(
            [
                "courses",
                "regions",
                "options",
                "help",
                "quit",
                "exit",
                "clear",
                "flat",
                "jumps",
            ]
        )
        readline.set_completer(completions.complete)
        readline.parse_and_bind("tab: complete")
    except ModuleNotFoundError:  # windows
        pass

    while True:
        args = input("[rpscrape]> ").lower().strip()
        parse_args([arg.strip() for arg in args.split()])


if __name__ == "__main__":
    main()
