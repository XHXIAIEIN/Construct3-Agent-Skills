# Reporting a problem to the skill's maintainers

How to write up a problem with this skill for its maintainers, in a form
they can turn into a checker rule, a script fix or a pitfall. Read this when
the user asks how to report a problem with the skill, or when a handed-over
change came back from the user with an editor or runtime error twice: then
offer the report once, in one sentence.

The report comes from this session's own context, or from the sessions the
user names (below): the errors as they were pasted or printed, the commands
that ran, and what each fix changed. A
maintainer reads it without the project, so it carries the text itself, not
a pointer to it. Give the report to the user in the reply; the user files it
at https://github.com/XHXIAIEIN/Construct3-Agent-Skills/issues. Do not file
it yourself. An issue is public, so before handing the report over,
replace what "Private details to replace" below lists.

## When the problems are in other sessions

A user may want to report problems from earlier sessions, often in another
project, that this session never saw. Ask which project and roughly when,
then ask before you read those sessions, because a transcript holds
everything that was said and read in it. The transcripts are kept here:

- Claude Code: `~/.claude/projects/<folder>/<session id>.jsonl`, where
  `<folder>` is the session's working folder with every character other
  than a letter or digit replaced by `-`, as in
  `D--Games-MyGame` for `D:\Games\MyGame`.
- Codex: `~/.codex/sessions/<year>/<month>/<day>/rollout-*.jsonl`. The
  first line, `session_meta`, names the working folder as `cwd`. Older
  sessions are in `~/.codex/archived_sessions/`, compressed as `.jsonl.zst`.
- Cursor: `~/.cursor/projects/<folder>/agent-transcripts/<id>/<id>.jsonl`,
  where `<folder>` is the working folder's path with its separators turned
  into `-`, as in `d-Games-MyGame` for `D:\Games\MyGame`.
- Gemini CLI: `~/.gemini/tmp/<project>/chats/session-*.jsonl`;
  `~/.gemini/projects.json` maps each working folder to its `<project>`.
  Antigravity keeps each conversation as a SQLite file in
  `~/.gemini/antigravity-cli/conversations/<id>.db`, and
  `~/.gemini/antigravity-cli/history.jsonl` names the `workspace` of each
  `conversationId`; read it with Python's `sqlite3`, its `steps` table
  first.
- GitHub Copilot in VS Code: `<VS Code user folder>/workspaceStorage/<hash>/chatSessions/*.jsonl`,
  where `workspace.json` beside `chatSessions` names the folder. The user
  folder is `%APPDATA%\Code\User` on Windows,
  `~/Library/Application Support/Code/User` on macOS and `~/.config/Code/User`
  on Linux. Copilot CLI: `~/.copilot/session-state/<id>/`, whose
  `workspace.yaml` names the folder as `cwd`.
- WorkBuddy: `~/.workbuddy-ai/projects/<folder>/<session id>.jsonl`.
- For an agent not listed here, ask the user to export the conversation or
  paste its errors.

A transcript runs to megabytes, so search it for the errors, such as
`error`, `Failed`, `exception` or the addon's id, and read the lines around
each hit, not the whole file. Take the verbatim text, the cause and the fix
from what the session said at the time. Write one report for all of them,
with the session's date in the tag of each of its errors,
`[R2 0.1.0.1 10-24]`.
What the transcripts do not show is [unknown]. Take from a transcript only
the lines about the errors, their causes and their fixes, never the rest of
what the user said in that session.

## Private details to replace

Go through the whole report once it is written, the verbatim errors
included, and replace each of these:

- Keys, tokens, passwords and cookies, wherever they appear, even inside an
  error or a URL: `<key>`.
- A path: below the project folder, the part from that folder down, as in
  `eventSheets/Game.json`; under the user's home, `~` for the home, as in
  `~/.cursor/projects/...`; any other absolute path, the file's name alone.
  A path then names neither the user's account on the machine nor the
  project's location.
- A file name that the user or an agent chose, such as an added script:
  `name.js`, `name2.js`, `name.json`, numbered in the order they first
  appear and the same throughout, the errors included. Keep the folder, as
  in `c3runtime/name.js`, because it says which side of the addon the file
  is on, and keep the names the SDK and the editor give, such as
  `addon.json`, `instance.js`, `lang/en-US.json` and `project.c3proj`.
