from pathlib import Path

VER = Path("src/version.py")
INS = Path("src/installer.iss")
TEST = Path("src/selftest_v130.py")

ver = VER.read_text(encoding="utf-8")
if 'APP_NAME = "CRM فارسی"' not in ver:
    raise SystemExit("Expected CRM Farsi identity missing")
if 'APP_VERSION = "1.3.3"' not in ver:
    raise SystemExit("Expected v1.3.3 version marker missing")
VER.write_text(ver.replace('APP_VERSION = "1.3.3"', 'APP_VERSION = "1.3.4"', 1), encoding="utf-8")

ins = INS.read_text(encoding="utf-8")
if '#define MyAppName "CRM فارسی"' not in ins:
    raise SystemExit("Expected installer CRM Farsi identity missing")
if '#define MyAppVersion "1.3.3"' not in ins:
    raise SystemExit("Expected installer v1.3.3 marker missing")
INS.write_text(ins.replace('#define MyAppVersion "1.3.3"', '#define MyAppVersion "1.3.4"', 1), encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test = test.replace('srv=LANServer(st,SERVER_PORT,"1.3.3")', 'srv=LANServer(st,SERVER_PORT,"1.3.4")')
test = test.replace('print("CRM v1.3.3 SELFTEST PASSED")', 'print("CRM v1.3.4 SELFTEST PASSED")')
TEST.write_text(test, encoding="utf-8")

print("Applied CRM Farsi v1.3.4 black-icon release bump")
