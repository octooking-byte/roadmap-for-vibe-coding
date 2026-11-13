# Installing roadmap-for-vibe-coding (for Claude)

Someone asked you to install this plugin.

## 1. Install the plugin

`/plugin` may not run in the desktop app's Code tab or the VS Code panel, so install from the shell with the Claude Code CLI. The desktop app ships its own `claude` executable, which may not be on PATH (`CLAUDE_CODE_EXECPATH` points to it).

```bash
"${CLAUDE_CODE_EXECPATH:-claude}" plugin marketplace add octooking-byte/roadmap-for-vibe-coding
"${CLAUDE_CODE_EXECPATH:-claude}" plugin install roadmap-for-vibe-coding@roadmap-for-vibe-coding-market
```

## 2. Check Python

The plugin builds pages with Python 3.8 or later. Run `python3 --version` (on Windows `py -3 --version`). If neither works, tell the person to install Python from https://www.python.org/downloads/ and stop.

## 3. Tell the person

- Start a new session. The plugin loads there.
- Then say "start a roadmap for this project".

Do nothing else: no other downloads, no settings changes.
