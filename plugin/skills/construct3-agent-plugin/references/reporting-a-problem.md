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
it yourself. An issue is public, so before handing the report over, take
out what "What stays out of the report" below lists.

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
- Grok Bot and CodeBuddy keep no transcript file to search. For them and
  for an agent not listed here, ask the user to export the conversation or
  paste its errors. `~/.agents` holds skills, not conversations, and Ollama's
  `~/.ollama/history` holds only the prompts typed into `ollama run`.

A transcript runs to megabytes, so search it for the errors, such as
`error`, `Failed`, `exception` or the addon's id, and read the lines around
each hit, not the whole file. Take the verbatim text, the cause and the fix
from what the session said at the time. Write one report for all of them,
and give the date and the project of each session in its errors' entries.
What the transcripts do not show is [unknown]. Take from a transcript only
the lines about the errors, their causes and their fixes, never the rest of
what the user said in that session.

## What stays out of the report

Go through the whole report once it is written, the verbatim errors
included, and replace each of these:

- Keys, tokens, passwords and cookies, wherever they appear, even inside an
  error or a URL: `<key>`.
- A path: below the project folder, the part from that folder down, as in
  `eventSheets/Game.json`; under the user's home, `~` for the home, as in
  `~/.cursor/projects/...`; any other absolute path, the file's name alone.
  A path then names neither the user's account on the machine nor the
  project's location.
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

The project's own names, its title and the names of its sheets, layouts,
objects, variables and functions, can matter to the error, as when a name
collides or an expression misspells one, and can also be unreleased. Ask
the user which: keep the names they allow, and replace the others with a
role, `Player`, `Enemy`, `Score`, the same replacement for the same name
throughout, so that the events still read. An addon the user wrote is
theirs too: ask before including its code, and include only the lines an
error names.

What is left is the structure: the events, conditions, actions and
expressions by their ids, the parameters and their types, the files, and
the punctuation of each value. Then tell the user, in one sentence, what
was replaced and which values were left as they were, and that they
should read the report before filing it.

## The report

Copy error messages, editor dialog text and console output verbatim: do not
paraphrase or translate them, because a checker rule matches the editor's
own words. The replacements of "What stays out of the report" are the only
change. Write [unknown] for anything this session does not know, and do
not guess.

Use these categories, in this order:

1. **Environment**: the Construct 3 release (e.g. r504, and whether stable
   or beta), the browser, the operating system, the agent and model, and
   the skill's version or commit if known.
2. **Task**: what the user asked for, in one or two sentences, and what was
   made: the sheets, layouts or objects changed, or, for an addon, the
   fields of "The addon" below.
3. **Checks run**: the skill scripts that ran, with their arguments, the
   skill documents and guides read, and what each check reported. Say
   whether `open_in_editor.py` ran with `--preview` (and `--install-addon`
   for an addon), and if not, why not.
4. **Errors**: one entry per error, in the order they happened, each with:
   - Round: after which hand-over to the user it was found
   - Stage: the step where it showed, such as the checker, opening in the
     editor, the Properties Bar, the preview, or the user's own project
   - The error text, verbatim
   - Cause: what it finally turned out to be
   - Fix: which file was changed, and how
   - Catchable before hand-over: whether a check could have caught it
     before the hand-over, and which
5. **Errors in the user's project**: problems that did not show in the
   session's own test but appeared when the user used the result in their
   project. Same format as category 4, plus how the project uses it.
6. **Final state**: whether the result works now, which problems are still
   open, and which were only worked around.

Format an error of categories 4 and 5 as:

```
[Round N][Stage] verbatim error text
  Cause: ...
  Fix: ...
  Catchable before hand-over: ...
```

Wrap the whole report in one code block. After it, say whether it covers
every error, or whether some are no longer in this session's context, and
list the ones remembered without their verbatim text.

## The addon

For a plugin, behavior, effect or theme written for the Addon Manager,
category 2 also gives: the addon's type, what it does, the official sample
under `Construct-Addon-SDK/` it was based on (such as
`effect-sdk/sample-tint`), its `sdk-version`, its `supported-renderers`, and
the list of its files. The stages of category 4 are then: packing,
installing into the editor, the Properties Bar, the preview in the editor,
the runtime under WebGL, the runtime under WebGPU, and the user's own
project. Category 5 also says which object the addon is on, how its
parameters are set, and whether the project has Bundle addons turned on.
