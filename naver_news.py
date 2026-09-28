"""네이버 뉴스: 지정 언론사별 '많이 본 뉴스' 1위 기사에서 공감순 상위 댓글 K개를 수집한다."""

import json
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from feed_store import merge_into_feed

RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
COMMENT_API = "https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
# 네이버 언론사 코드(oid)
PRESSES = {
    "001": "연합뉴스", "052": "YTN", "056": "KBS", "214": "MBC", "055": "SBS",
    "437": "JTBC", "023": "조선일보", "025": "중앙일보", "020": "동아일보",
    "469": "한국일보", "015": "한국경제", "009": "매일경제", "057": "MBN",
    "032": "경향신문", "028": "한겨레",
}
COMMENT_LIMIT = 4
DELAY_SEC = 1

session = requests.Session()
session.headers.update(HEADERS)


def get_articles():
    """랭킹 페이지 한 번으로 각 언론사의 1위 기사를 뽑는다."""
    res = session.get(RANKING_URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.content.decode("euc-kr", "replace"), "html.parser")
    articles = []
    for box in soup.select(".rankingnews_box"):
        a = box.select_one("a.list_title")
        m = a and re.search(r"/article/(\d+)/(\d+)", a["href"])
        if m and m.group(1) in PRESSES:
            oid, aid = m.groups()
            articles.append({"oid": oid, "aid": aid, "url": f"https://n.news.naver.com/article/{oid}/{aid}"})
    return articles


def get_best_comments(article):
    params = {
        "ticket": "news", "templateId": "default_society", "pool": "cbox5",
        "lang": "ko", "country": "KR",
        "objectId": f"news{article['oid']},{article['aid']}",
        "pageSize": 10, "indexSize": 10, "listType": "OBJECT", "pageType": "more",
        "page": 1, "sort": "FAVORITE",
    }
    # 댓글 API는 기사 페이지에서 호출된 것처럼 Referer가 있어야 응답한다
    res = session.get(COMMENT_API, params=params, headers={"Referer": article["url"]}, timeout=10)
    res.raise_for_status()
    text = res.text
    data = json.loads(text[text.index("(") + 1:text.rindex(")")])
    if not data.get("success"):
        return []
    comments = [
        c for c in data["result"].get("commentList", [])
        if c.get("contents") and not c.get("deleted") and not c.get("blind")
    ]
    comments.sort(key=lambda c: c["sympathyCount"], reverse=True)
    return comments[:COMMENT_LIMIT]


def collect():
    feed = []
    now = datetime.now().isoformat(timespec="seconds")
    for article in get_articles():
        time.sleep(DELAY_SEC)
        try:
            comments = get_best_comments(article)
        except (requests.RequestException, ValueError) as e:
            print(f"[skip] {article['url']}: {e}", file=sys.stderr)
            continue
        print(f"{PRESSES[article['oid']]}: 댓글 {len(comments)}개")
        for c in comments:
            feed.append({
                "id": f"naver:{c['commentNo']}",
                "source": "naver",
                "content": c["contents"],
                "votes": c["sympathyCount"],
                "created_at": datetime.strptime(c["regTime"], "%Y-%m-%dT%H:%M:%S%z").isoformat(),
                "post_url": article["url"],
                "collected_at": now,
            })
    return feed


if __name__ == "__main__":
    merge_into_feed(collect())
