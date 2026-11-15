"""궤적·백로그 점검기 — 데이터와 화면이 규칙을 지키는지 본다.

사용: python 궤적점검.py <궤적데이터.json 또는 궤적.html>
종료코드 0 = 통과, 1 = 위반 있음. 위반은 한 줄씩 사람이 읽는 문장으로 출력한다.
템플릿({{ }} 자리표시)은 문장 검사를 건너뛴다.
"""
import re
import sys
import pathlib

STATES = ["goal", "done", "now", "todo", "parked", "next"]
LANES = {0, 1, -1}
MAX_ITEMS = 3
MAX_TITLE = 36
MAX_ITEM = 45
STR = r'"((?:[^"\\]|\\.)*)"'


def field(line, key):
    가림 = re.sub(STR, lambda g: '"' + "_" * (len(g.group(0)) - 2) + '"', line)
    k = re.search(r"\b" + key + r':\s*(?=["\d-])', 가림)
    m = k and re.compile("(" + STR + r"|-?\d+)").match(line, k.end())
    if not m:
        return None
    return m.group(2) if m.group(2) is not None else int(m.group(1))


def nodes_of(html):
    m = re.search(r"const NODES = \[(.*?)\n\];", html, re.S)
    if not m:
        return None
    out = []
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line.startswith("{id:"):
            continue
        n = {k: field(line, k) for k in ("id", "tk", "lane", "from", "st", "w", "ax", "due", "t", "q", "sm")}
        sm7 = re.search(r"\bs:\s*\[(.*)\]\s*,\s*x:", line)
        n["s"] = [(h, re.findall(STR, body)) for h, body in re.findall(STR + r"\s*,\s*\[(.*?)\]", sm7.group(1))] if sm7 else None
        xm = re.search(r"\bx:\s*\[(.*?)\]\s*\}", line)
        n["x"] = re.findall(STR, xm.group(1)) if xm else None
        lm = re.search(r"\bn:\s*\[(.*)\]\s*\}", line)
        if lm:
            n["n"] = re.findall(STR, lm.group(1))
        else:
            sm = re.search(r"\bn:\s*" + STR, line)
            n["n"] = [sm.group(1)] if sm else []
        out.append(n)
    return out


def sentence_ok(s):
    s = s.rstrip()
    while True:
        t = re.sub(r"\s*\([^()]*\)\s*\.?$", "", s).rstrip()
        if t == s:
            break
        s = t if t.endswith(("다", "요", "까?")) and not t.endswith((".",)) else t
    return s.endswith(("다.", "다", "요.", "요", "까?"))


상태말 = {"목표": "goal", "완료": "done", "지금": "now", "대기": "todo", "보류": "parked", "다음": "next"}


약어 = re.compile(r"(?i)^(e\.g|i\.e|etc|vs|cf|no|mr|ms|dr|st|v\d+(\.\d+)*)\.$")


def 문장들(글):
    """마침표 · 물음표 · 느낌표 뒤 빈칸에서 나눈다. e.g. · i.e. · v2. 같은 약어 뒤에서는 나누지 않는다. 화면의 sentences()와 같은 규칙이다."""
    나눔, 지금 = [], ""
    for 조각 in re.split(r"(\s+)", 글.strip()):
        지금 += 조각
        끝말 = re.sub(r"[*」』)\]\"']+$", "", 조각)
        if re.search(r"[.!?]$", 끝말) and not 약어.match(끝말.split()[-1] if 끝말.split() else ""):
            나눔.append(지금.strip()); 지금 = ""
    if 지금.strip():
        나눔.append(지금.strip())
    return [s for s in 나눔 if s]


def 실제날(y, mo, d):
    from datetime import date
    try:
        date(y, mo, d)
        return True
    except ValueError:
        return False


