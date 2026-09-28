"""펨코 포텐 게시판(최신순) 상위 N개 게시물에서 베스트 댓글 상위 K개를 수집한다."""

import re
import sys
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from feed_store import merge_into_feed

BASE = "https://www.fmkorea.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
POST_LIMIT = 10
COMMENT_LIMIT = 4
DELAY_SEC = 5  # 펨코 요청 제한이 엄격해서 넉넉히 둔다

session = requests.Session()
session.headers.update(HEADERS)


def parse_date(text, now):
    """펨코 날짜 표기("10 분 전", "3 시간 전", "2026.09.27")를 ISO 시각으로 바꾼다."""
    text = text.strip()
    if m := re.match(r"(\d+)\s*초 전", text):
        return (now - timedelta(seconds=int(m[1]))).isoformat(timespec="seconds")
    if m := re.match(r"(\d+)\s*분 전", text):
        return (now - timedelta(minutes=int(m[1]))).isoformat(timespec="seconds")
    if m := re.match(r"(\d+)\s*시간 전", text):
        return (now - timedelta(hours=int(m[1]))).isoformat(timespec="seconds")
    if m := re.match(r"(\d{4})\.(\d{2})\.(\d{2})", text):
        return datetime(int(m[1]), int(m[2]), int(m[3])).isoformat(timespec="seconds")
    return None


class Blocked(Exception):
    pass


def fetch(url):
    res = session.get(url, timeout=10)
    # 430/432: 펨코 보안 시스템의 요청 제한. 우회하지 않고 즉시 중단한다.
    if res.status_code in (430, 432):
        raise Blocked(f"{res.status_code} 차단됨, Retry-After={res.headers.get('retry-after')}초")
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def get_posts():
    soup = fetch(f"{BASE}/best")
    posts = []
    for li in soup.select(".fm_best_widget li"):
        a = li.select_one("h3.title a")
        # 상단 화제순 위젯/광고는 제외하고 /best/<id> 형태의 최신순 목록만 사용
        if not a or not re.match(r"^/best/\d+", a["href"]):
            continue
        posts.append({
            "id": re.search(r"\d+", a["href"]).group(),
            "title": a.select_one(".ellipsis-target").get_text(strip=True),
            "url": BASE + a["href"],
        })
        if len(posts) >= POST_LIMIT:
            break
    return posts


def get_best_comments(post_url):
    soup = fetch(post_url)
    comments = {}
    for li in soup.select("li.comment_best"):
        cid = li["id"].split("_")[1]
        if cid in comments:
            continue
        content = li.select_one(".comment-content .xe_content")
        if content:
            # 답글 앞에 붙는 "원 댓글 작성자" 링크 제거
            for parent in content.select("a.findParent"):
                parent.decompose()
        votes = li.select_one(".voted_count")
        author = li.select_one(".meta .member_plate")
        date = li.select_one(".meta .date")
        comments[cid] = {
            "id": cid,
            "author": author.get_text(strip=True) if author else "",
            "content": content.get_text("\n", strip=True) if content else "",
            "votes": int(votes.get_text(strip=True) or 0) if votes else 0,
            "url": f"{post_url}/{cid}#comment_{cid}",
            "created_at": parse_date(date.get_text(), datetime.now()) if date else None,
        }
    ranked = sorted(comments.values(), key=lambda c: c["votes"], reverse=True)
    return ranked[:COMMENT_LIMIT]


def main():
    try:
        merge_into_feed(collect())
    except Blocked as e:
        sys.exit(f"[중단] {e}")


def collect():
    # 피드에는 제목 없이 "댓글 + 원본글 링크"만 노출한다
    feed = []
    now = datetime.now().isoformat(timespec="seconds")
    for post in get_posts():
        time.sleep(DELAY_SEC)
        try:
            comments = get_best_comments(post["url"])
        except requests.RequestException as e:
            print(f"[skip] {post['url']}: {e}", file=sys.stderr)
            continue
        for c in comments:
            feed.append({
                "id": f"fmkorea:{c['id']}",
                "source": "fmkorea",
                "content": c["content"],
                "votes": c["votes"],
                "created_at": c["created_at"],
                "post_url": post["url"],
                "collected_at": now,
            })
    return feed


if __name__ == "__main__":
    main()