- Email addresses, account names (Construct, GitHub, the agent's), the
  machine's name, IP addresses: `<email>`, `<account>`, `<machine>`, `<ip>`.
- Session, device, installation and user ids: `<id>`. A release number and
  an addon's id stay, because they are what the maintainers look up.
- Comments, of events, groups, scripts and shaders: `<comment>`.
- Every text the user wrote into a string: names of people, text the
  player reads, dialogue, story, labels, keys of a dictionary or a JSON
  file. Keep the quotes, escapes and special characters, such as `\"`,
  `\n`, `{0}`, `%`, `&` and the separators of a `tokenat`, and replace the
  words with generic ones, so `"\"Hi, {0}!\n\""` becomes
  `"\"Text, {0}!\n\""`. The structure that the error depends on stays,
  and the content does not.
- Numbers: round each to one significant figure, keeping its sign and
  whether it is whole, so `37.6` becomes `40.0`, `1280` becomes `1000` and
  `-0.27` becomes `-0.3`. Leave the release, `sdk-version`, a version
  string, and a number the error itself is about, such as the value
  outside a range; name the numbers left as they were.
- File contents beyond the lines an error names.

The project's own names do not go in either. Its title is `<project>`, and
each name of a sheet, layout, object, variable or function becomes a role
that says what the thing does, such as `Player`, `Enemy` or `Score`:

- Give a name the same role wherever it appears, and two different names
  two different roles, so that the events still read. If `Hero` becomes
  `Player`, every `Hero` in the report is `Player`.
- Give things that share a name the same role, because the error may come
  from the clash. If an object and a global variable are both named
  `Coins`, both become `Score`, and the report still shows the clash.
- Write `<no such name>` for a name that an expression uses and that
  matches nothing in the project, such as `Plyer` in `Plyer.X`. A role
  would make the expression look correct and hide the cause of the error.

An addon the user wrote is theirs: ask before including its code, and
include only the lines an error names.

What is left is the structure: the events, conditions, actions and
expressions by their ids, the parameters and their types, the files, and
the punctuation of each value. Then tell the user, in one sentence, what
was replaced and which values were left as they were, and that they
should read the report before filing it.

## The report

Each line answers one question a maintainer asks, so the report is a few
fields and the errors, with no prose. Copy error messages, editor dialog
text and console output verbatim: do not paraphrase or translate them,
because a checker rule matches the editor's own words. The replacements
above are the only change. Write [unknown] for what this session does not
know, and do not guess. Leave out a line that does not apply, such as the
addon lines for a game.

```
env:   r504 stable | Edge | Windows 11 | Codex, <model> | skill 1.1.55
task:  a line-drawing plugin with a Width and a Color property
addon: plugin | plugin-sdk/drawingPlugin | sdk-version 2
ran:   check_project.py ok; open_in_editor.py --install-addon --preview not run: <why>

[R1 0.1.0.0][install] verbatim error text
  cause: what it turned out to be
  fix:   c3runtime/instance.js: what changed
  catch: --install-addon | --preview | check_project.py | none

[R3 0.1.0.2][project] verbatim error text
  use:   the object it is on, the parameters set, Bundle addons on or off
  cause: ...

files: + c3runtime/name.js (file-list: no; imported by c3runtime/main.js)
       + lang/zh-CN.json (vs en-US.json: - line-width, + Line-Width)
state: works | open: <error> | worked around: <error>
gaps:  0.1.0.5 and 0.1.0.6 were made outside this session
```

- `env`: the release with stable or beta, the browser, the operating
  system, the agent and model, and the skill's version or commit.
- `addon`: its type, its sample, its `sdk-version`, and for an effect its
  `supported-renderers`.
- `ran`: the skill scripts that ran and what each ended with. Say whether
  `open_in_editor.py --preview` ran, and `--install-addon` for an addon,
  and if not, why not. The documents read do not go here.
- An error: `R` is the hand-over after which it was found, followed by
  the addon's version at that round. The stage is `check`, `open`,
  `properties`, `preview`, `project`, or for an addon `pack`, `install`,
  `webgl` or `webgpu`. Give the message and, of a stack trace, its first
  line and the line that names a file of the project or the addon. An error
  that came back the same is one entry with `×N` after its stage. `catch`
  names the check that would have caught it before the hand-over, or
  `none`.
- `files`: only the files an error is about, `+` added, `-` removed, `~`
  renamed or changed, never the whole list; leave the line out when no
  error is about a file. An added script says whether `addon.json` lists
  it in `file-list` and which file imports it; a lang file says which keys
  it lacks or adds against `en-US.json`. Name the sample by its folder and
  name, not a full path.
- `gaps`: the rounds, versions or sessions this report does not cover.
  The version history goes here only where it shows such a gap.

Wrap the report in one code block, and say after it, in one sentence,
whether it covers every error.
