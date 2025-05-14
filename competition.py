# pylint: disable=line-too-long
"""Competition code"""

import datetime
import os
import statistics
import time
from dataclasses import dataclass, field
from typing import Union

import holly
import mysql.connector
from dotenv import load_dotenv

import chirch
import dashboard
import transfer_calculator
import sql_library

load_dotenv()


def handle_request(request: holly.ParsedHollyMessage):
    """Parses the text to determine if we need to react"""
    print(request)
    if request.is_targeted and (
        request.match('what score')
        or request.match('whats score')
        or request.match('who winning')
        or request.match('get score')
    ):
        # if request.chat_id != "7016741568410945":
        #     return "shhhhhhh it's a secret"
        return get_score()
    return False


@dataclass
class ZoneResults:
    contact_time: list[float] = field(default_factory=list)


def get_score():
    """Gets the score of contacted/total referrals"""
    try:
        mydb = mysql.connector.connect(
            host='localhost',
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database='holly',
        )
        cursor = mydb.cursor()

        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()

        # get the last transfer
        last_transfer = datetime.datetime.fromtimestamp(transfer_calculator.get_most_recent_transfer_time_stamp())
        print(last_transfer)
        zones: dict[dashboard.Zone, list[float]] = {}
        total = 0
        successful = 0
        attempted = 0

        for person in persons:
            if person.referral_assigned_date < last_transfer:
                continue
            try:
                zone = person.zone

                # If the zone doesn't exist, insert it
                if zones.get(zone) is None:
                    zones[zone] = []

                status = person.referral_status

                # Get the time from assignment to contact
                if (
                    status == dashboard.ReferralStatus.NOT_SUCCESSFUL
                    or status == dashboard.ReferralStatus.SUCCESSFUL
                ):
                    attempted += 1
                    contact_time = get_contact_time(
                        person.guid, cursor, client
                    )
                    if contact_time is not None:
                        mydb.commit()
                        zones[zone].append(contact_time)

                total += 1
                if status == dashboard.ReferralStatus.SUCCESSFUL:
                    successful += 1

            except Exception as e:
                print(f'Error processing person: {e}')
                continue

        zones = {k: v for (k, v) in zones.items() if len(v) > 0}
        ranked = sorted(zones.items(), key=lambda x: statistics.mean(x[1]))

        # Create the string
        res = ''

        for zone, times in ranked:
            print(zone)
            percent_str = round((0.99 ** sql_library.count_blank_slates_in_zone_since_transfer_day(zone)) * statistics.mean(times))
            zone_name = zone.name.replace('_', ' ').capitalize()
            res += f'{zone_name}: {percent_str} mins\n'
        res += f'\nSuccessful: {successful}'
        res += f'\nAttempted: {attempted}'
        res += f'\nTotal: {total}'

        return res
    except Exception as e:
        print(f'Error getting score: {e}')
        return '*bark* unable to fetch the score *bark*'


def get_contact_time(guid: str, cursor, church_client) -> Union[float, None]:
    cursor.execute('SELECT contact_time FROM people WHERE guid = %s', (guid,))
    res = cursor.fetchone()
    if res is None:
        print('Getting the contact time for ', guid)
        timeline = church_client.get_person_timeline(guid)
        referral_time = 0
        contact_time = 0
        for event in timeline:
            if event['timelineItemType'] == 'NEW_REFERRAL':
                referral_time = int(event['itemDate'] / 1000)
                break
            elif (
                event['timelineItemType'] == 'CONTACT'
                or event['timelineItemType'] == 'TEACHING'
                or event['timelineItemType'] == 'STOPPED_TEACHING'
            ):
                contact_time = int(event['itemDate'] / 1000)
        if referral_time == 0 or contact_time == 0:
            return None
        referral_time = adjust_epoch_time(referral_time)
        contact_time = adjust_epoch_time(contact_time)
        delta = contact_time - referral_time

        minutes_difference = delta.total_seconds() / 60
        if minutes_difference < 0:
            print('Delta was calculated incorrectly!')
            print('Referral time: ', referral_time)
            print('Contact time: ', contact_time)
            print('Delta: ', minutes_difference)

        cursor.execute(
            'INSERT INTO people (guid, contact_time) VALUES (%s, %s)',
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
        if (
            dt.hour > 10
        ):  # doesn't have to be 10, just a number that checks if AM/PM
            next_day = dt + datetime.timedelta(days=1)
        adjusted_time = next_day.replace(
            hour=6, minute=30, second=0, microsecond=0
        )
        return adjusted_time


def main():
    """Main function duh"""
    parser = holly.HollyParser()

    while True:
        try:
            client = holly.HollyClient()
            print('Connected to Holly')
            while True:
                raw_msg = client.recv()
                print(raw_msg)
                ret = handle_request(raw_msg.parse(parser))
                if ret:
                    client.send(
                        holly.HollyMessage(
                            content=ret, chat_id=raw_msg.chat_id, sender=''
                        )
                    )

        except holly.HollyError as e:
            print(f'Error: {e}')

        print('Disconnected from Holly socket')
        time.sleep(30)


if __name__ == '__main__':
    main()
