from pathlib import Path

root = Path('src')

# ---------- networking.py ----------
p = root / 'networking.py'
s = p.read_text(encoding='utf-8')
if 'import http.client\n' not in s:
    s = s.replace('import json\n', 'import json\nimport http.client\n', 1)

old = '''def ping_server(host, port=SERVER_PORT, timeout=1.2):
    try:
        req = urllib.request.Request(f"http://{host}:{port}/ping", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data if data.get("ok") else None
    except Exception:
        return None
'''
new = '''def _http_request(host, port, method, path, payload=None, timeout=2.0):
    """Direct LAN HTTP request; intentionally bypasses Windows/system proxies."""
    conn = http.client.HTTPConnection(host, int(port), timeout=float(timeout))
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        headers["Content-Length"] = str(len(body))
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except Exception:
            data = {}
        return response.status, data
    finally:
        try: conn.close()
        except Exception: pass


def tcp_port_open(host, port=SERVER_PORT, timeout=0.8):
    try:
        with socket.create_connection((host, int(port)), timeout=float(timeout)):
            return True
    except OSError:
        return False


def ping_server(host, port=SERVER_PORT, timeout=1.2):
    try:
        status, data = _http_request(host, port, "GET", "/ping", timeout=timeout)
        return data if status == 200 and data.get("ok") else None
    except Exception:
        return None


def diagnose_server(host, port=SERVER_PORT, timeout=1.2):
    host = str(host or "").strip()
    if not host:
        return None, "no_host", "آدرس کامپیوتر سرور مشخص نیست."
    if not tcp_port_open(host, port, min(float(timeout), 0.9)):
        return None, "tcp_blocked", (
            "کامپیوتر سرور در شبکه دیده می‌شود، اما مسیر اصلی CRM باز نیست. "
            "معمولاً Windows Firewall روی کامپیوتر سرور مانع ارتباط است. "
            "نسخه جدید CRM را روی کامپیوتر سرور هم نصب و یک‌بار اجرا کنید."
        )
    try:
        status, data = _http_request(host, port, "GET", "/ping", timeout=timeout)
        if status == 200 and data.get("ok"):
            return data, "ok", "اتصال به سرور آماده است."
        return None, "bad_response", "پورت CRM باز است اما سرویس سرور پاسخ معتبر نمی‌دهد. CRM کامپیوتر اصلی را ببندید و دوباره اجرا کنید."
    except socket.timeout:
        return None, "timeout", "سرور پیدا شد اما پاسخ آن دیر می‌رسد. شبکه یا کامپیوتر اصلی را بررسی کنید."
    except Exception:
        return None, "http_error", "سرور پیدا شد اما ارتباط کامل برقرار نشد. CRM کامپیوتر اصلی را دوباره اجرا کنید."
'''
if old not in s:
    raise SystemExit('v1.1.1 ping_server block not found')
s = s.replace(old, new, 1)

