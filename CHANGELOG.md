# Changelog

All notable changes to this project are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

Everything below will ship as 0.1.0.

### Added
- Subway-map roadmap page with a Main line, Side and Extra branches, and a train on the current card.
- Builder and checker: one JSON file in, one HTML page out. The builder stops when the Main line changes without `--메인승인`.
- Editing on the page: drag cards, trash and restore, move the train, link stations, undo up to 50 steps, keyboard shortcuts.
- On claude.ai: ask about a card, let Claude rewrite a card, add a card from the line.
- Edit folding: copy edits made on the page back into the JSON.
- English page (`"language": "en"`) and English data keys.
- Bakery example in Korean and English.
- Claude Code plugin with the `roadmap` skill.

### Fixed
- The subway lines no longer disappear after the page was hidden and shown again.
- The builder accepts an output path only inside the data folder and only a date in `갱신` / `updated`.
