"""궤적데이터.json → 궤적틀.html → 화면 HTML.

쓰는 법:  py -3 궤적만들기.py <궤적데이터.json> [--출력 <시험 경로.html>] [--메인승인 "사용자 원문"]
- 데이터는 v9(맨 위 "판": 9, 칸마다 "id")여야 한다. 옛 데이터는 v9로옮기기.py로 한 번 옮긴다.
- 출력 파일 이름은 데이터의 "출력" 칸이고, 데이터와 같은 폴더에 쓴다.
- 데이터(JSON)와 만든 화면을 점검기(같은 엔진 폴더의 궤적점검.py)로 검사하고, 위반이 있으면 쓰지 않는다.
- 메인 줄(축 0)의 칸 목록이나 순서가 앞 판과 다르면 --메인승인 "사용자 원문" 없이는 만들지 않는다.
  메인 줄은 사용자만 늘린다. 승인 원문은 데이터의 "메인기록"에 한 줄씩 쌓인다.
- 화면은 손으로 고치지 않는다. 고칠 것은 데이터이고, 이 파일을 다시 돌린다.
"""
import hashlib
from html import escape as html_escape
import json
import os
import re
import subprocess
import unicodedata
import sys
from datetime import date
from pathlib import Path

엔진 = Path(__file__).resolve().parent
sys.path.insert(0, str(엔진))
import 키별칭
틀파일 = 엔진 / "궤적틀.html"
점검기 = 엔진 / "궤적점검.py"
상태 = {"목표": "goal", "완료": "done", "지금": "now", "대기": "todo", "보류": "parked", "다음": "next"}


def js(v):
    return json.dumps(v, ensure_ascii=False).replace("<", "\\u003c")


def 노드줄(data):
    줄 = []
    for tr in sorted(data["트랙"], key=lambda t: any(n["상태"] == "지금" for n in t["노드"])):
        메인, 줄끝 = None, {}
        for n in tr["노드"]:
            nid, lane = n["id"], int(n["축"])
            칸 = [f"id:{js(nid)}", f'tk:{js(tr["키"])}', f"lane:{lane}"]
            if lane:
                src = n.get("갈래") or 줄끝.get(lane) or (메인[0] if 메인 else None)
                if src:
                    칸.append(f"from:{js(src)}")
                if n.get("갈래"):
                    칸.append("gl:1")
            칸.append(f'st:{js(상태[n["상태"]])}')
            if n.get("날짜"):
                칸.append(f'w:{js(n["날짜"])}')
            칸.append(f'ax:{js(n.get("축이름") or {0: "메인", 1: "보조", -1: "추가"}[lane])}')
            if n.get("마감"):
                칸.append(f'due:{js(n["마감"])}')
            칸.append(f'q:{js(n["질문"])}')
            if n.get("요약"):
                칸.append(f'sm:{js(n["요약"])}')
            칸.append(f's:{js(n.get("소제목", []))}')
            칸.append(f'x:{js(n.get("보충", []))}')
            줄.append(" {" + ", ".join(칸) + "}")
            if lane == 0:
                메인, 줄끝 = (nid, 0), {}
            else:
                줄끝[lane] = nid
    return 줄


def 해시(b):
    return hashlib.sha256(b).hexdigest()[:12]


def 앞판읽기(앞판):
    """앞 판 화면에서 BUILD와 트랙별 메인 줄 id 순서를 읽는다. 앞 판이 없으면 빈 값."""
    if not 앞판.exists():
        return {}, None
    html = 앞판.read_text(encoding="utf-8")
    m = re.search(r"const BUILD = (\{.*?\});", html)
    build = json.loads(m.group(1)) if m else {}
    메인 = {}
    for nid, tk, lane in re.findall(r'\{id:"([^"]+)", tk:"([^"]+)", lane:(-?\d+)', html):
        if lane == "0":
            메인.setdefault(tk, []).append(nid)
    return build, 메인


def 갱신일(data, 데이터해시, 앞):
    """칸 내용이 앞 판과 같으면 앞 판의 갱신일을 지킨다. 파일 날짜는 형식만 바꿔도 오늘이 되므로 쓰지 않는다."""
    날 = 앞.get("갱신") if 앞.get("data") == 데이터해시 else data.get("갱신") if not 앞 else None
    return 날 if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(날)) else date.today().isoformat()


def 메인차이(앞메인, data):
    """트랙마다 메인 줄 id 순서를 앞 판과 견준다. 다른 트랙만 [(키, 앞, 지금)]로 돌려준다."""
    if 앞메인 is None:
        return []
    지금 = {t["키"]: [n["id"] for n in t["노드"] if int(n["축"]) == 0] for t in data["트랙"]}
    return [(k, 앞메인.get(k, []), 지금.get(k, [])) for k in sorted(set(앞메인) | set(지금)) if 앞메인.get(k, []) != 지금.get(k, [])]


def 데이터쓰기(경로, data):
    원본 = 경로.read_bytes()
    줄바꿈 = "\r\n" if b"\r\n" in 원본 else "\n"
    if 키별칭.영어인가(json.loads(원본.decode("utf-8-sig"))):
        data = 키별칭.영어로(data)
    경로.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").replace("\n", 줄바꿈).encode("utf-8"))


