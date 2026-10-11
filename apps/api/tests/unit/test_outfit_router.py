import uuid

from sqlalchemy import String, cast, select, text

from app.db.models import Outfit, WardrobeItem


async def test_outfit_generate_endpoint_returns_candidates(auth_client, db_session):
    me = await auth_client.get("/api/v1/auth/me")
    user_id = str(uuid.UUID(me.json()["id"]))

    await db_session.execute(
        text(
            """
            INSERT INTO wardrobe_items (id, user_id, category, name, is_available, wear_count, created_at, updated_at)
            VALUES (:id1, :user_id, 'top', 'Top 1', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                   (:id2, :user_id, 'bottom', 'Bottom 1', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                   (:id3, :user_id, 'shoes', 'Shoes 1', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                   (:id4, :user_id, 'dress', 'Dress 1', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {
            "user_id": user_id,
            "id1": str(uuid.uuid4()),
            "id2": str(uuid.uuid4()),
            "id3": str(uuid.uuid4()),
            "id4": str(uuid.uuid4()),
        },
    )
    await db_session.commit()

    rows = (
        await db_session.execute(select(WardrobeItem).where(cast(WardrobeItem.user_id, String) == user_id))
    ).scalars().all()
    assert len(rows) == 4

    response = await auth_client.post(
        "/api/v1/outfits/generate",
        json={"occasion": ["casual"], "n": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "outfits" in payload
    assert len(payload["outfits"]) >= 1
    assert payload["outfits"][0]["skeleton"] in {"top_bottom", "dress"}
    assert "id" in payload["outfits"][0]
    assert (await db_session.execute(select(Outfit).where(Outfit.user_id == uuid.UUID(user_id)))).scalars().all()


async def test_outfit_generation_and_saved_routes_are_user_scoped(client, auth_client, db_session):
    me = await auth_client.get("/api/v1/auth/me")
    user_a_id = uuid.UUID(me.json()["id"])

    await db_session.execute(
        text(
            """
            INSERT INTO wardrobe_items (id, user_id, category, name, is_available, wear_count, created_at, updated_at)
            VALUES (:id1, :user_id, 'top', 'Top A', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                   (:id2, :user_id, 'bottom', 'Bottom A', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                   (:id3, :user_id, 'shoes', 'Shoes A', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {
            "user_id": str(user_a_id),
            "id1": str(uuid.uuid4()),
            "id2": str(uuid.uuid4()),
            "id3": str(uuid.uuid4()),
        },
    )
    await db_session.commit()

    user_a_token = auth_client.headers["Authorization"]

    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "outfit-b@example.com", "password": "SecurePassword123!"},
    )
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token_b}"

    user_b_generate = await client.post(
        "/api/v1/outfits/generate",
        json={"occasion": ["casual"], "n": 5},
    )
    assert user_b_generate.status_code == 200
    assert user_b_generate.json()["count"] == 0

    user_a_generate = await auth_client.post(
        "/api/v1/outfits/generate",
        json={"occasion": ["casual"], "n": 5},
    )
    assert user_a_generate.status_code == 200
    outfit_id = user_a_generate.json()["outfits"][0]["id"]
    user_b_save = await client.post(f"/api/v1/outfits/{outfit_id}/save", json={"saved": True})
    assert user_b_save.status_code == 404

    user_b_events = await client.post(f"/api/v1/outfits/{outfit_id}/events", json={"type": "impression"})
    assert user_b_events.status_code == 404

    user_b_variation = await client.post(f"/api/v1/outfits/{outfit_id}/variation", json={"variation_type": "more_formal"})
    assert user_b_variation.status_code == 404

    user_b_saved = await client.get("/api/v1/outfits/saved")
    assert user_b_saved.status_code == 200
    assert user_b_saved.json()["outfits"] == []

    auth_client.headers["Authorization"] = user_a_token
    user_a_save = await auth_client.post(f"/api/v1/outfits/{outfit_id}/save", json={"saved": True})
    assert user_a_save.status_code == 200

    user_a_saved = await auth_client.get("/api/v1/outfits/saved")
    assert user_a_saved.status_code == 200
    assert len(user_a_saved.json()["outfits"]) >= 1
