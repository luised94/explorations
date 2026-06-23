"""Shared backend test support for the C-020 suite (ASCII only).

Three reusable pieces, all extracted from the harvested C-018a..C-019b
harnesses (see tests/README-PATTERNS.md, Pattern 1 and Pattern 4):

  load_drill()        -- import the REAL drill.py as a fresh module object,
                         by file path, so tests exercise shipping code rather
                         than a copy. Each call is an independent module so a
                         test can rebind DATABASE_PATH without disturbing
                         another.
  temp_db(m)          -- make a temp SQLite file, point the module's
                         DATABASE_PATH at it, connect + init_db, return the
                         open connection. The HTTP handlers read the module
                         global DATABASE_PATH, so rebinding it here is what
                         makes WSGI requests hit the temp DB.
  wsgi_get(m, path,..)-- drive the Bottle app directly through its WSGI
                         callable: no server, no socket, no network. Returns
                         (status_string, decoded_body).

Gotcha already paid for (kept here so it is never re-paid): start_response
MUST accept the third exc_info argument -- Bottle passes it, and a 2-arg
callable raises at request time.
"""
import importlib.util
import io
import os
import sys
import tempfile
import uuid


def load_drill(path="drill.py"):
    """Load drill.py from disk as a fresh, uniquely-named module object."""
    name = "drill_under_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def temp_db(m):
    """Create a temp DB, point m.DATABASE_PATH at it, init schema, return conn."""
    dbpath = os.path.join(tempfile.mkdtemp(), "drill.db")
    m.DATABASE_PATH = dbpath
    conn = m.connect(dbpath)
    m.init_db(conn)
    return conn


def wsgi_get(m, path, query_string=""):
    """GET path?query_string through the app's WSGI callable.

    Returns (status_string, body_text). No server is started.
    """
    captured = {}
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "test",
        "SERVER_PORT": "80",
        "wsgi.input": io.BytesIO(),
        "wsgi.errors": sys.stderr,
        "wsgi.url_scheme": "http",
    }

    def start_response(status, headers, exc_info=None):
        # The exc_info third arg is mandatory: Bottle passes it.
        captured["status"] = status

    body = b"".join(m.app(environ, start_response))
    return captured["status"], body.decode("utf-8")


def wsgi_post_json(m, path, payload):
    """POST a JSON body through the WSGI callable. Returns (status, body_text)."""
    import json

    raw = json.dumps(payload).encode("utf-8")
    captured = {}
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_TYPE": "application/json",
        "CONTENT_LENGTH": str(len(raw)),
        "SERVER_NAME": "test",
        "SERVER_PORT": "80",
        "wsgi.input": io.BytesIO(raw),
        "wsgi.errors": sys.stderr,
        "wsgi.url_scheme": "http",
    }

    def start_response(status, headers, exc_info=None):
        captured["status"] = status

    body = b"".join(m.app(environ, start_response))
    return captured["status"], body.decode("utf-8")
