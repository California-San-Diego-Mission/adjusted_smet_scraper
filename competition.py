#pylint: disable=line-too-long
"""Competition code"""

import datetime
import time
import holly

import chirch
import dashboard

def handle_request(request: holly.ParsedHollyMessage):
    """Parses the text to determine if we need to react"""
    print(request)
    if request.is_targeted and (request.match('what score') or request.match('who winning') or request.match('get score')):
        return get_score()

    return False

def get_score():
    """Gets the score of contacted/total referrals"""
    try:
        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()['persons']

        now = datetime.datetime.now()
        # get the last Sunday
        last_sunday = now - datetime.timedelta(days=now.weekday(), weeks=1)
        last_sunday = last_sunday.replace(hour=0, minute=0, second=0, microsecond=0)

        zones = {}
        for person in persons:
            assigned_date = person.get("referralAssignedDate")
            if assigned_date is None:
                continue
            assigned_date = datetime.datetime.fromtimestamp(assigned_date / 1000)
            if assigned_date < last_sunday:
                continue
            try:
                zone_id = person.get("zoneId")
                if zone_id is None:
                    continue
                zone = dashboard.Zone(zone_id)

                # If the zone doesn't exist, insert it
                if zones.get(zone) is None:
                    zones[zone] = (0, 0)

                status_id = person.get("referralStatusId")
                if status_id is None:
                    continue
                status = dashboard.ReferralStatus(status_id)

                if status == dashboard.ReferralStatus.NOT_ATTEMPTED:
                    zones[zone] = (zones[zone][0], zones[zone][1] + 1)
                elif status == dashboard.ReferralStatus.NOT_SUCCESSFUL:
                    zones[zone] = (zones[zone][0] + 0.8, zones[zone][1] + 1)
                elif status == dashboard.ReferralStatus.SUCCESSFUL:
                    zones[zone] = (zones[zone][0] + 1, zones[zone][1] + 1)
            except Exception as e:
                print(f"Error processing person: {e}")
                continue

        zone_percentages = {}
        for zone, zone_items in zones.items():
            if zone_items[1] != 0:
                zone_percentages[zone] = (zone_items[0] / zone_items[1]) * 100

        # Rank the zones
        ranked = sorted(zone_percentages.items(), key=lambda x: x[1], reverse=True)

        # Create the string
        res = "Here are the current scores:\n"
        for zone, percentage in ranked:
            percent_str = round(percentage, 2)
            zone_name = zone.name.replace('_', ' ').capitalize()
            res += f"{zone_name}: {percent_str}%\n"
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
                    client.send(holly.HollyMessage(content=ret, chat_id=raw_msg.chat_id, sender=''))

        except holly.HollyError as e:
            print(f"Error: {e}")

        print('Disconnected from Holly socket')
        time.sleep(30)

if __name__ == "__main__":
    main()
