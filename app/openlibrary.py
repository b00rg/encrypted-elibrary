import requests

API_BASE = "https://openlibrary.org"


def search_books(query: str, limit: int = 10) -> list[dict]:
    resp = requests.get(
        f"{API_BASE}/search.json",
        params={"q": query, "limit": limit, "fields": "key,title,author_name,first_publish_year,cover_i"},
    )
    if resp.status_code == 200:
        return [
            {
                "work_id": doc["key"].replace("/works/", ""),
                "title": doc.get("title", "Unknown"),
                "author": ", ".join(doc.get("author_name", [])) or "Unknown",
                "year": doc.get("first_publish_year"),
                "cover_id": doc.get("cover_i"),
            }
            for doc in resp.json().get("docs", [])
            if "key" in doc
        ]
    return []


def get_book(work_id: str) -> dict | None:
    resp = requests.get(f"{API_BASE}/works/{work_id}.json")
    if resp.status_code == 200:
        data = resp.json()
        desc = data.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("value", "")
        return {
            "work_id": work_id,
            "title": data.get("title", "Unknown"),
            "description": desc,
        }
    return None
