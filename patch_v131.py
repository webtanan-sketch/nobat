from pathlib import Path

APP = Path("src/app.py")
VER = Path("src/version.py")
INS = Path("src/installer.iss")
TEST = Path("src/selftest_v130.py")

app = APP.read_text(encoding="utf-8")

needle = '''def en_digits(value) -> str:\n    return str(value or "").translate(_EN_DIGITS)\n\ndef gregorian_to_jalali(gy, gm, gd):\n'''
insert = '''def en_digits(value) -> str:\n    return str(value or "").translate(_EN_DIGITS)\n\ndef legacy_stage_to_v4(value, default=0):\n    """Convert numeric or legacy Persian sales-stage values to the v4 stage index.\n\n    Older databases may contain Persian labels in INTEGER-affinity SQLite columns.\n    Migration must never fail just because a historic row stores e.g. «ثبت» instead\n    of 0. Unknown values fall back safely while preserving the rest of the record.\n    """\n    if value is None:\n        return default\n    text = en_digits(value).strip().replace("ي", "ی").replace("ك", "ک")\n    text = " ".join(text.replace("‌", " ").split())\n    if not text:\n        return default\n    try:\n        old = int(text)\n    except (TypeError, ValueError):\n        aliases = {\n            "ثبت": 0, "ثبت اولیه": 0,\n            "ارتباط": 1, "اولین ارتباط": 1,\n            "در حال پیگیری": 2, "پیگیری": 2, "مشاوره": 2, "شناخت نیاز": 2,\n            "انتخاب محصول": 3,\n            "پرسش و پاسخ": 4, "قیمت": 4, "اعلام قیمت": 4,\n            "پیش فاکتور": 5,\n            "فاکتور": 6, "فاکتور فروش": 6, "فروش": 6, "فروش موفق": 6,\n            "رضایت": 7, "رضایت مشتری": 7, "پس از فروش": 7,\n        }\n        return aliases.get(text, default)\n    return {0:0, 1:1, 2:2, 3:4, 4:5, 5:6}.get(old, old if 0 <= old <= 7 else default)\n\ndef gregorian_to_jalali(gy, gm, gd):\n'''
if needle not in app:
    raise SystemExit("v1.3.1 helper insertion point not found")
app = app.replace(needle, insert, 1)

old = '''        if version < 4:\n            # v1.3.0 expands the relationship/sales curve from 6 to 8 stages.\n            # Existing records are remapped once so previous customer history is preserved.\n            stage_map = {0:0, 1:1, 2:2, 3:4, 4:5, 5:6}\n            rows=c.execute("SELECT id,sales_stage FROM persons").fetchall()\n            for r in rows:\n                c.execute("UPDATE persons SET sales_stage=? WHERE id=?",(stage_map.get(int(r[1] or 0),0),r[0]))\n            evs=c.execute("SELECT id,from_stage,to_stage FROM sales_stage_events").fetchall()\n            for e in evs:\n                fs=None if e[1] is None else stage_map.get(int(e[1]),int(e[1]))\n                ts=stage_map.get(int(e[2] or 0),int(e[2] or 0))\n                c.execute("UPDATE sales_stage_events SET from_stage=?,to_stage=? WHERE id=?",(fs,ts,e[0]))\n            c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','4')")\n            self.conn.commit(); version=4\n'''
new = '''        if version < 4:\n            # v1.3.x expands the relationship/sales curve from 6 to 8 stages.\n            # Some older databases contain Persian stage labels (e.g. «ثبت») even\n            # in SQLite INTEGER-affinity columns. Convert both numeric and textual\n            # legacy values safely so an upgrade can never be blocked by one row.\n            rows=c.execute("SELECT id,sales_stage FROM persons").fetchall()\n            for r in rows:\n                c.execute("UPDATE persons SET sales_stage=? WHERE id=?",(legacy_stage_to_v4(r[1],0),r[0]))\n            evs=c.execute("SELECT id,from_stage,to_stage FROM sales_stage_events").fetchall()\n            for e in evs:\n                fs=None if e[1] is None else legacy_stage_to_v4(e[1],0)\n                ts=legacy_stage_to_v4(e[2],0)\n                c.execute("UPDATE sales_stage_events SET from_stage=?,to_stage=? WHERE id=?",(fs,ts,e[0]))\n            c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','4')")\n            self.conn.commit(); version=4\n'''
if old not in app:
    raise SystemExit("v1.3.1 migration replacement point not found")
