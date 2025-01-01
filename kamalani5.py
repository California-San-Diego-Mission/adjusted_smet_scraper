import mysql.connector
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List
from chirch import ChurchClient
import os
import csv


def most_recent_monday(base_date: datetime) -> datetime:
    # Calculate the most recent monday (backtrack if today isn't monday)
    days_since_monday = (base_date.weekday() + 7) % 7
    return base_date - timedelta(days=days_since_monday)

def generate_week_intervals(start_date: datetime, num_weeks: int) -> List[tuple]:
    weeks = []
    for _ in range(num_weeks):
        end_date = start_date + timedelta(days=7)
        weeks.append((start_date, end_date))
        start_date -= timedelta(days=7)
    return list(reversed(weeks))  # Start with oldest week


# Fetch contact times for a list of GUIDs
def fetch_contact_times_from_db(guid_list: List[str]) -> dict:
    connection = mysql.connector.connect(
        host='localhost',
        user=os.getenv('MYSQL_USERNAME'),
        password=os.getenv('MYSQL_PASSWORD'),
        database='holly',
    )

    cursor = connection.cursor(dictionary=True)
    
    # SQL query to fetch total contact times for the given GUIDs
    query = """
    SELECT guid, SUM(contact_time) AS total_contact_time
    FROM people
    WHERE guid IN (%s)
    GROUP BY guid
    """
    
    guid_placeholder = ",".join(["%s"] * len(guid_list))
    query = query % guid_placeholder
    
    cursor.execute(query, guid_list)
    results = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return {row['guid']: row['total_contact_time'] for row in results}

# Calculate average weekly contact times
def calculate_weekly_average_contact_time(num_weeks: int = 6) -> dict:
    # Determine week intervals
    today = datetime.now()
    last_monday = most_recent_monday(today)
    week_intervals = generate_week_intervals(last_monday, num_weeks)
    
    # Fetch the list of people
    church_client = ChurchClient()
    people = church_client.get_cached_people_list()

    # Map GUIDs to zones and areas, and also track contact dates
    guid_zone_area_date_map = defaultdict(lambda: defaultdict(list))
    for person in people:
        contact_date = person.referral_assigned_date  # Use ChurchClient data for the date
        guid_zone_area_date_map[person.zone.name][person.area_name].append((person.guid, contact_date))
    
    # Fetch contact times from the database
    all_guids = [person.guid for person in people]
    contact_times = fetch_contact_times_from_db(all_guids)
    
    # Initialize weekly data
    weekly_data = defaultdict(lambda: defaultdict(lambda: [0] * num_weeks))
    
    # Process each zone and area
    for zone, areas in guid_zone_area_date_map.items():
        for area, guid_date_pairs in areas.items():
            for guid, contact_date in guid_date_pairs:
                if guid in contact_times:
                    # Determine which week the contact date falls into
                    for week_index, (start_date, end_date) in enumerate(week_intervals):
                        if start_date <= contact_date < end_date:
                            weekly_data[zone][area][week_index] += contact_times[guid]
                            break

    return weekly_data, week_intervals

# Export weekly data to CSV
def export_weekly_data_to_csv(data: dict, week_intervals: List[tuple]) -> None:
    filename = "weekly_zone_reports.csv"
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Write header
        week_headers = [f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}" for start, end in week_intervals]
        writer.writerow(['Zone', 'Area'] + week_headers)
        
        # Write data rows
        for zone, areas in data.items():
            for area, week_data in areas.items():
                writer.writerow([zone, area] + [f"{avg:.2f}" for avg in week_data])
    
    print(f"Weekly results exported to {filename}")

# Main execution
weekly_data, week_intervals = calculate_weekly_average_contact_time()
export_weekly_data_to_csv(weekly_data, week_intervals)

