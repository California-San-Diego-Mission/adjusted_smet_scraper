#pylint: disable=line-too-long
"""
Code to send uncontacted referrals to the ZLs every morning
"""

import datetime
import json
import socket
import time

from os import listdir
from os.path import isfile, join

import chirch
import dashboard

AUTHORIZED_USERS = [
    "Coxson",
    "Nielson",
    "Meilstrup",
    "Bugby",
    "Widdison",
    "Rowley"
]

def generate_report(s: socket.socket, chat_id: str, sender: str):
    """Generates a report of uncontacted referrals"""
    # Get which zones we're trying out
    messenger_ids = {
        "2419609848082592": dashboard.Zone.ZONE_1,
        "4954822721225549": dashboard.Zone.ZONE_2,
        "5865277466887042": dashboard.Zone.ZONE_3,
        "1363317190447129": dashboard.Zone.ZONE_4,
        "5936540856451995": dashboard.Zone.ZONE_5,
        "4133470603409493": dashboard.Zone.ZONE_6,
        "4145470815511596": dashboard.Zone.ZONE_7,
    }

    requested_zones = messenger_ids.get(chat_id)
    if not requested_zones:
        # Authorize the user
        authorized = False
        for au in AUTHORIZED_USERS:
            if au in sender:
                authorized = True
                break
        if not authorized:
            s.send(json.dumps({
                "content": "new tennis ball, who dis?",
                "chat_id": chat_id,
                "sender": ""
            }).encode('utf-8'))
            return
        requested_zones = [dashboard.Zone.ZONE_1, dashboard.Zone.ZONE_2, dashboard.Zone.ZONE_3, dashboard.Zone.ZONE_4, dashboard.Zone.ZONE_5, dashboard.Zone.ZONE_6, dashboard.Zone.ZONE_7, dashboard.Zone.ZONE_8]
    else:
        requested_zones = [requested_zones]

    zones = None

    # Determine if a report already exists in a reports folder
    # Get the list of files in /reports
    reports = [f for f in listdir('reports') if isfile(join('reports', f))]
    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
    for report in reports:
        if now_str in report:
            print('Loading today\'s report')
            # If a report for today already exists, send it
            with open(f'reports/{report}', 'r', encoding='utf-8') as f:
                # Parse it as a JSON
                report_data = json.load(f)
                zones = report_data['zones']

    if zones is None:
        print('No report for today, generating a new one')
        s.send(json.dumps({'content': '*bark bark* (One minute)', 'chat_id': chat_id, 'sender': '_'}).encode('utf-8'))
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

        s.send(json.dumps({'content': f'{len(troubled)} uncontacted referrals', 'chat_id': chat_id, 'sender': 'urmom'}).encode('utf-8'))
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
        zones = json.loads(json.dumps({'zones': zones}))['zones'] # lazy I know

    for requested_zone in requested_zones:
        zone = zones.get(str(requested_zone.value))
        if zone is None:
            s.send(json.dumps({'content': f"{requested_zone.name.replace('_', ' ').capitalize()}\nNo uncontacted referrals! :)", 'chat_id': chat_id, 'sender': ''}).encode('utf-8'))
        print(zone)
        if zone:
            message = f"{requested_zone.name.replace('_', ' ').capitalize()}\n"
            for area, names in zone.items():
                message += f"- {area}: \n"
                for name in names:
                    message += f"  - {name}\n"
                message += "\n"
            print(message)
            s.send(json.dumps({'content': message, 'chat_id': chat_id, 'sender': ''}).encode('utf-8'))

def process_json_object(json_data):
    """Checks if this message was for us"""
    content = json_data['content'].lower().replace('go', '').replace(',', '').replace('  ', ' ')
    if 'holly fetch' in content:
        return True
    else:
        return False


def main():
    """Main"""
    host = 'localhost'
    port = 8011

    while True:
        print('Connecting to Holly socket')
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                while True:
                    data = s.recv(1024)
                    json_data = json.loads(data.decode('utf-8'))
                    pls_go = process_json_object(json_data)
                    if pls_go:
                        try:
                            generate_report(s, json_data['chat_id'], json_data['sender'])
                        except Exception as e: #pylint: disable=broad-exception-caught
                            print(e.with_traceback(None))
                            s.send(json.dumps({'content': '*sad bark* (I couldn\'t generate a report)', 'chat_id': json_data['chat_id'], 'sender': '_'}).encode('utf-8'))
                    data = []

        except (socket.error, json.JSONDecodeError) as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
