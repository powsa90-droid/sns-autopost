"""인스타 카드뉴스 3장(표지 · 목록 · 마지막 장)을 JPEG로 만든다.

표지는 4가지 스타일(stack 크림 · sticker 노랑 · note 민트 · night 남색)과 캐릭터 표정 4가지
(smile · wow · wink · sweat)를 최근 글과 겹치지 않게 무작위로 고른다. cover.style / cover.mood를
적으면 그대로 쓴다. cover.lines에서 줄 전체를 *별표*로 감싸면 그 줄이 가장 크게 나온다.

글 파일(queue-ig/*.json)의 cover / list / cta 칸을 받아 1080x1350 이미지를 만든다.
글자 안의 *별표*로 감싼 부분은 강조색으로 칠한다.

로컬 미리보기:  python scripts/ig_cards.py queue-ig/파일.json out_dir
"""
import glob
import html
import json
import os
import random
import re
import sys

W, H = 1080, 1350
SITE_DOMAIN = {"howmuch": "howmuchnote.com", "saenghwal": "saenghwal-note.com"}
HANDLE = "@hatifu2026"

FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Black+Han+Sans&family=Gaegu:wght@700&family=Noto+Sans+KR:wght@700;900&display=block">'
)

CSS = """
*{box-sizing:border-box}
body{margin:0;width:1080px;height:1350px;overflow:hidden;background:#FFF8EE;color:#111;
 font-family:'Gaegu','Noto Sans KR',sans-serif;font-weight:700}
.page{width:1080px;height:1350px;padding:64px;display:flex;flex-direction:column;
 justify-content:space-between;align-items:center;text-align:center}
.han{font-family:'Black Han Sans','Noto Sans KR',sans-serif;font-weight:400}
.badge{font-size:50px;padding:6px 34px;background:#BFF0DA;border:4px solid #111;border-radius:999px;white-space:nowrap}
.big{display:flex;flex-direction:column;gap:22px;align-items:center;width:100%}
.ol{-webkit-text-stroke:14px #111;paint-order:stroke fill;line-height:1.1;white-space:nowrap}
.row{display:flex;align-items:center;gap:28px;max-width:100%}
.bubble{font-size:60px;line-height:1.28;padding:22px 38px;background:#fff;border:6px solid #111;
 border-radius:36px;box-shadow:8px 8px 0 #111}
.hl{color:#D9301A}
.mk{background:#FFD400;padding:0 12px;white-space:nowrap}
.foot{font-size:44px;white-space:nowrap}
.sub{font-size:50px;white-space:nowrap}
.lpage{width:1080px;height:1350px;padding:60px 64px;display:flex;flex-direction:column;gap:34px}
.ltitle{align-self:center;font-size:80px;line-height:1.2;text-align:center;background:#FFD400;
 padding:16px 44px;border:6px solid #111;border-radius:24px;box-shadow:8px 8px 0 #111}
.lbox{display:flex;flex-direction:column;gap:14px;line-height:1.3;padding:34px 40px;background:#fff;
 border:4px solid #111;border-radius:24px;text-align:left}
.lbox small{font-size:.7em;color:#555}
.lfoot{margin-top:auto;display:flex;align-items:center;gap:24px;text-align:left}
.note{font-size:32px;color:#555;white-space:nowrap}
/* 표지: 스타일 4종 공통 */
.cv{width:1080px;height:1350px;padding:60px 60px 54px;display:flex;flex-direction:column;position:relative;overflow:hidden}
.cv .title{flex:1;display:flex;flex-direction:column;justify-content:center;gap:10px;width:100%;min-height:0}
.cv .tl{width:max-content;line-height:1.12;white-space:nowrap}
.cv .cfoot{font-size:40px;white-space:nowrap}
.tail{position:absolute;width:34px;height:34px;background:#fff;border:6px solid #111;border-top:none;border-right:none}
/* stack: 크림 배경, 가운데 정렬, 테두리 글씨 */
.s-stack{background:#FFF8EE;align-items:center;text-align:center}
.s-stack .title{align-items:center}
.s-stack .tl{color:#fff;-webkit-text-stroke:14px #111;paint-order:stroke fill}
.s-stack .tl.key,.s-stack .tl .k{color:#FFD400}
/* sticker: 노란 배경, 검은 글씨 + 검은 띠 키워드, 아래에서 올려다보는 캐릭터 */
.s-sticker{background:#FFD400}
.s-sticker .badge{align-self:flex-start;background:#fff;transform:rotate(-3deg);box-shadow:6px 6px 0 #111}
.s-sticker .title{align-items:flex-start}
.s-sticker .tl{color:#111}
.s-sticker .tl.key{background:#111;color:#fff;padding:0 .12em;transform:rotate(-2deg);border-radius:14px;margin:8px 0}
.s-sticker .tl .k{color:#fff;-webkit-text-stroke:12px #111;paint-order:stroke fill}
/* note: 민트 배경, 캐릭터가 위에서 말 걸고 형광펜 키워드 */
.s-note{background:#D5F5E6}
.s-note .title{align-items:flex-start}
.s-note .tl{color:#111}
.s-note .tl.key,.s-note .tl .k{color:#E8341C;background:linear-gradient(transparent 50%,#FFE24A 50%,#FFE24A 86%,transparent 86%)}
.s-note .answer{background:#fff;border:6px solid #111;border-radius:30px;box-shadow:8px 8px 0 #111;padding:20px 36px;font-size:62px;line-height:1.25;text-align:center}
/* night: 남색 배경, 흰 글씨 + 노란 키워드, 만세 캐릭터 */
.s-night{background:#232A57;color:#fff;align-items:center;text-align:center}
.s-night .title{align-items:center}
.s-night .tl{color:#fff}
.s-night .tl.key,.s-night .tl .k{color:#FFD400}
.s-night .badge{background:#FFD400;color:#111}
.s-night .cfoot{color:#C9CFF2}
"""