def 꼴검사(d):
    """손으로 고친 v9 JSON의 모양을 먼저 본다: 칸이 있나, 글 · 숫자 · 목록이 맞나, 날짜가 달력에 있나, 트랙 키가 겹치나."""
    bad = []
    머리 = d.get("머리")
    if not isinstance(머리, dict):
        bad.append("머리: 「머리」 칸(창제목 · 제목 · 부제목 · 바닥)이 없다.")
    else:
        for k in ("창제목", "제목", "바닥"):
            if not isinstance(머리.get(k), str):
                bad.append(f"머리: 「{k}」는 따옴표로 감싼 글이어야 한다. 지금 값: {머리.get(k)!r}")
        부 = 머리.get("부제목")
        if not (isinstance(부, list) and all(isinstance(x, str) for x in 부)):
            bad.append('머리: 「부제목」은 글 목록이다. 한 줄이어도 ["…"]처럼 대괄호로 감싼다.')
    트랙들 = d.get("트랙")
    if not isinstance(트랙들, list) or not 트랙들:
        return bad + ["트랙: 「트랙」 목록이 없거나 비었다."]
    키들 = set()
    for t, 트 in enumerate(트랙들, 1):
        키 = 트.get("키") if isinstance(트, dict) else None
        if not isinstance(키, str) or not 키:
            bad.append(f"트랙 {t}: 「키」가 없다.")
            continue
        if 키 in 키들:
            bad.append(f"트랙 {키}: 트랙 키가 겹친다. 트랙을 복사해 시작했으면 키를 새로 붙인다.")
        키들.add(키)
        if not isinstance(트.get("이름"), str):
            bad.append(f"트랙 {키}: 「이름」이 없다.")
        노드 = 트.get("노드")
        if not isinstance(노드, list):
            bad.append(f"트랙 {키}: 「노드」 목록이 없다.")
            continue
        for i, n in enumerate(노드, 1):
            곳 = f"{키}#{i}" + (f"({n['id']})" if isinstance(n, dict) and isinstance(n.get("id"), str) else "")
            if not isinstance(n, dict):
                bad.append(f"{곳}: 카드는 {{ … }}로 쓴다.")
                continue
            축 = n.get("축")
            if type(축) is not int or 축 not in (0, 1, -1):
                bad.append(f"{곳}: 「축」은 따옴표 없는 숫자 0(메인), 1(보조), -1(추가) 중 하나다. 지금 값: {축!r}")
            if n.get("상태") not in 상태말:
                bad.append(f"{곳}: 「상태」는 {' · '.join(상태말)} 중 하나다. 지금 값: {n.get('상태')!r}")
            if not isinstance(n.get("질문"), str) or not n["질문"].strip():
                bad.append(f"{곳}: 카드 제목 「질문」이 없다.")
            for k in ("id", "요약", "축이름", "갈래"):
                if n.get(k) is not None and not isinstance(n[k], str):
                    bad.append(f"{곳}: 「{k}」는 따옴표로 감싼 글이어야 한다. 지금 값: {n[k]!r}")
            소 = n.get("소제목")
            if 소 is not None and not (isinstance(소, list) and all(isinstance(s, list) and len(s) == 2 and isinstance(s[0], str) and isinstance(s[1], list) and all(isinstance(x, str) for x in s[1]) for s in 소)):
                bad.append(f'{곳}: 「소제목」은 [["머리", ["줄", …]], …] 꼴이다. 새로 쓰는 카드는 소제목 대신 「요약」을 쓴다.')
            if "보충" in n and not (isinstance(n["보충"], list) and all(isinstance(x, str) for x in n["보충"])):
                bad.append(f'{곳}: 「보충」은 글 목록이다. 없으면 [], 한 줄이면 ["…"]로 쓴다.')
            w = n.get("날짜")
            if w is not None and not ((m := re.fullmatch(r"(\d{2})/(\d{2})", str(w))) and 실제날(2024, int(m[1]), int(m[2]))):
                bad.append(f"{곳}: 「날짜」는 달/일 두 자리씩 MM/DD다(예: 11/09). 지금 값: {w!r}")
            due = n.get("마감")
            if due is not None and not ((m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(due))) and 실제날(int(m[1]), int(m[2]), int(m[3]))):
                bad.append(f"{곳}: 「마감」은 달력에 있는 날 YYYY-MM-DD다(예: 2026-11-25). 지금 값: {due!r}")
    return bad


