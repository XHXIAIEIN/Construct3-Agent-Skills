# Sound Files Are Measured, and Placeholders Pass the Measure

Date: 2026-10-16

## Problem

`Construct3-Cookbook/guides/recipes/sound.md` states loudness tiers over a reference M, a
true peak ceiling of −3 dBFS for an effect and −12 dBFS for music, the
Opus rates, and a four-layer recipe for placeholder files. The loudness,
the peak and the silence of a sound file are invisible to
`check_project.py`, which tests the extension and the name, and to the
preview, which runs with `--mute-audio`. A file can be twice as loud as
`sound.md` says, or clip when two peaks add, and the check loop says
nothing. A game has placeholder sounds only if something writes them.

## Evidence

Another agent framework's one audio script measures duration, codec,
loudness, true peak and sections with ffmpeg, refuses a mix that clips and
prints the gain that fits, with tests that synthesize their fixtures with
ffmpeg. ffmpeg's `ebur128` and `loudnorm` give the K-weighted measures
`sound.md` names, and a `highpass` before `ebur128` gives its 150 Hz floor.

An official example mixed for a master limiter has its music above the
window of M and effect peaks above −3 dBFS, the case `sound.md` warns of;
the measurer reports both, in a few seconds for a project of ten files.
The gain a loudness finding names, applied with the command it prints,
puts the file inside its window (`dev/tests/test_skill_check_sounds.py`).

## Options

- Measure in Python from decoded samples: needs a decoder and numpy, which
  the scripts do not carry, and a second implementation of BS.1770.
- Measure with ffmpeg's filters and parse what they print: one dependency
  the preview recording already uses, nothing to carry, and the measures
  are the standard's. Without ffmpeg nothing is measured, and the run
  exits 3 (`not-checked-is-not-a-pass.md`).
- Know a file's role by a name prefix: `sound.md` names files after their
  moments, so a prefix would be a new convention the examples do not
  follow.
- Know a file's role from a table beside the generator: the recipe already
  writes the pitched layers of each file to a JSON, so the table that
  names the cues is the natural place, and the generator reads it too.

## Decision

The second and the fourth. `check_sounds.py` runs ffprobe for the stream,
`ebur128` after a 150 Hz high-pass for the loudest 400 ms and 3 s,
`loudnorm` for the integrated loudness and the true peak, and
`silencedetect` for the head and the tail, each file padded with 3 s of
silence so that a sound shorter than a window still gets a value. It
compares the loudest 400 ms of an effect, or the loudest 3 s of a stem,
with its tier's window over M, and the true peak with the ceiling.

M is −30 LUFS, the music at its in-game level, and a music file is set to
M itself, within 1 dB: `sound.md` sets the stems at −30 in the game and
gives the music ceiling, so a file at M plays at the volume the prompt
reasons about without a *Set volume*. `reference_lufs` in the table moves
M for a project that chose another level.

The role comes from `tools/sounds.json`, the cue table: `role` reward,
impact or music, and `tier` key, action or repeat. A file under `music/`
without a cue is a stem; a file under `sounds/` without one is measured
against the whole span of the three tiers, and one finding lists those
files with the cue to add. Head silence over the grid's lead of 0.03 s is
a finding, because a scheduled play then lands late; tail silence is
printed only. A loudness finding names the gain to the middle of the
window and the ffmpeg command that applies it.

`make_sounds.py` reads the same table and renders each cue with ffmpeg's
sources and filters: filtered noise for the attack, harmonic partials for
the body (the bell's for a hard look), the A1 low layer for the key tier,
and a room baked in at the dry-to-wet ratio of the tier. A stem is one
pass of a progression, each note added at an integer sample, plus the
room's tail. Each file is set to the middle of its window on the
measurer's own functions, limited 1 dB under its ceiling, and encoded
Opus at the rates `sound.md` gives. It writes the pitched layers back into
the cue, lists each new file in `project.c3proj`, and ends by measuring
what it wrote, so its last line is the measurer's verdict. Its files carry
the COMMENT tag `c3-sound`, as `prepare_art.py` marks a painting, and a
file without the tag is refused unless `--replace` is given.

`check_sounds.py` measures one file at a time, so a stem's seam when it
is rescheduled, the in-game mix (`sound.md`, "Checking") and the timbre
are checked by a person.

## Re-evaluate when

A game's stems are set in the game by *Set volume* rather than in the
file, so that M in the file differs from M in the game. Or the engine
gains a master limiter, which removes the reason for the peak ceilings.
