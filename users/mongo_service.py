from datetime import datetime
from common.mongo import get_users_collection
from common.mongo_utils import to_object_id

def create_user(email, password_hash, password_salt, phone=None, yandex_id=None, vk_id=None):
    users = get_users_collection()
    now = datetime.utcnow()

    document = {
        "email": email,
        "phone": phone,
        "password_hash": password_hash,
        "password_salt": password_salt,
        "yandex_id": yandex_id,
        "vk_id": vk_id,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }

    result = users.insert_one(document)
    document["_id"] = result.inserted_id
    return document

def find_user_by_email(email):
    users = get_users_collection()
    return users.find_one({
        "email": email,
        "deleted_at": None,
    })

def find_user_by_id(user_id):
    users = get_users_collection()
    object_id = to_object_id(user_id)

    if not object_id:
        return None

    return users.find_one({
        "_id": object_id,
        "deleted_at": None,
    })

def find_user_by_yandex_id(yandex_id):
    users = get_users_collection()
    return users.find_one({
        "yandex_id": yandex_id,
        "deleted_at": None,
    })

def update_user(user_id, update_data: dict):
    users = get_users_collection()
    object_id = to_object_id(user_id)

    if not object_id:
        return None

    update_data["updated_at"] = datetime.utcnow()

    users.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )

    return users.find_one({"_id": object_id})

def soft_delete_user(user_id):
    users = get_users_collection()
    object_id = to_object_id(user_id)

    if not object_id:
        return None

    now = datetime.utcnow()

    users.update_one(
        {"_id": object_id},
        {
            "$set": {
                "deleted_at": now,
                "updated_at": now,
            }
        }
    )