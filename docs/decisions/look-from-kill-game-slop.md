# The Game's Look: What kill-game-slop Adds to the Review

Date: 2026-11-02

## Problem

[kill-game-slop](https://github.com/Ddrubok/kill-game-slop) (MIT, commit
`b1d41ff`) is an engine-agnostic skill that reviews and repairs a game's HUD,
copy, effects and audio. It has no scanner. An agent records the game's
intent, sorts each candidate into one of four judgments and verifies a fix
against a success condition and a preservation condition. This record reads
its `SKILL.md`, its three references, its evals and its one real application,
and compares them with `scripts/review_look.py`,
`scripts/preview_project.py`, `references/verifying-a-change.md`,
`assets/look-manifest.json` and `scripts/check_design.py`.

Task: find what the review of a Construct 3 game can use from it.

## Evidence

| kill-game-slop part | What it does | What this repository does | Change |
|---------------------|--------------|---------------------------|--------|
| Game intent | A brief record of the player's action, feeling, identity to keep, device and scope, inferred from documents first | `tools/design.json` holds the request in its words, the screen and the inputs; `pick_look.py` and `art/references/` hold the identity | None |
| Four judgments | Confirmed defect, hypothesis, optional proposal, preserve | Tiers by what the player loses (`look.severity`); `look.before-the-change` keeps what the change did not bring; step 7 of `verifying-a-change.md` keeps a claim open until the game's values settle it | None |
| No quota of defects | "No confirmed problems" is a valid result | A reply of all no passes; `look-judge-calibration.md` scores judges against a baseline that answers no to everything | None |
| A rule fires only on a demonstrated cost | Unfamiliar placement, nesting depth and a neon glow are no defects by themselves | A finding becomes a rule after a measurement on the official examples, and `layout.focal` and `touch.spacing` were rejected that way | None |
| Rectangle overlap is a candidate only | A label inside its panel is containment | `overlap` leaves out one inside a larger one, one hierarchy, a text and its shadow, an overlay | None |
| Evidence limits | A still shows layout, a recording shows an interval, a report stays attributed | `record` with `watch`, and the reviewer of `recording-describer.md`; step 2 sees a reported bug fail first; `not-checked-is-not-a-pass.md` | None |
| Whole flow and re-entry | Initialization, input, result, exit, re-entry | Step 1 plays each case a second time after a restart; kept plans replay after every change | None |
| Routine event against milestone | Reduce the repeated cue, keep the peak | `motion.frequency` is proposed for the HUD; `feel.md` scales the shake by event | None |
| Reduced motion | Respect the project's existing motion settings | `motion.reduced` is proposed until the examples are read for a setting | None |
| Copy length and tone | Generic hype replaced by the rule and the result | `look-from-unslop.md` keeps game text under event design; `text.placeholder` and `longest=` hold the rest | None |
| Slop score | Turned down: verify a success condition, not a score | Findings and yes answers, each with a place | None |
| Edit specification when the editor is out of reach | Target, change, scope, status, marked unapplied | `open_in_editor.py` drives the editor, and exit 3 says that no check ran | None |
| Three-arm eval: generic review, brief principles, full skill | Fresh conversations, a judge key kept apart, controls that must be preserved. All three arms scored the same, and the skill gained no rule from it | `grade.py` and `compare.py` test arms by permutation, and `judge_look.py` holds screenshots out | None |
| Relevant moments | Reach a reachable coincidence of two transient things, such as a toast over a timing cue, and judge it | Proposal 1 (below) | Proposed |
| State truth | A shown word or mark must match the state it claims: "Ready" with 0.8 s left, a prompt for the other player's keys | Proposal 2 (below) | Proposed |
| Preservation condition | Before a fix, name what must stay, and check it after the fix | The hand-over gives before, after and why. No step names what the fix must keep | Re-evaluate (below) |

### Two gaps at the level of the code

`review_look.py` calls `findings()` on instances it reads after `goToLayout`
and a settle time. Its data states change Texts and counts, and they create
no event. So a toast, a hint or a banner that events show for a moment is on
screen only by chance. `verifying-a-change.md` sends a scene that the flow
sets up to a plan's `shot` step, and `preview_project.screenshot()` writes
pixels and a blank test. The `text`, `overlap`, `stacked` and `edge` checks
do not run there, so an agent's own reading of its frame is the only check.

`check_design.py` holds each input's `feedback` to a row the player sees. That
shows that something changed on screen, and it leaves the meaning of the words
open. The questions of `review_look.py` read one screenshot, which cannot show
the state behind a text. Step 5 of `verifying-a-change.md` reads what is on
screen and has no case of a text that claims a state.

## Options

1. **Add the four judgments and the finding record to the look step.** The
   tiers, the new-or-before mark and the open claim cover the same ground, and
   a second vocabulary makes every reply longer.
2. **Add yes/no questions for moments and state truth.** One screenshot cannot
   answer either, and a new question needs a run of `judge_look.py`.
3. **Proposals on the check's own steps and tools.** Chosen: each one changes
   what a run reaches, and each one waits for its eval iteration.

## Decision

Option 3. These two changes are proposed and not made, because a change to a
reference or to what a script prints is an eval iteration
(`dev/AGENTS.md`, "Evals"):

1. **The checks run on a played frame.** A `shot` step prints `text`,
   `overlap`, `stacked` and `edge` findings from the instances at that frame,
   through `review_look.findings(snap, only=...)`. Step 1 of
   `verifying-a-change.md` gains a case: a change that shows something for a
   moment is also played with the other transient thing the flow can show at
   that time, when the game can reach both. A forced coincidence counts as a
   claim left open, as step 7 says. Before the change,
   `dev/evals/sweep_outputs.py` shows what the extra lines print.
2. **A text that claims a state is read against that state.** Step 5 gains a
   case: where a text or a mark claims a state (Saved, Ready, Locked, a full
   bar, a key prompt), the plan reads the value it claims while it shows. A
   Local Storage write shows why: *On item set* and *On error* arrive later, so
   a "Saved" set beside the write claims more than the game knows
   (`Construct3-Cookbook/guides/plugins/localstorage.md`).

## Re-evaluate when

- The owner takes proposal 1 or 2: run its eval iteration, then rewrite this
  record to what holds.
- A run's look fix removes something the user asked to keep: add a preservation
  condition to the look step.
- A generated game hides a timing cue under a notice on a recording: use that
  recording as the case for proposal 1.
- The source's held-out eval with human judges reports a difference between its
  arms: read which cases decided it.
