"""화면에서 고친 것(저장소 편집 문서)을 정본 궤적데이터.json에 옮긴다.

쓰는 법:  py -3 궤적접기.py <궤적데이터.json> <편집.json> [--트랙 <키>] [--시험]
- 편집.json은 저장소 문서(board/edits-<트랙>-<데이터해시>)의 data를 그대로 저장한 파일이다.
- 트랙이 여럿인 데이터는 --트랙으로 어느 트랙의 편집인지 정한다.
- 화면과 같은 차례로 얹는다: 새 칸 → 줄 옮김 → 상태 → 글 → 순서. 버린 칸은 옮기지 않고 보고만 한다.
- --시험이면 데이터 파일을 쓰지 않고 건수만 찍는다.
- 순서를 지킨다: 접기 → 만들기 → 발행 확인 → 저장소 비우기. 비우기를 먼저 하면 발행이 실패했을 때 편집이 사라진다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import 키별칭
from 궤적점검 import 갈래틀림

상태 = {"goal": "목표", "done": "완료", "now": "지금", "todo": "대기", "parked": "보류", "next": "다음"}


def 새칸(v):
    n = {"id": v["id"], "축": int(v.get("lane", 0)), "상태": 상태[v["st"]]}
    if v.get("w"):
        n["날짜"] = v["w"]
    if v.get("ax") and n["축"]:
        n["축이름"] = v["ax"]
    n["질문"] = v["q"]
    if v.get("sm"):
        n["요약"] = v["sm"]
    if any(xs for _, xs in v.get("s", [])):
        n["소제목"] = v["s"]
    n["보충"] = v.get("x", [])
    return n


def 접기(data, 편집, 키=None):
    """data를 고쳐 돌려주고, 사람이 읽는 보고 줄 목록을 함께 돌려준다."""
    트랙들 = data["트랙"]
    if 키 is None:
        if len(트랙들) != 1:
            sys.exit("트랙이 여럿이다. --트랙 <키>로 어느 트랙의 편집인지 정한다.")
        tr = 트랙들[0]
    else:
        tr = next((t for t in 트랙들 if t["키"] == 키), None) or sys.exit(f"트랙 {키}가 없다.")
    노드 = tr["노드"]
    찾기 = lambda i: next((n for n in 노드 if n["id"] == i), None)
    모든id = {n["id"] for t in 트랙들 for n in t["노드"]}
    보고, 메인 = [], []

    for e in 편집.get("news") or []:
        v = e["node"]
        if v["id"] in 모든id:
            보고.append(f"새 칸 {v['id']}는 이미 있어 건너뜀")
            continue
        n = 새칸(v)
        k = next((i for i, m in enumerate(노드) if m["id"] == e.get("before")), len(노드))
        노드.insert(k, n)
        모든id.add(n["id"])
        r = 찾기(e.get("relink") or "")
        if r and r.get("갈래"):
            r["갈래"] = n["id"]
        보고.append(f"새 칸 {n['id']} 「{n['질문']}」 ({n['상태']}, 축 {n['축']})")
        if n["축"] == 0:
            메인.append(f"메인에 새 칸: {n['id']} 「{n['질문']}」")

    for i, e in (편집.get("axes") or {}).items():
        n = 찾기(i)
        if not n:
            continue
        전 = int(n["축"])
        n["축"] = int(e["lane"])
        if e.get("fix") and e.get("from") and n["축"]:
            n["갈래"] = e["from"]
        else:
            n.pop("갈래", None)
        if e.get("ax") and n["축"]:
            n["축이름"] = e["ax"]
        if n["축"] == 0:
            n.pop("축이름", None)
        보고.append(f"줄 옮김 {i}: 축 {전} → {n['축']}" + (f", 갈래 {n.get('갈래')}" if n.get("갈래") else ""))
        if (전 == 0) != (n["축"] == 0):
            메인.append(f"{'메인에서 보조 · 추가 줄로 내림' if 전 == 0 else '보조 · 추가 줄에서 메인으로 올림'}: {i} 「{n['질문']}」")

    for i, e in (편집.get("status") or {}).items():
        n = 찾기(i)
        if not n or e.get("st") not in 상태:
            continue
        전 = n["상태"]
        n["상태"] = 상태[e["st"]]
        if e.get("w"):
            n["날짜"] = e["w"]
        else:
            n.pop("날짜", None)
        보고.append(f"상태 {i}: {전} → {n['상태']}")

    for i, e in (편집.get("texts") or {}).items():
        n = 찾기(i)
        if not n:
            continue
        n["질문"], n["보충"] = e["q"], e.get("x", [])
        if e.get("sm"):
            n["요약"] = e["sm"]
            n.pop("소제목", None)
        elif any(xs for _, xs in e.get("s", [])):
            n["소제목"] = e["s"]
        보고.append(f"글 {i}: 「{e['q']}」")

    순서 = [i for i in (편집.get("order") or []) if 찾기(i)]
    if 순서:
        앞 = [n["id"] for n in 노드]
        차례 = {i: k for k, i in enumerate(순서)}
        for k, i in enumerate(앞):
            if i not in 차례:
                차례[i] = (차례[앞[k - 1]] if k else -1) + 0.5
        노드.sort(key=lambda n: -1e9 if n["상태"] == "목표" else 차례[n["id"]])
        뒤 = [n["id"] for n in 노드]
        if 앞 != 뒤:
            보고.append(f"순서 1건: {sum(1 for a, b in zip(앞, 뒤) if a != b)}칸 자리가 바뀜")
            m앞 = [i for i in 앞 if int(찾기(i)["축"]) == 0]
            m뒤 = [i for i in 뒤 if int(찾기(i)["축"]) == 0]
            if m앞 != m뒤:
                메인.append("메인 줄 순서가 바뀜")

    for k, n in enumerate(노드):
        g = n.get("갈래")
        j = next((x for x, m in enumerate(노드) if m["id"] == g), None) if g else None
        if g and (j is None or 갈래틀림(노드, k, j)):
            n.pop("갈래")
            보고.append(f"갈래 뺌 {n['id']}: {g} — " + (갈래틀림(노드, k, j) if j is not None else "같은 트랙에 없다") + ". 자동으로 잇는다")

    버림 = [i for i in (편집.get("trash") or []) if 찾기(i)]
    if 버림:
        보고.append(f"버린 칸 {len(버림)}개(옮기지 않음 · 사용자에게 뺄지 묻는다): " + ", ".join(f"{i} 「{찾기(i)['질문']}」" for i in 버림))
        메인 += [f"메인 칸을 버림: {i}" for i in 버림 if int(찾기(i)["축"]) == 0]
    return data, 보고, 메인


def 쓰기(경로, data):
    원본 = 경로.read_bytes()
    줄바꿈 = "\r\n" if b"\r\n" in 원본 else "\n"
    if 키별칭.영어인가(json.loads(원본.decode("utf-8-sig"))):
        data = 키별칭.영어로(data)
    경로.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").replace("\n", 줄바꿈).encode("utf-8"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    인자 = sys.argv[1:]
    if len(인자) < 2:
        sys.exit("쓰는 법: py -3 궤적접기.py <궤적데이터.json> <편집.json> [--트랙 <키>] [--시험] [--판무시]")
    경로 = Path(인자[0])
    import 궤적만들기
    data = 궤적만들기.읽기(경로)
    편집 = json.loads(Path(인자[1]).read_text(encoding="utf-8-sig"))
    편집 = 편집.get("data", 편집)
    키 = 인자[인자.index("--트랙") + 1] if "--트랙" in 인자 and 인자.index("--트랙") + 1 < len(인자) else None
    if "--트랙" in 인자 and (not 키 or 키.startswith("--")):
        sys.exit("--트랙 뒤에 트랙 키를 쓴다(예: --트랙 bake).")
    if 편집.get("tk") and 키 and 편집["tk"] != 키:
        sys.exit(f"이 편집은 트랙 {편집['tk']}에서 했다. --트랙 {편집['tk']}로 접는다.")
    키 = 키 or 편집.get("tk") or None
    지금판 = 궤적만들기.해시(json.dumps({"머리": data["머리"], "트랙": data["트랙"]}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if 편집.get("base") and 편집["base"] != 지금판 and "--판무시" not in 인자:
        sys.exit(f"이 편집은 다른 판({편집['base']}) 위에서 했다. 지금 데이터는 {지금판}이다. 그 사이 데이터에서 바꾼 칸이 옛 값으로 돌아갈 수 있다. 화면을 다시 만들어 연 뒤 다시 고치거나, 알고 접으려면 --판무시를 붙인다.")
    data, 보고, 메인 = 접기(data, 편집, 키)
    for 줄 in 보고:
        print("·", 줄)
    for 줄 in 메인:
        print("★ 메인 줄:", 줄)
    print(f"모두 {len(보고)}건" + (" · 메인 줄이 바뀌어 다음 만들기에 --메인승인이 든다" if 메인 else ""))
    if not 보고:
        print("옮길 것이 없어 파일을 그대로 둔다." + (" --트랙 키가 맞는지 본다." if 키 else ""))
    elif "--시험" not in 인자:
        import tempfile, 궤적점검
        with tempfile.TemporaryDirectory() as 폴더:
            임시 = Path(폴더) / "d.json"
            임시.write_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            위반 = 궤적점검.check_json(str(임시))
        if 위반:
            print("\n".join("✗ " + v for v in 위반))
            sys.exit("접은 결과가 점검을 통과하지 못해 파일을 쓰지 않았다. 화면에서 그 칸을 고친 뒤 다시 내보내거나, 위 줄을 보고 편집 파일을 고친다.")
        쓰기(경로, data)
        print(f"썼다: {경로}")