def check_json(path):
    """생성기가 있는 프로젝트의 궤적 정본(JSON: 트랙 → 노드)을 같은 글쓰기 법으로 본다.
    from 은 생성기가 위치로 그리므로 보지 않는다. 「지금」은 트랙마다 하나 이하(아직 시작 안 한 트랙은 없다)."""
    import json
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import 키별칭
    import unicodedata
    d = 키별칭.한글로(json.loads(unicodedata.normalize("NFC", pathlib.Path(path).read_text(encoding="utf-8-sig"))))
    영어로보기(isinstance(d, dict) and d.get("언어") not in (None, "ko"))
    if isinstance(d, dict) and d.get("판") == 9 and (꼴 := 꼴검사(d)):
        return 꼴
    bad = []
    for 트 in d.get("트랙", []):
        키 = 트.get("키", "?")
        nodes = []
        for i, n in enumerate(트.get("노드", []), 1):
            설명 = n.get("설명", "")
            원줄 = [l.strip() for l in 설명.splitlines() if l.strip()]
            줄 = [l[2:] if l.startswith("- ") else l for l in 원줄]
            if len(원줄) >= 2 and not all(l.startswith("- ") for l in 원줄):
                bad.append(f"{키}#{i}: 설명이 두 줄 이상인데 「- 」 점 목록이 아니다.")
            node = {"id": n.get("id") or f"{키}#{i}", "lane": n.get("축"), "from": None, "st": 상태말.get(n.get("상태"), n.get("상태")),
                    "w": None, "ax": n.get("축이름"), "due": n.get("마감"), "t": n.get("제목", ""), "n": 줄}
            if "질문" in n:
                node.update(q=n["질문"], s=[(h, xs) for h, xs in n.get("소제목", [])] if "소제목" in n else None, x=n.get("보충"), sm=n.get("요약"))
            nodes.append(node)
        v7 = [n for n in nodes if n.get("q") is not None]
        if v7 and len(v7) != len(nodes):
            bad += [f"{n['id']}: 다른 노드가 v7(질문 · 소제목 · 보충)이면 이 노드도 v7로 쓴다." for n in nodes if n.get("q") is None]
        if sum(1 for n in nodes if n["st"] == "now") > 1:
            bad.append(f"{키}: 「지금」 노드가 둘 이상이다.")
        대기칸 = None
        멈춘메인 = False
        for n in nodes:
            if 대기칸 and n["lane"] in (0, None):
                멈춘메인 = False
            if n["st"] in ("todo", "next") and not 대기칸:
                대기칸, 멈춘메인 = n["id"], n["lane"] in (0, None)
            elif n["st"] in ("done", "now") and 대기칸 and not 멈춘메인:
                bad.append(f"{n['id']}: 「{'완료' if n['st'] == 'done' else '지금'}」 칸이 아직 시작하지 않은 칸 {대기칸} 아래에 있다. 끝낸 일과 지금 일은 대기 · 다음 칸보다 위에 둔다.")
        for n in nodes:
            if n["lane"] not in (0, None) and not n["ax"]:
                bad.append(f"{n['id']}: 보조 · 추가 줄 칸은 축이름(꼬리표, 예: 결제)이 있어야 한다.")
        bad += 노드_글(nodes)
    if d.get("판") == 9:
        bad += v9규칙(d)
    return bad


WARN = []
읽는법 = re.compile(r"위에서 아래로 (?:시간|읽|갈수록|내려갈수록)|아래로 (?:시간이|갈수록)|(?:가운데|오른쪽|왼쪽|메인|보조|추가) (?:줄|선)(?:은|는|이|가)(?= )|빨간 점(?:은|이)(?= )")


def 굵게짝(s):
    return re.sub(r"`[^`]*`", "", s).count("**") % 2 == 0


def 갈래틀림(노드, i, j):
    """노드[i]의 갈래가 노드[j]일 때 틀린 까닭을 돌려준다. 맞으면 빈 글. 접기(궤적접기.py)도 이 함수를 쓴다."""
    if j >= i:
        return "이 카드보다 위에 있는 카드여야 한다"
    위, 나 = int(노드[j].get("축", 0)), int(노드[i].get("축", 0))
    if 위 != 0 and 위 != 나:
        return "보조와 추가는 서로 잇지 않는다. 메인 카드나 같은 줄 카드에서 갈라진다"
    if any(int(m.get("축", 0)) == 0 for m in 노드[j + 1:i]):
        return "사이에 메인 카드가 있다. 메인 카드를 건너 잇지 않는다"
    return ""


