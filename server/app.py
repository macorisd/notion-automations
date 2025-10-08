from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware

from notion_automations_v1 import router as notion_automations_v1_router

app = FastAPI()
app.title = "Notion Automations API"
app.version = "1.0.0"
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lista de orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

app.include_router(notion_automations_v1_router, prefix="/api/v1")
