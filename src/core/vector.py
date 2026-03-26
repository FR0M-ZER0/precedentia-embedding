from qdrant_client.models import PointStruct


def vectorize(model, key, value):
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

    print(f"Entry precedent:{point_id} converted to vector")
    return point_id, vector, payload


def vectorize_entries(redis_client, qdrant_client, qdrant_collection_name, model):
    cursor = 0
    points = []

    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match="precedent:*")

        for key in keys:
            value = redis_client.hgetall(key)

            point_id, vector, payload = vectorize(model, key, value)

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

    print("Successfully saved all data into Qdrant")
