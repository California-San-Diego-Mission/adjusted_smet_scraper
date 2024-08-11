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
import pound_statics


def load_today_report() -> Union[dict[str, dict[str, list[str]]], None]:
    """Tries to load a report from today, returns None if none"""
    reports = [f for f in listdir("reports") if isfile(join("reports", f))]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d")
    for report in reports:
        if now_str in report:
            print("Loading today's report")
            # If a report for today already exists, send it
            with open(f"reports/{report}", "r", encoding="utf-8") as f:
                # Parse it as a JSON
                report_data = json.load(f)
                return report_data["zones"]
    return None


def generate_report(requested_zone: dashboard.Zone) -> Optional[str]:
    """Generates a report of uncontacted referrals"""
    zones = load_today_report()

    if zones is None:
        print("No report for today, generating a new one")
        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()["persons"]
        troubled = []
        for p in persons:
            res = client.parse_person(p)
            if res is None:
                continue
            if res["status"] != dashboard.ReferralStatus.SUCCESSFUL:
                troubled.append(res)

        print(f"{len(troubled)} uncontacted referrals")

        zones = {}
        for p in troubled:
            zone = zones.get(p["zone"])
            if zone is None:
                zones[p["zone"]] = {}
                zone = zones[p["zone"]]
            area = zone.get(p["area_name"])
            if area is None:
                zone[p["area_name"]] = []
                area = zone[p["area_name"]]
            if p["last_name"] is None:
                p["last_name"] = ""
            area.append(f"{p['first_name']} {p['last_name']}".strip())

        # Save the zone messages to reports/timestamp.json
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        json.dump(
            {"zones": zones},
            open(f"reports/{now}.json", "w", encoding="utf-8"),
            indent=4,
        )
        zones = json.loads(json.dumps(zones))  # lazy I know

    zone = zones.get(str(requested_zone.value))
    if zone is None:
        print(zone)
        return "NO UNCONTACTED REFERRALS!!11!"
    if zone:
        message = ""
        for area, names in zone.items():
            message += f"- {area}: \n"
            for name in names:
                message += f"  - {name}\n"
            message += "\n"
        print(message)
        return message


def main():
    print("Good morning")
    # chirch.ChurchClient().login()
    holly_client = holly.HollyClient()

    # Iterate over all the zones
    for zone in dashboard.Zone:
        print(zone)
        res_message = f"{choice(pound_statics.morning)}\n\n"
        res_message += choice(pound_statics.score_intro) + "\n"
        res_message += competition.get_score()
        res_message += "\n\n"
        report = generate_report(zone)
        if report:
            res_message += choice(pound_statics.referrals) + "\n"
            res_message += report
        else:
            res_message += "I couldn't fetch the referrals this morning...\n"
        res_message += "\n"
        res_message += choice(pound_statics.outro)

        holly_client.send(holly.HollyMessage(res_message, "7016741568410945"))
        raise "asdf"


if __name__ == "__main__":
    main()