CHAR_BOX = """<path d="M60 80 L20 40 L120 30 L150 70 Z" fill="#F2C48D"/><path d="M240 80 L280 40 L180 30 L150 70 Z" fill="#F2C48D"/>
<rect x="60" y="80" width="180" height="140" rx="10" fill="#F7D9A8"/><path d="M150 80 V120"/>"""
CHEEKS = '<circle cx="98" cy="165" r="12" fill="#FF9E8C" stroke="none"/><circle cx="202" cy="165" r="12" fill="#FF9E8C" stroke="none"/>'
FACES = {
    "smile": '<circle cx="115" cy="140" r="7" fill="#111"/><circle cx="185" cy="140" r="7" fill="#111"/><path d="M128 165 Q150 188 172 165"/>',
    "wow": '<circle cx="115" cy="142" r="10" fill="#111"/><circle cx="185" cy="142" r="10" fill="#111"/>'
           '<path d="M100 118 L124 112 M200 118 L176 112"/><ellipse cx="150" cy="180" rx="13" ry="17" fill="#111"/>',
    "wink": '<path d="M104 142 Q115 130 126 142"/><circle cx="185" cy="140" r="7" fill="#111"/><path d="M126 163 Q150 192 174 163 Z" fill="#111"/>',
    "sweat": '<circle cx="115" cy="142" r="7" fill="#111"/><circle cx="185" cy="142" r="7" fill="#111"/>'
             '<path d="M130 176 q7 -9 14 0 t14 0 t14 0"/><path d="M232 96 q-13 20 0 27 q13 -7 0 -27 Z" fill="#8FD3FF" stroke-width="4"/>',
}
ARMS = {
    "none": "",
    "up": '<path d="M60 150 L22 108 M240 150 L278 108"/>',
    "point": '<path d="M60 160 L30 185 M240 150 L282 112"/>',
}