def v9규칙(d):
    """v9 — 칸 이름표(id) · 갈래 · 머리글 · 굵게 표시 짝. 요약 길이와 완료 날짜는 경고."""
    bad, ids, 자리 = [], {}, {}
    트랙노드 = {트.get("키"): 트.get("노드", []) for 트 in d.get("트랙", [])}
    for 트 in d.get("트랙", []):
        메인봄 = False
        for i, n in enumerate(트.get("노드", []), 1):
            nid = n.get("id")
            if not isinstance(nid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", nid):
                bad.append(f"{트.get('키')}#{i}: id가 없거나 모양이 틀렸다(영문으로 시작, 32자 안).")
                continue
            if nid in ids:
                bad.append(f"{nid}: id가 겹친다. id는 한 번 붙이면 바꾸지 않고 다시 쓰지도 않는다.")
            ids[nid], 자리[nid] = n, (트.get("키"), i)
            if int(n.get("축", 0)) == 0:
                메인봄 = True
            elif not 메인봄 and not n.get("갈래"):
                bad.append(f"{nid}: 보조 · 추가 카드 위에 메인 카드(목표 포함)가 없다. 갈라져 나올 메인 카드 아래에 둔다.")
    for nid, n in ids.items():
        g = n.get("갈래")
        if g is not None:
            if int(n.get("축", 0)) == 0:
                bad.append(f"{nid}: 메인 칸에는 갈래를 쓰지 않는다.")
            elif g not in ids or g == nid:
                bad.append(f"{nid}: 갈래가 가리키는 {g} 칸이 없다.")
            elif 자리[g][0] != 자리[nid][0] or 자리[g][1] > 자리[nid][1]:
                bad.append(f"{nid}: 갈래 {g}는 같은 트랙에서 이 카드보다 위에 있는 카드여야 한다.")
            elif 왜 := 갈래틀림(트랙노드[자리[nid][0]], 자리[nid][1] - 1, 자리[g][1] - 1):
                bad.append(f"{nid}: 갈래 {g} — {왜}.")
        글들 = [n.get("질문", ""), n.get("요약", "")] + [s for _, xs in n.get("소제목", []) for s in xs] + list(n.get("보충", []))
        for s in 글들:
            if not 굵게짝(s):
                bad.append(f"{nid}: 굵게 표시 ** 가 짝이 안 맞는다 — 「{s[:24]}…」.")
        sm = n.get("요약", "")
        if len(re.sub(r"\*\*", "", sm)) > 140:
            WARN.append(f"{nid}: 요약이 {len(sm)}자다. 세 문장, 140자 안이 읽기 쉽다.")
        if n.get("상태") == "완료" and not n.get("날짜"):
            WARN.append(f"{nid}: 완료 칸에 날짜가 없다.")
    머리 = d.get("머리", {})
    if re.search(r"지금은|지금 하는 일|지금[^.]{0,20}(?:(?:하는|진행) 중|단계)", 머리.get("제목", "")):
        bad.append("머리: 제목에 「지금」을 쓰지 않는다. 지금 하는 일은 맨 위 띠가 보인다. 제목은 프로젝트가 하려는 일이다.")
    for s in 머리.get("부제목", []):
        if 읽는법.search(s):
            bad.append(f"머리: 부제목에 그림 읽는 법을 쓰지 않는다 — 「{s[:24]}」. 부제목은 프로젝트 설명이다.")
    return bad


def 노드_글(nodes):
    bad = []
    seen_now = False
    for n in nodes:
        nid = n["id"]
        if n["st"] not in STATES:
            bad.append(f"{nid}: 상태 {n['st']}는 쓰지 않는 값이다.")
        if n["lane"] not in LANES:
            bad.append(f"{nid}: 축 {n['lane']}은 쓰지 않는다. 축은 0, 1, -1 셋뿐이다.")
        if n["st"] == "now":
            seen_now, 지금뒤메인 = True, n["lane"] != 0
        elif n["lane"] == 0 and seen_now:
            지금뒤메인 = True
        if n["st"] == "done" and seen_now and (n["lane"] == 0 or 지금뒤메인):
            bad.append(f"{nid}: 「완료」가 「지금」보다 아래에 있다. 시간이 거꾸로 보인다.")
        if n.get("q") is not None:
            bad += 질문형(n, False)
            continue
        if not (1 <= len(n["n"]) <= MAX_ITEMS):
            bad.append(f"{nid}: 설명이 {len(n['n'])}문장이다. 1~3문장으로 쓴다.")
        t = n["t"] or ""
        if len(t) > MAX_TITLE:
            bad.append(f"{nid}: 제목이 {len(t)}자다. {MAX_TITLE}자 안으로 줄인다.")
        if not t.endswith("다"):
            bad.append(f"{nid}: 제목 「{t}」가 문장으로 끝나지 않는다. 「~했다/~한다」로 맺는다.")
        for s in n["n"]:
            if re.search(r"(다|요)\.\s+\S", s):
                bad.append(f"{nid}: 한 점에 두 문장이 있다 — 「{s[:24]}…」. 점을 나눈다.")
            if not sentence_ok(s):
                bad.append(f"{nid}: 「{s[:30]}」가 완결 문장이 아니다. 명사 토막을 쓰지 않는다.")
            if len(s) > MAX_ITEM:
                bad.append(f"{nid}: 문장이 {len(s)}자다. {MAX_ITEM}자 안으로 나눈다.")
        for s in [t] + n["n"]:
            if re.search(r"(?<!\d)·|·(?!\d)", re.sub(r"시·군·구|시·군|읍·면·동|시·구|시·도", "", s)):
                bad.append(f"{nid}: 문장 안에 가운뎃점(·)이 있다. 쉼표와 「~처럼」으로 푼다.")
            if re.search(r"(고|며|지만|면서|아서|어서),", s):
                bad.append(f"{nid}: 연결어미 바로 뒤에 쉼표가 있다.")
            if re.search(r"되어진|지게 된|가지고 있다", s):
                bad.append(f"{nid}: 번역투가 있다.")
    return bad


def 영어로보기(켬):
    """영어 화면: 한국어 문장 규칙은 빼고 길이 한도만 두 배로 본다."""
    global 영어, MAX_TITLE, MAX_ITEM, MAX_X_LEN
    if 켬 and not 영어:
        영어, MAX_TITLE, MAX_ITEM, MAX_X_LEN = True, MAX_TITLE * 2, MAX_ITEM * 2, MAX_X_LEN * 2


영어 = False


def check(path):
    if str(path).lower().endswith(".json"):
        return check_json(path)
    html = pathlib.Path(path).read_text(encoding="utf-8")
    영어로보기('const LANG = "en"' in html)
    bad = []
    nodes = nodes_of(html)
    if nodes is None:
        return ["NODES 배열을 찾지 못했다. 화면의 const NODES = [ ... ]; 줄을 바꾸지 않는다."]
    template = "{{" in html
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        bad.append("같은 id를 가진 노드가 둘 이상 있다.")
    트랙들 = list(dict.fromkeys(n.get("tk") for n in nodes))
    for 키 in 트랙들:
        k = sum(1 for n in nodes if n.get("tk") == 키 and n["st"] == "now")
        if k > 1:
            bad.append(f"{'트랙 ' + 키 + ': ' if 키 else ''}「지금」 노드가 {k}개다. 트랙마다 하나 이하여야 한다.")
    if not re.search(r'const UPDATED = "(\d{4}-\d{2}-\d{2}|YYYY-MM-DD)";', html):
        bad.append("UPDATED 날짜가 없다.")
    seen_now, 앞트랙 = False, object()
    for n in nodes:
        nid = n["id"]
        if n.get("tk") != 앞트랙:
            seen_now, 앞트랙, 대기메인, 멈춘메인 = False, n.get("tk"), None, False
        if 대기메인 and n["lane"] in (0, None):
            멈춘메인 = False
        if n["st"] in ("todo", "next") and not 대기메인:
            대기메인, 멈춘메인 = nid, n["lane"] in (0, None)
        elif n["st"] in ("done", "now") and 대기메인 and not 멈춘메인:
            bad.append(f"{nid}: 「{'완료' if n['st'] == 'done' else '지금'}」 칸이 아직 시작하지 않은 칸 {대기메인} 아래에 있다. 끝낸 일과 지금 일은 대기 · 다음 칸보다 위에 둔다.")
        if n["st"] not in STATES:
            bad.append(f"{nid}: 상태 {n['st']}는 쓰지 않는 값이다.")
        if n["lane"] not in LANES:
            bad.append(f"{nid}: 축 {n['lane']}은 쓰지 않는다. 축은 0, 1, -1 셋뿐이다.")
        if n["lane"] not in (0, None) and not (n["from"] and n["ax"]):
            bad.append(f"{nid}: 보조 · 추가 카드가 갈라져 나올 카드(from)나 꼬리표(ax)가 없다. 데이터에서는 위에 메인 카드를 두고 축이름을 쓴다.")
        if n["from"] and n["from"] not in ids:
            bad.append(f"{nid}: from이 가리키는 {n['from']} 노드가 없다.")
        if n["st"] == "now":
            seen_now, 지금뒤메인 = True, n["lane"] != 0
        elif n["lane"] == 0 and seen_now:
            지금뒤메인 = True
        if n["st"] == "done" and seen_now and (n["lane"] == 0 or 지금뒤메인):
            bad.append(f"{nid}: 「완료」가 「지금」보다 아래에 있다. 시간이 거꾸로 보인다.")
        if n["due"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}|YYYY-MM-DD", n["due"]):
            bad.append(f"{nid}: 마감일은 YYYY-MM-DD로 쓴다.")
        if n.get("q") is not None:
            bad += 질문형(n, template)
            continue
        if not (1 <= len(n["n"]) <= MAX_ITEMS):
            bad.append(f"{nid}: 설명이 {len(n['n'])}문장이다. 1~3문장으로 쓴다.")
        if template:
            continue
        t = n["t"] or ""
        if len(t) > MAX_TITLE:
            bad.append(f"{nid}: 제목이 {len(t)}자다. {MAX_TITLE}자 안으로 줄인다.")
        if not t.endswith("다"):
            bad.append(f"{nid}: 제목 「{t}」가 문장으로 끝나지 않는다. 「~했다/~한다」로 맺는다.")
        for s in n["n"]:
            if re.search(r"(다|요)\.\s+\S", s):
                bad.append(f"{nid}: 한 점에 두 문장이 있다 — 「{s[:24]}…」. 점을 나눈다.")
            if not sentence_ok(s):
                bad.append(f"{nid}: 「{s[:30]}」가 완결 문장이 아니다. 명사 토막을 쓰지 않는다.")
            if len(s) > MAX_ITEM:
                bad.append(f"{nid}: 문장이 {len(s)}자다. {MAX_ITEM}자 안으로 나눈다.")
        for s in [t] + n["n"]:
            if re.search(r"(?<!\d)·|·(?!\d)", s):
                bad.append(f"{nid}: 문장 안에 가운뎃점(·)이 있다. 쉼표와 「~처럼」으로 푼다.")
            if re.search(r"(고|며|지만|면서|아서|어서),", s):
                bad.append(f"{nid}: 연결어미 바로 뒤에 쉼표가 있다.")
            if re.search(r"되어진|지게 된|가지고 있다", s):
                bad.append(f"{nid}: 번역투가 있다.")
    return bad


소제목 = {"goal": ("무엇이 목표인가요?", "어떤 조건이 붙나요?"), "done": ("무엇을 했나요?", "결과는요?"),
          "now": ("왜 하나요?", "어디까지 왔나요?"), "todo": ("왜 하나요?", "무엇을 하나요?"),
          "next": ("왜 하나요?", "무엇을 하나요?"), "parked": ("왜 하나요?", "무엇을 기다리나요?")}
MAX_X, MAX_X_LEN = 3, 60


def 문장검사(nid, s, 한도, 이름):
    s = re.sub(r"\*\*「(.+?)」\*\*", r"\1", s).replace("**", "")
    if 영어:
        return [f"{nid}: {이름} 한 줄이 {len(s)}자다. {한도}자 안으로 쓴다."] if len(s) > 한도 else []
    bad = []
    if re.search(r"(다|요)\.\s+\S", s):
        bad.append(f"{nid}: {이름}의 한 줄에 두 문장이 있다 — 「{s[:24]}…」.")
    if not sentence_ok(s):
        bad.append(f"{nid}: {이름} 「{s[:30]}」가 완결 문장이 아니다.")
    if len(s) > 한도:
        bad.append(f"{nid}: {이름} 한 줄이 {len(s)}자다. {한도}자 안으로 쓴다.")
    if re.search(r"(?<!\d)·|·(?!\d)", s):
        bad.append(f"{nid}: {이름}에 가운뎃점(·)이 있다.")
    if re.search(r"(고|며|지만|면서|아서|어서),", s):
        bad.append(f"{nid}: {이름}에 연결어미 뒤 쉼표가 있다.")
    if re.search(r"되어진|지게 된|가지고 있다", s):
        bad.append(f"{nid}: {이름}에 번역투가 있다.")
    return bad


def 질문형(n, template):
    """v7 — 질문 제목 · 상태별 소제목 두 칸 · 보충 설명 0~3줄."""
    nid, bad, q = n["id"], [], n["q"] or ""
    if not n["s"] and n.get("sm"):
        줄 = 문장들(n["sm"])
        if not (1 <= len(줄) <= 3):
            bad.append(f"{nid}: 요약이 {len(줄)}문장이다. 지금 무엇을 하는지와 어느 단계인지 1~3문장으로 쓴다.")
        for s in 줄:
            bad += 문장검사(nid, s, MAX_ITEM, "요약")
        if n["x"] is None:
            bad.append(f"{nid}: 보충(없으면 [])이 없다.")
        elif len(n["x"]) > MAX_X:
            bad.append(f"{nid}: 보충 설명이 {len(n['x'])}줄이다. 진짜 보충되는 말만 {MAX_X}줄 안으로 남긴다.")
        else:
            정규 = lambda t: re.sub(r"[\W_]", "", t)
            요약글 = 정규("".join(줄))
            for s in n["x"]:
                bad += 문장검사(nid, s, MAX_X_LEN, "보충 설명")
                if (x := 정규(s)) and (x == 요약글 or (len(x) >= 8 and x in 요약글)):
                    bad.append(f"{nid}: 보충 설명 「{s[:24]}…」이 요약과 같다. 요약에 없는 숫자, 정의, 미검증만 쓴다.")
        if not template and (len(q) > MAX_TITLE or q.rstrip().endswith(("?", "？")) or not (영어 or re.search(r"(니다|요)\.?$", q.strip()))):
            bad.append(f"{nid}: 제목 「{q}」은 {MAX_TITLE}자 안에서 하는 일을 「~합니다」 「~했습니다」로 끝내는 평서문으로 쓴다(물음표 없이).")
        if not 영어 and n.get("st") == "now" and re.search(r"(었|았|였|했)습니다\.?$", q.strip()):
            bad.append(f"{nid}: 지금 카드 제목 「{q}」은 하는 일을 「~합니다」로 쓴다. 끝나면 완료로 바꾸며 「~했습니다」로 고친다.")
        return bad
    if n["s"] is None or n["x"] is None:
        return [f"{nid}: v7 노드는 s(소제목 두 칸)와 x(보충 설명, 없으면 [])를 함께 쓴다."]
    want = 소제목.get(n["st"])
    if [h for h, _ in n["s"]] != list(want or ()):
        bad.append(f"{nid}: 「{LABEL_KO.get(n['st'], n['st'])}」 노드의 소제목은 「{want[0]}」 「{want[1]}」 둘이다." if want else f"{nid}: 상태가 이상하다.")
    for h, xs in n["s"]:
        if not (1 <= len(xs) <= MAX_ITEMS):
            bad.append(f"{nid}: 「{h}」 칸이 {len(xs)}줄이다. 1~3줄로 쓴다.")
    if len(n["x"]) > MAX_X:
        bad.append(f"{nid}: 보충 설명이 {len(n['x'])}줄이다. 알짜만 {MAX_X}줄 안으로 남긴다.")
    if template:
        return bad
    if len(q) > MAX_TITLE or not q.endswith("?"):
        bad.append(f"{nid}: 제목 「{q}」은 {MAX_TITLE}자 안의 질문(「?」로 끝남)으로 쓴다.")
    본문 = [s for _, xs in n["s"] for s in xs]
    for s in 본문:
        bad += 문장검사(nid, s, MAX_ITEM, "본문")
    for s in n["x"]:
        bad += 문장검사(nid, s, MAX_X_LEN, "보충 설명")
        if s in 본문:
            bad.append(f"{nid}: 보충 설명 「{s[:24]}…」이 본문과 같다. 본문에 없는 숫자, 정의, 미검증만 쓴다.")
    return bad


LABEL_KO = {"goal": "목표", "done": "완료", "now": "지금", "todo": "대기", "next": "다음", "parked": "보류"}
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("사용: python 궤적점검.py <궤적데이터.json 또는 궤적.html>")
        sys.exit(2)
    problems = check(sys.argv[1])
    for p in problems:
        print("✗", p)
    for w in WARN:
        print("⚠", w)
    print("통과" if not problems else f"위반 {len(problems)}건")
    sys.exit(1 if problems else 0)