old = '''    def _rpc(self, method, *args, **kwargs):
        payload = json.dumps({"method": method, "args": args, "kwargs": kwargs}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"http://{self.host}:{self.port}/rpc", data=payload, method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.last_ok = False
            raise NetworkError("ارتباط با سرور CRM قطع است. اتصال شبکه و روشن بودن کامپیوتر اصلی را بررسی کنید.") from exc
        if not data.get("ok"):
            raise RuntimeError(data.get("error") or "خطای سرور")
        self.last_ok = True
        return data.get("result")
'''
new = '''    def _rpc(self, method, *args, **kwargs):
        payload = {"method": method, "args": args, "kwargs": kwargs}
        try:
            status, data = _http_request(self.host, self.port, "POST", "/rpc", payload=payload, timeout=8)
        except (TimeoutError, OSError, socket.timeout, http.client.HTTPException) as exc:
            self.last_ok = False
            raise NetworkError("ارتباط با سرور CRM قطع است. کامپیوتر اصلی باید روشن باشد و CRM روی آن باز بماند.") from exc
        except Exception as exc:
            self.last_ok = False
            raise NetworkError("ارتباط با سرور CRM برقرار نشد.") from exc
        if status != 200 or not data.get("ok"):
            raise RuntimeError(data.get("error") or "خطای سرور")
        self.last_ok = True
        return data.get("result")
'''
if old not in s:
    raise SystemExit('v1.1.1 RemoteStore RPC block not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# ---------- app.py ----------
p = root / 'app.py'
s = p.read_text(encoding='utf-8')
s = s.replace(
    'ping_server, load_network_config, save_network_config, clear_network_config)',
    'ping_server, diagnose_server, load_network_config, save_network_config, clear_network_config)', 1)

old = '''                info=ping_server(host,port,0.8) if host else None
                if not info:
                    servers=discover_servers(1.4)
                    if servers:
                        host=servers[0]["host"]; port=int(servers[0].get("port",SERVER_PORT)); save_network_config({"mode":"client","host":host,"port":port}); self.net_config={"mode":"client","host":host,"port":port}
                    else:
                        self.network_connect_screen(); return
                self.store=RemoteStore(host,port,"کاربر شبکه")
'''
new = '''                info=ping_server(host,port,1.0) if host else None
                if not info:
                    servers=discover_servers(1.4)
                    ready=None
                    for candidate in servers:
                        c_host=candidate.get("host") or ""; c_port=int(candidate.get("port",SERVER_PORT))
                        c_info,_,_=diagnose_server(c_host,c_port,1.2)
                        if c_info:
                            ready=(candidate,c_info); break
                    if ready:
                        item,_=ready; host=item["host"]; port=int(item.get("port",SERVER_PORT)); save_network_config({"mode":"client","host":host,"port":port}); self.net_config={"mode":"client","host":host,"port":port}
                    else:
                        self.network_connect_screen(); return
                self.store=RemoteStore(host,port,"کاربر شبکه")
'''
if old not in s:
    raise SystemExit('v1.1.1 client init block not found')
s = s.replace(old, new, 1)
s = s.replace('''        except NetworkError:
            self.network_connect_screen()
''','''        except NetworkError as exc:
            self.network_connect_screen(connection_error=str(exc))
''',1)
s = s.replace('def network_connect_screen(self, auto_start=True):', 'def network_connect_screen(self, auto_start=True, connection_error=""):', 1)

needle = '''        retry_btn=ttk.Button(actions,text="جستجوی دوباره"); retry_btn.pack(side="right",padx=5)

'''
if needle not in s:
    raise SystemExit('v1.1.1 connection buttons block not found')
s = s.replace(needle, '''        retry_btn=ttk.Button(actions,text="جستجوی دوباره"); retry_btn.pack(side="right",padx=5)
        if connection_error:
            status.configure(text="● اتصال قبلی کامل نشد",fg="#b45309")
            detail.configure(text=connection_error,fg="#8a4b08")

''', 1)

old = '''        def connect_found():
            item=self._found_server
            if not item: return
            host=item["host"]; port=int(item.get("port",SERVER_PORT))
            self.net_config={"mode":"client","host":host,"port":port}
            save_network_config(self.net_config)
            status.configure(text="● در حال اتصال…",fg="#2563eb")
            self.after(150,self.init_network_store)
'''
new = '''        def connect_found():
            item=self._found_server
            if not item: return
            host=item["host"]; port=int(item.get("port",SERVER_PORT))
            status.configure(text="● در حال تست اتصال…",fg="#2563eb")
            detail.configure(text="ارتباط اصلی CRM در حال بررسی است.",fg="#64748b")
            connect_btn.configure(state="disabled"); retry_btn.configure(state="disabled")
            def worker():
                info,code,msg=diagnose_server(host,port,1.8)
                def done():
                    retry_btn.configure(state="normal")
                    if not info:
                        status.configure(text="● سرور دیده شد ولی اتصال کامل نیست",fg="#b45309")
                        detail.configure(text=msg,fg="#8a4b08")
                        connect_btn.configure(state="normal")
                        return
                    self.net_config={"mode":"client","host":host,"port":port}
                    save_network_config(self.net_config)
                    status.configure(text="● اتصال برقرار شد",fg="#15803d")
                    detail.configure(text=f"کامپیوتر سرور: {item.get('name') or item.get('computer') or host}\nدر حال ورود به CRM مشترک…",fg="#334155")
                    self.after(250,self.init_network_store)
                try:self.after(0,done)
                except Exception:pass
            threading.Thread(target=worker,daemon=True).start()
'''
if old not in s:
    raise SystemExit('v1.1.1 connect_found block not found')
s = s.replace(old, new, 1)

old = '''        def finish(items):
            self._discovering_server=False
            retry_btn.configure(state="normal")
            if items:
                item=items[0]; self._found_server=item
                server_name=item.get("name") or item.get("computer") or "CRM Server"
                status.configure(text="● سرور پیدا شد",fg="#15803d")
                detail.configure(text=f"کامپیوتر سرور: {server_name}\nبرای ورود به اطلاعات مشترک، «اتصال» را بزنید.",fg="#334155")
                connect_btn.configure(state="normal")
            else:
                self._found_server=None
                status.configure(text="● سرور پیدا نشد",fg="#b45309")
                detail.configure(text="مطمئن شوید کامپیوتر اصلی روشن است و هر دو سیستم به یک مودم یا شبکه وصل‌اند؛ سپس «جستجوی دوباره» را بزنید.",fg="#64748b")
                connect_btn.configure(state="disabled")
'''
new = '''        def finish(items):
            self._discovering_server=False
            retry_btn.configure(state="normal")
            if items:
                item=items[0]; self._found_server=item
                server_name=item.get("name") or item.get("computer") or "CRM Server"
                host=item.get("host") or ""; port=int(item.get("port",SERVER_PORT))
                info,code,msg=diagnose_server(host,port,1.3)
                if info:
                    status.configure(text="● سرور آماده اتصال است",fg="#15803d")
                    detail.configure(text=f"کامپیوتر سرور: {server_name}\nارتباط شبکه بررسی شد؛ روی «اتصال» بزنید.",fg="#334155")
                    connect_btn.configure(state="normal")
                else:
                    status.configure(text="● سرور پیدا شد ولی ارتباط اصلی بسته است",fg="#b45309")
                    detail.configure(text=msg,fg="#8a4b08")
                    connect_btn.configure(state="normal")
            else:
                self._found_server=None
                status.configure(text="● سرور پیدا نشد",fg="#b45309")
                detail.configure(text="مطمئن شوید کامپیوتر اصلی روشن است، CRM روی آن باز است و هر دو سیستم به یک مودم یا شبکه وصل‌اند؛ سپس «جستجوی دوباره» را بزنید.",fg="#64748b")
                connect_btn.configure(state="disabled")
'''
if old not in s:
    raise SystemExit('v1.1.1 discovery finish block not found')
s = s.replace(old, new, 1)

old = '''                info=ping_server(value,SERVER_PORT,1.4)
                if not info: return messagebox.showwarning("پیدا نشد","CRM روی این آدرس پیدا نشد.",parent=win)
                item=dict(info); item["host"]=value; item["port"]=int(item.get("port",SERVER_PORT)); item["name"]=item.get("computer") or value
'''
new = '''                info,code,msg=diagnose_server(value,SERVER_PORT,1.5)
                if not info: return messagebox.showwarning("اتصال کامل نشد",msg,parent=win)
                item=dict(info); item["host"]=value; item["port"]=int(item.get("port",SERVER_PORT)); item["name"]=item.get("computer") or value
'''
if old not in s:
    raise SystemExit('v1.1.1 manual connection block not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# ---------- version.py ----------
(root / 'version.py').write_text('APP_NAME = "CRM فارسی"\nAPP_VERSION = "1.1.2"\nDB_SCHEMA_VERSION = 3\n', encoding='utf-8')

# ---------- installer.iss ----------
p = root / 'installer.iss'
s = p.read_text(encoding='utf-8')
s = s.replace('#define MyAppVersion "1.1.1"', '#define MyAppVersion "1.1.2"', 1)
start = s.index('[Run]')
end = s.index('[UninstallDelete]')
run = '''[Run]
; Automatic CRM LAN firewall rules. Setup runs elevated.
Filename: "{sys}\\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CRM Farsi LAN TCP"""; Flags: runhidden waituntilterminated; StatusMsg: "تنظیم خودکار شبکه CRM..."
Filename: "{sys}\\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CRM Farsi LAN UDP"""; Flags: runhidden waituntilterminated
Filename: "{sys}\\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CRM Farsi Program"""; Flags: runhidden waituntilterminated
Filename: "{sys}\\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CRM Farsi LAN TCP"" dir=in action=allow protocol=TCP localport=8765 profile=any remoteip=localsubnet enable=yes"; Flags: runhidden waituntilterminated
Filename: "{sys}\\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CRM Farsi LAN UDP"" dir=in action=allow protocol=UDP localport=8766 profile=any remoteip=localsubnet enable=yes"; Flags: runhidden waituntilterminated
Filename: "{sys}\\netsh.exe"; Parameters: "advfirewall firewall add rule name=""CRM Farsi Program"" dir=in action=allow program=""{app}\\CRM.exe"" profile=any remoteip=localsubnet enable=yes"; Flags: runhidden waituntilterminated
Filename: "{app}\\{#MyAppExeName}"; Description: "اجرای CRM"; Flags: nowait postinstall skipifsilent

'''
s = s[:start] + run + s[end:]
p.write_text(s, encoding='utf-8')

print('CRM v1.1.2 patch applied')
