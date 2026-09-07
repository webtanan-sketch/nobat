# -*- coding: utf-8 -*-
"""CRM فارسی Professional v2.1.0 updater.
Patches only resources/app.asar of the original v2.x installation.
User data is never opened, modified, moved, or deleted.
"""
from __future__ import annotations
import copy, hashlib, json, os, shutil, struct, sys, time, zipfile
from pathlib import Path

PRODUCT_NAME = "CRM فارسی Professional"
TARGET_VERSION = "2.1.0"
PACKAGE_NAME = "crm-farsi-professional"
EXPECTED_FILES = {
    "main.js", "preload.js", "package.json", "lib/data-engine.js",
    "lib/importer.js", "src/app.js", "src/styles.css"
}


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def load_replacements() -> dict[str, bytes]:
    zpath = resource_path("crm_v210_replacements.zip")
    with zipfile.ZipFile(zpath, "r") as zf:
        names = set(zf.namelist())
        missing = EXPECTED_FILES - names
        if missing:
            raise RuntimeError("بسته بروزرسانی ناقص است: " + ", ".join(sorted(missing)))
        return {name: zf.read(name) for name in EXPECTED_FILES}


def parse_asar(blob: bytes):
    if len(blob) < 16:
        raise RuntimeError("فایل app.asar معتبر نیست.")
    size_payload, header_total = struct.unpack_from("<II", blob, 0)
    if size_payload != 4 or header_total < 12 or header_total > len(blob):
        raise RuntimeError("ساختار app.asar شناخته نشد.")
    payload_size, json_len = struct.unpack_from("<II", blob, 8)
    if json_len <= 0 or json_len > payload_size or 16 + json_len > len(blob):
        raise RuntimeError("هدر app.asar معتبر نیست.")
    try:
        header = json.loads(blob[16:16 + json_len].decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("هدر app.asar خوانده نشد.") from exc
    data_base = 8 + header_total
    if data_base > len(blob):
        raise RuntimeError("آدرس داده‌های app.asar معتبر نیست.")
    return header, data_base


def iter_files(node: dict, prefix: str = ""):
    for name, meta in node.get("files", {}).items():
        full = f"{prefix}/{name}" if prefix else name
        if "files" in meta:
            yield from iter_files(meta, full)
        else:
            yield full, meta


def get_meta(header: dict, file_path: str):
    node = header
    for part in file_path.split("/"):
        node = node.get("files", {}).get(part)
        if node is None:
            return None
    return node


def read_asar_file(blob: bytes, header: dict, data_base: int, file_path: str) -> bytes:
    meta = get_meta(header, file_path)
    if not meta or meta.get("unpacked"):
        raise RuntimeError(f"فایل {file_path} داخل برنامه پیدا نشد.")
    offset = int(meta.get("offset", "0") or 0)
    size = int(meta.get("size", 0) or 0)
    end = data_base + offset + size
    if end > len(blob):
        raise RuntimeError(f"فایل {file_path} داخل app.asar ناقص است.")
    return blob[data_base + offset:end]


def validate_target(blob: bytes):
    header, base = parse_asar(blob)
    package = json.loads(read_asar_file(blob, header, base, "package.json").decode("utf-8"))
    if package.get("name") != PACKAGE_NAME:
        raise RuntimeError("این فایل متعلق به CRM فارسی Professional نیست.")
    for name in EXPECTED_FILES:
        if get_meta(header, name) is None:
            raise RuntimeError(f"نسخه نصب‌شده سازگار نیست؛ فایل {name} پیدا نشد.")
    return package, header, base


def rebuild_asar(source: bytes, replacements: dict[str, bytes]) -> bytes:
    package, header, data_base = validate_target(source)
    header = copy.deepcopy(header)
    contents: dict[str, bytes] = {}
    ordered = []
    for file_path, meta in iter_files(header):
        if meta.get("unpacked"):
            continue
        ordered.append(file_path)
        if file_path in replacements:
            payload = replacements[file_path]
        else:
            offset = int(meta.get("offset", "0") or 0)
            size = int(meta.get("size", 0) or 0)
            payload = source[data_base + offset:data_base + offset + size]
        contents[file_path] = payload

    offset = 0
    for file_path, meta in iter_files(header):
        if meta.get("unpacked"):
            continue
        payload = contents[file_path]
        meta["offset"] = str(offset)
        meta["size"] = len(payload)
        if "integrity" in meta:
            block_size = int(meta.get("integrity", {}).get("blockSize") or 4194304)
            meta["integrity"] = {
                "algorithm": "SHA256",
                "hash": hashlib.sha256(payload).hexdigest(),
                "blockSize": block_size,
                "blocks": [hashlib.sha256(payload[i:i + block_size]).hexdigest() for i in range(0, len(payload), block_size)]
            }
        offset += len(payload)

    json_bytes = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_len = (4 + len(json_bytes) + 3) // 4 * 4
    padding = b"\0" * (payload_len - 4 - len(json_bytes))
    header_pickle = struct.pack("<I", payload_len) + struct.pack("<I", len(json_bytes)) + json_bytes + padding
    size_pickle = struct.pack("<II", 4, len(header_pickle))
    body = b"".join(contents[name] for name in ordered)
    result = size_pickle + header_pickle + body

    pkg2, h2, b2 = validate_target(result)
    if pkg2.get("version") != TARGET_VERSION:
        raise RuntimeError("نسخه بسته بروزرسانی با نسخه مقصد یکسان نیست.")
    for name, expected in replacements.items():
        actual = read_asar_file(result, h2, b2, name)
        if actual != expected:
            raise RuntimeError(f"کنترل نهایی {name} ناموفق بود.")
    return result


def candidate_paths():
    env = os.environ
    roots = []
    for key in ("LOCALAPPDATA", "APPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        value = env.get(key)
        if value:
            roots.append(Path(value))
    direct = []
    local = Path(env.get("LOCALAPPDATA", "")) if env.get("LOCALAPPDATA") else None
    if local:
        direct += [
            local / "Programs" / "crm-farsi-professional" / "resources" / "app.asar",
            local / "Programs" / "CRM فارسی Professional" / "resources" / "app.asar",
            local / "Programs" / "CRM Farsi Professional" / "resources" / "app.asar",
        ]
    for root in roots:
        direct += [
            root / "crm-farsi-professional" / "resources" / "app.asar",
            root / "CRM فارسی Professional" / "resources" / "app.asar",
            root / "CRM Farsi Professional" / "resources" / "app.asar",
        ]
    seen = set()
    for path in direct:
        text = str(path).lower()
        if text not in seen:
            seen.add(text)
            yield path

    try:
        import winreg
        hives = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
        views = [0, getattr(winreg, "KEY_WOW64_64KEY", 0), getattr(winreg, "KEY_WOW64_32KEY", 0)]
        key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        for hive in hives:
            for view in views:
                try:
                    base = winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view)
                except OSError:
                    continue
                with base:
                    count, _, _ = winreg.QueryInfoKey(base)
                    for i in range(count):
                        try:
                            subname = winreg.EnumKey(base, i)
                            with winreg.OpenKey(base, subname) as sub:
                                display = str(winreg.QueryValueEx(sub, "DisplayName")[0])
                                if "crm" not in display.lower() or ("فارسی" not in display and "farsi" not in display.lower()):
                                    continue
                                location = ""
                                try:
                                    location = str(winreg.QueryValueEx(sub, "InstallLocation")[0])
                                except OSError:
                                    pass
                                if location:
                                    p = Path(location) / "resources" / "app.asar"
                                    t = str(p).lower()
                                    if t not in seen:
                                        seen.add(t)
                                        yield p
                        except OSError:
                            continue
    except Exception:
        pass


def find_installation():
    for path in candidate_paths():
        if not path.is_file():
            continue
        try:
            blob = path.read_bytes()
            package, _, _ = validate_target(blob)
            return path, package
        except Exception:
            continue
    return None, None


def select_asar_manually():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        chosen = filedialog.askopenfilename(
            title="فایل app.asar نرم افزار CRM فارسی را انتخاب کنید",
            filetypes=[("app.asar", "app.asar"), ("همه فایل‌ها", "*.*")]
        )
        root.destroy()
        return Path(chosen) if chosen else None
    except Exception:
        return None


def message(title: str, text: str, error: bool = False):
    try:
        import ctypes
        flags = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(None, text, title, flags | 0x00040000)
    except Exception:
        print(title, text)


def run_update(target: Path | None = None):
    replacements = load_replacements()
    if target is None:
        target, package = find_installation()
        if target is None:
            target = select_asar_manually()
    if target is None:
        raise RuntimeError("نصب CRM فارسی Professional پیدا نشد. نرم‌افزار اصلی v2.0.0 باید ابتدا نصب باشد.")
    if not target.is_file():
        raise RuntimeError("فایل app.asar پیدا نشد.")

    original = target.read_bytes()
    package, _, _ = validate_target(original)
    if package.get("version") == TARGET_VERSION:
        return "already", target, None

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(f"app.asar.backup-v{package.get('version','unknown')}-{stamp}")
    shutil.copy2(target, backup)
    if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(original).digest():
        raise RuntimeError("کنترل بکاپ برنامه ناموفق بود؛ بروزرسانی متوقف شد.")

    patched = rebuild_asar(original, replacements)
    temp = target.with_name("app.asar.v210.tmp")
    temp.write_bytes(patched)
    validate_target(temp.read_bytes())
    try:
        os.replace(temp, target)
    except PermissionError as exc:
        try:
            temp.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError("CRM در حال اجراست. برنامه را کامل ببندید و بروزرسانی را دوباره اجرا کنید.") from exc
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    try:
        final = target.read_bytes()
        final_pkg, _, _ = validate_target(final)
        if final_pkg.get("version") != TARGET_VERSION:
            raise RuntimeError("کنترل نسخه نهایی ناموفق بود.")
    except Exception:
        shutil.copy2(backup, target)
        raise
    return "updated", target, backup


def main():
    try:
        target_arg = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.asar') else None
        status, target, backup = run_update(target_arg)
        if status == "already":
            message("CRM فارسی Professional", "نسخه 2.1.0 قبلاً روی این رایانه نصب شده است.")
        else:
            message(
                "بروزرسانی با موفقیت انجام شد",
                "CRM فارسی Professional به نسخه 2.1.0 ارتقا یافت.\n\nاطلاعات مشتریان دست‌نخورده باقی مانده است.\nاز میانبر قبلی CRM فارسی برنامه را اجرا کنید."
            )
        return 0
    except Exception as exc:
        message("بروزرسانی انجام نشد", str(exc), True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
