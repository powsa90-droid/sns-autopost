"""queue-ig/ 폴더의 예약 글 중 발행 시각이 지난 글을 인스타그램 캐러셀로 올린다.

순서: 카드 3장 만들기(scripts/ig_cards.py) → cards/{slug}/에 커밋·푸시
      → 공개 주소(raw.githubusercontent.com)로 인스타 API에 올리기 → posted-ig/로 옮기기

글 파일 형식 (queue-ig/{YYYY-MM-DD}-{HHMM}-{site}-{slug}.json):
{
  "publish_at": "2026-11-27T15:00:00+09:00",
  "site": "howmuch" | "saenghwal",
  "slug": "...",
  "link": "사이트 글 주소",
  "cover": {...}, "list": {...}, "cta": {...},   # 카드 글 (ig_cards.py 참고)
  "caption": "인스타 본문 (2,200자 이하)"
}

환경 변수
  INSTAGRAM_ACCESS_TOKEN  발행 토큰 (IG로 시작하면 graph.instagram.com, 아니면 graph.facebook.com)
  INSTAGRAM_USER_ID       graph.facebook.com 토큰일 때만 필요 (인스타 프로페셔널 계정 ID)
  RENDER_ONLY=1           카드만 만들어 커밋하고 발행은 하지 않음 (미리보기용, 발행 시각 무시)
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import ig_cards  # noqa: E402

MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "1"))
CAPTION_LIMIT = 2200
REPO = os.environ.get("GITHUB_REPOSITORY", "powsa90-droid/sns-autopost")


def api_base(token):
    return "https://graph.instagram.com/v23.0" if token.startswith("IG") else "https://graph.facebook.com/v23.0"


def request(method, url, params, token):
    params = {**params, "access_token": token}
    data = None
    if method == "GET":
        url = f"{url}?{urllib.parse.urlencode(params)}"
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        path = url.split("?")[0].rsplit("/", 2)[-2:]
        raise RuntimeError(f"{'/'.join(path)} 실패 ({e.code}): {e.read().decode()[:500]}")


def user_id(base, token):
    if os.environ.get("INSTAGRAM_USER_ID"):
        return os.environ["INSTAGRAM_USER_ID"]
    if "graph.instagram.com" not in base:
        raise RuntimeError("graph.facebook.com 토큰은 INSTAGRAM_USER_ID가 필요합니다")
    me = request("GET", f"{base}/me", {"fields": "user_id,username"}, token)
    print(f"계정: @{me.get('username')} ({me.get('user_id')})")
    return me["user_id"]


def wait_ready(base, cid, token, label):
    for _ in range(30):
        st = request("GET", f"{base}/{cid}", {"fields": "status_code"}, token).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"{label} 처리 실패: {st}")
        time.sleep(4)
    raise RuntimeError(f"{label} 처리 시간 초과")


def wait_public(urls):
    for url in urls:
        for _ in range(30):
            try:
                with urllib.request.urlopen(url, timeout=20) as r:
                    if r.status == 200:
                        break
            except Exception:
                pass
            time.sleep(3)
        else:
            raise RuntimeError(f"이미지 주소가 열리지 않습니다: {url}")


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def render_and_push(item):
    out = os.path.join("cards", item["slug"])
    ig_cards.render(item, out)
    git("add", out)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        git("commit", "-m", f"cards: {item['slug']}")
        git("pull", "--rebase", "--autostash")
        git("push")
    sha = git("rev-parse", "HEAD")
    return [f"https://raw.githubusercontent.com/{REPO}/{sha}/{out}/{i}.jpg" for i in (1, 2, 3)]


def publish(item, urls, token):
    base = api_base(token)
    uid = user_id(base, token)
    children = []
    for i, url in enumerate(urls, 1):
        cid = request("POST", f"{base}/{uid}/media", {"image_url": url, "is_carousel_item": "true"}, token)["id"]
        wait_ready(base, cid, token, f"{i}번 카드")
        children.append(cid)
    carousel = request(
        "POST", f"{base}/{uid}/media",
        {"media_type": "CAROUSEL", "children": ",".join(children), "caption": item.get("caption", "")}, token,
    )["id"]
    wait_ready(base, carousel, token, "캐러셀")
    return request("POST", f"{base}/{uid}/media_publish", {"creation_id": carousel}, token)["id"]


def due_items(now, render_only):
    items = []
    for path in sorted(glob.glob("queue-ig/*.json")):
        with open(path, encoding="utf-8") as f:
            item = json.load(f)
        at = datetime.fromisoformat(item["publish_at"])
        if at.tzinfo is None:
            raise RuntimeError(f"{path}: publish_at에 시간대(+09:00)가 없습니다")
        if len(item.get("caption", "")) > CAPTION_LIMIT:
            raise RuntimeError(f"{path}: 본문이 {len(item['caption'])}자입니다 ({CAPTION_LIMIT}자 이하)")
        ig_cards.validate(item)
        if render_only or at <= now:
            items.append((path, item))
    return items


def main():
    render_only = os.environ.get("RENDER_ONLY") == "1"
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not render_only and not token:
        print("INSTAGRAM_ACCESS_TOKEN이 아직 없어 발행을 건너뜁니다 (Secrets에 넣으면 다음 실행부터 발행)")
        return
    now = datetime.now(timezone.utc)
    items = due_items(now, render_only)
    if not items:
        print("발행할 글 없음")
        return
    os.makedirs("posted-ig", exist_ok=True)
    for path, item in items[: (len(items) if render_only else MAX_PER_RUN)]:
        urls = render_and_push(item)
        print("카드:", *urls, sep="\n  ")
        if render_only:
            continue
        wait_public(urls)
        media_id = publish(item, urls, token)
        item["posted_id"] = media_id
        item["posted_at"] = datetime.now(timezone.utc).isoformat()
        item["image_urls"] = urls
        dest = os.path.join("posted-ig", os.path.basename(path))
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
        os.remove(path)
        print(f"발행 완료: {item['slug']} → {media_id}")


if __name__ == "__main__":
    main()
