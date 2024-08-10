"""
Elder Coxson is done playing
"""

import chirch
import dashboard
import datetime
import json

from os import listdir
from os.path import isfile, join
from typing import Union


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


def generate_report(zone: dashboard.Zone):
    """Generates a report of uncontacted referrals"""
    # Get which zones we're trying out
    requested_zones = [zone]

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
        zones = json.loads(json.dumps({"zones": zones}))[
            "zones"]  # lazy I know

    for requested_zone in requested_zones:
        zone = zones.get(str(requested_zone.value))
        if zone is None:
        print(zone)
        if zone:
            message = f"{requested_zone.name.replace('_', ' ').capitalize()}\n"
            for area, names in zone.items():
                message += f"- {area}: \n"
                for name in names:
                    message += f"  - {name}\n"
                message += "\n"
            print(message)
            s.send(
                json.dumps(
                    {"content": message, "chat_id": chat_id, "sender": ""}
                ).encode("utf-8")
            )
