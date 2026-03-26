from sentence_transformers import SentenceTransformer
from qdrant_client.models import PointStruct


def vectorize_entries(redis_client, qdrant_client, qdrant_collection_name):
    model = SentenceTransformer("all-MiniLM-L6-v2")

    cursor = 0
    points = []

    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match="precedent:*")

        for key in keys:
            value = redis_client.hgetall(key)

            text = f"{value.get('name')}. {value.get('description')}"
            vector = model.encode(text).tolist()

            payload = {
                "name": value.get("name"),
                "description": value.get("description"),
                "tribunal": value.get("tribunal"),
                "situation": value.get("situation"),
                "url": value.get("url"),
            }

            point_id = int(key.split(":")[1])

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        if cursor == 0:
            break

    qdrant_client.upsert(
        collection_name=qdrant_collection_name,
        points=points,
    )
