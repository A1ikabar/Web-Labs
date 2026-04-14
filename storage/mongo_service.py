import uuid
from datetime import datetime

from common.mongo import get_mongo_db

def get_files_collection():
    return get_mongo_db()["files"]

def create_file_metadata(user_id, original_name, object_key, size, mimetype, bucket):
    collection = get_files_collection()

    document = {
        "_id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "original_name": original_name,
        "object_key": object_key,
        "size": size,
        "mimetype": mimetype,
        "bucket": bucket,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "deleted_at": None,
    }

    collection.insert_one(document)
    return document

def find_active_file_by_id(file_id: str):
    collection = get_files_collection()
    return collection.find_one({
        "_id": file_id,
        "deleted_at": None,
    })

def find_active_file_by_id_for_user(file_id: str, user_id: str):
    collection = get_files_collection()
    return collection.find_one({
        "_id": file_id,
        "user_id": str(user_id),
        "deleted_at": None,
    })

def soft_delete_file(file_id: str):
    collection = get_files_collection()
    collection.update_one(
        {"_id": file_id, "deleted_at": None},
        {
            "$set": {
                "deleted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        }
    )