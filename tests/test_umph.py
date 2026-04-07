"""Tests for jeff.guard.umph — UMPH signature scanner.

These tests pin the behavior that caught the SQL injection in workplay/
telemetry.py. The 180-vs-13 finding that justified the port.
"""

from jeff.guard.umph import (
    BUILT_IN_SIGNATURES,
    InfectionType,
    critical_infections,
    format_report,
    scan,
    scan_directory,
    summarize,
)


# ── Signature coverage ─────────────────────────────────────────────

def test_built_in_signatures_cover_security_categories():
    """The default signature set must cover the critical security types."""
    types = {s.infection_type for s in BUILT_IN_SIGNATURES}
    assert InfectionType.SQL_INJECTION in types
    assert InfectionType.COMMAND_INJECTION in types
    assert InfectionType.HARDCODED_SECRET in types
    assert InfectionType.INSECURE_DESERIALIZE in types
    assert InfectionType.PATH_TRAVERSAL in types
    assert InfectionType.BACKDOOR in types
    assert InfectionType.KEYLOGGER in types
    assert InfectionType.EXFILTRATION in types


def test_all_critical_sigs_are_severity_8_or_higher():
    critical_types = {
        InfectionType.SQL_INJECTION,
        InfectionType.COMMAND_INJECTION,
        InfectionType.HARDCODED_SECRET,
        InfectionType.INSECURE_DESERIALIZE,
        InfectionType.PATH_TRAVERSAL,
        InfectionType.BACKDOOR,
        InfectionType.KEYLOGGER,
        InfectionType.EXFILTRATION,
    }
    for sig in BUILT_IN_SIGNATURES:
        if sig.infection_type in critical_types:
            assert sig.severity >= 8, f"{sig.name} should be critical severity"


# ── SQL injection detection ───────────────────────────────────────

def test_catches_fstring_sql_injection():
    """The original telemetry.py bug pattern: f-string SQL."""
    code = '''
def record(self, d):
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    self.db.execute(
        f"INSERT INTO decisions ({cols}) VALUES ({placeholders})",
        list(data.values()))
'''
    infections = scan(code, file_path="test.py")
    sql_injections = [i for i in infections if i.infection_type == InfectionType.SQL_INJECTION]
    assert len(sql_injections) >= 1


def test_catches_string_concat_sql():
    code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    infections = scan(code)
    assert any(i.infection_type == InfectionType.SQL_INJECTION for i in infections)


def test_catches_percent_format_sql():
    code = 'db.execute("SELECT * FROM users WHERE name = %s" % name)'
    infections = scan(code)
    assert any(i.infection_type == InfectionType.SQL_INJECTION for i in infections)


def test_allows_parameterized_queries():
    """Parameterized queries should not be flagged."""
    code = '''
cursor.execute(
    "INSERT INTO users (name, age) VALUES (?, ?)",
    (name, age),
)
'''
    infections = scan(code)
    sql_hits = [i for i in infections if i.infection_type == InfectionType.SQL_INJECTION]
    assert len(sql_hits) == 0


def test_sql_arithmetic_is_not_injection():
    """SET score = score + ? is SQL arithmetic, not Python concatenation."""
    code = '''
self.db.execute(
    "UPDATE memories SET score = MIN(score + ?, 1.0) WHERE id = ?",
    (delta, entry_id),
)
'''
    infections = scan(code)
    sql_hits = [i for i in infections if i.infection_type == InfectionType.SQL_INJECTION]
    assert len(sql_hits) == 0


def test_create_table_multiline_not_flagged():
    """CREATE TABLE with triple-quoted literal is safe."""
    code = '''
self.db.execute("""
    CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        actor TEXT
    )""")
'''
    infections = scan(code)
    sql_hits = [i for i in infections if i.infection_type == InfectionType.SQL_INJECTION]
    assert len(sql_hits) == 0


# ── Command injection ─────────────────────────────────────────────

def test_catches_shell_true():
    code = 'subprocess.run(cmd, shell=True)'
    infections = scan(code)
    assert any(i.infection_type == InfectionType.COMMAND_INJECTION for i in infections)


def test_catches_os_system_concat():
    code = 'os.system("rm -rf " + path)'
    infections = scan(code)
    assert any(i.infection_type == InfectionType.COMMAND_INJECTION for i in infections)


