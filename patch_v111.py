from pathlib import Path

root = Path('src')
net_path = root / 'networking.py'
app_path = root / 'app.py'

# --- Network discovery: UDP first, then automatic /24 LAN scan fallback ---
net = net_path.read_text(encoding='utf-8')
if 'import concurrent.futures\n' not in net:
    net = net.replace('import base64\n', 'import base64\nimport concurrent.futures\nimport ipaddress\n', 1)

start = net.index('def discover_servers(timeout=1.2):')
end = net.index('def ping_server(host, port=SERVER_PORT, timeout=1.2):', start)
network_block = '''def _local_ipv4_addresses():
    ips = []
    def add(ip):
        try:
            obj = ipaddress.ip_address(ip)
            if obj.version == 4 and not obj.is_loopback and not obj.is_link_local and ip not in ips:
                ips.append(ip)
        except Exception:
            pass
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM):
            add(item[4][0])
    except Exception:
        pass
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        add(sock.getsockname()[0])
        sock.close()
    except Exception:
        pass
    return ips


def _udp_discover_servers(timeout=1.2):
    found = {}
    targets = {"255.255.255.255"}
    for ip in _local_ipv4_addresses():
        try:
            targets.add(str(ipaddress.ip_network(f"{ip}/24", strict=False).broadcast_address))
        except Exception:
            pass
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.22)
    deadline = time.time() + timeout
    try:
        for _ in range(2):
            for target in targets:
                try:
                    sock.sendto(DISCOVER_MAGIC, (target, DISCOVERY_PORT))
                except OSError:
                    pass
            time.sleep(0.08)
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                payload = json.loads(data.decode("utf-8"))
                host = addr[0]
                payload["host"] = host
                payload.setdefault("name", payload.get("computer") or host)
                found[(host, int(payload.get("port", SERVER_PORT)))] = payload
            except Exception:
                continue
    finally:
        sock.close()
    return list(found.values())


def _scan_local_subnets(timeout=4.5):
    own = set(_local_ipv4_addresses())
    hosts = []
    for ip in own:
        try:
            subnet = ipaddress.ip_network(f"{ip}/24", strict=False)
            for host in subnet.hosts():
                text = str(host)
                if text not in own and text not in hosts:
                    hosts.append(text)
        except Exception:
            pass
    if not hosts:
        return []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=56)
    futures = {executor.submit(ping_server, host, SERVER_PORT, 0.28): host for host in hosts}
    found = []
    try:
        for future in concurrent.futures.as_completed(futures, timeout=timeout):
            host = futures[future]
            try:
                info = future.result()
            except Exception:
                info = None
            if info:
                item = dict(info)
                item["host"] = host
                item["port"] = int(item.get("port", SERVER_PORT))
                item["name"] = item.get("computer") or item.get("name") or host
                found.append(item)
                break
    except concurrent.futures.TimeoutError:
        pass
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
    return found


def discover_servers(timeout=1.2, deep_scan=True):
    found = _udp_discover_servers(timeout=max(0.8, min(float(timeout), 2.2)))
    if found or not deep_scan:
        return found
    return _scan_local_subnets()


'''
net = net[:start] + network_block + net[end:]
net_path.write_text(net, encoding='utf-8')

# --- Minimal client UI: no IP shown to staff ---
app = app_path.read_text(encoding='utf-8')
if 'import threading\n' not in app:
    app = app.replace('import time\n', 'import time\nimport threading\n', 1)
