from common.mongo import get_users_collection, get_user_tokens_collection, get_works_collection

def create_indexes():
    users = get_users_collection()
    tokens = get_user_tokens_collection()
    works = get_works_collection()

    # Уникальный email
    users.create_index("email", unique=True)

    # Индексы токенов
    tokens.create_index("user_id")
    tokens.create_index("token_type")
    tokens.create_index("expires_at")

    # Индексы работ
    works.create_index("owner_id")
    works.create_index("created_at")