# pylint: disable=line-too-long
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
from person import Person

AUTHORIZED_USERS = ['Williams', 'Broman', 'Coxson', 'Davis']


def load_today_report():
    """Tries to load a report from today, returns None if none"""
    reports = [f for f in listdir('reports') if isfile(join('reports', f))]
    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
    for report in reports:
        if now_str in report:
            print("Loading today's report")
            # If a report for today already exists, send it
            with open(f'reports/{report}', 'r', encoding='utf-8') as f:
                # Parse it as a JSON
                report_data = json.load(f)
                return report_data['zones']
    return None


def generate_report(s: socket.socket, chat_id: str, sender: str):
    """Generates a report of uncontacted referrals"""
    # Get which zones we're trying out
    messenger_ids = {
        '2419609848082592': dashboard.Zone.ZONE_1,
        '4954822721225549': dashboard.Zone.ZONE_2,
        '5865277466887042': dashboard.Zone.ZONE_3,
        '1363317190447129': dashboard.Zone.ZONE_4,
        '5936540856451995': dashboard.Zone.ZONE_5,
        '4133470603409493': dashboard.Zone.ZONE_6,
        '4145470815511596': dashboard.Zone.ZONE_7,
        '24976215742026849': dashboard.Zone.ZONE_8,
        '7554625987953132': dashboard.Zone.ZONE_8,  # Jackson and Holly group chat
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
            s.send(
                json.dumps(
                    {
                        'content': "this isn't a zone chat ya silly goose",
                        'chat_id': chat_id,
                        'sender': '',
                    }
                ).encode('utf-8')
            )
            return
        requested_zones = [
            dashboard.Zone.ZONE_1,
            dashboard.Zone.ZONE_2,
            dashboard.Zone.ZONE_3,
            dashboard.Zone.ZONE_4,
            dashboard.Zone.ZONE_5,
            dashboard.Zone.ZONE_6,
            dashboard.Zone.ZONE_7,
            dashboard.Zone.ZONE_8,
        ]
    else:
        requested_zones = [requested_zones]
        now_str = datetime.datetime.now().strftime('%Y-%m-%d')
        today = {}
        try:
            today = json.load(open('fetched_today.json', 'r'))
        except:
            print('Making new today JSON')
            today = {'today': now_str, 'fetched': []}
        if today['today'] != now_str:
            today['fetched'] = []
            today['today'] = now_str
        today['fetched'].append(requested_zones[0])
        json.dump(today, open('fetched_today.json', 'w'))

    zones = load_today_report()

    if zones is None:
        print('No report for today, generating a new one')
        s.send(
            json.dumps(
                {
                    'content': '*bark bark* (one minute)',
                    'chat_id': chat_id,
                    'sender': '_',
                }
            ).encode('utf-8')
        )
        client = chirch.ChurchClient()
        persons = client.get_cached_people_list()
        troubled: list[Person] = []
        for p in persons:
            res = client.filter_person(p)
            if res is False:
                continue
            troubled.append(p)

        print(f'{len(troubled)} uncontacted referrals')

        zones = {}
        for p in troubled:
            zone = zones.get(p.zone)
            if zone is None:
                zones[p.zone] = {}
                zone = zones[p.zone]
            area = zone.get(p.area_name)
            if area is None:
                zone[p.area_name] = []
                area = zone[p.area_name]
            area.append(p.first_name.strip())

        # Save the zone messages to reports/timestamp.json
        now = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        json.dump(
            {'zones': zones},
            open(f'reports/{now}.json', 'w', encoding='utf-8'),
            indent=4,
        )
        zones = json.loads(json.dumps({'zones': zones}))[
            'zones'
        ]  # lazy I know

    for requested_zone in requested_zones:
        zone = zones.get(str(requested_zone.value))
        if zone is None:
            s.send(
                json.dumps(
                    {
                        'content': f"{requested_zone.name.replace('_', ' ').capitalize()}\nNO UNCONTACTED REFERRALS!!!  *happy zooms around the backyard*",
                        'chat_id': chat_id,
                        'sender': '',
                    }
                ).encode('utf-8')
            )
        print(zone)
        if zone:
            message = f"{requested_zone.name.replace('_', ' ').capitalize()}\n"
            for area, names in zone.items():
                message += f'- {area}: \n'
                for name in names:
                    message += f'  - {name}\n'
                message += '\n'
            print(message)
            s.send(
                json.dumps(
                    {'content': message, 'chat_id': chat_id, 'sender': ''}
                ).encode('utf-8')
            )


def process_json_object(json_data):
    """Checks if this message was for us"""
    content = (
        json_data['content']
        .lower()
        .replace('go', '')
        .replace(',', '')
        .replace('  ', ' ')
    )
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
                            generate_report(
                                s, json_data['chat_id'], json_data['sender']
                            )
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            print(e.with_traceback(None))
                            s.send(
                                json.dumps(
                                    {
                                        'content': f"*sad bark* (I couldn't generate a report)\n{e}",
                                        'chat_id': json_data['chat_id'],
                                        'sender': '_',
                                    }
                                ).encode('utf-8')
                            )
                    data = []

        except (socket.error, json.JSONDecodeError) as e:
            print(f'Error: {e}')
            time.sleep(30)


if __name__ == '__main__':
    main()