def 점검(경로):
    결과 = subprocess.run([sys.executable, str(점검기), str(경로)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return 결과.returncode, (결과.stdout + 결과.stderr).strip()


def 읽기(경로):
    """데이터 JSON을 읽는다. 메모장이 붙이는 BOM을 떼고, 맥에서 붙여 넣은 풀어쓴 한글(NFD)을 모아쓴다."""
    return 키별칭.한글로(json.loads(unicodedata.normalize("NFC", Path(경로).read_text(encoding="utf-8-sig"))))


def 만들기(데이터경로, 시험출력=None, 메인승인=None):
    데이터경로 = Path(데이터경로).resolve()
    data = 읽기(데이터경로)
    if data.get("판") != 9:
        옮기기 = 엔진 / "v9로옮기기.py"
        sys.exit(f"v9 데이터가 아니다(판 {data.get('판')}). " + (f"먼저 한 번 옮긴다: py -3 {옮기기} {데이터경로}" if 옮기기.exists() else '맨 위에 "판": 9가 있어야 한다. 예시/궤적데이터.json을 복사해 시작한다.'))
    코드, 글 = 점검(데이터경로)
    if 코드:
        print(글)
        sys.exit("데이터 점검 위반이 있어 화면을 만들지 않았다. 데이터를 고친다.")
    머리 = data["머리"]
    본출력 = (데이터경로.parent / str(data.get("출력", "궤적백로그.html"))).resolve()
    if 본출력.suffix != ".html" or not 본출력.is_relative_to(데이터경로.parent):
        sys.exit(f"출력은 데이터 폴더 안의 .html 파일이어야 한다: {data.get('출력')}")
    출력 = Path(시험출력).resolve() if 시험출력 else 본출력
    출력.parent.mkdir(parents=True, exist_ok=True)
    앞, 앞메인 = 앞판읽기(본출력)
    차이 = 메인차이(앞메인, data)
    if 차이 and not 메인승인:
        for k, a, b in 차이:
            print(f"메인 줄이 바뀌었다 · 트랙 {k}: 뺀 칸 {[x for x in a if x not in b]} · 넣은 칸 {[x for x in b if x not in a]} · 순서 {'바뀜' if [x for x in a if x in b] != [x for x in b if x in a] else '같음'}")
        sys.exit('메인 줄은 사용자만 늘린다. 사용자가 시킨 것이면 --메인승인 "사용자 원문"을 붙여 다시 돌린다.')
    틀 = 틀파일.read_text(encoding="utf-8")
    if data.get("언어") not in (None, "ko"):
        틀 = 영어로(틀)
    내용 = json.dumps({"머리": 머리, "트랙": data["트랙"]}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    데이터해시 = 해시(내용)
    엔진해시 = 해시(틀파일.read_bytes() + Path(__file__).read_bytes())
    갱신 = 갱신일(data, 데이터해시, 앞)
    앞해시 = 앞.get("prev", "") if 앞.get("data") == 데이터해시 else 앞.get("data", "")
    트랙 = [{"k": t["키"], "name": t["이름"]} for t in data["트랙"]] if len(data["트랙"]) > 1 else []
    글 = lambda s: re.sub(r"`([^`]+)`", r"<code>\1</code>", html_escape(str(s), quote=False))
    바꿈 = [
        (r"<title>.*?</title>", f'<title>{html_escape(str(머리["창제목"]), quote=False)}</title>'),
        (r"<h1>.*?</h1>", f'<h1>{글(머리["제목"])}</h1>'),
        (r'<p class="lede">.*?</p>', '<p class="lede">' + "<br>".join(글(x) for x in 머리["부제목"]) + "</p>"),
        (r'<div class="foot">.*?</div>', f'<div class="foot">{글(머리["바닥"])}</div>'),
        (r'^const UPDATED = ".*?";', f'const UPDATED = "{갱신}";'),
        (r"^const BUILD = \{.*?\};", "const BUILD = " + json.dumps({"engine": 엔진해시, "data": 데이터해시, "prev": 앞해시, "갱신": 갱신}, ensure_ascii=False) + ";"),
        (r"^const NODES = \[.*?\n\];", "const NODES = [\n" + ",\n".join(노드줄(data)) + "\n];"),
        (r"^const TRACKS = \[\];", "const TRACKS = " + js(트랙) + ";"),
    ]
    html = 틀
    for 자리, 새것 in 바꿈:
        html, 수 = re.subn(자리, lambda _m, s=새것: s, html, count=1, flags=re.S | re.M)
        if 수 != 1:
            sys.exit(f"틀에서 「{자리}」 자리를 못 찾았다. 엔진/궤적틀.html을 확인한다.")
    임시 = 출력.with_name(f"{출력.stem}.점검중.{os.getpid()}.html")
    임시.write_bytes(html.encode("utf-8"))
    코드, 글 = 점검(임시)
    print(글)
    if 코드:
        임시.unlink()
        sys.exit("화면 점검 위반이 있어 화면을 쓰지 않았다. 데이터를 고친다.")
    임시.replace(출력)
    if 차이 and not 시험출력:
        data.setdefault("메인기록", []).extend(f"{date.today().isoformat()} 「{메인승인}」 — {k}: {len(a)}칸 → {len(b)}칸" for k, a, b in 차이)
        데이터쓰기(데이터경로, data)
    print(f"만듦: {출력} · 갱신 {갱신} · 엔진 {엔진해시} · 데이터 {데이터해시}")
    키들 = [t["키"] for t in data["트랙"]] if len(data["트랙"]) > 1 else [None]
    print("저장 문서: " + ", ".join(f"board/edits-{k + '-' if k else ''}{데이터해시}" for k in 키들) + (f" · 앞 판 문서 해시 {앞해시}" if 앞해시 else ""))


def 남은한글(html):
    """주석을 뺀 화면 코드에서 한글이 남은 줄을 돌려준다. 카드 글(NODES)과 머리글은 사용자 글이라 뺀다."""
    본 = re.sub(r"const NODES = \[.*?\n\];", "", html, flags=re.S)
    본 = re.sub(r"<!--.*?-->|/\*.*?\*/", "", 본, flags=re.S)
    본 = re.sub(r'"궤적\|[^"]*"|"갱신":|궤적접기\.py', "", 본)   # 저장 키 이름과 BUILD 칸 이름은 화면에 안 보인다(키를 바꾸면 이미 저장한 편집을 잃는다)
    본 = re.sub(r"<title>.*?</title>", "", 본, count=1, flags=re.S)
    본 = re.sub(r'<h1>.*?</h1>|<div class="(eyebrow|foot)">.*?</div>|<p class="lede">.*?</p>', "", 본, flags=re.S)
    줄들 = [re.sub(r"(?<![:\"'`\\])//.*$", "", 줄) for 줄 in 본.split("\n")]   # 한 줄 주석(주소 속 // 는 남긴다)
    return [줄.strip()[:80] for 줄 in 줄들 if re.search(r"[가-힣]", 줄)]


def 영어로(html):
    for 옛, 새 in json.loads((엔진 / "영어판.json").read_text(encoding="utf-8"))["바꿈"]:
        if 옛 not in html:
            sys.exit(f"영어판.json의 글자열이 틀에 없다: {옛[:60]} — 틀을 고쳤으면 표도 고친다.")
        html = html.replace(옛, 새)
    if 남은 := 남은한글(html):
        sys.exit(f"영어 화면에 한국어가 {len(남은)}줄 남았다. 엔진/영어판.json에 더한다:\n" + "\n".join(남은[:20]))
    return html


def 카드이름(data):
    """화면 카드 머리의 이름을 화면(bandInfo)과 같은 규칙으로 센다.
    목표 카드가 메인1이다. 보조 · 추가는 선을 거슬러 닿는 메인 번호 - 그 메인 아래 그 줄의 순서다."""
    이름 = {}
    for tr in data["트랙"]:
        번호, 메인, 줄끝, 순번, 뿌리 = 0, None, {}, {}, {}
        for n in tr["노드"]:
            nid, lane = n["id"], int(n["축"])
            if lane == 0:
                번호 += 1; 메인, 줄끝 = nid, {}
                이름[nid], 뿌리[nid] = f"메인{번호}", 번호
                continue
            src = n.get("갈래") or 줄끝.get(lane) or 메인
            r = 뿌리.get(src, 번호)
            순번[(lane, r)] = 순번.get((lane, r), 0) + 1
            이름[nid], 뿌리[nid] = f'{"보조" if lane > 0 else "추가"}{r}-{순번[(lane, r)]}', r
            줄끝[lane] = nid
    return 이름


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    인자 = sys.argv[1:]
    쓰는법 = '쓰는 법: py -3 궤적만들기.py <궤적데이터.json> [--출력 <시험 경로.html>] [--메인승인 "사용자 원문"] [--번호]'
    def 값(깃발):
        if 깃발 not in 인자:
            return None
        i = 인자.index(깃발)
        if i + 1 >= len(인자) or 인자[i + 1].startswith("--"):
            sys.exit(f"{깃발} 뒤에 값을 쓴다. {쓰는법}")
        return 인자[i + 1]
    시험, 승인 = 값("--출력"), 값("--메인승인")
    남은 = [a for k, a in enumerate(인자) if not a.startswith("--") and not (k and 인자[k - 1] in ("--출력", "--메인승인"))]
    if len(남은) != 1 or not Path(남은[0]).is_file():
        sys.exit((f"데이터 파일 {남은[0]}이 없다. " if len(남은) == 1 else "") + 쓰는법)
    if "--번호" in 인자:
        d = 읽기(남은[0])
        이름 = 카드이름(d)
        for tr in d["트랙"]:
            for n in tr["노드"]:
                print(f'{이름[n["id"]]}\t{n["id"]}\t{n["상태"]}\t{n["질문"]}')
        sys.exit(0)
    만들기(남은[0], 시험, 승인)
