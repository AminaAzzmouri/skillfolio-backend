from rest_framework.test import APIClient

def test_platforms_basic_list():
    c = APIClient()
    r = c.get("/api/platforms/")
    assert r.status_code == 200
    data = r.json()
    assert "platforms" in data and len(data["platforms"]) >= 5
    assert all("search_url" in p and "home" in p for p in data["platforms"])

def test_platforms_query_is_encoded():
    c = APIClient()
    q = "machine learning"
    r = c.get("/api/platforms/", {"q": q})
    assert r.status_code == 200
    p = r.json()["platforms"][0]
    assert "machine+learning" in p["search_url"] or "machine%20learning" in p["search_url"]
