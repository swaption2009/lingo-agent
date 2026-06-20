import pytest
from fastapi.testclient import TestClient
from app.fast_api_app import app

client = TestClient(app)

def test_user_crud():
    # 1. Get all users
    response = client.get("/api/users")
    assert response.status_code == 200
    users = response.json()
    initial_count = len(users)

    # 2. Create user
    new_user = {
        "username": "test_user_crud",
        "target_language": "Japanese",
        "skill_level": "intermediate"
    }
    response = client.post("/api/users", json=new_user)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "test_user_crud"
    assert user_data["target_language"] == "Japanese"
    user_id = user_data["user_id"]

    # Verify count increased
    response = client.get("/api/users")
    assert len(response.json()) == initial_count + 1

    # 3. Update user
    updated_user = {
        "username": "test_user_crud_updated",
        "target_language": "Japanese",
        "skill_level": "advanced"
    }
    response = client.put(f"/api/users/{user_id}", json=updated_user)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "test_user_crud_updated"
    assert user_data["skill_level"] == "advanced"

    # 4. Delete user
    response = client.delete(f"/api/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify count is back to initial
    response = client.get("/api/users")
    assert len(response.json()) == initial_count


def test_media_crud():
    # 1. Get all media
    response = client.get("/api/media")
    assert response.status_code == 200
    media_list = response.json()
    initial_count = len(media_list)

    # 2. Create media content
    new_media = {
        "title": "Subaru Song",
        "artist_or_movie": "Subaru Band",
        "media_type": "song",
        "language": "Japanese",
        "difficulty": "beginner",
        "original_text": "Subaru lines\nAnother line",
        "translated_text": "Pleiades lines\nAnother translation",
        "pinyin_text": "subaru line\nanother line",
        "video_id": "subaru123"
    }
    response = client.post("/api/media", json=new_media)
    assert response.status_code == 200
    media_data = response.json()
    assert media_data["title"] == "Subaru Song"
    content_id = media_data["content_id"]

    # 3. Get media detail
    response = client.get(f"/api/media/{content_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["title"] == "Subaru Song"
    assert detail["original_text"] == "Subaru lines\nAnother line"

    # 4. Update media
    updated_media = new_media.copy()
    updated_media["title"] = "Subaru Song Edited"
    response = client.put(f"/api/media/{content_id}", json=updated_media)
    assert response.status_code == 200
    assert response.json()["title"] == "Subaru Song Edited"

    # 5. Delete media
    response = client.delete(f"/api/media/{content_id}")
    assert response.status_code == 200

    # Verify media detail returns 404
    response = client.get(f"/api/media/{content_id}")
    assert response.status_code == 404


def test_vocab_crud():
    # 1. Manually add vocabulary (which will create a card)
    vocab_data = {
        "user_id": 2, # chinese_learner
        "word": "明日",
        "translation": "Tomorrow",
        "context_sentence": "明日があるさ",
        "pinyin": "míng rì",
        "box_number": 1,
        "next_review_date": "2026-06-21"
    }
    response = client.post("/api/vocab/manual", json=vocab_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    vocab_id = res_data["vocab_id"]

    # 2. Update vocabulary card by ID
    updated_vocab = {
        "word": "明日 (Updated)",
        "translation": "Tomorrow (Updated)",
        "context_sentence": "明日があるさ",
        "pinyin": "míng rì",
        "box_number": 2,
        "next_review_date": "2026-06-23"
    }
    response = client.put(f"/api/vocab/id/{vocab_id}", json=updated_vocab)
    assert response.status_code == 200
    assert response.json()["word"] == "明日 (Updated)"
    assert response.json()["box_number"] == 2

    # 3. Delete vocabulary card by ID
    response = client.delete(f"/api/vocab/id/{vocab_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_quiz_history_crud():
    # 1. Create a quiz history entry
    # Note: user_id 2 and content_id 5 are seeded in the database.
    history_data = {
        "user_id": 2,
        "content_id": 5,
        "score": 3,
        "total_questions": 3,
        "notes": "Test quiz log",
        "date_taken": "2026-06-20T16:00:00Z"
    }
    response = client.post("/api/quiz_history", json=history_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["score"] == 3
    quiz_id = res_data["quiz_id"]

    # 2. Retrieve history for user
    response = client.get("/api/quiz_history?user_id=2")
    assert response.status_code == 200
    history_list = response.json()
    # Find our logged quiz
    logged_quiz = next((q for q in history_list if q["quiz_id"] == quiz_id), None)
    assert logged_quiz is not None
    assert logged_quiz["notes"] == "Test quiz log"
    assert logged_quiz["media_title"] == "甜蜜蜜 (Tian Mi Mi)" # Verify join with media_content table

    # 3. Update notes
    updated_notes = {
        "notes": "Updated notes for quiz",
        "score": 2,
        "total_questions": 3
      }
    response = client.put(f"/api/quiz_history/{quiz_id}", json=updated_notes)
    assert response.status_code == 200
    assert response.json()["notes"] == "Updated notes for quiz"

    # 4. Delete history entry
    response = client.delete(f"/api/quiz_history/{quiz_id}")
    assert response.status_code == 200

    # Verify deleted
    response = client.get("/api/quiz_history?user_id=2")
    history_list = response.json()
    assert not any(q["quiz_id"] == quiz_id for q in history_list)
