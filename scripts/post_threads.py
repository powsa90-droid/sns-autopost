"""queue/ 폴더의 예약 글 중 발행 시각이 지난 글을 스레드에 올린다.

글 파일 형식 (queue/아무이름.json):
{
  "text": "본문 (500자 이하)",
  "link": "https://howmuchnote.com/...",   # 선택. 링크 미리보기 카드로 붙는다
  "publish_at": "2026-11-25T09:00:00+09:00"
}
발행에 성공하면 결과를 덧붙여 posted/ 폴더로 옮긴다.
"""
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://graph.threads.net/v1.0"
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "1"))  # 한 번 실행에 올릴 최대 글 수
TEXT_LIMIT = 500


def call(path, params, token):
    data = urllib.parse.urlencode({**params, "access_token": token}).encode()
    req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{path} 실패 ({e.code}): {e.read().decode()[:500]}")


def publish(item, token):
    params = {"media_type": "TEXT", "text": item["text"]}
    if item.get("link"):
        params["link_attachment"] = item["link"]
    container = call("me/threads", params, token)
    time.sleep(10)  # 컨테이너 처리 대기
    result = call("me/threads_publish", {"creation_id": container["id"]}, token)
    return result["id"]


def load_due(now):
    due = []
    for path in sorted(glob.glob("queue/*.json")):
        with open(path, encoding="utf-8") as f:
            item = json.load(f)
        when = datetime.fromisoformat(item["publish_at"])
        if when.tzinfo is None:
            raise ValueError(f"{path}: publish_at에 시간대(+09:00)를 넣어주세요")
        if when <= now:
            due.append((when, path, item))
    due.sort(key=lambda x: x[0])
    return due


def main():
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        sys.exit("THREADS_ACCESS_TOKEN 시크릿이 없습니다")

    now = datetime.now(timezone.utc)
    due = load_due(now)
    if not due:
        print("발행할 글 없음")
        return

    os.makedirs("posted", exist_ok=True)
    for _, path, item in due[:MAX_PER_RUN]:
        if len(item["text"]) > TEXT_LIMIT:
            sys.exit(f"{path}: 본문이 {len(item['text'])}자입니다 (최대 {TEXT_LIMIT}자)")
        post_id = publish(item, token)
        item["posted_id"] = post_id
        item["posted_at"] = now.isoformat()
        with open(os.path.join("posted", os.path.basename(path)), "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
        os.remove(path)
        print(f"발행 완료: {path} -> {post_id}")


if __name__ == "__main__":
    main()
