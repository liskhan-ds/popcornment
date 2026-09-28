#!/bin/bash
# 6시간마다 launchd가 실행: 세 소스를 수집하고 feed.json이 바뀌었으면 push해서 Vercel에 반영한다.
cd "$(dirname "$0")" || exit 1
PYTHON=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3

echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="

# 잠자기에서 깨어난 직후엔 네트워크가 아직 없을 수 있으므로 최대 5분 기다린다
for i in $(seq 1 30); do
  curl -s -o /dev/null --max-time 5 https://www.google.com && break
  echo "네트워크 대기 중... ($i)"
  sleep 10
done
# 한 소스가 실패(예: 펨코 차단)해도 나머지는 계속 진행
for src in naver_news youtube fmkorea; do
  echo "--- $src"
  "$PYTHON" "$src.py" || echo "[$src] 실패 (exit $?)"
done

if git diff --quiet -- feed.json; then
  echo "feed.json 변경 없음"
  exit 0
fi

git add feed.json
git commit -q -m "Auto-update feed ($(date '+%Y-%m-%d %H:%M'))"
GIT_TERMINAL_PROMPT=0 git push -q && echo "push 완료" || echo "[push] 실패"
