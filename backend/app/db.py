from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

invoice_col = db["invoices"]
