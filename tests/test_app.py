import copy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def client():
    with TestClient(app_module.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = copy.deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original_activities)


def activity_path(activity_name):
    return quote(activity_name, safe="")


def participant_path(email):
    return quote(email, safe="")


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data(client):
    response = client.get("/activities")

    assert response.status_code == 200
    activities = response.json()
    assert "Chess Club" in activities
    assert activities["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_registers_new_participant(client):
    email = "new-student@mergington.edu"

    response = client.post(
        f"/activities/{activity_path('Chess Club')}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for Chess Club"
    }
    assert email in app_module.activities["Chess Club"]["participants"]


def test_signup_for_unknown_activity_returns_not_found(client):
    email = "new-student@mergington.edu"

    response = client.post(
        f"/activities/{activity_path('Unknown Club')}/signup",
        params={"email": email},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert all(
        email not in activity["participants"]
        for activity in app_module.activities.values()
    )


def test_duplicate_signup_returns_bad_request_without_duplicate(client):
    email = "new-student@mergington.edu"
    signup_path = f"/activities/{activity_path('Chess Club')}/signup"

    first_response = client.post(signup_path, params={"email": email})
    duplicate_response = client.post(signup_path, params={"email": email})

    assert first_response.status_code == 200
    assert duplicate_response.status_code == 400
    assert duplicate_response.json() == {
        "detail": "Student already signed up for this activity"
    }
    assert app_module.activities["Chess Club"]["participants"].count(email) == 1


def test_unregister_removes_registered_participant(client):
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    response = client.delete(
        f"/activities/{activity_path(activity_name)}/participants/"
        f"{participant_path(email)}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    assert email not in app_module.activities[activity_name]["participants"]


def test_unregister_from_unknown_activity_returns_not_found(client):
    response = client.delete(
        f"/activities/{activity_path('Unknown Club')}/participants/"
        f"{participant_path('student@mergington.edu')}"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_missing_participant_returns_not_found(client):
    activity_name = "Chess Club"
    participants_before = list(app_module.activities[activity_name]["participants"])

    response = client.delete(
        f"/activities/{activity_path(activity_name)}/participants/"
        f"{participant_path('missing@mergington.edu')}"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }
    assert app_module.activities[activity_name]["participants"] == participants_before
