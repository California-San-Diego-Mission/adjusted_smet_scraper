#pylint: disable=line-too-long
"""Competition code"""

import datetime
import json
import socket
import time

import chirch
import dashboard

AUTHORIZED_USERS = [
    "Coxson",
    "Nielson",
    "Meilstrup",
    "Bugby",
    "Widdison"
]

GARBAGE = [
    'holly',
    ',',
    ', ',
    'the',
    'a ',
    'is',
    '?',
    '.',
    'please',
    'can',
    'you',
]

def is_authorized(name):
    """Determines if the sender is authorized to run this command"""
    for user in AUTHORIZED_USERS:
        if user.lower() in name.lower():
            return True
    return False

def handle_request(request):
    """Parses the text to determine if we need to react"""
    content: str = request['content'].lower()
    if not is_authorized(request['sender']):
        return False
    if not content.startswith('holly'):
        return False

    for g in GARBAGE:
        content = content.replace(g, '')
    for _ in range(1,5):
        content = content.replace('  ', ' ')
    content = content.strip()

    print(f"Parsing {content}")
    if content == 'what score':
        return True

    if content == 'who winning':
        return True

    if content == 'get score':
        return True

    return False

def get_score():
    """Gets the score of contacted/total referrals"""
    client = chirch.ChurchClient()
    persons = client.get_people_list()['persons']
    # persons = json.load(open('test.json', 'r', encoding='utf-8'))

    now = datetime.datetime.now()
    # get the last Sunday
    last_sunday = now - datetime.timedelta(days=now.weekday(), weeks=1)
    last_sunday = last_sunday.replace(hour=0, minute=0, second=0, microsecond=0)

    zones = {}
    for person in persons:
        assigned_date = person["referralAssignedDate"]
        if assigned_date is None:
            continue
        assigned_date = datetime.datetime.fromtimestamp(person["referralAssignedDate"] / 1000)
        if assigned_date < last_sunday:
            continue
        try:
            zone = dashboard.Zone(person["zoneId"])

            # If the zone doesn't exist, insert it in
            if zones.get(zone) is None:
                zones[zone] = (0, 0)

            status = dashboard.ReferralStatus(person["referralStatusId"])

            if status == dashboard.ReferralStatus.NOT_ATTEMPTED:
                zones[zone] = (zones[zone][0], zones[zone][1] + 1)
            else:
                zones[zone] = (zones[zone][0] + 1, zones[zone][1] + 1)
        except: #pylint: disable=bare-except
            continue
    return zones

def main():
    """Main function duh"""
    host = 'localhost'
    port = 8011

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                while True:
                    data = s.recv(1024)
                    json_data = json.loads(data.decode('utf-8'))
                    if handle_request(json_data):
                        zones = get_score()
                        zone_percentages = {}
                        for zone in zones:
                            zone_percentages[zone] = (zones[zone][0] / zones[zone][1]) * 100
                        # Rank the zones
                        ranked = []
                        for zone in zone_percentages:
                            ranked.append((zone, zone_percentages[zone]))
                        ranked.sort(key=lambda x: x[1], reverse=True)
                        # Create the string
                        res = "Here are the current scores:\n"
                        for zone in ranked:
                            percent_str = round(zone[1], 2)
                            zone_name = zone[0].name.replace('_', ' ').capitalize()
                            res += f"{zone_name}: {percent_str}%\n"
                        # Send the string
                        s.sendall(json.dumps({'content': res, 'chat_id': json_data['chat_id'], 'sender': ''}).encode('utf-8'))

        except (socket.error, json.JSONDecodeError) as e:
            print(f"Error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    # get_score({})
    main()
