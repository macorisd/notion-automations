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

        total_hours = sum_times(worked_hours)

        return JSONResponse(
            status_code=200,
            content=total_hours,
            headers={"Accept-Encoding": "gzip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar la información: {str(e)}")