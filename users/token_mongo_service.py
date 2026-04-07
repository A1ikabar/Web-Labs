from datetime import datetime
from common.mongo import get_user_tokens_collection
from common.mongo_utils import to_object_id

def create_user_token(user_id, token_hash, token_salt, token_type, expires_at, revoked=False):
    tokens = get_user_tokens_collection()

    document = {
        "user_id": user_id,
        "token_hash": token_hash,
        "token_salt": token_salt,
        "token_type": token_type,
        "expires_at": expires_at,
        "revoked": revoked,
        "created_at": datetime.utcnow(),
    }

    result = tokens.insert_one(document)
    document["_id"] = result.inserted_id
    return document

def find_active_tokens_by_user_and_type(user_id, token_type, now):
    tokens = get_user_tokens_collection()

    return list(tokens.find({
        "user_id": user_id,
        "token_type": token_type,
        "revoked": False,
        "expires_at": {"$gt": now},
    }))

def revoke_token_by_id(token_id):
    tokens = get_user_tokens_collection()
    object_id = to_object_id(token_id)

    if not object_id:
        return

    tokens.update_one(
        {"_id": object_id},
        {"$set": {"revoked": True}}
    )

def revoke_all_user_tokens(user_id):
    tokens = get_user_tokens_collection()

    tokens.update_many(
        {
            "user_id": user_id,
            "revoked": False,
        },
        {
            "$set": {"revoked": True}
        }
    )