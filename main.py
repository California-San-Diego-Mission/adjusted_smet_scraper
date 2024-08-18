"""Runner script for SMET scraper"""

import datetime
import time

import chirch
import dashboard
import spread

if __name__ == '__main__':
    while True:
        # Wait until it's 1am-2am
        while True:
            current_time = datetime.datetime.now()
            print('Current hour: ', current_time.hour)
            time.sleep(58 * 60)
            if current_time.hour > 21 and current_time.hour < 23:
                print('System is a go!')
                break

        # Get them datas
        church_client = chirch.ChurchClient()
        data = {}

        for i in range(1, 4):
            try:
                data = church_client.get_referral_dashboard_counts()
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(
                    'Church credentials expired, logging in with username/pass'
                )
                try:
                    church_client.login()
                except Exception as e2:  # pylint: disable=broad-exception-caught
                    if i > 2:
                        raise e2
                    else:
                        continue
                data = church_client.get_referral_dashboard_counts()
                if i > 2:
                    raise e

        data = dashboard.parse_dashboard_json(data)
        print(data)
        spread_client = spread.SpreadClient()
        spread_client.add_daily_data(data)

        print('Done :)')