start = app.index('    def choose_client_mode(self):')
end = app.index('    def clear(self):', start)
ui_block = '''    def choose_client_mode(self):
        self.network_connect_screen(auto_start=True)

    def network_connect_screen(self, auto_start=True):
        self.clear()
        self._found_server = None
        self._discovering_server = False
        box=tk.Frame(self,bg="#fff",bd=1,relief="solid")
        box.place(relx=.5,rely=.5,anchor="center",width=590,height=430)
        tk.Label(box,text="اتصال خودکار به CRM",bg="#fff",font=("Tahoma",20,"bold"),fg=self.TEXT).pack(pady=(34,7))
        tk.Label(box,text="هیچ تنظیم شبکه‌ای لازم نیست؛ فقط کامپیوتر اصلی روشن و CRM روی آن باز باشد.",bg="#fff",fg="#667085",font=("Tahoma",9),wraplength=500).pack()
        status=tk.Label(box,text="● آماده جستجو",bg="#fff",fg="#64748b",font=("Tahoma",11,"bold")); status.pack(pady=(32,6))
        detail=tk.Label(box,text="",bg="#fff",fg="#64748b",font=("Tahoma",9),wraplength=460,justify="center"); detail.pack(pady=4)
        actions=tk.Frame(box,bg="#fff"); actions.pack(pady=(18,4))
        connect_btn=ttk.Button(actions,text="اتصال",state="disabled"); connect_btn.pack(side="right",padx=5)
        retry_btn=ttk.Button(actions,text="جستجوی دوباره"); retry_btn.pack(side="right",padx=5)

        def connect_found():
            item=self._found_server
            if not item: return
            host=item["host"]; port=int(item.get("port",SERVER_PORT))
            self.net_config={"mode":"client","host":host,"port":port}
            save_network_config(self.net_config)
            status.configure(text="● در حال اتصال…",fg="#2563eb")
            self.after(150,self.init_network_store)
        connect_btn.configure(command=connect_found)

        def finish(items):
            self._discovering_server=False
            retry_btn.configure(state="normal")
            if items:
                item=items[0]; self._found_server=item
                server_name=item.get("name") or item.get("computer") or "CRM Server"
                status.configure(text="● سرور پیدا شد",fg="#15803d")
                detail.configure(text=f"کامپیوتر سرور: {server_name}\\nبرای ورود به اطلاعات مشترک، «اتصال» را بزنید.",fg="#334155")
                connect_btn.configure(state="normal")
            else:
                self._found_server=None
                status.configure(text="● سرور پیدا نشد",fg="#b45309")
                detail.configure(text="مطمئن شوید کامپیوتر اصلی روشن است و هر دو سیستم به یک مودم یا شبکه وصل‌اند؛ سپس «جستجوی دوباره» را بزنید.",fg="#64748b")
                connect_btn.configure(state="disabled")

        def search():
            if self._discovering_server: return
            self._discovering_server=True; self._found_server=None
            status.configure(text="● در حال پیدا کردن سرور CRM…",fg="#2563eb")
            detail.configure(text="معمولاً چند ثانیه طول می‌کشد.",fg="#64748b")
            retry_btn.configure(state="disabled"); connect_btn.configure(state="disabled")
            def worker():
                try: items=discover_servers(1.5,deep_scan=True)
                except Exception: items=[]
                try: self.after(0,lambda:finish(items))
                except Exception: pass
            threading.Thread(target=worker,daemon=True).start()
        retry_btn.configure(command=search)

        def advanced():
            win=tk.Toplevel(self); win.title("تنظیمات پیشرفته مدیر"); win.geometry("430x285"); win.resizable(False,False); win.transient(self); win.grab_set(); win.configure(bg="#fff")
            tk.Label(win,text="تنظیمات پیشرفته مدیر",bg="#fff",font=("Tahoma",15,"bold")).pack(pady=(24,5))
            tk.Label(win,text="فقط اگر جستجوی خودکار در شبکه خاص شما جواب نداد از این بخش استفاده کنید.",bg="#fff",fg="#64748b",font=("Tahoma",8),wraplength=360).pack()
            host=tk.StringVar(value=(self.net_config or {}).get("host",""))
            tk.Label(win,text="IP کامپیوتر سرور",bg="#fff",font=("Tahoma",9,"bold")).pack(pady=(20,5))
            ttk.Entry(win,textvariable=host,justify="center",font=("Tahoma",10)).pack(fill="x",padx=65)
            def manual_connect():
                value=host.get().strip()
                if not value: return
                info=ping_server(value,SERVER_PORT,1.4)
                if not info: return messagebox.showwarning("پیدا نشد","CRM روی این آدرس پیدا نشد.",parent=win)
                item=dict(info); item["host"]=value; item["port"]=int(item.get("port",SERVER_PORT)); item["name"]=item.get("computer") or value
                win.destroy(); finish([item])
            ttk.Button(win,text="بررسی سرور",command=manual_connect).pack(pady=18)
            tk.Label(win,text="ⓘ پرسنل معمولاً هیچ نیازی به این قسمت ندارند.",bg="#fff",fg="#94a3b8",font=("Tahoma",8)).pack()
        advanced_link=tk.Label(box,text="تنظیمات پیشرفته مدیر",bg="#fff",fg="#64748b",cursor="hand2",font=("Tahoma",8,"underline"))
        advanced_link.pack(pady=(14,3)); advanced_link.bind("<Button-1>",lambda e:advanced())
        ttk.Button(box,text="بازگشت",command=self.network_setup_screen).pack(pady=7)
        tk.Label(box,text="ⓘ راهنما: روی کامپیوتر اصلی حالت «سرور» را انتخاب کنید؛ بقیه کامپیوترها سرور را خودکار پیدا می‌کنند.",bg="#fff",fg="#64748b",font=("Tahoma",8),wraplength=470).pack(pady=(5,0))
        if auto_start: self.after(250,search)

'''
app = app[:start] + ui_block + app[end:]
app = app.replace('CRM سرور را در شبکه به‌صورت خودکار پیدا می‌کند.\\nتمام کاربران همان اطلاعات مشترک را می‌بینند.', 'فقط این گزینه را بزنید؛ CRM سرور را خودش پیدا می‌کند.\\nتمام کاربران همان اطلاعات مشترک را می‌بینند.', 1)
app_path.write_text(app, encoding='utf-8')

(root / 'version.py').write_text('APP_NAME = "CRM فارسی"\nAPP_VERSION = "1.1.1"\nDB_SCHEMA_VERSION = 3\n', encoding='utf-8')

iss_path = root / 'installer.iss'
iss = iss_path.read_text(encoding='utf-8').replace('#define MyAppVersion "1.1.0"', '#define MyAppVersion "1.1.1"')
if '[Code]' not in iss:
    iss = iss.replace('\n[Dirs]\n', '''\n[Code]\nfunction PrepareToInstall(var NeedsRestart: Boolean): String;\nvar\n  ResultCode: Integer;\nbegin\n  Exec(ExpandConstant('{sys}\\taskkill.exe'), '/F /IM CRM.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);\n  Result := '';\nend;\n\n[Dirs]\n''', 1)
iss_path.write_text(iss, encoding='utf-8')
print('CRM v1.1.1 automatic server discovery patch applied')
