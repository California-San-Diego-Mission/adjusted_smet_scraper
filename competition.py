# pylint: disable=line-too-long
"""Competition code"""

import datetime
import time
import random

import holly
import chirch
import dashboard


def handle_request(request: holly.ParsedHollyMessage):
    """Parses the text to determine if we need to react"""
    print(request)
    if request.is_targeted and (request.match('what score') or request.match('whats score') or request.match('who winning') or request.match('get score')):
        # if request.chat_id != "7016741568410945":
        #     return "shhhhhhh it's a secret"
        return get_score()

    return False


def get_score():
    """Gets the score of contacted/total referrals"""
    try:
        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()['persons']

        now = datetime.datetime.now()
        # get the last Sunday
        # last_sunday = now - datetime.timedelta(days=now.weekday(), weeks=1)
        # last_sunday = last_sunday.replace(hour=0, minute=0, second=0, microsecond=0)
        last_sunday = datetime.datetime.fromtimestamp(1712905200)

        zones = {}
        total_referrals = 0
        total_successful = 0
        total_attempted = 0
        for person in persons:
            assigned_date = person.get("referralAssignedDate")
            if assigned_date is None:
                continue
            assigned_date = datetime.datetime.fromtimestamp(
                assigned_date / 1000)
            if assigned_date < last_sunday:
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
                    dashboard.PersonStatus.YELLOW
                ]

                if dot_status not in permissable_dots:
                    continue

                # If the zone doesn't exist, insert it
                if zones.get(zone) is None:
                    zones[zone] = (0, 0, 0)

                status_id = person.get("referralStatusId")
                if status_id is None:
                    continue
                status = dashboard.ReferralStatus(status_id)

                if status == dashboard.ReferralStatus.NOT_ATTEMPTED:
                    zones[zone] = (zones[zone][0], zones[zone]
                                   [1], zones[zone][2] + 1)
                    print(f"{zone.name}: {person.get('lastName')}")
                    total_referrals += 1
                elif status == dashboard.ReferralStatus.NOT_SUCCESSFUL:
                    zones[zone] = (zones[zone][0], zones[zone]
                                   [1] + 1, zones[zone][2] + 1)
                    total_referrals += 1
                    total_attempted += 1
                elif status == dashboard.ReferralStatus.SUCCESSFUL:
                    zones[zone] = (zones[zone][0] + 1, zones[zone]
                                   [1], zones[zone][2] + 1)
                    total_referrals += 1
                    total_attempted += 1
                    total_successful += 1
            except Exception as e:
                print(f"Error processing person: {e}")
                continue

        zone_percentages = {}
        for zone, zone_items in zones.items():
            if zone_items[2] != 0:
                print(
                    f"{zone.name} - S:{zone_items[0]} A:{zone_items[1]} T:{zone_items[2]}")
                zone_percentages[zone] = (
                    (zone_items[0] + (zone_items[1] * 0.3)) / zone_items[2]) * 1000  # change me for weighted successful

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
            zone_name = zone.name.replace('_', ' ').capitalize()
            res += f"{zone_name}: {percent_str}\n"

        res += f"\nthis transfer we have received {total_referrals} referrals. of which {total_attempted} were attempted. and {total_successful} were successful! so many new people to meet!\n"

        funny = ["my tail might wag off", "I hope they like fetch",
                 "I want to jump on them all", "i will be friends with all of them"]
        res += random.choice(funny)

        return res
    except Exception as e:
        print(f"Error getting score: {e}")
        return "*bark* unable to fetch the score *bark*"


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
                    client.send(holly.HollyMessage(
                        content=ret, chat_id=raw_msg.chat_id, sender=''))

        except holly.HollyError as e:
            print(f"Error: {e}")

        print('Disconnected from Holly socket')
        time.sleep(30)


if __name__ == "__main__":
    main()
