---
name: roadmap
description: Keep a subway-map roadmap of a project while vibe coding with an AI. Use when the user asks to start, update, or show a roadmap, backlog, progress board, or "where are we" view; when a task on the plan is finished or a new request arrives; or when the user edited the roadmap page and wants the edits folded back into the data.
---

# roadmap — a subway-map roadmap for vibe coding

The roadmap is one JSON file (the source of truth) and one HTML page built from it.
Time flows top to bottom. Three lanes:

| lane | value | what goes there |
|---|---|---|
| Main | `0` | the plan the user made. Only the user adds or removes main cards |
| Side | `1` | new work the user asked for outside the plan |
| Extra | `-1` | cleanup and tooling that helped the main work |

The black strip on top shows the current card. On the page the first main card is named 시작 (Start), the last 마무리 (Finish), the others 메인2, 메인3 … (Main 2 …). Side and extra cards are named after the main card they hang from: 보조6-1 (Side 6-1), 추가6-1 (Extra 6-1).

## Steps

`${CLAUDE_PLUGIN_ROOT}` is the plugin's folder when this is installed as a plugin. If you only cloned the repository, use the path of the cloned folder instead.

1. Look for an existing roadmap (`roadmap.json` / `궤적데이터.json`) and its built `.html` in the project.
2. If there is none, copy `${CLAUDE_PLUGIN_ROOT}/예시/궤적데이터.json` into the project (for example `docs/roadmap/roadmap.json`). Replace the bakery example with the user's plan: set the header and `출력` (below), then the cards. Ask the user for the main plan; do not invent main cards.
3. Edit cards in the JSON (rules below).
4. Build and check:
   `python3 "${CLAUDE_PLUGIN_ROOT}/엔진/궤적만들기.py" <roadmap.json>`
   On Windows use `py -3` and set `PYTHONIOENCODING=utf-8` so Korean messages print.
   The builder checks the data first and writes nothing if a rule is broken; fix the lines it prints and run it again.
   Its last line, `저장 문서: board/edits-…`, is the name under which a claude.ai artifact saves edits made on the page. You only need it when folding edits back.
5. Show the page. If you have a claude.ai artifact publishing tool, publish the built HTML as an artifact with the capabilities `db` (saves edits made on the page) and `sample` (the ✦ ask button and the AI rewrite slot). Republish to the **same URL** every time and write that URL in `roadmap-url.txt` next to the data file. Without such a tool, tell the user to open the HTML file in a browser; drag, undo and saving in that browser still work.
6. Tell the user what changed, card by card, using the card names shown on the page.

## Top-level fields

| field (Korean / English) | rule |
|---|---|
| `판` / `version` | `9` |
| `출력` / `output` | file name of the built page, written next to the JSON (e.g. `roadmap.html`) |
| `머리` / `header` | `창제목` window title · `제목` title, one sentence saying what the project wants to achieve · `부제목` lede, 2–4 lines, one sentence per line (each line becomes a station on the page) · `바닥` footer |
| `트랙` / `tracks` | one or more tracks, each with `키` / `key` (letters), `이름` / `name`, `노드` / `nodes` (the cards) |
| `언어` / `language` | optional `"en"` builds an English page; the checker then checks lengths and still blocks a title that ends in a question mark |
| `설명` / `description` · `갱신` / `updated` | a free note that is not shown, and the "last updated" date the page shows. Only the first build reads `갱신`; after that the page itself carries the day card text last changed, and the JSON value is not rewritten. When you copy the example, rewrite `설명` for the project and delete `갱신`, so the first build uses today |

Use Korean keys throughout or English keys throughout, not a mix. Card statuses may be written either way in both.

## Card fields

| field | rule |
|---|---|
| `id` | starts with a letter, unique, never changed or reused |
| `축` / `lane` | `0`, `1` or `-1` |
| `상태` / `status` | see the status table below. At most one 지금 / `now` per track |
| `날짜` / `date` | `MM/DD`: on a 지금 card the day it started, on a 완료 card the day it finished, on the 목표 card (optional) the day the plan started. Other cards need none. If you do not know a finish date, leave it out instead of guessing; the checker only warns |
| `갈래` / `branch` | side and extra cards only: the `id` of the card they branch from. Without it, a card hangs from the nearest main card above it |
| `마감` / `due` | optional `YYYY-MM-DD` |
| `질문` / `title` | one short sentence, 36 characters or fewer (72 on an English page) |
| `요약` / `summary` | 1–3 sentences, 45 characters or fewer each (90 on an English page): what was done and the result, or what is being done now |
| `보충` / `notes` | 0–3 lines of numbers, definitions or open questions, 60 characters or fewer each (120 on an English page); `[]` if none |
| `축이름` / `label` | required on side and extra cards: a short tag such as "Payments" |

| status (Korean / English) | meaning |
|---|---|
| 목표 / `goal` | the first main card: what "done" looks like for the whole project. One per track, at the top |
| 완료 / `done` | finished |
| 지금 / `now` | being worked on now |
| 다음 / `next` | optional: the one card you will start right after 지금 |
| 대기 / `todo` | planned, not started yet (use this for every other future card) |
| 보류 / `parked` | on hold; say in the summary what it waits for |

- Start a new roadmap with a 목표 card built from the user's goal, then the user's main steps.
- Never delete cards; a roadmap is a record. Finish a card by setting 완료 and today's date, then move 지금 to the next card.
- Keep 완료 and 지금 cards above 대기 and 다음 cards. A 보류 card stays where it was in the plan, even between 완료 cards.
- When the user's notes disagree (a plan table says one thing, the progress log another), follow the newest progress record and tell the user which one you followed.
- When the user asks for something outside the plan, add a Side card: status 대기, a short `축이름`, and `갈래` set to the main card it belongs to. Put it below the last 완료 / 지금 card.
- Blockers and errors go into the card text, not new cards.
- Bold the one phrase that matters: `**「...」**` on a Korean page, `**...**` on an English page.
- On a Korean page the checker also blocks: a title that does not end in 「~니다」 or 「~요」, a question mark in a title, a past-tense title on a 지금 card, a summary sentence that does not end in 「다」 or 「요」, a middle dot (·) listing words inside a sentence, and a comma right after a connective ending such as 「~고,」.

## Main lane is the user's

The first build sets the main lane. After that, if main cards are added, removed or reordered, the builder stops. It compares with the page it built last time, next to the JSON, so keep that HTML file (commit it with the JSON). Run it again with
`--메인승인 "<the user's own words approving the change>"`; the note is kept in the data's `메인기록` (`main_log`).
When you think something belongs on the main lane, put it on Side and ask the user.

## Edits made on the page

On claude.ai the page saves edits in its artifact database under the `저장 문서` name; opened as a file it saves them in the browser and offers "Export changes".
Fold them back before rebuilding:
`python3 "${CLAUDE_PLUGIN_ROOT}/엔진/궤적접기.py" <roadmap.json> <edits.json> [--트랙 <key>]`
Order matters: fold → build → publish and check → clear the stored edits.
The `저장 문서` name changes every time the data changes, so fold stored edits before you edit the JSON. Edits left under an old name are not applied; the page shows a notice that unfolded edits remain.

## Offline

The page loads the Noto Sans KR font from Google Fonts. Without internet it falls back to the device font; everything else works offline.
