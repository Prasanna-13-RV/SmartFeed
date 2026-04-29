from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from app.config import settings


client = MongoClient(
    settings.mongo_uri,
    serverSelectionTimeoutMS=5000,   # fail fast so startup is quick
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    tls=True,
)
db = client[settings.mongo_db_name]
posts_collection = db["news_posts"]


def init_db_indexes() -> None:
    posts_collection.create_index([("rss_id", ASCENDING)], unique=True)


def is_mongo_reachable() -> bool:
    try:
        client.admin.command("ping")
        return True
    except PyMongoError:
        return False
