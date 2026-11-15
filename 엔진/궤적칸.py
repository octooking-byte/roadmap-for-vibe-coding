"""궤적 칸 하나를 더하고 화면까지 만든다 — 명령 한 번으로 끝내 도구 호출을 줄인다.

쓰기:
  py -3 궤적칸.py <궤적데이터.json> --축 1 --질문 "단골에게 주문 링크를 보냅니다" --요약 "문자로 주문 링크를 보냈습니다." \
      [--상태 완료|지금|대기|보류|다음] [--뒤 <id>] [--갈래 <id>] [--축이름 꼬리표] [--트랙 <키>] [--id <새 id>] \
      [--보충 "한 줄" ...] [--메인승인 "사용자 원문"] [--출력 <시험 경로.html>]

- 새 id는 그 트랙에서 가장 많이 쓰인 앞글자 + (가장 큰 번호 + 1)이다. --id로 직접 줄 수 있다.
- 자리는 --뒤 칸 바로 아래다. 없으면 완료 칸은 「지금」 칸 바로 위, 나머지는 「지금」 칸 바로 아래에 둔다.
- --상태 지금이면 그 트랙의 옛 「지금」 칸을 완료(오늘 날짜)로 바꾼다. 「지금」은 트랙마다 하나이기 때문이다.
- 완료 · 지금 칸에는 오늘 날짜(MM/DD)를 넣는다.
- 다 쓰면 같은 폴더의 궤적만들기.py를 불러 점검과 화면 만들기까지 한다. 점검에 걸리면 데이터도 되돌린다.
"""
import argparse, collections, datetime, json, os, re, subprocess, sys

여기 = os.path.dirname(os.path.abspath(__file__))


def 새id(노드들: list) -> str:
    짝 = [re.match(r"^([A-Za-z]+)(\d+)$", n.get("id", "")) for n in 노드들]
    짝 = [m for m in 짝 if m]
    if not 짝:
        return "n1"
    앞 = collections.Counter(m.group(1) for m in 짝).most_common(1)[0][0]
    return 앞 + str(max(int(m.group(2)) for m in 짝 if m.group(1) == 앞) + 1)


def main() -> int:
    p = argparse.ArgumentParser(description="궤적 칸 하나를 더하고 화면을 만든다")
    p.add_argument("데이터")
    p.add_argument("--축", type=int, required=True, choices=[-1, 0, 1])
    p.add_argument("--질문", required=True)
    p.add_argument("--요약", required=True)
    p.add_argument("--상태", default="완료", choices=["완료", "지금", "대기", "보류", "다음"])
    p.add_argument("--뒤"); p.add_argument("--갈래"); p.add_argument("--축이름")
    p.add_argument("--트랙"); p.add_argument("--id"); p.add_argument("--마감")
    p.add_argument("--보충", nargs="*", default=[])
    p.add_argument("--메인승인"); p.add_argument("--출력")
    a = p.parse_args()

    원문 = open(a.데이터, encoding="utf-8", newline="").read()
    d = json.loads(원문)
    트랙들 = d.get("트랙") or []
    if a.트랙:
        트랙 = next((t for t in 트랙들 if t.get("키") == a.트랙), None)
    elif len(트랙들) == 1:
        트랙 = 트랙들[0]
    else:
        트랙 = next((t for t in 트랙들 if any(n.get("id") == a.뒤 for n in t["노드"])), None) if a.뒤 else None
    if 트랙 is None:
        print("트랙을 정할 수 없다 — --트랙 <키>를 준다. 있는 키: " + ", ".join(t.get("키", "?") for t in 트랙들))
        return 2
    노드 = 트랙["노드"]
    모든id = {n.get("id") for t in 트랙들 for n in t["노드"]}
    nid = a.id or 새id(노드)
    if nid in 모든id:
        print(f"id {nid}가 이미 있다 — --id로 다른 이름을 준다")
        return 2
    if a.축 != 0 and not a.축이름:
        print("옆 줄 칸에는 --축이름(꼬리표)이 필요하다")
        return 2

    오늘 = datetime.date.today().strftime("%m/%d")
    옛지금 = next((n["id"] for n in 노드 if n.get("상태") == "지금"), None)
    안시작 = next((i for i, n in enumerate(노드) if n.get("상태") in ("대기", "다음", "보류")), len(노드))
    if a.뒤:
        자리 = next((i + 1 for i, n in enumerate(노드) if n.get("id") == a.뒤), None)
        if 자리 is None:
            print(f"--뒤 {a.뒤} 칸이 이 트랙에 없다")
            return 2
    elif a.상태 == "완료":
        자리 = next((i for i, n in enumerate(노드) if n.get("상태") == "지금"), 안시작)
    elif 옛지금:
        자리 = next(i + 1 for i, n in enumerate(노드) if n.get("id") == 옛지금)
    else:
        자리 = 안시작 if a.상태 == "지금" else len(노드)
    if a.상태 == "지금":
        for n in 노드:
            if n.get("상태") == "지금":
                n["상태"], n["날짜"] = "완료", 오늘
    칸 = {"id": nid, "축": a.축}
    if a.갈래: 칸["갈래"] = a.갈래
    칸["상태"] = a.상태
    if a.상태 in ("완료", "지금"): 칸["날짜"] = 오늘
    if a.축이름: 칸["축이름"] = a.축이름
    if a.마감: 칸["마감"] = a.마감
    칸.update({"질문": a.질문, "요약": a.요약, "보충": a.보충})

    노드.insert(자리, 칸)
    기준 = 노드[자리 - 1]["id"] if 자리 else None

    줄바꿈 = "\r\n" if "\r\n" in 원문 else "\n"
    새글 = json.dumps(d, ensure_ascii=False, indent=2).replace("\n", 줄바꿈) + 줄바꿈
    open(a.데이터, "w", encoding="utf-8", newline="").write(새글)

    명령 = [sys.executable, os.path.join(여기, "궤적만들기.py"), a.데이터]
    if a.메인승인: 명령 += ["--메인승인", a.메인승인]
    if a.출력: 명령 += ["--출력", a.출력]
    r = subprocess.run(명령)
    if r.returncode != 0:
        open(a.데이터, "w", encoding="utf-8", newline="").write(원문)
        print("만들기가 멈춰 데이터를 되돌렸다 — 위 위반을 고쳐 다시 준다")
        return r.returncode
    print(f"더함: {nid} · 축 {a.축} · {a.상태} · {기준 or '맨 끝'} 아래")
    return 0


if __name__ == "__main__":
    sys.exit(main())
