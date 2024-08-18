import requests
import time
from datetime import datetime, timedelta
import holly

SUBSCRIBED_CHATS = [
    '7016741568410945',
    '61550123653538',
    '100024445521321',
    '100009153609363',
    '100066453672395',
    '100080664574831',
    '100065230159630',
    '100050515731507',
]


def get_yesterday_date():
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


def homerun(team_id, date):
    endpoint = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&teamId={team_id}'
    response = requests.get(endpoint)
    if response.status_code == 200:
        data = response.json()
        dates = data['dates']
        if len(dates) > 0:
            games = dates[0]['games']
            if len(games) > 0:
                for game in games:
                    if game['teams']['home']['team']['id'] == team_id:
                        game_pk = game['gamePk']
                        if did_homerun(game_pk):
                            return True
    return False


def did_homerun(game_pk):
    endpoint = f'https://statsapi.mlb.com/api/v1/game/{game_pk}/playByPlay'
    response = requests.get(endpoint)
    if response.status_code == 200:
        data = response.json()
        plays = data['allPlays']
        for play in plays:
            # filter out away team
            if play['about']['halfInning'] == 'bottom':
                if play['result']['eventType'] == 'home_run':
                    return True
    return False


if __name__ == '__main__':
    while True:
        # Get the current hour
        now = datetime.now()
        hour = now.hour
        if hour == 7:
            print('Checking for homeruns...')
            client = holly.HollyClient()
            if homerun(135, get_yesterday_date()):
                print('Padres hit a homerun and were home yesterday.')
                for chat in SUBSCRIBED_CHATS:
                    client.send(
                        holly.HollyMessage(
                            'Padres hit a homerun, go get your burger!', chat
                        )
                    )
            else:
                print('Padres did not play at home or did not hit a homerun')
                for chat in SUBSCRIBED_CHATS:
                    client.send(
                        holly.HollyMessage(
                            'Padres did not play at home or did not hit a homerun. Cringe.',
                            chat,
                        )
                    )

        # Wait for 1 hour
        time.sleep(60 * 60)
