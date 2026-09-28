"""유튜브: 지역별 인기 급상승 동영상 상위 N개에서 인기순 댓글 K개를 수집한다. (YouTube Data API v3)"""

import os
import re
import sys
import time
from datetime import datetime

import requests

from feed_store import merge_into_feed

API = "https://www.googleapis.com/youtube/v3"
REGION = os.environ.get("YOUTUBE_REGION", "KR")  # 해외 서비스 시 US, JP 등으로 변경
VIDEO_LIMIT = 10
COMMENT_LIMIT = 4
DELAY_SEC = 0.5


def load_api_key():
    """환경변수 또는 .env 파일에서 YOUTUBE_API_KEY를 읽는다."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                name, _, value = line.strip().partition("=")
                if name == "YOUTUBE_API_KEY":
                    return value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    sys.exit("YOUTUBE_API_KEY가 없습니다. .env 파일에 YOUTUBE_API_KEY=... 를 넣어주세요.")


def get_videos(key):
    res = requests.get(f"{API}/videos", params={
        "part": "id", "chart": "mostPopular", "regionCode": REGION,
        "maxResults": VIDEO_LIMIT, "key": key,
    }, timeout=10)
    res.raise_for_status()
    return [item["id"] for item in res.json().get("items", [])]


def get_top_comments(key, video_id):
    res = requests.get(f"{API}/commentThreads", params={
        "part": "snippet", "videoId": video_id, "order": "relevance",
        "maxResults": 20, "textFormat": "plainText", "key": key,
    }, timeout=10)
    if res.status_code == 403:  # 댓글이 꺼진 영상
        return []
    res.raise_for_status()
    comments = []
    for thread in res.json().get("items", []):
        comment = thread["snippet"]["topLevelComment"]
        author = comment["snippet"].get("authorChannelId", {}).get("value")
        # 채널 주인이 직접 단 댓글(고정 홍보 댓글 등)은 제외
        if author == thread["snippet"]["channelId"]:
            continue
        comments.append(comment)
    comments.sort(key=lambda c: c["snippet"]["likeCount"], reverse=True)
    return comments[:COMMENT_LIMIT]


def clean_text(text):
    # 스포일러 방지용 빈 줄 도배 등을 정리
    text = text.replace("\r\n", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def collect():
    key = load_api_key()
    feed = []
    now = datetime.now().isoformat(timespec="seconds")
    for video_id in get_videos(key):
        time.sleep(DELAY_SEC)
        try:
            comments = get_top_comments(key, video_id)
        except requests.RequestException as e:
            print(f"[skip] {video_id}: {e}", file=sys.stderr)
            continue
        print(f"{video_id}: 댓글 {len(comments)}개")
        for c in comments:
            feed.append({
                "id": f"youtube:{c['id']}",
                "source": "youtube",
                "content": clean_text(c["snippet"]["textDisplay"]),
                "votes": c["snippet"]["likeCount"],
                "created_at": c["snippet"]["publishedAt"],
                "post_url": f"https://www.youtube.com/watch?v={video_id}",
                "collected_at": now,
            })
    return feed


if __name__ == "__main__":
    merge_into_feed(collect())
