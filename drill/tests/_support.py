"""Shared backend test support for the C-020 suite (ASCII only).

Three reusable pieces, all extracted from the harvested C-018a..C-019b
harnesses (see tests/README-PATTERNS.md, Pattern 1 and Pattern 4):

  load_drill()        -- import the REAL drill.py as a fresh module object,
                         by file path, so tests exercise shipping code rather
                         than a copy. Each call is an independent module so a
                         test can rebind DATABASE_PATH without disturbing
                         another.
  temp_db(m)          -- make a temp SQLite file at the BASELINE schema
                         (init_db only, migrations NOT applied), point the
                         module's DATABASE_PATH at it, return the open
                         connection. For the migration tests, which drive
                         run_migrations against a baseline DB.
  current_db(m)       -- like temp_db but at the CURRENT schema (init_db +
                         run_migrations to SCHEMA_VERSION): the DB a running
                         app actually has. For reader/endpoint tests that touch
                         migration-added columns. The HTTP handlers read the
                         module global DATABASE_PATH, so rebinding it here is
                         what makes WSGI requests hit the temp DB.
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
    """Load drill.py from disk as a fresh, uniquely-named module object.

    drill.py is the thin MAIN composition root + not-yet-extracted layers (HTTP,
    LOGIC). It re-exports the db/config names it imports, so the WSGI-driving
    helpers below (which need connect/init_db/run_migrations and the HTTP-layer
    DATABASE_PATH global) all resolve on this module. Backend tests that exercise
    a specific extracted layer import that layer directly instead -- e.g.
    test_db uses load_db() (D-MOD-3 / D-4: tests import the submodule they
    exercise)."""
    name = "drill_under_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_db(path="db.py"):
    """Load db.py from disk as a fresh, uniquely-named module object (D2).

    The DATABASE layer extracted in D2. Backend tests that exercise DB functions
    directly (test_db) load this rather than the whole drill.py, per D-4. Because
    db imports config, config.py must be importable from the cwd -- conftest
    chdirs to PROJECT_ROOT, so it is."""
    name = "db_under_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_http(path="http_layer.py"):
    """Load http_layer.py from disk as a fresh, uniquely-named module object (D4).

    The HTTP layer (the Bottle app + routes + request helpers). HTTP tests drive
    it through its WSGI callable (m.app) and rebind m.DATABASE_PATH at a temp DB,
    per D-4. Module named http_layer, not http, to avoid shadowing the stdlib
    http package that bottle imports. Because http_layer imports config/db/logic,
    those must be importable from the cwd -- conftest chdirs to PROJECT_ROOT."""
    name = "http_layer_under_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_logic(path="logic.py"):
    """Load logic.py from disk as a fresh, uniquely-named module object (D3).

    The LOGIC layer (pure functions). D3a extracted the arithmetic-engine half;
    D3b adds the general-logic half. Tests exercising LOGIC load this per D-4.
    Because logic imports config, config.py must be importable from the cwd --
    conftest chdirs to PROJECT_ROOT, so it is."""
    name = "logic_under_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path="config.py"):
    """Load config.py from disk as a fresh, uniquely-named module object (D1).

    The CONFIG leaf. Tests read scalars/QTYPE names/etc. from here directly
    rather than via whichever higher layer happens to re-export them, per D-4
    (a test gets a config value from config, not from db's incidental import)."""
    name = "config_under_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Temp directories created by temp_db() WITHOUT a caller-supplied dir_ (the
# mkdtemp fallback). pytest's tmp_path cleans up after itself, but the
# fallback path does not -- so we record those dirs here and an autouse
# session fixture in conftest.py removes them at the end of the run. This
# stops the per-call mkdtemp leak from accumulating across repeated runs.
_FALLBACK_TMP_DIRS = []


def temp_db(m, dir_=None):
    """Create a temp DB at the BASELINE schema (init_db only), return conn.

    init_db lays down the baseline schema and stamps BASELINE_SCHEMA_VERSION; it
    does NOT run migrations. So this DB sits at the baseline, with pending
    migrations unapplied -- which is exactly what the migration tests want (a
    DB to drive run_migrations against). Tests that need a DB at the CURRENT
    schema (readers/endpoints that touch migration-added columns) want
    current_db instead.

    dir_ -- optional directory to put the DB file in. Pass pytest's tmp_path
            so the file is cleaned up automatically with the test's tmp tree.
            When omitted, a mkdtemp() directory is created and registered for
            end-of-session cleanup (see _FALLBACK_TMP_DIRS); this keeps
            standalone/non-pytest use working without leaking.
    """
    if dir_ is None:
        dir_ = tempfile.mkdtemp()
        _FALLBACK_TMP_DIRS.append(dir_)
    dbpath = os.path.join(str(dir_), "drill.db")
    # Set up the DB file itself through the DATABASE layer (connect + init_db are
    # db's, not http's -- an HTTP module has connect via its route imports but not
    # init_db, which is a startup concern). When m IS the db module (test_db /
    # test_migrate), this is the same object; when m is http (test_http), we load
    # db here for the baseline build.
    setup = m if hasattr(m, "init_db") else load_db()
    # DATABASE_PATH is the HTTP-layer request-path global: when the caller passes
    # the http module (WSGI tests), rebind it so the route handlers open the temp
    # DB. Modules without it (db) use the returned conn directly and need none.
    if hasattr(m, "DATABASE_PATH"):
        m.DATABASE_PATH = dbpath
    conn = setup.connect(dbpath)
    setup.init_db(conn)
    return conn


def current_db(m, dir_=None):
    """Create a temp DB at the CURRENT schema (init_db + run_migrations), return conn.

    This is the database a running app actually has: init_db builds and stamps
    the baseline, then run_migrations applies every shipped migration up to
    SCHEMA_VERSION (the exact sequence main() runs at startup). Use this for any
    test that reads or writes through the real readers/endpoints, since those
    touch migration-added columns (e.g. questions.metadata, v2/D1). The clock is
    injected here the same way MAIN does it, so the DATABASE layer stays
    clock-free.

    For the baseline-only DB the migration tests drive run_migrations against,
    use temp_db instead.
    """
    conn = temp_db(m, dir_)
    # run_migrations + the clock read are DATABASE/startup concerns; resolve them
    # from db (same object when m is db; a fresh db load when m is http).
    setup = m if hasattr(m, "run_migrations") else load_db()
    setup.run_migrations(conn, setup.utc_now_iso())
    conn.commit()
    return conn


def cleanup_fallback_tmp_dirs():
    """Remove every mkdtemp fallback directory temp_db created. Idempotent;
    safe to call from a session-scoped teardown."""
    import shutil

    while _FALLBACK_TMP_DIRS:
        path = _FALLBACK_TMP_DIRS.pop()
        shutil.rmtree(path, ignore_errors=True)


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


def wsgi_post_multipart(m, path, fields, file_field, filename, file_bytes):
    """POST a multipart/form-data body through the WSGI callable.

    fields      -- dict of plain form fields (name -> value, stringified).
    file_field  -- the form name of the file part (the import endpoint wants
                   "file"; pass a different name to exercise the missing-part
                   400).
    filename    -- the upload's filename (its extension drives format
                   inference when no explicit format field is given).
    file_bytes  -- the raw upload bytes (pass non-UTF-8 bytes to exercise the
                   decode-error 400).

    Returns (status_string, body_text). Builds the body by hand so the test
    needs no extra dependency; the boundary is unique per call.
    """
    boundary = "----c020test" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(("--" + boundary).encode())
        parts.append(('Content-Disposition: form-data; name="%s"' % name).encode())
        parts.append(b"")
        parts.append(str(value).encode())
    parts.append(("--" + boundary).encode())
    parts.append(
        (
            'Content-Disposition: form-data; name="%s"; filename="%s"'
            % (file_field, filename)
        ).encode()
    )
    parts.append(b"Content-Type: application/octet-stream")
    parts.append(b"")
    parts.append(file_bytes)
    parts.append(("--" + boundary + "--").encode())
    parts.append(b"")
    body = b"\r\n".join(parts)

    captured = {}
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_TYPE": "multipart/form-data; boundary=" + boundary,
        "CONTENT_LENGTH": str(len(body)),
        "SERVER_NAME": "test",
        "SERVER_PORT": "80",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": sys.stderr,
        "wsgi.url_scheme": "http",
    }

    def start_response(status, headers, exc_info=None):
        captured["status"] = status

    out = b"".join(m.app(environ, start_response))
    return captured["status"], out.decode("utf-8")