# ── Hardcoded secrets ─────────────────────────────────────────────

def test_catches_hardcoded_password():
    code = 'password = "supersecret123456"'
    infections = scan(code)
    assert any(i.infection_type == InfectionType.HARDCODED_SECRET for i in infections)


def test_allows_env_var_lookup():
    code = 'password = os.environ.get("DB_PASSWORD")'
    infections = scan(code)
    secrets = [i for i in infections if i.infection_type == InfectionType.HARDCODED_SECRET]
    assert len(secrets) == 0


# ── Insecure deserialization ──────────────────────────────────────

def test_catches_pickle_loads():
    code = 'data = pickle.loads(untrusted_bytes)'
    infections = scan(code)
    assert any(i.infection_type == InfectionType.INSECURE_DESERIALIZE for i in infections)


# ── Allow marker ──────────────────────────────────────────────────

def test_allow_marker_suppresses_finding():
    code = '''
# umph:allow:command_injection
subprocess.run(cmd, shell=True)
'''
    infections = scan(code)
    cmd_injections = [i for i in infections if i.infection_type == InfectionType.COMMAND_INJECTION]
    assert len(cmd_injections) == 0


def test_allow_marker_only_suppresses_matching_type():
    code = '''
# umph:allow:sql_injection
subprocess.run(cmd, shell=True)
'''
    infections = scan(code)
    # The allow marker is for sql_injection but the finding is command_injection
    cmd_injections = [i for i in infections if i.infection_type == InfectionType.COMMAND_INJECTION]
    assert len(cmd_injections) >= 1


# ── Self-exclusion ────────────────────────────────────────────────

def test_umph_module_excluded_from_self_scan():
    """umph.py contains signature patterns by design — don't match itself."""
    code = '''
patterns = [
    r'os\\.system\\s*\\(\\s*f["\\\']',
    r'execute\\s*\\(\\s*f["\\\']',
]
'''
    infections = scan(code, file_path="jeff/guard/umph.py")
    assert len(infections) == 0


# ── Summary + reporting ───────────────────────────────────────────

def test_summarize_empty():
    s = summarize([])
    assert s["total"] == 0
    assert s["critical"] == 0


def test_summarize_counts_by_severity():
    infections = scan("""
pickle.loads(data)
password = "hardcoded_password_here_long_enough"
""")
    s = summarize(infections)
    assert s["total"] >= 2
    assert s["critical"] >= 2


def test_critical_infections_filter():
    infections = scan('pickle.loads(data)\nif False: pass')
    critical = critical_infections(infections)
    assert all(i.severity >= 8 for i in critical)
    assert len(critical) >= 1


def test_format_report_empty():
    assert "No infections" in format_report([])


def test_format_report_contains_counts():
    infections = scan('pickle.loads(data)')
    report = format_report(infections)
    assert "UMPH:" in report
    assert "critical:" in report


# ── Full codebase scan ────────────────────────────────────────────

def test_jeff_codebase_has_no_critical_findings():
    """Jeff's own codebase should be clean of critical findings.

    This is the regression test for the SQL injection fix. If UMPH ever
    finds a critical severity 8+ issue in Jeff's code, this test fails
    and the fix has to land before shipping.
    """
    infections = scan_directory("jeff")
    critical = [i for i in infections if i.severity >= 8]
    if critical:
        report = format_report(critical)
        raise AssertionError(f"Jeff has critical findings:\n{report}")


# ── Gate integration ──────────────────────────────────────────────

def test_gate_integration_detects_security(tmp_path, monkeypatch):
    """The quality gate should flag security issues via UMPH."""
    monkeypatch.setenv("JEFF_GATE_DIR", str(tmp_path))
    from jeff.gate import check, CognitiveFlaw
    code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    result = check(code, context="unit_test")
    assert not result.passed
    assert CognitiveFlaw.SECURITY in result.flaws


def test_gate_umph_can_be_disabled(tmp_path, monkeypatch):
    """use_umph=False skips UMPH scanning for static-only unit tests."""
    monkeypatch.setenv("JEFF_GATE_DIR", str(tmp_path))
    from jeff.gate import check, CognitiveFlaw
    code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    result = check(code, context="unit_test", use_umph=False)
    # Static checks alone shouldn't catch this short snippet
    assert CognitiveFlaw.SECURITY not in result.flaws