def char(w, mood="smile", arms="none", legs=True):
    """상자 캐릭터 SVG. mood: smile/wow/wink/sweat, arms: none/up/point."""
    h = round(w * 0.9)
    leg = '<path d="M110 220 V250 M190 220 V250"/>' if legs else ""
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 300 270" fill="none" stroke="#111" stroke-width="6" '
        f'stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0" aria-hidden="true">'
        f'{ARMS.get(arms, "")}{CHAR_BOX}{FACES.get(mood, FACES["smile"])}{CHEEKS}{leg}</svg>'
    )


CHAR = char(0).replace('width="0" height="0"', 'width="{w}" height="{h}"')

# 넘치는 글자를 줄이는 스크립트: data-fit 요소는 가로로, #fitbox는 세로로 맞춘다
FIT_JS = """
async () => {
  await document.fonts.ready;
  // 표지 제목: 줄마다 가로를 꽉 채우되 data-fill(최대 크기)까지만 키운다
  const fills = [...document.querySelectorAll('[data-fill]')];
  for (const el of fills) {
    const max = parseFloat(el.dataset.fill);
    const target = el.parentElement.clientWidth - 24;
    let s = 100;
    for (let i = 0; i < 3; i++) { el.style.fontSize = s + 'px'; s = Math.min(max, s * target / el.offsetWidth); }
    el.style.fontSize = Math.floor(s) + 'px';
  }
  for (let i = 0; i < 40 && fills.length && document.documentElement.scrollHeight > 1350; i++) {
    for (const el of fills) el.style.fontSize = Math.floor(parseFloat(el.style.fontSize) * 0.96) + 'px';
  }
  for (const el of document.querySelectorAll('[data-fit]')) {
    let s = parseFloat(getComputedStyle(el).fontSize);
    const max = el.parentElement.clientWidth;
    while (el.scrollWidth > max && s > 30) { s -= 2; el.style.fontSize = s + 'px'; }
  }
  const box = document.getElementById('fitbox');
  if (box) {
    let s = parseFloat(getComputedStyle(box).fontSize);
    while (document.body.scrollHeight > 1350 && s > 28) { s -= 2; box.style.fontSize = s + 'px'; }
  }
  return document.body.scrollHeight;
}
"""


def rich(text, cls="hl"):
    """*강조* 표시를 span으로 바꾸고 나머지는 이스케이프한다."""
    parts = re.split(r"(\*[^*]+\*)", text or "")
    out = []
    for p in parts:
        if p.startswith("*") and p.endswith("*") and len(p) > 2:
            out.append(f'<span class="{cls}">{html.escape(p[1:-1])}</span>')
        else:
            out.append(html.escape(p))
    return "".join(out)


def big_lines(lines):
    colors = ["#FFD400", "#FFFFFF"]
    n = max(len(l) for l in lines)
    size = 150 if n <= 6 else max(96, int(900 / n))
    return "".join(
        f'<div class="ol han" data-fit style="font-size:{size}px;color:{colors[i % 2]}">{html.escape(l)}</div>'
        for i, l in enumerate(lines)
    )


def doc(body):
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{body}</body></html>'


def footer(item):
    dom = SITE_DOMAIN.get(item.get("site"), "")
    return f"{HANDLE} · {dom}" if dom else HANDLE


COVER_STYLES = ["stack", "sticker", "note", "night"]
MOODS = ["smile", "wow", "wink", "sweat"]


