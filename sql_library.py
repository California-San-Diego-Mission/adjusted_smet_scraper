import mysql.connector
import dotenv
import os
from datetime import date
import re
from transfer_calculator import get_most_recent_transfer_date

# Example of the zone_report_history table:
# There is a column for the date, which has a UNIQUE constraint so we don't end up in circumstances of double-counting scores on the same day
# Each zone has a column, storing a bit. Zeros represent days where the slate was not blank, and ones represent blank slate days
# This library has functions that edit this based on reports and that count up how many days each zone has a blank slate for
# 
# mysql> select * from zone_report_history;
# +------------+------------+------------+------------+------------+------------+------------+------------+------------+
# | day        | z1         | z2         | z3         | z4         | z5         | z6         | z7         | z8         |
# +------------+------------+------------+------------+------------+------------+------------+------------+------------+
# | 2024-01-01 | 0x00       | 0x00       | 0x01       | 0x01       | 0x00       | 0x00       | 0x01       | 0x01       |
# | 2024-02-01 | 0x01       | 0x01       | 0x01       | 0x01       | 0x00       | 0x00       | 0x01       | 0x01       |
# | 2024-02-21 | 0x01       | 0x01       | 0x00       | 0x00       | 0x00       | 0x00       | 0x01       | 0x01       |
# | 2023-07-31 | 0x01       | 0x01       | 0x00       | 0x01       | 0x01       | 0x00       | 0x00       | 0x00       |
# +------------+------------+------------+------------+------------+------------+------------+------------+------------+
# 4 rows in set (0.01 sec)

dotenv.load_dotenv()

ALLOWED_ZONES = list(range(1, 9))
VALID_COLUMNS = {f"z{i}" for i in ALLOWED_ZONES}

def is_valid_date_format(date_string):
    pattern = r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
    return bool(re.match(pattern, date_string))

def zone_is_allowed(zone):
    if zone not in ALLOWED_ZONES:
        raise ValueError("Invalid zone")

def create_column_from_zone(zone):
    column = f"z{zone}"
    if column not in VALID_COLUMNS:
        raise ValueError("Unsafe column name")
    return column

def mark_today_zone_blank_slate(zone):
    mark_zone_blank_slate_on_day(zone, date.today().strftime("%Y-%m-%d"))

def valid_date(day):
    if not is_valid_date_format(day):
        raise ValueError("Invalid date format")

def mark_zone_blank_slate_on_day(zone, day):
    zone_is_allowed(zone)
    zone_column = create_column_from_zone(zone)
    valid_date(day)

    query = f"""
        INSERT INTO zone_report_history (day, {zone_column})
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE {zone_column} = %s;
    """

    try:
        with mysql.connector.connect(
            host='localhost',
            user=os.environ['MYSQL_USERNAME'],
            password=os.environ['MYSQL_PASSWORD'],
            database='holly',
        ) as mydb:
            with mydb.cursor() as cursor:
                cursor.execute(query, (day, 1, 1))
                mydb.commit()
    except mysql.connector.Error as err:
        print(f"Database error while inserting blank slate: {err}")

def count_blank_slates_in_zone_since_day(zone, day):
    zone_is_allowed(zone)
    zone_column = create_column_from_zone(zone)
    valid_date(day)

    query = f"""
        SELECT COUNT(*) FROM zone_report_history
        WHERE {zone_column} = 1 AND day >= %s;
    """

    try:
        with mysql.connector.connect(
            host='localhost',
            user=os.environ['MYSQL_USERNAME'],
            password=os.environ['MYSQL_PASSWORD'],
            database='holly',
        ) as mydb:
            with mydb.cursor() as cursor:
                cursor.execute(query, (day,))
                result = cursor.fetchone()
                return result[0] if result else 0
    except mysql.connector.Error as err:
        print(f"Database error while counting blank slates: {err}")
        return None

def count_blank_slates_in_zone_since_transfer_day(zone):
    return count_blank_slates_in_zone_since_day(zone, get_most_recent_transfer_date())

# Example usage
if __name__ == "__main__":
    for i in ALLOWED_ZONES:
        result = count_blank_slates_in_zone_since_transfer_day(i)
        print(f"Zone {i}: {result}")
