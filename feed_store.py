"""여러 소스의 수집 결과를 feed.json 하나에 누적 저장한다."""

import json

FEED_PATH = "feed.json"


def load_feed():
    try:
        with open(FEED_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def merge_into_feed(new_items):
    """이미 있는 댓글은 추천수를 갱신(작성 시각이 없으면 채움)하고, 새 댓글은 추가한다. 추가된 개수를 반환."""
    feed = {item["id"]: item for item in load_feed()}
    added = 0
    for item in new_items:
        if item["id"] in feed:
            feed[item["id"]]["votes"] = item["votes"]
            feed[item["id"]].setdefault("created_at", item.get("created_at"))
        else:
            feed[item["id"]] = item
            added += 1

    with open(FEED_PATH, "w", encoding="utf-8") as f:
        json.dump(list(feed.values()), f, ensure_ascii=False, indent=2)

    print(f"새 댓글 {added}개 추가, 총 {len(feed)}개")
    return added
