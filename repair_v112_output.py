from pathlib import Path

root = Path('src')
bs = chr(92)

# Rebuild the two client connection functions from clean boundaries.
p = root / 'app.py'
s = p.read_text(encoding='utf-8')

start = s.index('        def connect_found():')
end = s.index('        connect_btn.configure(command=connect_found)', start)
new_connect = '''        def connect_found():
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
                    detail.configure(text=f"کامپیوتر سرور: {item.get('name') or item.get('computer') or host}<NL>در حال ورود به CRM مشترک…",fg="#334155")
                    self.after(250,self.init_network_store)
                try:self.after(0,done)
                except Exception:pass
            threading.Thread(target=worker,daemon=True).start()
'''.replace('<NL>', bs + 'n')
s = s[:start] + new_connect + s[end:]

start = s.index('        def finish(items):')
end = s.index('        def search():', start)
new_finish = '''        def finish(items):
            self._discovering_server=False
            retry_btn.configure(state="normal")
            if items:
                item=items[0]; self._found_server=item
                server_name=item.get("name") or item.get("computer") or "CRM Server"
                host=item.get("host") or ""; port=int(item.get("port",SERVER_PORT))
                info,code,msg=diagnose_server(host,port,1.3)
                if info:
                    status.configure(text="● سرور آماده اتصال است",fg="#15803d")
                    detail.configure(text=f"کامپیوتر سرور: {server_name}<NL>ارتباط شبکه بررسی شد؛ روی «اتصال» بزنید.",fg="#334155")
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

'''.replace('<NL>', bs + 'n')
s = s[:start] + new_finish + s[end:]
p.write_text(s, encoding='utf-8')

# Rebuild installer firewall section without escape-sensitive source text.
p = root / 'installer.iss'
s = p.read_text(encoding='utf-8')
start = s.index('[Run]')
end = s.index('[UninstallDelete]')
run = '''[Run]
; CRM LAN firewall rules - installed automatically with admin privileges.
Filename: "{sys}<BS>netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CRM Farsi LAN TCP"""; Flags: runhidden waituntilterminated; StatusMsg: "تنظیم خودکار شبکه CRM..."
Filename: "{sys}<BS>netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CRM Farsi LAN UDP"""; Flags: runhidden waituntilterminated
Filename: "{sys}<BS>netsh.exe"; Parameters: "advfirewall firewall delete rule name=""CRM Farsi Program"""; Flags: runhidden waituntilterminated
Filename: "{sys}<BS>netsh.exe"; Parameters: "advfirewall firewall add rule name=""CRM Farsi LAN TCP"" dir=in action=allow protocol=TCP localport=8765 profile=any remoteip=localsubnet enable=yes"; Flags: runhidden waituntilterminated
Filename: "{sys}<BS>netsh.exe"; Parameters: "advfirewall firewall add rule name=""CRM Farsi LAN UDP"" dir=in action=allow protocol=UDP localport=8766 profile=any remoteip=localsubnet enable=yes"; Flags: runhidden waituntilterminated
Filename: "{sys}<BS>netsh.exe"; Parameters: "advfirewall firewall add rule name=""CRM Farsi Program"" dir=in action=allow program=""{app}<BS>CRM.exe"" profile=any remoteip=localsubnet enable=yes"; Flags: runhidden waituntilterminated
Filename: "{app}<BS>{#MyAppExeName}"; Description: "اجرای CRM"; Flags: nowait postinstall skipifsilent

'''.replace('<BS>', bs)
s = s[:start] + run + s[end:]
p.write_text(s, encoding='utf-8')

print('CRM v1.1.2 output repaired and normalized')
