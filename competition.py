# pylint: disable=line-too-long
"""Competition code"""

import datetime
import time
import random
import mysql.connector
import os
import pytz
import statistics
from dotenv import load_dotenv

import holly
import chirch
import dashboard

load_dotenv()


def handle_request(request: holly.ParsedHollyMessage):
    """Parses the text to determine if we need to react"""
    print(request)
    if request.is_targeted and (
        request.match("what score")
        or request.match("whats score")
        or request.match("who winning")
        or request.match("get score")
    ):
        # if request.chat_id != "7016741568410945":
        #     return "shhhhhhh it's a secret"
        return get_score()

    return False


def get_score():
    """Gets the score of contacted/total referrals"""
    try:

        mydb = mysql.connector.connect(
            host="localhost",
            user=os.getenv("MYSQL_USERNAME"),
            password=os.getenv("MYSQL_PASSWORD"),
            database="holly",
        )
        cursor = mydb.cursor()

        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()["persons"]

        now = datetime.datetime.now()
        # get the last transfer
        last_transfer = datetime.datetime.fromtimestamp(1720033200)

        zones = {}
        total_referrals = 0
        total_successful = 0
        total_attempted = 0
        for person in persons:
            assigned_date = person.get("referralAssignedDate")
            if assigned_date is None:
                continue
            assigned_date = datetime.datetime.fromtimestamp(assigned_date / 1000)
            if assigned_date < last_transfer:
                continue
            try:
                zone_id = person.get("zoneId")
                if zone_id is None:
                    continue
                zone = dashboard.Zone(zone_id)

                # Determine if it's actually a dot
                dot_status = person.get("personStatusId")
                dot_status = dashboard.PersonStatus(dot_status)
                permissable_dots = [
                    dashboard.PersonStatus.BETTER_GREEN,
                    dashboard.PersonStatus.GREEN,
                    dashboard.PersonStatus.MOVED,
                    dashboard.PersonStatus.NOT_INTERESTED,
                    dashboard.PersonStatus.NOT_PROGRESSING,
                    dashboard.PersonStatus.NOT_RECENTLY_CONTACTED,
                    dashboard.PersonStatus.PROGRESSING_GREEN,
                    dashboard.PersonStatus.TOO_BUSY,
                    dashboard.PersonStatus.YELLOW,
                ]

                if dot_status not in permissable_dots:
                    continue

                # If the zone doesn't exist, insert it
                if zones.get(zone) is None:
                    zones[zone] = (0, 0, 0, [])

                status_id = person.get("referralStatusId")
                if status_id is None:
                    continue
                status = dashboard.ReferralStatus(status_id)

                # Get the time from assignment to contact
                if (
                    status == dashboard.ReferralStatus.NOT_SUCCESSFUL
                    or status == dashboard.ReferralStatus.SUCCESSFUL
                ):
                    contact_time = get_contact_time(
                        person.get("personGuid"), cursor, client
                    )
                    if contact_time is not None:
                        mydb.commit()
                        zones[zone][3].append(contact_time)

                if status == dashboard.ReferralStatus.NOT_ATTEMPTED:
                    zones[zone] = (
                        zones[zone][0],
                        zones[zone][1],
                        zones[zone][2] + 1,
                        zones[zone][3],
                    )
                    print(f"{zone.name}: {person.get('lastName')}")
                    total_referrals += 1
                elif status == dashboard.ReferralStatus.NOT_SUCCESSFUL:
                    zones[zone] = (
                        zones[zone][0],
                        zones[zone][1] + 1,
                        zones[zone][2] + 1,
                        zones[zone][3],
                    )
                    total_referrals += 1
                    total_attempted += 1
                elif status == dashboard.ReferralStatus.SUCCESSFUL:
                    zones[zone] = (
                        zones[zone][0] + 1,
                        zones[zone][1],
                        zones[zone][2] + 1,
                        zones[zone][3],
                    )
                    total_referrals += 1
                    total_attempted += 1
                    total_successful += 1
            except Exception as e:
                print(f"Error processing person: {e}")
                continue

        zone_percentages = {}
        for zone, zone_items in zones.items():
            time_average = statistics.median(zone_items[3])
            if zone_items[2] != 0:
                print(
                    f"{zone.name} - S:{zone_items[0]} A:{zone_items[1]} T:{zone_items[2]} M:{time_average}"
                )
                zone_percentages[zone] = (
                    ((zone_items[0] + (zone_items[1] * 0.8)) / zone_items[2]) * 1000
                ) - time_average  # change me for weighted successful

        # Rank the zones
        ranked = sorted(zone_percentages.items(), key=lambda x: x[1], reverse=True)

        # Create the string
        res = "the current winners of my dog bowl. are the following hooomans:\n\n"

        if len(ranked) > 0:
            first = ranked.pop(0)
            res += f"furst:  {first[0].name.replace('_', ' ').capitalize()} with {round(first[1])} treats\n"
        if len(ranked) > 0:
            second = ranked.pop(0)
            res += f"second: {second[0].name.replace('_', ' ').capitalize()} with {round(second[1])} treats\n"
        if len(ranked) > 0:
            third = ranked.pop(0)
            res += f"third: {third[0].name.replace('_', ' ').capitalize()} with {round(third[1])} treats\n"

        res += "\n"
        for zone, percentage in ranked:
            percent_str = round(percentage)
            zone_name = zone.name.replace("_", " ").capitalize()
            res += f"{zone_name}: {percent_str}\n"

        res += f"\nthis transfer we have received {total_referrals} referrals. of which {total_attempted} were attempted. and {total_successful} were successful! so many new people to meet!\n"

        funny = [
            "my tail might wag off",
            "I hope they like fetch",
            "I want to jump on them all",
            "i will be friends with all of them",
        ]
        res += random.choice(funny)

        return res
    except Exception as e:
        print(f"Error getting score: {e}")
        return "*bark* unable to fetch the score *bark*"


