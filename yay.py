"""Code to find referrals that have been successfully contacted"""
# Jackson Coxson

from datetime import datetime, timedelta
import chirch

PERSON_PAGE = "https://referralmanager.churchofjesuschrist.org/person/"

client = chirch.ChurchClient()
persons = client.get_cached_people_list()['persons']

start_time = datetime.now() - timedelta(hours=80)

# Collect results
yellow = []
green = []

for item in persons:
    assigned_date = item["createDate"]
    if assigned_date is None:
        continue
    referral_assigned_date = datetime.fromtimestamp(
        assigned_date / 1000)
    if referral_assigned_date >= start_time and item["referralStatusId"] == 30:
        if item["offerId"] is None:
            continue
        if item["personStatusId"] == 1:
            yellow.append(
                f"{item['firstName']} - {PERSON_PAGE}{item['personGuid']}")
        elif item["personStatusId"] > 1 and item["personStatusId"] < 6:
            green.append(
                f"{item['firstName']} - {PERSON_PAGE}{item['personGuid']}")

# Print results
print(f"--- Green: {len(green)} ---")
for item in green:
    print(item)

print(f"--- Yellow: {len(yellow)} ---")
for item in yellow:
    print(item)
