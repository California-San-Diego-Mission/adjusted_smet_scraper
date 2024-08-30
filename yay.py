"""Code to find referrals that have been successfully contacted"""
# Jackson Coxson

from datetime import datetime, timedelta
import chirch
from dashboard import PersonStatus, ReferralStatus

PERSON_PAGE = 'https://referralmanager.churchofjesuschrist.org/person/'

client = chirch.ChurchClient()
persons = client.get_cached_people_list()

start_time = datetime.now() - timedelta(hours=80)

# Collect results
yellow = []
green = []

for item in persons:
    referral_assigned_date = item.referral_assigned_date
    if (
        referral_assigned_date >= start_time
        and item.referral_status == ReferralStatus.SUCCESSFUL
    ):
        if item.offer_id is None:
            continue
        if item.status == PersonStatus.YELLOW:
            yellow.append(f'{item.first_name} - {PERSON_PAGE}{item.guid}')
        elif item.status.value > 1 and item.status.value < 6:
            green.append(f'{item.first_name} - {PERSON_PAGE}{item.guid}')

# Print results
print(f'--- Green: {len(green)} ---')
for item in green:
    print(item)

print(f'--- Yellow: {len(yellow)} ---')
for item in yellow:
    print(item)
