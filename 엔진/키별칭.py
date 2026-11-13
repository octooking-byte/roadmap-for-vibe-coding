"""궤적데이터.json을 영어 키로 써도 받는다. 생성기 · 점검기 · 접기가 같이 쓴다.

한국어 키가 정본이다. 영어 키 파일은 읽을 때 한국어로 바꾸고, 다시 쓸 때 영어로 되돌려 사용자의 파일 모양을 지킨다.
"""
위 = {"version": "판", "description": "설명", "output": "출력", "updated": "갱신", "language": "언어",
      "header": "머리", "main_log": "메인기록", "tracks": "트랙", "archive": "보관칸"}
머리 = {"window_title": "창제목", "eyebrow": "작은글", "title": "제목", "lede": "부제목", "footer": "바닥"}
트랙 = {"key": "키", "name": "이름", "nodes": "노드"}
노드 = {"lane": "축", "branch": "갈래", "status": "상태", "date": "날짜", "label": "축이름", "due": "마감",
        "title": "질문", "summary": "요약", "subheads": "소제목", "notes": "보충", "shared": "공통"}
상태 = {"goal": "목표", "done": "완료", "now": "지금", "todo": "대기", "parked": "보류", "next": "다음"}


def _바꿈(d, 표):
    return {표.get(k, k): v for k, v in d.items()}


def 영어인가(data):
    return "version" in data or "tracks" in data


def 한글로(data):
    """영어 키 데이터를 한국어 키로 바꾼다. 한국어 키 데이터는 그대로 돌려준다."""
    if not 영어인가(data):
        for t in data.get("트랙", []) if isinstance(data.get("트랙"), list) else []:
            for n in t.get("노드", []) if isinstance(t, dict) and isinstance(t.get("노드"), list) else []:
                if isinstance(n, dict) and n.get("상태") in 상태:
                    n["상태"] = 상태[n["상태"]]
        return data
    d = _바꿈(data, 위)
    if isinstance(d.get("머리"), dict):
        d["머리"] = _바꿈(d["머리"], 머리)
    d["트랙"] = [_바꿈(t, 트랙) for t in d.get("트랙", [])]
    for t in d["트랙"]:
        t["노드"] = [_바꿈(n, 노드) for n in t.get("노드", [])]
        for n in t["노드"]:
            n["상태"] = 상태.get(n.get("상태"), n.get("상태"))
    return d


def 영어로(data):
    """한글로의 반대. 영어 키 파일에 다시 쓸 때 쓴다."""
    뒤 = lambda 표: {v: k for k, v in 표.items()}
    d = _바꿈(data, 뒤(위))
    if isinstance(d.get("header"), dict):
        d["header"] = _바꿈(d["header"], 뒤(머리))
    d["tracks"] = [_바꿈(t, 뒤(트랙)) for t in d.get("tracks", [])]
    for t in d["tracks"]:
        t["nodes"] = [_바꿈(n, 뒤(노드)) for n in t.get("nodes", [])]
        for n in t["nodes"]:
            n["status"] = 뒤(상태).get(n.get("status"), n.get("status"))
    return d
