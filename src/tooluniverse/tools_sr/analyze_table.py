"""Custom tool: analyze_table_with_python (DSR-404b).

Code-runner tool that lets the AIRA agent write Python over the session's
existing AIRA tables. The cache architecture (DSR-402's _raw_study_json,
DSR-403/404a deterministic projections) provides the universal substrate;
this tool provides the open-ended analysis layer.

Two-step UX matching the existing EXECUTE_CODE branch:
  1. PROPOSE: agent submits with approve=false; tool returns the code +
     explanation as Markdown for the user to review.
  2. EXECUTE: agent resubmits with approve=true; tool runs through TU's
     python_code_executor, projects the result back as an AIRA table.

Per-call escape hatch `auto_approve=true` collapses both steps for
trusted/short ops.

The wrapper composes around TU's python_code_executor — no fork. AST
safety, timeout, dependency-install, output capture all live upstream.
The wrapper handles AIRA-side I/O glue: SQLite table introspection
(inject every non-underscore-prefixed table as df_<name>), result-shape
dispatch (list-of-dicts | scalar | base64-encoded image bytes), and
file writes for image results.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

def python_code_executor(**kwargs):
    """Run user code through TU's safety machinery with a single-namespace
    Python-builtin runner.

    Why this exists rather than calling PythonCodeExecutor.run directly:
    upstream's run method invokes the Python builtin runner with two
    distinct namespace dicts (one for globals, one for locals). Top-level
    assignments in user code land in the locals dict, but comprehensions
    and nested defs look up free variables only in their __globals__,
    which is the globals dict. Result: `result = 2 + 2` works, but
    `n = 5; result = [i for i in range(n)]` raises `NameError: n is not
    defined`. This wrapper reuses every upstream helper (AST check,
    allowed-imports update, dependency install, safe-globals construction,
    output capture, timeout, error formatting) but runs the code against
    a single namespace dict so module-level state is visible to nested
    scopes -- restoring expected Python module-level semantics.

    Tests can still patch this single module-level symbol.
    """
    try:
        try:
            from ..python_executor_tool import PythonCodeExecutor
        except (ImportError, SystemError):
            from tooluniverse.python_executor_tool import PythonCodeExecutor
    except ImportError as e:
        raise RuntimeError(
            f"PythonCodeExecutor not available: {e}")

    import builtins as _builtins
    import time

    _py_exec = _builtins.exec  # python builtin runner, not Node child_process

    executor = PythonCodeExecutor({
        "name": "python_code_executor",
        "description": "AST-sandboxed Python execution",
        "parameter": {},
    })

    code = kwargs.get("code", "")
    if not code:
        return {"status": "error",
                "data": executor._format_error_response(
                    ValueError("Code parameter is required"),
                    "ValueError", execution_time=0)}

    timeout = min(max(int(kwargs.get("timeout", 30)), 1), 300)
    return_variable = kwargs.get("return_variable", "result")
    additional_vars = kwargs.get("arguments", {}) or {}

    if "allowed_imports" in kwargs and kwargs["allowed_imports"]:
        executor.allowed_modules.update(kwargs["allowed_imports"])

    is_safe, ast_warnings = executor._check_ast_safety(code)
    if not is_safe:
        return {"status": "error",
                "data": executor._format_error_response(
                    ValueError(
                        f"Code contains forbidden operations: "
                        f"{', '.join(ast_warnings)}"),
                    "SecurityError", execution_time=0)}

    dependencies = kwargs.get("dependencies", []) or []
    if dependencies:
        dep_result = executor._check_and_install_dependencies(
            dependencies,
            kwargs.get("auto_install_dependencies", False),
            kwargs.get("require_confirmation", True),
        )
        if not dep_result["success"]:
            if dep_result.get("requires_confirmation"):
                return {"success": False, "data": {
                    "requires_confirmation": True,
                    "missing_packages": dep_result["missing_packages"],
                    "packages_to_install": dep_result.get("packages_to_install", []),
                    "install_command": dep_result["install_command"],
                    "message": dep_result["message"],
                }}
            return {"status": "error",
                    "data": executor._format_error_response(
                        RuntimeError(dep_result.get("error", dep_result["message"])),
                        "DependencyError", execution_time=0)}

    # Single-namespace evaluation -- the actual fix. Same dict for both
    # globals and locals so module-level assignments in user code are
    # visible to comprehensions and nested defs.
    safe_ns = executor._create_safe_globals(additional_vars)

    start_time = time.time()

    def execute_code():
        return executor._capture_output(_py_exec, code, safe_ns, safe_ns)

    try:
        _, stdout, stderr = executor._execute_with_timeout(execute_code, timeout)
        execution_time = time.time() - start_time
        final_result = safe_ns.get(return_variable, None)
        return {"status": "success",
                "data": executor._format_success_response(
                    final_result, stdout, stderr, execution_time,
                    len(code.splitlines()), ast_warnings)}
    except TimeoutError:
        return {"status": "error",
                "data": executor._format_error_response(
                    TimeoutError(f"Code execution timed out after {timeout} seconds"),
                    "TimeoutError",
                    execution_time=time.time() - start_time)}
    except Exception as e:
        return {"status": "error",
                "data": executor._format_error_response(
                    e, type(e).__name__,
                    execution_time=time.time() - start_time)}


# Default allowed imports for analyse-layer code. The TU executor's own
# DEFAULT_ALLOWED_MODULES already covers most of these; we explicitly add
# pandas (the analysis backbone) and seaborn (plotting). This list is
# union-merged with any per-call `allowed_imports` the agent passes.
_DEFAULT_ALLOWED_IMPORTS = [
    "pandas", "numpy", "scipy", "statistics",
    "matplotlib", "seaborn",
    "io", "base64",
    "json", "re", "math", "datetime",
    "collections", "itertools", "functools",
    "dataclasses", "decimal", "fractions", "random",
    "sympy",
]


# Image-result protocol: agent's code prefixes a base64-encoded payload
# with this sentinel so the wrapper can recognise the result kind. TU's
# executor JSON-stringifies bytes (verified empirically), so b64 is the
# only reliable way to round-trip binary through the response.
_IMAGE_PREFIXES = {
    "PNG_B64:": "png",
    "PDF_B64:": "pdf",
    "SVG_B64:": "svg",
    "JPEG_B64:": "jpeg",
    "JPG_B64:": "jpg",
}


# --- Pure helpers -----------------------------------------------------------

def _introspect_session_tables(db_path: str) -> List[str]:
    """Return non-underscore-prefixed tables in the session SQLite.

    Convention: tables starting with `_` are AIRA-internal (cache,
    metadata) and should not be exposed as DataFrames to user code.
    """
    if not db_path or not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
    except sqlite3.Error as e:
        log.warning("_introspect_session_tables(%s): %s", db_path, e)
        return []
    return [r[0] for r in rows if not r[0].startswith("_")]


def _truncate_cell(v: Any, max_chars: int) -> str:
    s = "" if v is None else str(v)
    return s if len(s) <= max_chars else s[: max_chars - 3] + "..."


def _looks_like_json(val: Any) -> bool:
    """Cheap-then-precise JSON detection on a sample value.

    Cheap pre-filter: starts with '{' or '[' (avoids json.loads on every
    string cell). Precise confirm: try json.loads and require a dict/list
    so plain numeric strings ("123") don't get flagged.
    """
    if not isinstance(val, str):
        return False
    s = val.strip()
    if not s or s[0] not in "{[":
        return False
    try:
        parsed = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(parsed, (dict, list))


def build_session_schema_preview(
    db_path: str,
    max_sample_rows: int = 2,
    max_cell_chars: int = 100,
) -> str:
    """Markdown preview of every non-_-prefixed table in the session.

    Returned as a string for inclusion in PROPOSE_CODE responses so the
    LLM can verify column names, spot JSON-encoded columns, and pick the
    right join keys before resubmitting with approve=true.

    Decisions baked into v1 (call out if you want different):
    - All tables, not just the chained predecessor — multi-table joins
      (population + outcomes, etc.) need both schemas in one preview.
    - Cells truncated at 100 chars — `eligibility_criteria` and similar
      free-text fields routinely exceed 3 KB and would dominate the chat.
    - JSON detection: starts-with-{/[ pre-filter, then `json.loads`
      requiring dict/list (so "123" doesn't get flagged). Only the first
      sampled value per column is checked — cheap but means a column
      with mixed JSON/plain rows may slip through.
    - 2 sample rows — enough to see variation, not enough to bloat.
    - Markdown format — survives Squirro's react-markdown chat renderer
      (per `reference_squirro_chat_markdown` memory).
    """
    if not db_path or not os.path.exists(db_path):
        return ""
    table_names = _introspect_session_tables(db_path)
    if not table_names:
        return ""

    parts: List[str] = ["**Session tables** (auto-injected as `df_<name>`):"]
    for tname in table_names:
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            cur = conn.execute(f"SELECT * FROM [{tname}] LIMIT {max_sample_rows}")
            cols = [d[0] for d in cur.description]
            sample_rows = cur.fetchall()
            count = conn.execute(
                f"SELECT COUNT(*) FROM [{tname}]"
            ).fetchone()[0]
            conn.close()
        except sqlite3.Error as e:
            parts.append(f"- `df_{tname}`: error reading ({e})")
            continue

        json_cols: List[str] = []
        for col_idx, col in enumerate(cols):
            if sample_rows and _looks_like_json(sample_rows[0][col_idx]):
                json_cols.append(col)

        col_list = ", ".join(f"`{c}`" for c in cols)
        parts.append(f"- `df_{tname}` ({count} rows): {col_list}")
        if json_cols:
            parts.append(
                f"  - JSON-encoded (use `json.loads`): "
                f"{', '.join(json_cols)}"
            )
        for i, row in enumerate(sample_rows):
            preview = {
                c: _truncate_cell(v, max_cell_chars)
                for c, v in zip(cols, row)
            }
            parts.append(f"  - sample[{i}]: `{preview}`")
    return "\n".join(parts)


def _read_table_as_records(
    db_path: str, table_name: str,
) -> List[Dict[str, Any]]:
    """Read a SQLite table into a list of dicts. Empty list on error."""
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cur = conn.execute(f"SELECT * FROM [{table_name}]")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        log.warning("_read_table_as_records(%s/%s): %s",
                     db_path, table_name, e)
        return []


def _coerce_result_to_rows(
    result: Any,
) -> Tuple[List[Dict[str, Any]], str]:
    """Map the executor's `result` value into AIRA-table-friendly rows.

    Returns (rows, kind) where kind ∈ {"table", "scalar", "image", "empty"}.
    Image rows carry inline `_image_bytes` and `_image_ext` for the
    caller to materialise to /storage/localfile/.
    """
    if result is None:
        return ([], "empty")

    # pandas DataFrame: convert to list-of-dicts so we can persist to SQLite
    try:
        import pandas as _pd
        if isinstance(result, _pd.DataFrame):
            return (result.to_dict(orient="records"), "table")
        if isinstance(result, _pd.Series):
            return ([{"index": str(i), "value": str(v)} for i, v in result.items()], "table")
    except ImportError:
        pass

    # Image: agent emitted base64-encoded bytes with a recognised prefix.
    if isinstance(result, str):
        for prefix, ext in _IMAGE_PREFIXES.items():
            if result.startswith(prefix):
                payload = result[len(prefix):]
                try:
                    img_bytes = base64.b64decode(payload, validate=True)
                except Exception as e:
                    log.warning("_coerce_result_to_rows: %s payload "
                                "failed b64 decode: %s", prefix, e)
                    return ([{"error": f"invalid {prefix} payload",
                               "error_type": "Base64DecodeError"}], "table")
                return ([{"_image_bytes": img_bytes,
                           "_image_ext": ext}], "image")
        # Plain string scalar
        return ([{"result": result}], "scalar")

    # list-of-dicts: pass through as a table
    if isinstance(result, list):
        if all(isinstance(item, dict) for item in result):
            return (result, "table")
        # Non-dict list: fall through to scalar coercion (one row per item)
        return ([{"result": json.dumps(result, default=str)}], "scalar")

    # Single dict: one-row table
    if isinstance(result, dict):
        return ([result], "table")

    # Scalar: one-row, one-col
    return ([{"result": str(result)}], "scalar")


def _storage_dir() -> str:
    """Where to write image results.

    Resolution order:
      1. AIRA_STORAGE_DIR env var (set by tests + future production override)
      2. /storage/localfile/aira_charts (Squirro container default)
      3. /tmp/aira_charts (local dev fallback)
    """
    return (
        os.environ.get("AIRA_STORAGE_DIR")
        or ("/storage/localfile/aira_charts"
            if os.path.isdir("/storage/localfile") else None)
        or "/tmp/aira_charts"
    )


def _write_image(img_bytes: bytes, ext: str) -> str:
    """Write image bytes to /storage/localfile/, return URL.

    URL form mirrors `tools_sr/export_table.py`'s `/storage/localfile/`
    pattern — direct path that AIRA's chat-renderer will linkify.
    """
    sd = _storage_dir()
    os.makedirs(sd, exist_ok=True)
    h = hashlib.sha256(img_bytes).hexdigest()[:12]
    fname = f"chart-{h}.{ext}"
    fpath = os.path.join(sd, fname)
    with open(fpath, "wb") as f:
        f.write(img_bytes)
    # The URL form depends on whether we're in a Squirro container or a
    # test directory. For Squirro, the path under /storage/localfile/
    # is web-accessible at /storage/localfile/<rest>. For tests, just
    # return a file:// URL to the on-disk path so assertions can verify.
    if sd.startswith("/storage/localfile"):
        rel = os.path.relpath(fpath, "/storage/localfile")
        return f"/storage/localfile/{rel}"
    return f"file://{fpath}"


# --- exec function ----------------------------------------------------------

def exec_analyze_table(arguments, input_table, output_table, db_path):
    """Run LLM-generated Python over the session's AIRA tables.

    Two-step UX:
      - approve=false (default) → PROPOSE: return the code as a render-
        friendly row asking the user for approval.
      - approve=true → EXECUTE: forward to TU's python_code_executor with
        all session tables auto-injected as df_<name> + df alias.
      - auto_approve=true → skip PROPOSE entirely.
    """
    code = arguments.get("code") or ""
    if not code:
        return [{"error": "`code` is required.",
                 "error_type": "ValueError"}]

    approve = bool(arguments.get("approve", False))
    auto_approve = bool(arguments.get("auto_approve", False))

    if not approve and not auto_approve:
        # PROPOSE step
        return [{
            "status": "awaiting_approval",
            "proposed_code": code,
            "explanation": arguments.get("code_explanation", ""),
            "next_action": (
                "Show the proposed_code to the user (rendered as a Python "
                "code block). When the user approves, call this tool again "
                "with the SAME code plus approve=true."
            ),
        }]

    # EXECUTE step

    # 1. Introspect session tables and inject them as pandas DataFrames.
    #    The executor receives `arguments` dict — its values become locals.
    #    We convert list-of-dicts to DataFrames here so the LLM's code can
    #    use full pandas API (df.copy(), df['col'].apply(), groupby, etc.).
    #    Falls back to list-of-dicts only if pandas is unavailable.
    runtime_args: Dict[str, Any] = {}
    try:
        import pandas as _pd

        def _make_df(records):
            return _pd.DataFrame(records)
    except ImportError:
        log.warning("exec_analyze_table: pandas not installed; injecting "
                    "session tables as list-of-dicts. LLM code that expects "
                    "DataFrame methods will fail.")

        def _make_df(records):
            return records
    table_names = _introspect_session_tables(db_path)
    for tname in table_names:
        records = _read_table_as_records(db_path, tname)
        runtime_args[f"df_{tname}"] = _make_df(records)
    # `df` alias for the chained predecessor
    if input_table and input_table in table_names:
        runtime_args["df"] = runtime_args.get(f"df_{input_table}",
                                                _make_df([]))

    # 2. Merge default allowed imports with any per-call extension.
    user_imports = arguments.get("allowed_imports") or []
    if isinstance(user_imports, str):
        user_imports = [s.strip() for s in user_imports.split(",") if s.strip()]
    merged_imports = list(dict.fromkeys(_DEFAULT_ALLOWED_IMPORTS + list(user_imports)))

    # 3. Forward dependencies (auto-install enabled per v1 user steer).
    dependencies = arguments.get("dependencies") or []
    if isinstance(dependencies, str):
        dependencies = [s.strip() for s in dependencies.split(",") if s.strip()]

    # 4. Call TU's executor.
    response = python_code_executor(
        code=code,
        arguments=runtime_args,
        return_variable=arguments.get("return_variable", "result"),
        timeout=int(arguments.get("timeout", 30)),
        allowed_imports=merged_imports,
        dependencies=dependencies,
        auto_install_dependencies=True,
        require_confirmation=False,
    )

    # 5. Unwrap the response.
    data = (response or {}).get("data") or {}
    if not data.get("success"):
        return [{
            "error": data.get("error") or "execution failed",
            "error_type": data.get("error_type") or "Error",
            "stdout": data.get("stdout") or "",
            "stderr": data.get("stderr") or "",
            "traceback": data.get("traceback") or "",
        }]

    raw_result = data.get("result")
    rows, kind = _coerce_result_to_rows(raw_result)

    if kind == "image":
        # Materialise bytes to disk, replace the placeholder row with a
        # chart_url row.
        img_row = rows[0]
        url = _write_image(img_row["_image_bytes"], img_row["_image_ext"])
        return [{
            "chart_url": url,
            "chart_format": img_row["_image_ext"],
            "stdout": data.get("stdout") or "",
        }]

    if kind == "empty":
        return [{
            "result": "",
            "stdout": data.get("stdout") or "",
            "note": "Code ran successfully but `result` was None.",
        }]

    # table or scalar — pass through; if stdout is non-empty, surface it as
    # an extra column on row[0] so the user can see prints.
    if rows and data.get("stdout"):
        rows[0].setdefault("stdout", data["stdout"])
    return rows
