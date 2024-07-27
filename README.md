# SMET Scraper

A collection of scripts that started as a project to scrape the SMET
statistics from referral manager, but has since expanded in scope.

_Note:_ As of writing, Elder Hodgkinson is attempting to rewrite
a large portion of this infrastructure in Rust.

## Files

**chirch.py:** A library to connect to referral manager, using HTTP requests.

**competition.py:** A Holly program for a zone-based competition based
on how many referrals have been contacted.

**dashboard.py:** Hard-coded definitions for values found on referral
manager, as well as helper scripts for munching data dictionaries.

**fetched_today:** A cron script to send a list of all the zones
that have asked Holly to fetch the list of referrals.

**finding_ideas.py:** An incomplete Holly program to generate finding
ideas.

**lols.py:** Mission-specific joke responses for Holly.

**main.py:** Old code to calculate who did their SMET for the day.

**messenger.py:** Old code that used to send messages into FB chats
before Holly was created.

**padres.py:** Library and Holly program for determing if the Padres
hit a home run, so missionaries can go get a free burger from
Jack in the Box.

**referrals.py:** Holly program to fetch a list of uncontacted referrals
from the church servers and send it in zone chats.

**spread.py:** Old code that used to put SMET data on a spreadsheet.

**streak.py:** Unfinished code that was intended to calculate streaks
for doing SMET every day.

**yay.py:** Code that prints a list of all referrals that missionaries
started teaching within the last few days.
