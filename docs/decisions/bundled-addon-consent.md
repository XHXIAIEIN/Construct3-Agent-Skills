# A Bundled Addon Is Installed Only on the User's Word

Date: 2026-10-22

## Problem

A project saved with Bundle addons carries its addons, and the editor asks to
install each one its browser profile lacks before the project opens.
`open_in_editor.py` clicked Install, so did every script that opens a project
through it, and the export answered the dialog the same way. Installing an
addon runs its code in the editor, and an agent opens projects the user
downloaded or was sent: opening one installed whatever it carried, without the
user (R10 of the audit of 2026-10-07). `--install-addon FILE` already installs
a file the user names, which is a different act.

## Options

- Keep clicking Install and name the addon afterwards: the code has run by then.
- Read the project's `addons/` folder before opening and refuse any project
  that has one: it refuses a project whose addons the profile already holds,
  and the editor asks only for the ones it lacks.
- Answer the dialog no, stop with the addon as the dialog and `addons/` name
  it, and install only with a flag the user's yes gives.

## Decision

The third. The script that waits for the project to open answers the
confirmation by Cancel or its close button, never OK, and returns the
dialog's text. `open_in_editor.py` prints `addon <project>` with that text and
each `.c3addon` of the project's `addons/` folder by id, name, version, type
and author, and a line that tells the agent to name it to the user;
`export_project.py` stops with the same text. `--install-bundled-addons`, on
both scripts, clicks Install and names the addon in a `warning:` line. The
profile keeps an installed addon, so the scripts that share the profile then
open the project without the flag; the export's profile is its own and needs
the flag once. The dialogs that the scripts close by an OK button leave this
one to Cancel or close as well.

Unverified: what the editor does after Cancel. The run stops and closes its
tab either way, and no run of a real editor has been made with this change.

## Re-evaluate when

The editor asks before it runs an addon's code in another way, or a run
shows that Cancel leaves the editor in a state the next open cannot clear.
