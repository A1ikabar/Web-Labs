from bson import ObjectId
from datetime import datetime

def to_object_id(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None

def serialize_mongo_id(document: dict):
    if not document:
        return document

    document = dict(document)

    if "_id" in document:
        document["id"] = str(document["_id"])
        del document["_id"]

    return document

def serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value