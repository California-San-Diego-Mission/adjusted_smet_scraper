# Holly needs to know when the most recent transfer was for the sake of calculating competition scores
# This was previously done by manually editing a variable in competition.py, which is really stupid and error-prone
# Score calculation starts the day after transfers
# Transfers are on Wednesdays, so referrals for "this transfer" start on Thursday at midnight
# This approach uses a known Thursday after transfers as a constant, then uses the constant number of miliseconds per transfer to see how many transfers it has been
# We are making no effort to account for daylight savings time changes. The error that will cause is insignificant. Boohoo.
# We are also making no effort to account for the occasional difference in transfer lengths with 5 or 7 week transfers that occasionally come up due to President's meetings. Boohoo.

import time
import datetime

KNOWN_TRANSFER_THURSDAY = 1734566400 #Thursday, December 19, 2024 (Koloss-Head-Munching Day, for those who are educated)

SECONDS_PER_TRANSFER = 60 * 60 * 24 * 7 * 6 # 60 sec/min, 60 min/hr, 24 hr/day, 7 day/week, 6 week/transfer

def get_most_recent_transfer_time_stamp():
    current_time = int(time.time()) #current time in seconds
    print(current_time)
    current_displacement = current_time - KNOWN_TRANSFER_THURSDAY #current number of seconds since the constant transfer
    current_transfer_number = int(current_displacement / SECONDS_PER_TRANSFER) #gets the number of full transfers it has been
    result_time_stamp = KNOWN_TRANSFER_THURSDAY + (current_transfer_number * SECONDS_PER_TRANSFER) #calculates the time stamp of the most recent transfer thursday
    print(result_time_stamp)
    return result_time_stamp

# testing
print(datetime.datetime.fromtimestamp(get_most_recent_transfer_time_stamp()))