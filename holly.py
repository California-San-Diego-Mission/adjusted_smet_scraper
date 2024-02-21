#pylint: disable=line-too-long
"""
Code to send uncontacted referrals to the ZLs every morning
"""

import datetime
import json
import socket

from os import listdir
from os.path import isfile, join

import chirch
import dashboard

def generate_report(s: socket.socket, chat_id: str):
    """Generates a report of uncontacted referrals"""
    # Determine if a report already exists in a reports folder
    # Get the list of files in /reports
    reports = [f for f in listdir('reports') if isfile(join('reports', f))]
    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
    for report in reports:
        if now_str in report:
            # If a report for today already exists, send it
            with open(f'reports/{report}', 'r', encoding='utf-8') as f:
                # Parse it as a JSON
                report_data = json.load(f)
                zones = report_data['zones']
                # Walk the dictionary, getting the key and values
                for zone, zone_data in zones.items():
                    zone_name = dashboard.Zone(int(zone)).name.replace('_', ' ').capitalize()
                    message = f'{zone_name}\n'
                    for area_name, people in zone_data.items():
                        message += f'- {area_name}:\n'
                        for person in people:
                            message += f'  - {person}\n'
                        message += '\n'
                    # Send the message
                    s.send(json.dumps({'content': message, 'chat_id': chat_id, 'sender': 'urmom'}).encode('utf-8'))
                return

    client = chirch.ChurchClient()
    # persons = json.load(open('test.json', 'r', encoding='utf-8'))['persons']
    persons = client.get_people_list()['persons']
    troubled = []
    for p in persons:
        res = client.parse_person(p)
        if res is None:
            continue
        if res['status'] != dashboard.ReferralStatus.SUCCESSFUL:
            troubled.append(res)

    print(f'{len(troubled)} uncontacted referrals')

    zones = {}
    for p in troubled:
        zone = zones.get(p['zone'])
        if zone is None:
            zones[p['zone']] = {}
            zone = zones[p['zone']]
        area = zone.get(p['area_name'])
        if area is None:
            zone[p['area_name']] = []
            area = zone[p['area_name']]
        if p['last_name'] is None:
            p['last_name'] = ''
        area.append(f"{p['first_name']} {p['last_name']}".strip())

    # Save the zone messages to reports/timestamp.json
    now = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    json.dump({'zones': zones}, open(f'reports/{now}.json', 'w', encoding='utf-8'), indent=4)

    for zone, items in zones.items():
        message = f"{zone.name.replace('_', ' ')}\n"
        for area, names in items.items():
            message += f"- {area}: \n"
            for name in names:
                message += f"  - {name}\n"
            message += "\n"
        print(message)
        s.send(json.dumps({'content': message, 'chat_id': chat_id, 'sender': 'urmom'}).encode('utf-8'))

AUTHORIZED_USERS = [
    "Coxson",
    "Nielson",
    "Meilstrup"
]

def process_json_object(json_data):
    if 'holly, go fetch' in json_data['content'].lower():
        authorized = False
        for user in AUTHORIZED_USERS:
            if user.lower() in json_data['sender'].lower():
                authorized = True
                break
        if authorized:
            return json_data['chat_id']
    else:
        return None


def main():
    host = 'localhost'
    port = 8011

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            while True:
                data = s.recv(1024)
                json_data = json.loads(data.decode('utf-8'))
                chat_id = process_json_object(json_data)
                if chat_id:
                    s.send(json.dumps({'content': '*bark bark* (I\'m on my way, one minute)', 'chat_id': chat_id, 'sender': '_'}).encode('utf-8'))
                    try:
                        generate_report(s, chat_id)
                    except Exception as e:
                        print(e)
                        s.send(json.dumps({'content': '*sad bark* (I couldn\'t generate a report for some reason)', 'chat_id': chat_id, 'sender': '_'}).encode('utf-8'))
                data = []

    except (socket.error, json.JSONDecodeError) as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
