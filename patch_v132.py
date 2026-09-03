from pathlib import Path

VER = Path("src/version.py")
INS = Path("src/installer.iss")
TEST = Path("src/selftest_v130.py")

ver = VER.read_text(encoding="utf-8")
if 'APP_NAME = "CRM فروشگاه کاشی"' not in ver:
    raise SystemExit("Expected v1.3.x app name marker missing")
if 'APP_VERSION = "1.3.1"' not in ver:
    raise SystemExit("Expected v1.3.1 version marker missing")
ver = ver.replace('APP_NAME = "CRM فروشگاه کاشی"', 'APP_NAME = "CRM فارسی"', 1)
ver = ver.replace('APP_VERSION = "1.3.1"', 'APP_VERSION = "1.3.2"', 1)
VER.write_text(ver, encoding="utf-8")

ins = INS.read_text(encoding="utf-8")
if '#define MyAppName "CRM فروشگاه کاشی"' not in ins:
    raise SystemExit("Expected installer app name marker missing")
if '#define MyAppVersion "1.3.1"' not in ins:
    raise SystemExit("Expected installer version marker missing")
ins = ins.replace('#define MyAppName "CRM فروشگاه کاشی"', '#define MyAppName "CRM فارسی"', 1)
ins = ins.replace('#define MyAppVersion "1.3.1"', '#define MyAppVersion "1.3.2"', 1)

old_icons = '''[Icons]\nName: "{autodesktop}\\CRM"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\\{#MyAppExeName}"\nName: "{group}\\CRM فارسی"; Filename: "{app}\\{#MyAppExeName}"\n'''
new_icons = '''[Icons]\n; Preserve an existing legacy "CRM فارسی" desktop shortcut (including its cached/custom icon).\n; On a clean install create it only when it does not already exist.\nName: "{autodesktop}\\CRM فارسی"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\\{#MyAppExeName}"; Check: not FileExists(ExpandConstant('{autodesktop}\\CRM فارسی.lnk'))\nName: "{group}\\CRM فارسی"; Filename: "{app}\\{#MyAppExeName}"\n'''
if old_icons not in ins:
    raise SystemExit("Expected v1.3.1 icon block missing")
ins = ins.replace(old_icons, new_icons, 1)

needle = '''[InstallDelete]\n; پاک‌سازی فایل‌های نسخه قبلی فقط از پوشه برنامه؛ دیتای ProgramData دست‌نخورده می‌ماند.\nType: filesandordirs; Name: "{app}\\*"\n'''
replacement = '''[InstallDelete]\n; پاک‌سازی فایل‌های نسخه قبلی فقط از پوشه برنامه؛ دیتای ProgramData دست‌نخورده می‌ماند.\nType: filesandordirs; Name: "{app}\\*"\n; v1.3.0 accidentally created a second blue desktop shortcut named CRM. Remove only that duplicate.\nType: files; Name: "{autodesktop}\\CRM.lnk"\n'''
if needle not in ins:
    raise SystemExit("InstallDelete block not found")
ins = ins.replace(needle, replacement, 1)
INS.write_text(ins, encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test = test.replace('srv=LANServer(st,SERVER_PORT,"1.3.1")', 'srv=LANServer(st,SERVER_PORT,"1.3.2")')
test = test.replace('print("CRM v1.3.1 SELFTEST PASSED")', 'print("CRM v1.3.2 SELFTEST PASSED")')
TEST.write_text(test, encoding="utf-8")

print("Applied CRM فارسی v1.3.2 identity/shortcut hotfix")
