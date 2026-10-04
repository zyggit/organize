# organize GUI engine

This package is the local, stdio-driven engine for the desktop application.
It deliberately separates **planning** from **execution**:

1. A profile is validated and scanned into an immutable plan.
2. The UI reviews and edits plan selection.
3. The executor applies only the selected plan items and journals every change.

The planning, execution and journaling core uses the Python standard library so
it can be tested independently of the desktop shell. The optional system-trash
integration is provided by `send2trash`. The upstream `organize` package is
kept as the future filter adapter; filesystem mutations remain owned by this
engine so preview, recovery, and undo share one source of truth.

Run the tests from the repository root:

```bash
python3 -m unittest discover -s engine/tests -v
```

Install the runtime dependency before using “move to system trash”:

```bash
python3 -m pip install -r engine/requirements.txt
```

Run the NDJSON server:

```bash
PYTHONPATH=engine/src python3 -m organize_gui.rpc_server
```
