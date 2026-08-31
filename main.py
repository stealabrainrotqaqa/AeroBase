from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient
import os

app = FastAPI()

# Render ortamındaki MONGO_URL değişkenini okur
MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["my_firebase"]
collection = db["store"]

@app.get("/ping")
async def ping():
    return {"status": "alive"}

# --- READ (GET) ---
@app.get("/{path:path}")
async def read_data(path: str):
    clean_key = path.replace(".json", "").strip("/")
    if not clean_key:
        cursor = collection.find({}, {"_id": 0})
        results = {}
        async for doc in cursor:
            results[doc["_key"]] = doc["value"]
        return results
    
    doc = await collection.find_one({"_key": clean_key}, {"_id": 0})
    if doc:
        return doc.get("value")
    return None

# --- WRITE (POST / PUT / PATCH) ---
@app.api_route("/{path:path}", methods=["POST", "PUT", "PATCH"])
async def write_data(path: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    clean_key = path.replace(".json", "").strip("/")
    
    await collection.update_one(
        {"_key": clean_key},
        {"$set": {"_key": clean_key, "value": body}},
        upsert=True
    )
    return body

# --- DELETE ---
@app.delete("/{path:path}")
async def delete_data(path: str):
    clean_key = path.replace(".json", "").strip("/")
    await collection.delete_one({"_key": clean_key})
    return {"status": "ok"}