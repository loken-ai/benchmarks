"""An engine started by fair-run.sh never holds the output of the cell: `engine_start`."""

import os
import re
import signal
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FAIR_RUN = os.path.join(HERE, "..", "scripts", "engines", "fair-run.sh")


def functions(*names):
    with open(FAIR_RUN) as f:
        text = f.read()
    return "".join(re.search(rf"^{n}\(\) \{{.*?^\}}\n", text, re.S | re.M).group(0) for n in names)


class EngineStart(unittest.TestCase):
    def test_a_cell_that_dies_after_an_engine_started_ends_at_once(self):
        with tempfile.TemporaryDirectory() as logs:
            script = (
                "set -euo pipefail\n"
                "kill_all() { :; }\ngpu_env_for() { :; }\nsystemd-run() { return 1; }\n"
                "declare -A E_BIN E_ARGS E_ENV E_CWD E_PROBE E_WANT E_WAIT\n"
                + functions("wait_url", "engine_start")
                # An engine that runs long and never answers, then an error that ends the cell.
                + "E_BIN[x]=sleep; E_ARGS[x]=60; E_PROBE[x]=http://127.0.0.1:9/; E_WAIT[x]=1\n"
                + "engine_start x || true\n"
                + "false\n"
            )
            started = time.monotonic()
            # The cell's output is read through a pipe, as the driver reads it.
            r = subprocess.run(
                ["bash", "-c", 'bash -c "$1" | cat', "bash", script],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "LOGDIR": logs},
            )
            elapsed = time.monotonic() - started
            with open(os.path.join(logs, "x.pid")) as f:
                pid = int(f.read())
            try:
                with open(f"/proc/{pid}/comm") as f:
                    comm = f.read().strip()
            finally:
                os.kill(pid, signal.SIGKILL)
        self.assertLess(elapsed, 15, r.stderr)
        # The pid file names the engine itself, not a shell around it.
        self.assertEqual(comm, "sleep")


if __name__ == "__main__":
    unittest.main()
