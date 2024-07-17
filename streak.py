"""
Jackson Coxson
Holly program to determine if a user has done their interactions for the day
"""

from threading import Thread
import time
import sqlite3
import holly
import chirch
import dashboard

# SQLITE TABLES
# [users]: CHURCH_ID, FB_NAME
# [report]: USER_ID, NC, NR, PR, BR, MNC, MNR, MPR, MBR, DAYS


def midnight_handler():
    while True:
        # Wait until 23:00
        while time.localtime().tm_hour != 22:
            time.sleep(1)

        # Get the dashboard data from referral manager
        client = chirch.ChurchClient()
        res = client.get_referral_dashboard_counts()
        res = dashboard.parse_dashboard_json(res)

        for name, data in res["user"]:
            # Try to get the row from the database
            conn = sqlite3.connect('smet.db')
            c = conn.cursor()
            c.execute('SELECT * FROM smet WHERE CHURCH_ID=?', (name,))
            row = c.fetchone()
            conn.close()

            # If the row doesn't exist, create it
            if not row:
                conn = sqlite3.connect('smet.db')
                c = conn.cursor()
                c.execute('INSERT INTO smet (CHURCH_ID, FB_NAME) VALUES (?, ?)',

                          )

        time.sleep(60 * 60 * 2)


def handle_request(request: holly.ParsedHollyMessage):
    """Parses the text to determine if we need to react"""
    print(request)
    if request.is_targeted and (request.match('smet')):
        return calculate_smet()
    return False


def calculate_smet():
    """Read from the database and calculate the score"""
    conn = sqlite3.connect('smet.db')
    c = conn.cursor()
    c.execute('SELECT * FROM smet')
    rows = c.fetchall()
    conn.close()

    score = 0
    for row in rows:
        if row[1] == 1:
            score += 1
    return score


def main():
    print("Running SMET")

    # Start another thread to wait until 23:00
    wait_thread = Thread(target=midnight_handler)
    wait_thread.start()

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
