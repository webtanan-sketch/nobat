from pathlib import Path

p = Path('patch_v112.py')
s = p.read_text(encoding='utf-8')
start = s.index("old = '''        def finish(items):")
end = s.index("old = '''                info=ping_server(value,SERVER_PORT,1.4)", start)
replacement = r'''# Replace discovery finish by function boundaries (avoids escaped-newline mismatch on Windows builds).
finish_start = s.index('        def finish(items):')
finish_end = s.index('        def search():', finish_start)
new_finish = ''' + "'''" + r'''        def finish(items):
            self._discovering_server=False
            retry_btn.configure(state="normal")
            if items:
                item=items[0]; self._found_server=item
                server_name=item.get("name") or item.get("computer") or "CRM Server"
                host=item.get("host") or ""; port=int(item.get("port",SERVER_PORT))
                info,code,msg=diagnose_server(host,port,1.3)
                if info:
                    status.configure(text="● سرور آماده اتصال است",fg="#15803d")
                    detail.configure(text=f"کامپیوتر سرور: {server_name}\\nارتباط شبکه بررسی شد؛ روی «اتصال» بزنید.",fg="#334155")
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

''' + "'''" + r'''
s = s[:finish_start] + new_finish + s[finish_end:]

'''
s = s[:start] + replacement + s[end:]
p.write_text(s, encoding='utf-8')
print('patch_v112 prepared')
