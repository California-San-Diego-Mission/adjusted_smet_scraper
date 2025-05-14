"""
Elder Coxson is done playing
"""

import datetime
import json
from os import listdir
from os.path import isfile, join
from random import choice
from typing import Optional, Union

import holly

import chirch
import competition
import dashboard
from person import Person
import pound_statics
import sql_library

# risky_global_report_status = 0
#This is a bad idea implemented by Elder Davis to make keeping track of empty zone reports easy. When the generate_report function is run,
# it will set this variable to 0 every single time. If the report is empty, it will set this value to 1, and then the main function will check
# this variable to determine whether or not to record an instance of an empty report day


def load_today_report() -> Union[dict[str, dict[str, list[str]]], None]:
    """Tries to load a report from today, returns None if none"""
    reports = [f for f in listdir('reports') if isfile(join('reports', f))]
    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
    for report in reports:
        if now_str in report:
            print("Loading today's report")
            # If a report for today already exists, send it
            with open(f'reports/{report}', 'r', encoding='utf-8') as f:
                # Parse it as a JSON
                report_data = json.load(f)
                return report_data['zones']
    return None


def generate_report(requested_zone: dashboard.Zone) -> Optional[str]:
    """Generates a report of uncontacted referrals"""
    # global risky_global_report_status
    # risky_global_report_status= 0
    zones = load_today_report()

    if zones is None:
        print('No report for today, generating a new one')
        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()
        troubled: list[Person] = []
        for p in persons:
            res = client.filter_person(p)
            if res is False:
                print('continuing')
                continue
            troubled.append(p)

        print(f'{len(troubled)} uncontacted referrals')

        zones = {}
        for p in troubled:
            zone = zones.get(p.zone)
            if zone is None:
                zones[p.zone] = {}
                zone = zones[p.zone]
            area = zone.get(p.area_name)
            if area is None:
                zone[p.area_name] = []
                area = zone[p.area_name]
            area.append(p.first_name.strip())

        # Save the zone messages to reports/timestamp.json
        now = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        json.dump(
            {'zones': zones},
            open(f'reports/{now}.json', 'w', encoding='utf-8'),
            indent=4,
        )
        zones = json.loads(json.dumps(zones))  # lazy I know

    zone = zones.get(str(requested_zone.name))
    if zone is None:
        zone_number = competition.strip_zone_number_from_name(requested_zone.name)
        print(f'Zone {zone_number} got a blank slate today')
        sql_library.mark_today_zone_blank_slate(zone_number)
        return f'NO UNCONTACTED REFERRALS!!11! Your zone earned a bonus for a blank slate!\n{choice(pound_statics.blank_slates)}'
    if zone:
        message = ''
        for area, names in zone.items():
            message += f'- {area}: \n'
            for name in names:
                message += f'  - {name}\n'
            message += '\n'
        print(message)
        return message


def main():
    print('Good morning')
    chirch.ChurchClient().login()
    holly_client = holly.HollyClient()

    for zone in dashboard.Zone:
        generate_report(zone)
            
    score = competition.get_score()

    # Iterate over all the zones
    for zone in dashboard.Zone:
        # print(competition.strip_zone_number_from_name(zone.name))
        # print("that was the zone")
        res_message = f'{choice(pound_statics.morning)}\n\n'
        res_message += choice(pound_statics.score_intro) + '\n'
        res_message += score
        res_message += '\n\n'
        report = generate_report(zone)
        if report:
            res_message += choice(pound_statics.referrals) + '\n'
            res_message += report
        else:
            res_message += "I couldn't fetch the referrals this morning...\n"
        res_message += '\n'
        res_message += choice(pound_statics.outro)

        # chat = pound_statics.messenger_ids.get(zone)
        holly_client.send(holly.HollyMessage(res_message, '26732959939628175'))


if __name__ == '__main__':
    main()