def _recent(key, n):
    """최근 발행한 글 n개의 표지 스타일/표정 (posted-ig 기준, 기록이 없으면 예전 기본값)."""
    old = {"style": "stack", "mood": "smile"}
    rows = []
    for path in glob.glob("posted-ig/*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            rows.append((d.get("posted_at", ""), d.get("cover", {}).get(key, old[key])))
        except Exception:
            pass
    return [v for _, v in sorted(rows)[-n:]]


def choose_look(item):
    """표지 스타일·표정을 정해 item["cover"]에 적는다. 글에 적혀 있으면 그대로, 없으면
    최근 글과 겹치지 않게 무작위로 고른다(스타일은 최근 2개, 표정은 직전 1개를 피한다)."""
    c = item["cover"]
    for key, options, n in (("style", COVER_STYLES, 2), ("mood", MOODS, 1)):
        if c.get(key) in options:
            continue
        recent = _recent(key, n)
        c[key] = random.choice([o for o in options if o not in recent] or options)
    return c["style"], c["mood"]


def _key_index(lines):
    """별표로 감싼 줄이 없을 때 가장 크게 보여줄 줄: 숫자가 있는 줄, 없으면 가장 짧은 줄."""
    if any("*" in l for l in lines):
        return -1
    nums = [i for i, l in enumerate(lines) if re.search(r"\d", l)]
    return nums[0] if nums else min(range(len(lines)), key=lambda i: len(lines[i]))


def title_lines(lines, normal_max, key_max):
    """제목 줄. 줄 전체가 *별표*면 가장 크게, 줄 안의 *별표*는 색만 바꾼다."""
    out = []
    auto = _key_index(lines)
    for i, l in enumerate(lines):
        m = re.fullmatch(r"\*([^*]+)\*", l.strip())
        if m or i == auto:
            out.append(f'<div class="tl han key" data-fill="{key_max}">{html.escape(m.group(1) if m else l)}</div>')
        else:
            out.append(f'<div class="tl han" data-fill="{normal_max}">{rich(l, "k")}</div>')
    return "".join(out)


def cover_html(item):
    c = item["cover"]
    style, mood = choose_look(item)
    bubble = "<br>".join(rich(x) for x in c["bubble"])
    tag = c.get("tag", "")
    foot = f"{html.escape(tag)} · {SITE_DOMAIN.get(item.get('site'), HANDLE)}" if tag else footer(item)
    badge = html.escape(c["badge"])

    if style == "sticker":
        body = (
            f'<div class="badge" data-fit style="font-size:46px">{badge}</div>'
            f'<div class="title" style="padding-top:20px">{title_lines(c["lines"], 190, 300)}</div>'
            f'<div style="display:flex;align-items:flex-end;gap:26px;height:300px">'
            f'<div style="margin:0 0 -110px -10px">{char(400, mood, "none", legs=False)}</div>'
            f'<div style="display:flex;flex-direction:column;gap:22px;align-items:flex-start;padding-bottom:6px;min-width:0">'
            f'<div class="bubble han" style="position:relative;font-size:58px">{bubble}'
            f'<span class="tail" style="left:-23px;bottom:38px;transform:rotate(45deg)"></span></div>'
            f'<div class="cfoot" data-fit style="font-size:34px">{foot}</div></div></div>'
        )
    elif style == "note":
        body = (
            f'<div style="display:flex;align-items:center;gap:20px">{char(190, mood, "point")}'
            f'<div class="bubble" style="position:relative;font-size:46px;padding:14px 30px;border-width:5px;box-shadow:6px 6px 0 #111">{badge}'
            f'<span class="tail" style="left:-21px;top:32px;transform:rotate(45deg);border-width:5px;width:28px;height:28px"></span></div></div>'
            f'<div class="title">{title_lines(c["lines"], 180, 290)}</div>'
            f'<div class="answer han">{" ".join(rich(x) for x in c["bubble"])}</div>'
            f'<div class="cfoot" data-fit style="margin-top:30px;align-self:center">{foot}</div>'
        )
    elif style == "night":
        body = (
            f'<div class="badge" data-fit style="font-size:46px">{badge}</div>'
            f'<div class="title">{title_lines(c["lines"], 170, 300)}</div>'
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:20px">'
            f'<div class="bubble han" style="position:relative;color:#111;font-size:56px;padding:16px 36px">{" ".join(rich(x) for x in c["bubble"])}'
            f'<span class="tail" style="left:50%;bottom:-23px;margin-left:-17px;transform:rotate(-45deg)"></span></div>'
            f'{char(230, mood, "up")}</div>'
            f'<div class="cfoot" data-fit style="margin-top:18px">{foot}</div>'
        )
    else:
        style = "stack"
        body = (
            f'<div class="badge" data-fit style="font-size:46px">{badge}</div>'
            f'<div class="title">{title_lines(c["lines"], 175, 300)}</div>'
            f'<div class="row">{char(240, mood, "up")}<div class="bubble han">{bubble}</div></div>'
            f'<div class="cfoot" data-fit style="margin-top:34px">{foot}</div>'
        )
    return doc(f'<div class="cv s-{style}">{body}</div>')


def list_html(item):
    l = item["list"]
    n = len(l["items"])
    size = 60 if n <= 4 else 56 if n <= 6 else 52
    rows = []
    for i, it in enumerate(l["items"], 1):
        main, note = (it + [""])[:2] if isinstance(it, list) else (it, "")
        extra = f" <small>({html.escape(note)})</small>" if note else ""
        rows.append(f"<div>{i}. {rich(main)}{extra}</div>")
    title = "<br>".join(html.escape(x) for x in l["title"])
    note = l.get("note", "")
    note_line = f"{html.escape(note)} · {SITE_DOMAIN.get(item.get('site'), HANDLE)}" if note else footer(item)
    return doc(
        f'<div class="lpage"><div class="ltitle han">{title}</div>'
        f'<div class="lbox" id="fitbox" style="font-size:{size}px">{"".join(rows)}</div>'
        f'<div class="lfoot">{CHAR.format(w=170, h=153)}<div style="display:flex;flex-direction:column;gap:6px;min-width:0;flex:1">'
        f'<div style="font-size:50px;line-height:1.25">{rich(l["bottom"], "mk")}</div>'
        f'<div class="note" data-fit>{note_line}</div></div></div></div>'
    )


def cta_html(item):
    c = item["cta"]
    bubble = "<br>".join(rich(x) for x in c["bubble"])
    return doc(
        f'<div class="page"><div class="badge" data-fit>{html.escape(c["badge"])}</div>'
        f'<div class="big">{big_lines(c["lines"])}</div>'
        f'<div class="row">{CHAR.format(w=250, h=225)}<div class="bubble han" style="font-size:56px">{bubble}</div></div>'
        f'<div class="sub" data-fit>{html.escape(c.get("sub", ""))}</div>'
        f'<div class="foot" data-fit>{footer(item)}</div></div>'
    )


def validate(item):
    for key in ("cover", "list", "cta"):
        if key not in item:
            raise ValueError(f"'{key}' 칸이 없습니다")
    if not 2 <= len(item["cover"]["lines"]) <= 4:
        raise ValueError("cover.lines는 2~4줄이어야 합니다")
    if not 3 <= len(item["list"]["items"]) <= 8:
        raise ValueError("list.items는 3~8개여야 합니다")


def render(item, out_dir, chrome=None):
    """카드 3장을 out_dir/1.jpg, 2.jpg, 3.jpg로 저장하고 경로 목록을 돌려준다."""
    from playwright.sync_api import sync_playwright

    validate(item)
    os.makedirs(out_dir, exist_ok=True)
    pages = [cover_html(item), list_html(item), cta_html(item)]
    paths = []
    chrome = chrome or os.environ.get("CHROME_PATH") or "/usr/bin/google-chrome"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, src in enumerate(pages, 1):
            page.set_content(src, wait_until="networkidle", timeout=60000)
            h = page.evaluate(FIT_JS)
            if h > H + 2:
                print(f"경고: {i}번 카드 내용이 넘칩니다 (높이 {h}px)")
            path = os.path.join(out_dir, f"{i}.jpg")
            page.screenshot(path=path, type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": W, "height": H})
            paths.append(path)
        browser.close()
    return paths


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        print(render(json.load(f), out))
