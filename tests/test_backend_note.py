"""The page of a backend no reference engine runs says so.

    python3 -m unittest discover tests
"""
import importlib.util
import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "records"))
# scripts/site.py shares its name with the standard library's site module.
spec = importlib.util.spec_from_file_location("site_pages", SCRIPTS / "site.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


class BackendNote(unittest.TestCase):
    def test_an_opencl_page_says_no_reference_engine_runs_it(self):
        note = " ".join(R.backend_note("opencl"))
        self.assertIn("No reference engine runs a language model through OpenCL", note)

    def test_the_other_backends_have_peers_and_carry_no_note(self):
        for backend in ("rocm", "cuda", "vulkan", "unstated"):
            self.assertEqual(R.backend_note(backend), [])


if __name__ == "__main__":
    unittest.main()
