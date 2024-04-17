# Jackson Coxson

import chirch
from datetime import datetime, timedelta

client = chirch.ChurchClient()
persons = client.get_cached_people_list()['persons']

seventeen_hours_ago = datetime.now() - timedelta(hours=17)

for item in persons:
    referral_assigned_date = datetime.utcfromtimestamp(
        item["referralAssignedDate"] / 1000)
    if referral_assigned_date >= seventeen_hours_ago and item["referralStatusId"] == 30:
        print(item["firstName"], item["lastName"], "-", item["personGuid"])
