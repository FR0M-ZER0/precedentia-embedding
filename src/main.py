from src.db.db_init import init_qdrant, init_redis


if __name__ == "__main__":
    print("Inilializing Database")
    init_qdrant()
    init_redis()