app = app.replace(old, new, 1)
APP.write_text(app, encoding="utf-8")

ver = VER.read_text(encoding="utf-8")
if 'APP_VERSION = "1.3.0"' not in ver:
    raise SystemExit("v1.3.0 version marker missing")
VER.write_text(ver.replace('APP_VERSION = "1.3.0"', 'APP_VERSION = "1.3.1"', 1), encoding="utf-8")

ins = INS.read_text(encoding="utf-8")
if '#define MyAppVersion "1.3.0"' not in ins:
    raise SystemExit("v1.3.0 installer marker missing")
INS.write_text(ins.replace('#define MyAppVersion "1.3.0"', '#define MyAppVersion "1.3.1"', 1), encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test = test.replace('srv=LANServer(st,SERVER_PORT,"1.3.0")', 'srv=LANServer(st,SERVER_PORT,"1.3.1")')
test = test.replace('print("CRM v1.3.0 SELFTEST PASSED")', 'print("CRM v1.3.1 SELFTEST PASSED")')
needle_test = '''    pre=list(st.backup_dir.glob('pre_upgrade_v3_to_v4_*.db'))\n    assert pre, "pre-upgrade backup missing"\n\n    # LAN/RPC real smoke test including new stage_hint argument.\n'''
insert_test = '''    pre=list(st.backup_dir.glob('pre_upgrade_v3_to_v4_*.db'))\n    assert pre, "pre-upgrade backup missing"\n\n    # Regression for the field crash reported from a real upgraded database:\n    # schema-3 rows may store Persian text such as «ثبت» / «فاکتور» in stage columns.\n    textpid=st.add_person(name="قدیمی متنی",mobile="09125550001",roles="مشتری",stars=1,status="زرد",owner_user_id=manager,city="",source="",notes="",photo_path="",whatsapp="",instagram="",telegram="",email="",website="",address="",created_by_user_id=manager)\n    st.conn.execute("UPDATE persons SET sales_stage='ثبت' WHERE id=?",(textpid,))\n    st.conn.execute("INSERT INTO sales_stage_events(person_id,from_stage,to_stage,reason,user_id,created_at) VALUES(?,?,?,?,?,?)",(textpid,"پیش‌فاکتور","فاکتور","legacy text",manager,app.now_iso()))\n    st.conn.execute("UPDATE meta SET value='3' WHERE key='schema_version'")\n    st.conn.commit(); st.close()\n    st=app.Store()\n    assert_eq(st.schema_version,4,"text-stage migrated schema")\n    assert_eq(int(st.person(textpid)["sales_stage"]),0,"legacy text ثبت remapped")\n    hist=st.stage_history(textpid)\n    assert any(int(h["from_stage"] or 0)==5 and int(h["to_stage"] or 0)==6 for h in hist), "legacy Persian event stages not remapped"\n\n    assert_eq(app.legacy_stage_to_v4("ثبت"),0,"legacy ثبت")\n    assert_eq(app.legacy_stage_to_v4("پیش فاکتور"),5,"legacy preinvoice text")\n    assert_eq(app.legacy_stage_to_v4("فاکتور"),6,"legacy invoice text")\n    assert_eq(app.legacy_stage_to_v4("۳"),4,"legacy Persian numeric stage")\n    assert_eq(app.legacy_stage_to_v4("مقدار ناشناخته"),0,"unknown legacy stage safe fallback")\n\n    # LAN/RPC real smoke test including new stage_hint argument.\n'''
if needle_test not in test:
    raise SystemExit("v1.3.1 regression-test insertion point not found")
test = test.replace(needle_test, insert_test, 1)
TEST.write_text(test, encoding="utf-8")

print("Applied CRM v1.3.1 legacy-stage migration hotfix")
