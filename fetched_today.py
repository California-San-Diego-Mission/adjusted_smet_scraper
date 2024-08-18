#!/usr/bin/env python3
# Jackson Coxson

import json
import holly


zones = {
    500271388: 'Zone 1',
    500350997: 'Zone 2',
    457719924: 'Zone 3',
    3528712: 'Zone 4',
    136030695: 'Zone 5',
    3528714: 'Zone 6',
    500366346: 'Zone 7',
    500576704: 'Zone 8',
}
chat = '7016741568410945'

today = json.load(open('fetched_today.json', 'r'))

message = 'Zones who have fetched today:\n'

for key, value in zones.items():
    if key in today['fetched']:
        message += value + '\n'

client = holly.HollyClient()
client.send(holly.HollyMessage(message, chat))
