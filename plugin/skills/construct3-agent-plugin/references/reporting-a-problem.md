# Reporting a problem to the skill's maintainers

How to write up a problem with this skill for its maintainers, in a form
they can turn into a checker rule, a script fix or a pitfall. Read this when
the user asks how to report a problem with the skill, or when a handed-over
change came back from the user with an editor or runtime error twice: then
offer the report once, in one sentence.

The report comes from this session's own context: the errors as they were
pasted or printed, the commands that ran, and what each fix changed. A
maintainer reads it without the project, so it carries the text itself, not
a pointer to it. Give the report to the user in the reply; the user files it
at https://github.com/XHXIAIEIN/Construct3-Agent-Skills/issues. Do not file
it yourself. Before handing it over, leave out what the user may not want
public: names of people, keys and tokens, and file contents beyond the lines
an error names. Shorten a path to the part below the project folder.

## The report

Copy error messages, editor dialog text and console output verbatim: do not
paraphrase or translate them, because a checker rule matches the editor's
own words. Write [unknown] for anything this session does not know, and do
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
