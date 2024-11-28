import mysql.connector
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List
from chirch import ChurchClient
import os
import csv

# Function to fetch contact times for the list of GUIDs from MySQL
def fetch_contact_times_from_db(guid_list: List[str]) -> dict:
    connection = mysql.connector.connect(
        host='localhost',
        user=os.getenv('MYSQL_USERNAME'),
        password=os.getenv('MYSQL_PASSWORD'),
        database='holly',
    )

    cursor = connection.cursor(dictionary=True)
    
    # SQL query to fetch the contact times for the given GUIDs
    query = """
    SELECT guid, SUM(contact_time) AS total_contact_time
    FROM people
    WHERE guid IN (%s) 
    GROUP BY guid
    """
    
    # Create a comma-separated list of GUIDs to use in the query
    guid_placeholder = ",".join(["%s"] * len(guid_list))
    query = query % guid_placeholder
    
    # Execute query
    cursor.execute(query, guid_list)
    
    # Fetch results
    results = cursor.fetchall()
    
    # Close the connection
    cursor.close()
    connection.close()
    
    # Convert results to a dictionary with GUID as the key
    contact_times = {row['guid']: row['total_contact_time'] for row in results}
    
    return contact_times

# Function to calculate average contact time by area and zone
def calculate_average_contact_time_by_area_and_zone() -> dict:
    # Get the current date and date for 6 weeks ago
    six_weeks_ago = datetime.now() - timedelta(days=7)

    # Fetch the list of people
    church_client = ChurchClient()
    people = church_client.get_cached_people_list()

    # Filter people by referral assigned date within the last 6 weeks
    filtered_people = [
        person for person in people if person.referral_assigned_date >= six_weeks_ago
    ]

    # Extract GUIDs from the filtered list
    guid_list = [person.guid for person in filtered_people]

    # Fetch contact times from the database for these GUIDs
    contact_times = fetch_contact_times_from_db(guid_list)

    # Group the people by zone and area_name, and calculate the total contact time and count per area
    zone_area_data = defaultdict(lambda: defaultdict(lambda: {"total_time": 0, "count": 0}))

    for person in filtered_people:
        if person.guid in contact_times:
            zone_area_data[person.zone.name][person.area_name]["total_time"] += contact_times[person.guid]
            zone_area_data[person.zone.name][person.area_name]["count"] += 1

    # Calculate average contact time per area, within each zone
    average_contact_times_by_zone_area = {
        zone: {
            area: data["total_time"] / data["count"] if data["count"] > 0 else 0
            for area, data in areas.items()
        }
        for zone, areas in zone_area_data.items()
    }

    return average_contact_times_by_zone_area

# Function to export the data to separate CSV files by zone
def export_to_csv_by_zone(data: dict) -> None:
    # For each zone, export the area data to a separate CSV file
    for zone, areas in data.items():
        # Define the filename for each zone
        filename = f"zone_reports/{zone}.csv"
        
        # Write the data to the CSV file
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write the header
            writer.writerow(['Area', 'Average Contact Time (minutes)'])
            
            # Write the data rows for each area in the zone
            for area, avg_time in areas.items():
                writer.writerow([area, f"{avg_time:.2f}"])
        
        print(f"Results for Zone '{zone}' exported to {filename}")

# Main execution: Calculate average contact times and export to separate CSVs
average_contact_times = calculate_average_contact_time_by_area_and_zone()

# Export the results to CSVs by zone
export_to_csv_by_zone(average_contact_times)

