# pylint: disable=line-too-long
"""Competition code"""

import datetime
import os
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Union

import holly
import mysql.connector
from dotenv import load_dotenv

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


@dataclass
class ZoneResults:
    successful: int = 0
    attempted: int = 0
    total: int = 0
    contact_time: list[float] = field(default_factory=list)


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

        # get the last transfer
        last_transfer = datetime.datetime.fromtimestamp(1720033200)

        zones: dict[dashboard.Zone, ZoneResults] = {}

        total_referrals = 0
        total_successful = 0
        total_attempted = 0
        for person in persons:
            assigned_date = person.get("referralAssignedDate")
            if assigned_date is None:
                print(
                    "Person does not have a referralAssignedDate",
                    person.get("personGuid"),
                )
                continue
            assigned_date = datetime.datetime.fromtimestamp(
                assigned_date / 1000)
            if assigned_date < last_transfer:
                continue
            try:
                zone_id = person.get("zoneId")
                if zone_id is None:
                    print("Person does not have a zoneId",
                          person.get("personGuid"))
                    continue
                zone = dashboard.Zone(zone_id)

                # If the zone doesn't exist, insert it
                if zones.get(zone) is None:
                    zones[zone] = ZoneResults()

                status_id = person.get("referralStatusId")
                if status_id is None:
                    print(
                        "Person doesn't have referralStatusId: ",
                        person.get("personGuid"),
                    )
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
                        zones[zone].contact_time.append(contact_time)

                if status == dashboard.ReferralStatus.NOT_ATTEMPTED:
                    zones[zone].total += 1
                    total_referrals += 1
                elif status == dashboard.ReferralStatus.NOT_SUCCESSFUL:
                    zones[zone].attempted += 1
                    zones[zone].total += 1
                    total_referrals += 1
                    total_attempted += 1
                elif status == dashboard.ReferralStatus.SUCCESSFUL:
                    zones[zone].successful += 1
                    zones[zone].total += 1
                    total_referrals += 1
                    total_attempted += 1
                    total_successful += 1
            except Exception as e:
                print(f"Error processing person: {e}")
                continue

        zone_percentages = {}
        for zone, zone_items in zones.items():
            time_average = statistics.median(zone_items.contact_time)
            if zone_items.total != 0:
                print(
                    f"{zone.name} - S:{zone_items.successful} A:{zone_items.attempted} T:{zone_items.total} M:{time_average}"
                )
                zone_percentages[zone] = (
                    (
                        (zone_items.successful + (zone_items.attempted * 0.5))
                        / zone_items.total
                    )
                    * 1000
                ) - time_average

        # Rank the zones
        ranked = sorted(zone_percentages.items(),
                        key=lambda x: x[1], reverse=True)

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


def get_contact_time(guid: str, cursor, church_client) -> Union[float, None]:
    cursor.execute("SELECT contact_time FROM people WHERE guid = %s", (guid,))
    res = cursor.fetchone()
    if res is None:
        print("Getting the contact time for ", guid)
        timeline = church_client.get_person_timeline(guid)
        referral_time = 0
        contact_time = 0
        for event in timeline:
            if event["timelineItemType"] == "NEW_REFERRAL":
                referral_time = int(event["itemDate"] / 1000)
                break
            elif (
                event["timelineItemType"] == "CONTACT"
                or event["timelineItemType"] == "TEACHING"
            ):
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
        adjusted_time = next_day.replace(
            hour=6, minute=30, second=0, microsecond=0)
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
