# main.py
import os
from typing import List
from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
import motor.motor_asyncio
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

API_KEY = os.getenv("API_KEY", "")
MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("DB_NAME", "roblox")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "players")

if not API_KEY or not MONGO_URI:
    raise RuntimeError("MONGO_URI e API_KEY devem estar configurados nas variáveis de ambiente")

app = FastAPI(title="Roblox Player API")

# CORS (opcional, não afeta Roblox HttpService que usa server-side)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

class PlayerIn(BaseModel):
    name: str

class PlayerOut(BaseModel):
    name: str

async def check_key(x_api_key: str | None):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

@app.post("/players", response_model=List[PlayerOut])
async def add_player(payload: PlayerIn, x_api_key: str | None = Header(None)):
    """
    Recebe { "name": "<player.Name>" }.
    Faz upsert e retorna a lista completa de players salvos.
    """
    await check_key(x_api_key)

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name vazio")

    # Upsert: registra o nome (pode adicionar timestamp)
    await collection.update_one(
        {"name": name},
        {"$set": {"name": name}, "$setOnInsert": {"createdAt":  __import__("datetime").datetime.utcnow()}},
        upsert=True
    )

    # Retorna todos os players (apenas campo name)
    cursor = collection.find({}, {"_id": 0, "name": 1})
    docs = await cursor.to_list(length=10000)  # limite seguro
    return docs

@app.get("/players", response_model=List[PlayerOut])
async def get_players(x_api_key: str | None = Header(None)):
    """Retorna todos os players salvos."""
    await check_key(x_api_key)
    cursor = collection.find({}, {"_id": 0, "name": 1})
    docs = await cursor.to_list(length=10000)
    return docs

@app.get("/")
async def root():
    return {"ok": True, "info": "Roblox Player API"}
