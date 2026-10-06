"""
Phase 1 Community System Test Suite
====================================
Tests the full functionality, database design, security, authorization,
deterministic trending calculation, and API endpoints for SeoulMate Community.
"""

import sys
from pathlib import Path

# Add project root and backend to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, event, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# SQLite DDL shims for PostgreSQL types
compiles(ARRAY, "sqlite")(lambda element, compiler, **kw: "TEXT")
compiles(UUID, "sqlite")(lambda element, compiler, **kw: "TEXT")
compiles(JSONB, "sqlite")(lambda element, compiler, **kw: "TEXT")

from database.base import Base
from database.models import (
    Profile,
    Drama,
    CommunityPost,
    CommunityComment,
    CommunityReaction,
)
from fastapi import FastAPI
from community import community_router
from database.session import get_db
from auth import require_user, optional_user, AuthenticatedUser

app = FastAPI()
app.include_router(community_router)


from sqlalchemy.pool import StaticPool

# Setup In-Memory Test Database
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable Foreign Key enforcement in SQLite and register gen_random_uuid
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
    dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)

# Create only the required tables
Base.metadata.create_all(
    test_engine,
    tables=[
        Profile.__table__,
        Drama.__table__,
        CommunityPost.__table__,
        CommunityComment.__table__,
        CommunityReaction.__table__,
    ],
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


USER_1_ID = uuid.uuid4()
USER_2_ID = uuid.uuid4()

USER_1 = AuthenticatedUser(
    id=USER_1_ID,
    email="user1@example.com",
    role="authenticated",
)

USER_2 = AuthenticatedUser(
    id=USER_2_ID,
    email="user2@example.com",
    role="authenticated",
)

current_mock_user: AuthenticatedUser | None = None


def override_require_user():
    if current_mock_user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    return current_mock_user


def override_optional_user():
    return current_mock_user


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[require_user] = override_require_user
app.dependency_overrides[optional_user] = override_optional_user

client = TestClient(app)


def setup_module():
    """Seed test database with profiles and dramas."""
    db: Session = TestingSessionLocal()
    try:
        # Create Profiles
        p1 = Profile(
            id=USER_1_ID,
            display_name="HallyuHero",
            avatar_path="avatars/user1.jpg",
        )
        p2 = Profile(
            id=USER_2_ID,
            display_name="KdramaFanatic",
            avatar_path="avatars/user2.jpg",
        )
        db.add_all([p1, p2])

        # Create Drama
        d1 = Drama(
            id=101,
            source_key="crash-landing-on-you",
            catalog_index=1,
            slug="crash-landing-on-you",
            title="Crash Landing on You",
            image_id="cloy-img",
            poster_thumbnail_key="posters/cloy.jpg",
            rating_value=Decimal("9.4"),
        )
        d2 = Drama(
            id=102,
            source_key="vincenzo",
            catalog_index=2,
            slug="vincenzo",
            title="Vincenzo",
            image_id="vincenzo-img",
            poster_thumbnail_key="posters/vincenzo.jpg",
            rating_value=Decimal("8.9"),
        )
        db.add_all([d1, d2])
        db.commit()
    finally:
        db.close()


def test_anonymous_reading_and_rejection():
    """Verify public visitors can read but cannot mutate."""
    global current_mock_user
    current_mock_user = None

    # Public reading
    res = client.get("/community/posts")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "posts" in data

    # Trending read
    res_trending = client.get("/community/trending")
    assert res_trending.status_code == 200
    assert isinstance(res_trending.json(), list)

    # Anonymous mutations fail with 401
    assert client.post("/community/posts", json={"title": "Test", "body": "Test", "post_type": "discussion"}).status_code == 401
    assert client.patch(f"/community/posts/{uuid.uuid4()}", json={"title": "Update"}).status_code == 401
    assert client.delete(f"/community/posts/{uuid.uuid4()}").status_code == 401
    assert client.post(f"/community/posts/{uuid.uuid4()}/comments", json={"body": "Nice"}).status_code == 401
    assert client.put(f"/community/posts/{uuid.uuid4()}/like").status_code == 401
    assert client.delete(f"/community/posts/{uuid.uuid4()}/like").status_code == 401
    print("✅ Anonymous read succeeds and unauthenticated mutations return 401.")


def test_post_lifecycle_and_ownership():
    """Verify post creation, retrieval, ownership edit, and cross-user rejection."""
    global current_mock_user
    current_mock_user = USER_1

    # 1. Create Post
    payload = {
        "title": "What did you think of the Ending?",
        "body": "The ending was heartwarming but felt slightly rushed in the final minutes.",
        "post_type": "review",
        "drama_id": 101,
        "contains_spoilers": True,
        "rating": 9,
    }
    create_res = client.post("/community/posts", json=payload)
    assert create_res.status_code == 201, create_res.text
    post_data = create_res.json()
    post_id = post_data["id"]
    assert post_data["title"] == payload["title"]
    assert post_data["post_type"] == "review"
    assert post_data["contains_spoilers"] is True
    assert post_data["rating"] == 9
    assert post_data["drama"]["title"] == "Crash Landing on You"
    assert post_data["author"]["display_name"] == "HallyuHero"

    # 2. Get Post by ID
    get_res = client.get(f"/community/posts/{post_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == post_id

    # 3. Cross-user edit attempt (USER_2 tries to edit USER_1's post)
    current_mock_user = USER_2
    hacked_res = client.patch(f"/community/posts/{post_id}", json={"title": "Hacked Title"})
    assert hacked_res.status_code == 403, "Non-owner should not be able to edit post"

    # 4. Cross-user delete attempt
    hacked_del = client.delete(f"/community/posts/{post_id}")
    assert hacked_del.status_code == 403, "Non-owner should not be able to delete post"

    # 5. Author edit succeeds
    current_mock_user = USER_1
    edit_res = client.patch(f"/community/posts/{post_id}", json={"title": "Updated Ending Discussion", "rating": 10})
    assert edit_res.status_code == 200
    assert edit_res.json()["title"] == "Updated Ending Discussion"
    assert edit_res.json()["rating"] == 10

    print("✅ Post creation, detail fetch, author edit, and cross-user 403 guard passed.")
    return post_id


def test_comments_lifecycle_and_ownership():
    """Verify comment creation, oldest-first ordering, owner edit/delete, and cross-user 403."""
    global current_mock_user
    post_id = test_post_lifecycle_and_ownership()

    # User 2 comments
    current_mock_user = USER_2
    comment_res1 = client.post(
        f"/community/posts/{post_id}/comments",
        json={"body": "First comment: I totally agree with this point!", "contains_spoilers": False},
    )
    assert comment_res1.status_code == 201
    c1_id = comment_res1.json()["id"]

    # User 1 replies
    current_mock_user = USER_1
    comment_res2 = client.post(
        f"/community/posts/{post_id}/comments",
        json={"body": "Second comment: Thanks for chiming in!", "contains_spoilers": False},
    )
    assert comment_res2.status_code == 201
    c2_id = comment_res2.json()["id"]

    # Verify oldest-first order
    comments_get = client.get(f"/community/posts/{post_id}/comments")
    assert comments_get.status_code == 200
    comments = comments_get.json()
    assert len(comments) >= 2
    assert comments[0]["id"] == c1_id
    assert comments[1]["id"] == c2_id

    # Cross-user edit attempt: User 1 tries to edit User 2's comment
    current_mock_user = USER_1
    hack_c_res = client.patch(f"/community/comments/{c1_id}", json={"body": "Changed by user 1"})
    assert hack_c_res.status_code == 403

    # Owner edit succeeds: User 2 edits own comment
    current_mock_user = USER_2
    edit_c_res = client.patch(f"/community/comments/{c1_id}", json={"body": "First comment updated!"})
    assert edit_c_res.status_code == 200
    assert edit_c_res.json()["body"] == "First comment updated!"

    # Cross-user delete attempt
    current_mock_user = USER_1
    assert client.delete(f"/community/comments/{c1_id}").status_code == 403

    # Owner delete succeeds
    current_mock_user = USER_2
    del_c_res = client.delete(f"/community/comments/{c1_id}")
    assert del_c_res.status_code == 204

    # Verify count decremented
    updated_post = client.get(f"/community/posts/{post_id}").json()
    assert updated_post["comment_count"] == 1

    print("✅ Comment creation, oldest-first ordering, author edit/delete, and 403 guard passed.")


def test_reactions_like_and_unlike():
    """Verify liking, duplicate prevention (idempotency), and unliking."""
    global current_mock_user
    post_id = test_post_lifecycle_and_ownership()

    # User 1 likes
    current_mock_user = USER_1
    like_res1 = client.put(f"/community/posts/{post_id}/like")
    assert like_res1.status_code == 200
    assert like_res1.json()["liked"] is True
    assert like_res1.json()["like_count"] == 1

    # Duplicate like attempt by User 1 (idempotent)
    dup_res = client.put(f"/community/posts/{post_id}/like")
    assert dup_res.status_code == 200
    assert dup_res.json()["like_count"] == 1

    # User 2 likes
    current_mock_user = USER_2
    like_res2 = client.put(f"/community/posts/{post_id}/like")
    assert like_res2.status_code == 200
    assert like_res2.json()["like_count"] == 2

    # User 1 unlikes
    current_mock_user = USER_1
    unlike_res = client.delete(f"/community/posts/{post_id}/like")
    assert unlike_res.status_code == 200
    assert unlike_res.json()["liked"] is False
    assert unlike_res.json()["like_count"] == 1

    print("✅ Reaction like, duplicate prevention, and unlike completed successfully.")


def test_trending_deterministic_calculation():
    """Verify trending formula: likes + comments * 2 + recency bonus."""
    global current_mock_user
    current_mock_user = USER_1

    # Create 4 distinct posts to check homepage trending requirement
    post_ids = []
    for i in range(4):
        res = client.post(
            "/community/posts",
            json={
                "title": f"Trending Test Post #{i+1}",
                "body": f"Discussion body for trending algorithm test #{i+1}",
                "post_type": "discussion",
                "contains_spoilers": False,
            },
        )
        assert res.status_code == 201
        post_ids.append(res.json()["id"])

    # Give post 0 extra engagement: 1 like + 2 comments (Score boost: 1 + 2*2 = 5)
    current_mock_user = USER_2
    client.put(f"/community/posts/{post_ids[0]}/like")
    client.post(f"/community/posts/{post_ids[0]}/comments", json={"body": "Comment 1"})
    client.post(f"/community/posts/{post_ids[0]}/comments", json={"body": "Comment 2"})

    # Check trending endpoint
    trending_res = client.get("/community/trending")
    assert trending_res.status_code == 200
    items = trending_res.json()
    assert len(items) == 4, f"Trending should return 4 items, got {len(items)}"
    assert items[0]["id"] == post_ids[0], "Most engaged post should rank first in trending"
    print("✅ Trending endpoint returns exactly 4 items and orders by score correctly.")


def test_cascades_and_foreign_keys():
    """Verify drama deletion sets drama_id to NULL, and user deletion cascades community data."""
    db: Session = TestingSessionLocal()
    try:
        # Create temp user and post
        temp_user_id = uuid.uuid4()
        temp_profile = Profile(id=temp_user_id, display_name="TempUser")
        db.add(temp_profile)
        db.commit()

        # Create temp drama
        temp_drama = Drama(
            id=999,
            source_key="temp-drama",
            catalog_index=999,
            slug="temp-drama",
            title="Temporary Drama",
            image_id="temp-img",
        )
        db.add(temp_drama)
        db.commit()

        # Create post linked to temp user and temp drama
        post = CommunityPost(
            id=uuid.uuid4(),
            user_id=temp_user_id,
            drama_id=999,
            post_type="discussion",
            title="Drama Cascade Test",
            body="Testing drama deletion cascade to null",
        )
        db.add(post)
        db.commit()
        p_id = post.id

        # 1. Test Drama Deletion -> sets drama_id to NULL
        db.delete(temp_drama)
        db.commit()
        db.expire_all()

        reloaded_post = db.get(CommunityPost, p_id)
        assert reloaded_post is not None
        assert reloaded_post.drama_id is None, "Drama deletion must set drama_id to NULL"

        # 2. Test Comment and Reaction Cascade on Post / User deletion
        comment = CommunityComment(
            id=uuid.uuid4(),
            post_id=p_id,
            user_id=temp_user_id,
            body="Temp comment",
        )
        reaction = CommunityReaction(
            post_id=p_id,
            user_id=temp_user_id,
            reaction_type="like",
        )
        db.add_all([comment, reaction])
        db.commit()

        comment_id = comment.id

        # Delete Temp Profile -> cascades and deletes post, comment, and reaction
        db.delete(temp_profile)
        db.commit()
        db.expire_all()

        assert db.get(CommunityPost, p_id) is None, "User deletion must cascade to community_posts"
        assert db.get(CommunityComment, comment_id) is None, "User deletion must cascade to community_comments"
        assert db.get(CommunityReaction, (p_id, temp_user_id, "like")) is None, "User deletion must cascade to community_reactions"

        print("✅ Database foreign key cascades (SET NULL on drama, CASCADE on user) verified.")
    finally:
        db.close()


if __name__ == "__main__":
    setup_module()
    test_anonymous_reading_and_rejection()
    test_post_lifecycle_and_ownership()
    test_comments_lifecycle_and_ownership()
    test_reactions_like_and_unlike()
    test_trending_deterministic_calculation()
    test_cascades_and_foreign_keys()
    print("\n🎉 ALL 6 COMMUNITY TEST SUITES PASSED FLAWLESSLY! 🎉\n")
