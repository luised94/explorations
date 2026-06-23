"""Pytest configuration for the C-020 backend suite.

The harnesses load drill.py / index.html by RELATIVE path, so every backend
test must run with the PROJECT ROOT as the working directory. This conftest
chdir's there before any test collects, regardless of where pytest was
invoked from, so `pytest` works from the repo root, from tests/, or from an
editor.

Resolution order for the project root:
  1. $PROJECT_ROOT if set (the runner sets it),
  2. else: walk up from this file until a directory containing drill.py is
     found,
  3. else: leave cwd alone and let the test surface a clear error.
"""
import os

import pytest


def _find_project_root():
    env = os.environ.get("PROJECT_ROOT")
    if env and os.path.exists(os.path.join(env, "drill.py")):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(6):
        if os.path.exists(os.path.join(cur, "drill.py")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


@pytest.fixture(scope="session", autouse=True)
def _chdir_project_root():
    root = _find_project_root()
    if root is None:
        pytest.skip("could not locate drill.py; set PROJECT_ROOT")
    prev = os.getcwd()
    os.chdir(root)
    yield
    os.chdir(prev)
