from pathlib import Path

APP = Path("src/app.py")
VER = Path("src/version.py")
INS = Path("src/installer.iss")
TEST = Path("src/selftest_v130.py")

app = APP.read_text(encoding="utf-8")

# Some real legacy databases never had sales_stage_events. v1.3.x migration
# must create the table before trying to read/remap it.
needle = '''        if version < 4:\n            # v1.3.x expands the relationship/sales curve from 6 to 8 stages.\n'''
insert = '''        # Defensive schema repair for legacy databases. Some installations\n        # reached schema v3 without ever creating sales_stage_events. Ensure it\n        # exists BEFORE the v4 migration queries it. This is idempotent and does\n        # not alter existing rows when the table already exists.\n        c.execute("""CREATE TABLE IF NOT EXISTS sales_stage_events(\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            person_id INTEGER NOT NULL,\n            from_stage INTEGER,\n            to_stage INTEGER NOT NULL DEFAULT 0,\n            reason TEXT DEFAULT '',\n            user_id INTEGER,\n            created_at TEXT NOT NULL DEFAULT ''\n        )""")\n        self.conn.commit()\n\n        if version < 4:\n            # v1.3.x expands the relationship/sales curve from 6 to 8 stages.\n'''
if needle not in app:
    raise SystemExit("v1.3.3 migration insertion point not found")
app = app.replace(needle, insert, 1)
APP.write_text(app, encoding="utf-8")

ver = VER.read_text(encoding="utf-8")
if 'APP_VERSION = "1.3.2"' not in ver:
    raise SystemExit("Expected v1.3.2 version marker missing")
VER.write_text(ver.replace('APP_VERSION = "1.3.2"', 'APP_VERSION = "1.3.3"', 1), encoding="utf-8")

ins = INS.read_text(encoding="utf-8")
if '#define MyAppVersion "1.3.2"' not in ins:
    raise SystemExit("Expected v1.3.2 installer marker missing")
INS.write_text(ins.replace('#define MyAppVersion "1.3.2"', '#define MyAppVersion "1.3.3"', 1), encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test = test.replace('srv=LANServer(st,SERVER_PORT,"1.3.2")', 'srv=LANServer(st,SERVER_PORT,"1.3.3")')

regression_anchor = '''    assert_eq(app.legacy_stage_to_v4("مقدار ناشناخته"),0,"unknown legacy stage safe fallback")\n\n    # LAN/RPC real smoke test including new stage_hint argument.\n'''
regression_insert = '''    assert_eq(app.legacy_stage_to_v4("مقدار ناشناخته"),0,"unknown legacy stage safe fallback")\n\n    # Regression for field crash reported from a legacy DB:\n    # sqlite3.OperationalError: no such table: sales_stage_events\n    st.conn.execute("DROP TABLE IF EXISTS sales_stage_events")\n    st.conn.execute("UPDATE meta SET value='3' WHERE key='schema_version'")\n    st.conn.commit(); st.close()\n    st=app.Store()\n    assert_eq(st.schema_version,4,"missing-stage-table migrated schema")\n    tbl=st.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales_stage_events'").fetchone()\n    assert tbl is not None, "sales_stage_events was not recreated during migration"\n    cols={r[1] for r in st.conn.execute("PRAGMA table_info(sales_stage_events)").fetchall()}\n    required={"id","person_id","from_stage","to_stage","reason","user_id","created_at"}\n    assert required.issubset(cols), f"sales_stage_events columns missing: {required-cols}"\n\n    # Verify the repaired table is actually writable by the current application schema.\n    st.conn.execute("INSERT INTO sales_stage_events(person_id,from_stage,to_stage,reason,user_id,created_at) VALUES(?,?,?,?,?,?)",(textpid,None,1,"repair-test",manager,app.now_iso()))\n    st.conn.commit()\n\n    # LAN/RPC real smoke test including new stage_hint argument.\n'''
if regression_anchor not in test:
    raise SystemExit("v1.3.3 regression insertion point not found")
test = test.replace(regression_anchor, regression_insert, 1)

test = test.replace('print("CRM v1.3.2 SELFTEST PASSED")', 'print("CRM v1.3.3 SELFTEST PASSED")')
TEST.write_text(test, encoding="utf-8")

print("Applied CRM Farsi v1.3.3 missing-table migration hotfix")
