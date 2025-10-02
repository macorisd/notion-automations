from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
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

    def calculate_time_difference(start_time, end_time):
        """Calculate time difference between two time strings (e.g., '9:25' and '14:10')."""
        if not start_time or not end_time:
            return 0
        
        fmt = "%H:%M"
        t1 = datetime.strptime(start_time, fmt)
        t2 = datetime.strptime(end_time, fmt)
        
        # Handle case where end time is next day (e.g., night shift)
        if t2 < t1:
            from datetime import timedelta
            t2 += timedelta(days=1)
        
        diff = t2 - t1
        return diff.seconds // 60  # Return minutes
    
    APIUtils.check_accept_json(request)

    try:
        response = notion.databases.query(database_id=DATABASE_ID)

        total_worked_minutes = 0

        for item in response["results"]:
            properties = item["properties"]
            
            # Get the new time columns
            inicio = properties.get("Inicio", {}).get("select")
            fin = properties.get("Fin", {}).get("select")
            inicio_2 = properties.get("Inicio 2", {}).get("select")
            fin_2 = properties.get("Fin 2", {}).get("select")
            
            inicio_time = inicio["name"] if inicio else None
            fin_time = fin["name"] if fin else None
            inicio_2_time = inicio_2["name"] if inicio_2 else None
            fin_2_time = fin_2["name"] if fin_2 else None
            
            # Case 1: All 4 fields filled - day concluded with lunch break
            if inicio_time and fin_time and inicio_2_time and fin_2_time:
                morning_minutes = calculate_time_difference(inicio_time, fin_time)
                afternoon_minutes = calculate_time_difference(inicio_2_time, fin_2_time)
                day_total_minutes = morning_minutes + afternoon_minutes
                total_worked_minutes += day_total_minutes
                
            # Case 2: Only first 2 fields filled - day concluded without breaks
            elif inicio_time and fin_time and not inicio_2_time and not fin_2_time:
                day_total_minutes = calculate_time_difference(inicio_time, fin_time)
                total_worked_minutes += day_total_minutes
                
            # Case 3: Currently working (only Inicio or no fields filled)
            # Don't add to total as the day is not concluded

        # Convert total minutes to hours and minutes
        total_hours = total_worked_minutes // 60
        total_minutes = total_worked_minutes % 60
        worked_hours_str = f"{total_hours}h {total_minutes}min"

        # Prepare the JSON response
        result = {
            "worked_hours_str": worked_hours_str,
            "worked_hours": total_hours,
            "worked_minutes": total_minutes,
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
    Endpoint that updates empty worked hours fields by calculating the difference 
    between the time columns: Inicio, Fin, Inicio 2, Fin 2.
    """

    def calculate_time_difference(start_time, end_time):
        """Calculate time difference between two time strings (e.g., '9:25' and '14:10')."""
        if not start_time or not end_time:
            return 0
        
        fmt = "%H:%M"
        t1 = datetime.strptime(start_time, fmt)
        t2 = datetime.strptime(end_time, fmt)
        
        # Handle case where end time is next day (e.g., night shift)
        if t2 < t1:
            from datetime import timedelta
            t2 += timedelta(days=1)
        
        diff = t2 - t1
        return diff.seconds // 60  # Return minutes

    APIUtils.check_accept_json(request)
    
    try:
        response = notion.databases.query(database_id=DATABASE_ID)

        updated_entries = []
        for item in response["results"]:
            properties = item["properties"]
            page_id = item["id"]

            # Get current values for new columns
            horas_trabajadas = properties.get("Horas trabajadas", {}).get("rich_text", [])
            inicio = properties.get("Inicio", {}).get("select")
            fin = properties.get("Fin", {}).get("select")
            inicio_2 = properties.get("Inicio 2", {}).get("select")
            fin_2 = properties.get("Fin 2", {}).get("select")
            
            inicio_time = inicio["name"] if inicio else None
            fin_time = fin["name"] if fin else None
            inicio_2_time = inicio_2["name"] if inicio_2 else None
            fin_2_time = fin_2["name"] if fin_2 else None
            
            # Only process if "Horas trabajadas" is empty and we have concluded work data
            should_update = not horas_trabajadas and (
                # Case 1: All 4 fields filled (day with lunch break)
                (inicio_time and fin_time and inicio_2_time and fin_2_time) or
                # Case 2: Only first 2 fields filled (day without breaks)
                (inicio_time and fin_time and not inicio_2_time and not fin_2_time)
            )
            
            if should_update:
                total_minutes = 0
                
                # Case 1: Day with lunch break
                if inicio_time and fin_time and inicio_2_time and fin_2_time:
                    morning_minutes = calculate_time_difference(inicio_time, fin_time)
                    afternoon_minutes = calculate_time_difference(inicio_2_time, fin_2_time)
                    total_minutes = morning_minutes + afternoon_minutes
                    
                # Case 2: Day without breaks
                elif inicio_time and fin_time:
                    total_minutes = calculate_time_difference(inicio_time, fin_time)
                
                # Convert to hours and minutes
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

                updated_entries.append({
                    "page_id": page_id, 
                    "worked_hours": worked_time_str,
                    "inicio": inicio_time,
                    "fin": fin_time,
                    "inicio_2": inicio_2_time,
                    "fin_2": fin_2_time
                })

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({"updated_entries": updated_entries}),
            headers={"Accept-Encoding": "gzip"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating information: {str(e)}")