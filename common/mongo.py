from pymongo import MongoClient
from django.conf import settings

_client = None
_db = None

def get_mongo_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client

def get_mongo_db():
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[settings.MONGO_DB_NAME]
    return _db

def get_users_collection():
    return get_mongo_db()["users"]

def get_user_tokens_collection():
    return get_mongo_db()["user_tokens"]

def get_works_collection():
    return get_mongo_db()["works"]