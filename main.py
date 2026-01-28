from fastapi import FastAPI, Request
import random
import re
from datetime import datetime

app = FastAPI()

# ---- 메뉴 DB: 태그 기반(필요하면 계속 추가 가능) ----
MENUS = [
    ("제육덮밥", {"밥","고기","매운","든든","가성비","혼밥","빠름"}),
    ("김치찌개", {"국물","밥","매운","든든","해장","추움","혼밥"}),
    ("된장찌개", {"국물","밥","담백","가벼움","혼밥","가성비"}),
    ("순두부찌개", {"국물","밥","매운","해장","추움","혼밥"}),
    ("부대찌개", {"국물","밥","든든","해장","비오는날","2인이상"}),
    ("국밥", {"국물","밥","해장","든든","가성비","추움","혼밥"}),
    ("돈까스", {"밥","고기","바삭","든든","혼밥","빠름"}),
    ("비빔밥", {"밥","야채","담백","가벼움","혼밥"}),
    ("샐러드", {"다이어트","가벼움","야채","빠름"}),
    ("닭가슴살도시락", {"다이어트","가성비","단백질","빠름","혼밥"}),
    ("초밥", {"가벼움","비싼편","혼밥","빠름"}),
    ("우동", {"면","국물","담백","비오는날","추움","빠름","혼밥"}),
    ("라멘", {"면","국물","든든","비오는날","추움","혼밥"}),
    ("짬뽕", {"면","국물","매운","해장","비오는날","추움"}),
    ("짜장면", {"면","가성비","빠름","혼밥"}),
    ("쌀국수", {"면","국물","담백","가벼움","비오는날","혼밥"}),
    ("칼국수", {"면","국물","비오는날","추움","혼밥"}),
    ("햄버거", {"간단","빠름","혼밥","가성비"}),
    ("샌드위치", {"간단","가벼움","빠름","혼밥"}),
    ("떡볶이", {"분식","매운","가성비","간단","혼밥"}),
    ("김밥+라면", {"분식","간단","가성비","혼밥","빠름"}),
]

# ---- 키워드 -> 태그 매핑 ----
KEYWORD_TO_TAGS = {
    "매운": {"매운"},
    "얼큰": {"매운","국물"},
    "담백": {"담백"},
    "가벼": {"가벼움"},
    "든든": {"든든"},
    "고기": {"고기"},
    "야채": {"야채"},
    "다이어트": {"다이어트","가벼움"},
    "헬스": {"다이어트","단백질"},
    "단백질": {"단백질"},
    "해장": {"해장","국물"},
    "국물": {"국물"},
    "면": {"면"},
    "밥": {"밥"},
    "분식": {"분식"},
    "간단": {"간단","빠름"},
    "빨리": {"빠름"},
    "빠름": {"빠름"},
    "가성비": {"가성비"},
    "혼밥": {"혼밥"},
    "2인": {"2인이상"},
    "둘": {"2인이상"},
    "비오는": {"비오는날","국물"},
    "추운": {"추움","국물"},
}

TAG_WEIGHT = {
    "다이어트": 4,
    "매운": 3,
    "해장": 3,
    "국물": 2,
    "가성비": 2,
    "빠름": 2,
    "혼밥": 2,
    "든든": 2,
    "가벼움": 2,
    "면": 1,
    "밥": 1,
    "고기": 1,
    "야채": 1,
    "비오는날": 1,
    "추움": 1,
    "2인이상": 1,
}

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def extract_option(utterance: str) -> str:
    u = utterance.strip()
    u = u.replace("/점메추", "").replace("점메추", "")
    return normalize(u)

def option_to_tags(option: str) -> set:
    tags = set()
    if not option:
        return tags
    for k, tset in KEYWORD_TO_TAGS.items():
        if k in option:
            tags |= tset
    return tags

def weekday_hint_tags() -> set:
    wd = datetime.now().weekday()  # 0=Mon
    if wd == 0:
        return {"빠름","가성비"}
    if wd == 4:
        return {"든든"}
    if wd == 2:
        return {"담백"}
    return set()

def score_menu(menu_tags: set, want_tags: set) -> int:
    s = 0
    for t in want_tags:
        if t in menu_tags:
            s += TAG_WEIGHT.get(t, 1)
    if "다이어트" in want_tags and "든든" in menu_tags and "가벼움" not in menu_tags:
        s -= 1
    return s

def pick_recommendations(want_tags: set, k: int = 5):
    scored = []
    for name, tags in MENUS:
        s = score_menu(tags, want_tags)
        scored.append((s, name, tags))
    scored.sort(reverse=True, key=lambda x: x[0])

    top = scored[:12]
    if not want_tags:
        random.shuffle(top)
        return top[:k], "기본 추천(랜덤+요일 힌트)"

    pool = [x for x in top if x[0] > 0] or top[:8]
    random.shuffle(pool)
    return pool[:k], f"조건 태그: {', '.join(sorted(want_tags))}"

def format_reason(tags: set, want_tags: set) -> str:
    reasons = []
    if "다이어트" in want_tags and "다이어트" in tags:
        reasons.append("가볍게 먹기 좋음")
    if "해장" in want_tags and "해장" in tags:
        reasons.append("해장에 딱")
    if "국물" in want_tags and "국물" in tags:
        reasons.append("국물로 만족감")
    if "가성비" in want_tags and "가성비" in tags:
        reasons.append("가성비 굿")
    if "빠름" in want_tags and "빠름" in tags:
        reasons.append("빨리 해결 가능")
    if "혼밥" in want_tags and "혼밥" in tags:
        reasons.append("혼밥 무난")
    if "매운" in want_tags and "매운" in tags:
        reasons.append("매콤하게 스트레스 컷")

    if not reasons:
        if "든든" in tags:
            reasons.append("든든하게 한 끼")
        elif "가벼움" in tags:
            reasons.append("부담 적음")
        else:
            reasons.append("무난한 선택")
    return ", ".join(reasons[:2])

@app.get("/")
def health():
    return {"ok": True}

@app.post("/skill")
async def skill(req: Request):
    body = await req.json()

    # 사용자 발화 (예: "/점메추 매운 해장")
    utterance = body.get("userRequest", {}).get("utterance", "").strip()

    option = extract_option(utterance)
    want_tags = option_to_tags(option)
    want_tags |= weekday_hint_tags()

    recs, hint = pick_recommendations(want_tags, k=5)

    lines = []
    lines.append("🍽️ 오늘 점심 추천!")
    if option:
        lines.append(f"입력: {option}")
    lines.append(f"기준: {hint}")
    lines.append("")

    for i, (_, name, tags) in enumerate(recs, start=1):
        lines.append(f"{i}) {name} — {format_reason(tags, want_tags)}")

    lines.append("")
    lines.append("예) /점메추 매운 해장 /점메추 다이어트 /점메추 혼밥 빠름 /점메추 비오는날 국물")
    text = "\n".join(lines)

    # 카카오 스킬 응답(JSON): version 2.0 + simpleText
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]}
    }
