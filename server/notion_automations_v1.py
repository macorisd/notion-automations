from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Query, Request, Path
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from bson.objectid import ObjectId
from db_connection import DatabaseConnection
from api_utils import APIUtils

import os
from notion_client import Client
from dotenv import load_dotenv
import re

router = APIRouter()

endpoint_name = "maco"
version = "v1"

load_dotenv()

NOTION_TOKEN = os.getenv("MACO_NOTION_TOKEN")
DATABASE_ID = os.getenv("MACO_MAPIR_DB_ID")

notion = Client(auth=NOTION_TOKEN)

@router.get("/" + endpoint_name + "/mapir/worked-hours", tags=["[Maco] MAPIR Endpoints"])
async def get_mapir_worked_hours(request: Request):
    REQUIRED_MAPIR_HOURS = 420

    def sum_times(time_list):
        """Sum a list of time strings (e.g., '4h 30min') and return total hours, minutes and formatted string."""
        total_minutes = 0

        for time in time_list:
            hours = re.search(r'(\d+)h', time)  # Extract hours
            minutes = re.search(r'(\d+)min', time)  # Extract minutes
            
            h = int(hours.group(1)) if hours else 0
            m = int(minutes.group(1)) if minutes else 0
            
            total_minutes += h * 60 + m
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        formatted_time = f"{hours}h {minutes}min"
        remaining_hours = REQUIRED_MAPIR_HOURS - total_minutes // 60
        remaining_minutes = 60 - total_minutes % 60

        return hours, minutes, formatted_time, remaining_hours, remaining_minutes
    
    APIUtils.check_accept_json(request)

    try:
        response = notion.databases.query(database_id=DATABASE_ID)

        worked_hours = []

        for item in response["results"]:
            properties = item["properties"]
            if "Horas trabajadas" in properties:  # Ensure the field exists           
                rich_text_field = properties["Horas trabajadas"]["rich_text"]
                if rich_text_field:
                    worked_hours.append(rich_text_field[0]["text"]["content"])

        total_hours, total_minutes, worked_hours_str, remaining_hours, remaining_minutes = sum_times(worked_hours)

        # Prepare the JSON response
        result = {
            "worked_hours_str": worked_hours_str,
            "worked_hours": total_hours,
            "worked_minutes": total_minutes,
            "remaining_hours": remaining_hours,
            "remaining_minutes": remaining_minutes,
        }

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(result),
            headers={"Accept-Encoding": "gzip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching information: {str(e)}")

@router.post(f"/{endpoint_name}/mapir/fill-worked-hours", tags=["[Maco] MAPIR Endpoints"])
async def fill_worked_hours(request: Request):
    """
    Endpoint that updates empty 'Horas trabajadas' fields by calculating the difference 
    between 'Hora de entrada' and 'Hora de salida'.
    """

    APIUtils.check_accept_json(request)
    
    try:
        response = notion.databases.query(database_id=DATABASE_ID)

        updated_entries = []
        for item in response["results"]:
            properties = item["properties"]
            page_id = item["id"]

            # Get current values
            horas_trabajadas = properties["Horas trabajadas"]["rich_text"]
            hora_entrada = properties["Hora de entrada"]["select"]
            hora_salida = properties["Hora de salida"]["select"]

            # Only process if "Horas trabajadas" is empty and both times exist
            if not horas_trabajadas and hora_entrada and hora_salida:
                start_time = hora_entrada["name"]  # Example: "9:25"
                end_time = hora_salida["name"]  # Example: "14:10"

                # Convert to datetime for subtraction
                fmt = "%H:%M"
                t1 = datetime.strptime(start_time, fmt)
                t2 = datetime.strptime(end_time, fmt)

                # Calculate time difference
                diff = t2 - t1
                total_minutes = diff.seconds // 60
                hours = total_minutes // 60
                minutes = total_minutes % 60

                # Format the time worked
                worked_time_str = f"{hours}h {minutes}min"

                # Update Notion with the calculated time
                notion.pages.update(
                    page_id=page_id,
                    properties={
                        "Horas trabajadas": {
                            "rich_text": [
                                {"type": "text", "text": {"content": worked_time_str}}
                            ]
                        }
                    }
                )

                updated_entries.append({"page_id": page_id, "worked_hours": worked_time_str})

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({"updated_entries": updated_entries}),
            headers={"Accept-Encoding": "gzip"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating information: {str(e)}")