def get_contact_time(guid: str, cursor, church_client) -> int:
    cursor.execute("SELECT contact_time FROM people WHERE guid = %s", (guid,))
    res = cursor.fetchone()
    if res is None:
        print("Getting the contact time for ", guid)
        timeline = church_client.get_person_timeline(guid)
        referral_time = 0
        contact_time = 0
        for idx, event in enumerate(timeline):
            if event["timelineItemType"] == "NEW_REFERRAL":
                referral_time = int(event["itemDate"] / 1000)
                break
            elif event["timelineItemType"] == "CONTACT" or event["timelineItemType"] == "TEACHING":
                contact_time = int(event["itemDate"] / 1000)
        if referral_time == 0 or contact_time == 0:
            return None
        referral_time = adjust_epoch_time(referral_time)
        contact_time = adjust_epoch_time(contact_time)
        delta = contact_time - referral_time

        minutes_difference = delta.total_seconds() / 60
        if minutes_difference < 0:
            print("Delta was calculated incorrectly!")
            print("Referral time: ", referral_time)
            print("Contact time: ", contact_time)
            print("Delta: ", minutes_difference)

        cursor.execute(
            "INSERT INTO people (guid, contact_time) VALUES (%s, %s)",
            (guid, minutes_difference),
        )
        return minutes_difference
    else:
        return res[0]


def adjust_epoch_time(epoch_time):
    # Convert the epoch time to a datetime object
    timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    dt = datetime.datetime.fromtimestamp(epoch_time, timezone)

    # Define the start and end times
    start_time = dt.replace(hour=6, minute=30, second=0, microsecond=0)
    end_time = dt.replace(hour=22, minute=30, second=0, microsecond=0)

    if start_time <= dt <= end_time:
        # Time is within the range
        return dt
    else:
        # Time is outside the range, set to 6:30 AM of the next day
        next_day = dt
        if dt.hour > 10:  # doesn't have to be 10, just a number that checks if AM/PM
            next_day = dt + datetime.timedelta(days=1)
        adjusted_time = next_day.replace(hour=6, minute=30, second=0, microsecond=0)
        return adjusted_time


def main():
    """Main function duh"""
    parser = holly.HollyParser()

    while True:
        try:
            client = holly.HollyClient()
            print("Connected to Holly")
            while True:
                raw_msg = client.recv()
                print(raw_msg)
                ret = handle_request(raw_msg.parse(parser))
                if ret:
                    client.send(
                        holly.HollyMessage(
                            content=ret, chat_id=raw_msg.chat_id, sender=""
                        )
                    )

        except holly.HollyError as e:
            print(f"Error: {e}")

        print("Disconnected from Holly socket")
        time.sleep(30)


if __name__ == "__main__":
    main()
