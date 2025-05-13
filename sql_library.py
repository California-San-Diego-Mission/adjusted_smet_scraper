import mysql.connector
import dotenv
import os
from datetime import date
import re

dotenv.load_dotenv()

mydb = mysql.connector.connect(
    host='localhost',
    user=os.environ['MYSQL_USERNAME'],
    password=os.environ['MYSQL_PASSWORD'],
    database='holly',
)

cursor = mydb.cursor()

def is_valid_date_format(date_string):
    pattern = r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
    return bool(re.match(pattern, date_string))

def zone_is_allowed(zone):
    allowed_zones = [i for i in range(1, 9)]  # Example allowed zones: z1 to z8
    if zone not in allowed_zones:
        raise ValueError("Invalid zone")

def create_column_from_zone(zone):
    return f"z{zone}"

def count_zone_blank_slates(zone):
    zone_is_allowed(zone)
    column = create_column_from_zone(zone)
    query = f"SELECT count(*) FROM zone_report_history WHERE {column} = 1;"
    cursor.execute(query)
    return cursor.fetchall()[0][0]

def mark_today_zone_blank_slate(zone):
    mark_zone_blank_slate_on_day(zone, date.today().strftime("%Y-%m-%d"))

def valid_date(day):
    if not is_valid_date_format(day):
        raise ValueError("Invalid date")

def mark_zone_blank_slate_on_day(zone, day):
    #expects an integer zone number and a string yyyy-mm-dd date
    zone_is_allowed(zone)
    zone_column = create_column_from_zone(zone)
    valid_date(day)
    query = f"""
        INSERT INTO zone_report_history (day, {zone_column})
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE {zone_column} = %s;
        """
    cursor.execute(query, (day, 1, 1))
    mydb.commit()

def count_blank_slates_in_zone_since_day(zone, day):
    #expects an integer zone number and a string yyyy-mm-dd date
    zone_is_allowed()
    zone_column = create_column_from_zone(zone)
    valid_date(day)
    query = f"select count(*) from zone_report_history where {zone_column} = 1 AND day >= %s;"
    cursor.execute(query, (day))
    

mark_zone_blank_slate_on_day(5, "2023-07-31")
# mark_today_zone_blank_slate(1)