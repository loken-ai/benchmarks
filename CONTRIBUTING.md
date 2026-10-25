# Contributing

## Runs

Share the runs of your machine as described in the README: file them under `runs/` with
`scripts/add.py` and open a pull request. CI checks every record; run `scripts/check.py` on yours
first. Do not edit a record, and do not add one taken with a protocol other than the campaign's.

## Code

- Python 3 and the standard library only; the scripts run on Linux.
- `python3 -m unittest discover tests` passes before a pull request.
- A change to how a record is filed, checked or described comes with a test in `tests/`.
- One commit, one capability. The subject follows Conventional Commits, in lower case and in the
  imperative (`feat(runs): file a run without the time it was taken`). The body says what was wrong
  as a user saw it, then what the code does now.
- English for code, comments, documentation and commit messages.
