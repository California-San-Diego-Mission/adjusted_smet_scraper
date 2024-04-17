"""Code to parse the dashboard JSON"""

from datetime import timedelta
from datetime import datetime
from enum import Enum


class FbPageId(Enum):
    """SLC's ID for each page"""
    ENGLISH = "2994"
    IMPERIAL_VALLEY = "3446"
    SPANISH = "3447"
    ARABIC = "5573"
    MANDARIN = "6613"
    SWAHILI = "6633"
    HAITIAN = "6634"
    FARCI = "6653"
    TAGALOG = "6654"
    ASL = "6735"


class ClaimedStatus(Enum):
    """Status of claimed interactions from the dashboard JSON"""
    NOT_CONTACTED = "0"
    NO_RESPONSE = "1"
    POSITIVE_RESPONSE = "2"
    NEGATIVE_RESPONSE = "3"


class Zone(int, Enum):
    """Each of the mission zones"""
    ZONE_1 = 500271388
    ZONE_2 = 500350997
    ZONE_3 = 457719924
    ZONE_4 = 3528712
    ZONE_5 = 136030695
    ZONE_6 = 3528714
    ZONE_7 = 500366346
    ZONE_8 = 500576704


class ReferralStatus(Enum):
    """The status a referral can be in"""
    NOT_ATTEMPTED = 10
    NOT_SUCCESSFUL = 20
    SUCCESSFUL = 30


class PersonStatus(Enum):
    """The status of a person"""
    YELLOW = 1
    GREEN = 2
    BETTER_GREEN = 3
    PROGRESSING_GREEN = 4
    NEW_MEMBER = 6
    NOT_INTERESTED = 20
    NOT_INTERESTED_DECLARED = 21  # canceled referral
    NOT_PROGRESSING = 22
    UNABLE_TO_CONTACT = 23
    PRANK = 25  # Fake name, doesn't show up in referral manager, unsure
    NOT_RECENTLY_CONTACTED = 26
    TOO_BUSY = 27
    OUTSIDE_AREA_STRENGTH = 28
    MEMBER = 40
    MOVED = 201


def parse_dashboard_json(json_data):
    """Parses a JSON object into a dictionary of pages"""
    user_results = {}
    overview_results = {}

    today_str = datetime.today().strftime('%Y-%m-%d')

    for page in FbPageId:
        page_id = page.value
        page_data = json_data.get(page_id)

        page_results = {
            "missed": 0,
            "received": 0,
            "dots": 0,
        }

        if page_data:
            # Get the names
            user_dict = page_data.get("cmisIdToName")
            if not user_dict:
                print("Uh oh no user dictionary for page ", page_id)
                continue
            for _, name in user_dict.items():
                # Add to user_results if not exist
                if name not in user_results:
                    user_results[name] = {
                        "messaging": {
                            ClaimedStatus.NOT_CONTACTED.value: 0,
                            ClaimedStatus.NO_RESPONSE.value: 0,
                            ClaimedStatus.POSITIVE_RESPONSE.value: 0,
                            ClaimedStatus.NEGATIVE_RESPONSE.value: 0
                        },
                        "responses":  {
                            ClaimedStatus.NOT_CONTACTED.value: 0,
                            ClaimedStatus.NO_RESPONSE.value: 0,
                            ClaimedStatus.POSITIVE_RESPONSE.value: 0,
                            ClaimedStatus.NEGATIVE_RESPONSE.value: 0
                        },
                        "dots": 0
                    }

            # Get the messaging stats
            for uid, value in page_data.get('chatsClaimedByStatus').items():
                name = user_dict.get(uid)
                if not name:
                    print('Somehow the id to name wasnt included')
                    continue
                for key, val in value.items():
                    user_results[name]['messaging'][key] += val

            # Get the responses stats
            for uid, value in page_data.get('responsesClaimedByStatus').items():
                name = user_dict.get(uid)
                if not name:
                    print('Somehow the id to name wasnt included')
                    continue
                for key, val in value.items():
                    user_results[name]['responses'][key] += val

            # Get the dot
            dot_dict = page_data.get('linkedToPersonByDate')
            today_dot_dict = dot_dict.get(today_str)
            if today_dot_dict:
                for uid, value in today_dot_dict.items():
                    name = user_dict.get(uid)
                    if not name:
                        print('Somehow the id to name wasnt included')
                        continue
                    user_results[name]['dots'] += value['total']
                    page_results['dots'] += value['total']

            # Missed interactions
            missed_dict = page_data.get('missedByDate')
            today_missed_dict = missed_dict.get(today_str)
            if today_missed_dict:
                page_results["missed"] = today_missed_dict['total']

            # Received interactions
            received_dict = page_data.get('receivedByDate')
            today_received_dict = received_dict.get(today_str)
            if today_received_dict:
                page_results["received"] = today_received_dict['total']

            overview_results[page_id] = page_results
        else:
            print("Uh oh no data for ", page.name)
    return {'user': user_results, 'overview': overview_results}


def parse_timeline(timeline_data, grey_dot=False):
    """
    Goes through the timeline and determines if the person should be on the list
    """
    attempts = 0
    for event in timeline_data:
        match event['timelineItemType']:
            case 'CONTACT':
                # If the contact is more than 48 hours old, return true
                timestamp = datetime.fromtimestamp(event['itemDate'] / 1000)
                if timestamp > datetime.now() - timedelta(hours=48):
                    return False
                if event['eventStatus'] is False:
                    attempts += 1
                if attempts > 4 and grey_dot:
                    return False
            case 'STOPPED_TEACHING':
                # If the referral was dropped after it was received
                return False
            case 'NEW_REFERRAL':
                return True
    # If there's no contacts, return true
    return True
