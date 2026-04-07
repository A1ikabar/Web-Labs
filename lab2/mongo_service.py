from datetime import datetime
from common.mongo import get_works_collection
from common.mongo_utils import to_object_id

def create_work(title, description, author_name, owner_id):
    works = get_works_collection()
    now = datetime.utcnow()

    document = {
        "title": title,
        "description": description,
        "author_name": author_name,
        "owner_id": owner_id,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }

    result = works.insert_one(document)
    document["_id"] = result.inserted_id
    return document

def find_active_work_by_id(work_id):
    works = get_works_collection()
    object_id = to_object_id(work_id)

    if not object_id:
        return None

    return works.find_one({
        "_id": object_id,
        "deleted_at": None,
    })

def get_works_paginated(page, limit):
    works = get_works_collection()

    query = {"deleted_at": None}
    total = works.count_documents(query)
    skip = (page - 1) * limit

    items = list(
        works.find(query)
        .sort("created_at", 1)
        .skip(skip)
        .limit(limit)
    )

    return total, items

def update_work(work_id, update_data: dict):
    works = get_works_collection()
    object_id = to_object_id(work_id)

    if not object_id:
        return None

    update_data["updated_at"] = datetime.utcnow()

    works.update_one(
        {
            "_id": object_id,
            "deleted_at": None,
        },
        {
            "$set": update_data
        }
    )

    return works.find_one({
        "_id": object_id,
        "deleted_at": None,
    })

def soft_delete_work(work_id):
    works = get_works_collection()
    object_id = to_object_id(work_id)

    if not object_id:
        return None

    now = datetime.utcnow()

    works.update_one(
        {
            "_id": object_id,
            "deleted_at": None,
        },
        {
            "$set": {
                "deleted_at": now,
                "updated_at": now,
            }
        }
    )