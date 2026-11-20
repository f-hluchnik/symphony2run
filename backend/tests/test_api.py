from tests.conftest import ADMIN


def search(client, minutes=20, headers=None, **params):
    response = client.get(
        "/api/search/", params={"run_duration": minutes, **params}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_search_returns_five_works_within_five_percent(client):
    works = search(client)
    assert len(works) == 5
    assert all(19 * 60_000 <= w["duration_ms"] <= 21 * 60_000 for w in works)


def test_search_draws_from_the_whole_duration_window(client):
    # Regression: suggestions used to come only from the 100 shortest matches.
    seen = {w["duration_ms"] for _ in range(40) for w in search(client)}
    assert max(seen) > 20 * 60_000 + 40_000  # the top of the window is reachable
    assert len(seen) > 100


def test_composer_and_verified_filters(client):
    only_b = search(client, composers=["Composer B"])
    assert [w["work"] for w in only_b] == ["Twenty minutes"]

    assert search(client, verified_only=True) == []
    work_id = only_b[0]["id"]
    client.patch(f"/api/works/{work_id}/verified", params={"value": True}, headers=ADMIN)
    assert [w["id"] for w in search(client, verified_only=True)] == [work_id]


def test_excluded_works_are_hidden_except_from_the_admin(client):
    work_id = search(client, composers=["Composer B"])[0]["id"]
    response = client.patch(f"/api/works/{work_id}/excluded", params={"value": True}, headers=ADMIN)
    assert response.json() == {"id": work_id, "excluded": True}

    assert search(client, composers=["Composer B"]) == []
    for_admin = search(client, composers=["Composer B"], headers=ADMIN)
    assert [(w["id"], w["excluded"]) for w in for_admin] == [(work_id, True)]

    # ... so the admin can undo it.
    client.patch(f"/api/works/{work_id}/excluded", params={"value": False}, headers=ADMIN)
    assert len(search(client, composers=["Composer B"])) == 1


def test_admin_endpoints_need_the_secret(client):
    assert client.get("/api/admin/verify").status_code == 403
    assert client.get("/api/admin/verify", headers={"x-admin-secret": "wrong"}).status_code == 403
    assert client.get("/api/admin/verify", headers=ADMIN).json() == {"ok": True}
    assert client.patch("/api/works/1/verified", params={"value": True}).status_code == 403
    assert (
        client.patch("/api/works/999/verified", params={"value": True}, headers=ADMIN).status_code
        == 404
    )


def test_invalid_duration_is_rejected(client):
    for minutes in (0, -5, 100_000):
        assert client.get("/api/search/", params={"run_duration": minutes}).status_code == 422


def test_composers_health_and_frontend(client):
    assert client.get("/api/composers/").json() == ["Composer A", "Composer B"]
    assert client.get("/api/health").json() == {"status": "ok"}
    assert "<title>Symphony2Run</title>" in client.get("/").text
