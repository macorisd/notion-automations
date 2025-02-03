import os
from notion_client import Client
from dotenv import load_dotenv
import re

def sum_times(time_list):
    """Sum a list of time strings (e.g., '4h 30min') and return total hours and minutes."""
    total_minutes = 0

    for time in time_list:
        hours = re.search(r'(\d+)h', time)  # Extract hours
        minutes = re.search(r'(\d+)min', time)  # Extract minutes
        
        h = int(hours.group(1)) if hours else 0
        m = int(minutes.group(1)) if minutes else 0
        
        total_minutes += h * 60 + m
    
    total_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

    return f"{total_hours}h {remaining_minutes}min"

def main():
    """Fetch data from Notion and calculate total worked hours."""
    load_dotenv()

    NOTION_API_KEY = os.getenv("SECRET_TOKEN")
    DATABASE_ID = os.getenv("DB_ID")

    notion = Client(auth=NOTION_API_KEY)

    response = notion.databases.query(database_id=DATABASE_ID)

    worked_hours = []

    for item in response["results"]:
        properties = item["properties"]
        if "Horas trabajadas" in properties:  # Ensure the field exists           
            rich_text_field = properties["Horas trabajadas"]["rich_text"]
            if rich_text_field:
                worked_hours.append(rich_text_field[0]["text"]["content"])

    print(sum_times(worked_hours))

if __name__ == "__main__":
    main()
