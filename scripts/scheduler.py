import datetime as dt
import subprocess

from apscheduler.schedulers.background import BlockingScheduler

scheduler = BlockingScheduler()


def run_rpscrape(country, date):
    subprocess.call(f'echo "-d {date} {country}" | python3 rpscrape.py', shell=True)
    print(f'Finished scraping {country} - {date}')


date_today = dt.datetime.today().date()
start_date = date_today - dt.timedelta(days=round(364.25*10))
print(f"Start date: {start_date}")
end_date = date_today - dt.timedelta(days=1)
print(f"End date: {end_date}")

# Get the countries we want
countries = ["gb", "ire"]
# Find the number of days between the start and end dates
delta = end_date - start_date
dates = list()
for country in countries:
    for i in range(delta.days + 1):
        day = (start_date + dt.timedelta(days=i)).strftime(format='%Y/%m/%d')
        scheduler.add_job(id=str(hash(f"{day}_{country}")), func=run_rpscrape, name=f"{country}-{day}",
                          kwargs={'country': country, 'date': day}, replace_existing=True,
                          misfire_grace_time=99999999999)

scheduler.start()
