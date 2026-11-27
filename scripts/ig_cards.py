"""인스타 카드뉴스 3장(표지 · 목록 · 마지막 장)을 JPEG로 만든다.

글 파일(queue-ig/*.json)의 cover / list / cta 칸을 받아 1080x1350 이미지를 만든다.
글자 안의 *별표*로 감싼 부분은 강조색으로 칠한다.

로컬 미리보기:  python scripts/ig_cards.py queue-ig/파일.json out_dir
"""
import html
import json
import os
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
.ol{-webkit-text-stroke:18px #111;paint-order:stroke fill;line-height:1.1;white-space:nowrap}
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
"""

CHAR = """<svg width="{w}" height="{h}" viewBox="0 0 300 270" fill="none" stroke="#111" stroke-width="6"
 stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0" aria-hidden="true">
<path d="M60 80 L20 40 L120 30 L150 70 Z" fill="#F2C48D"/><path d="M240 80 L280 40 L180 30 L150 70 Z" fill="#F2C48D"/>
<rect x="60" y="80" width="180" height="140" rx="10" fill="#F7D9A8"/><path d="M150 80 V120"/>
<circle cx="115" cy="140" r="7" fill="#111"/><circle cx="185" cy="140" r="7" fill="#111"/>
<path d="M128 165 Q150 188 172 165"/><circle cx="98" cy="165" r="12" fill="#FF9E8C" stroke="none"/>
<circle cx="202" cy="165" r="12" fill="#FF9E8C" stroke="none"/><path d="M110 220 V250 M190 220 V250"/></svg>"""

# 넘치는 글자를 줄이는 스크립트: data-fit 요소는 가로로, #fitbox는 세로로 맞춘다
FIT_JS = """
async () => {
  await document.fonts.ready;
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


def cover_html(item):
    c = item["cover"]
    bubble = "<br>".join(rich(x) for x in c["bubble"])
    tag = c.get("tag", "")
    foot = f"{html.escape(tag)} · {SITE_DOMAIN.get(item.get('site'), HANDLE)}" if tag else footer(item)
    return doc(
        f'<div class="page"><div class="badge" data-fit>{html.escape(c["badge"])}</div>'
        f'<div class="big">{big_lines(c["lines"])}</div>'
        f'<div class="row">{CHAR.format(w=250, h=225)}<div class="bubble han">{bubble}</div></div>'
        f'<div class="foot" data-fit>{foot}</div></div>'
    )


def list_html(item):
    l = item["list"]
    n = len(l["items"])
    size = 52 if n <= 5 else 48 if n <= 7 else 44
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
