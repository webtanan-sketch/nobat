from pathlib import Path
import re

root = Path('src')
app_path = root / 'app.py'
net_path = root / 'networking.py'

network_path = net_path if net_path.exists() and 'def pair_server' in net_path.read_text(encoding='utf-8') else app_path
ns = network_path.read_text(encoding='utf-8')
if 'import concurrent.futures\n' not in ns:
    if 'import csv\n' in ns:
        ns = ns.replace('import csv\n', 'import csv\nimport concurrent.futures\nimport ipaddress\n', 1)
    else:
        ns = 'import concurrent.futures\nimport ipaddress\n' + ns

new_network = r'''def pair_server(ip,port=API_PORT,timeout=1.0):
    try:
        data=http_json(f"http://{ip}:{port}/pair",timeout=timeout)
        if data.get("ok"):
            return {"url":f"http://{ip}:{int(data.get('port',port))}","token":data["token"],"server_name":data.get("server_name") or ip,"server_ip":ip}
    except Exception:
        pass
    return None

def local_ipv4_addresses():
    ips=[]
    def add(ip):
        try:
            obj=ipaddress.ip_address(ip)
            if obj.version==4 and not obj.is_loopback and not obj.is_link_local and ip not in ips:
                ips.append(ip)
        except Exception:
            pass
    try:
        for item in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET,socket.SOCK_DGRAM):
            add(item[4][0])
    except Exception:
        pass
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); add(s.getsockname()[0]); s.close()
    except Exception:
        pass
    return ips

def _udp_discover(timeout=1.5):
    targets={"255.255.255.255"}
    for ip in local_ipv4_addresses():
        try:
            net=ipaddress.ip_network(f"{ip}/24",strict=False)
            targets.add(str(net.broadcast_address))
        except Exception:
            pass
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    sock.settimeout(.22)
    try:
        sock.bind(("",0))
        for _ in range(2):
            for target in targets:
                try: sock.sendto(DISCOVERY_MAGIC,(target,DISCOVERY_PORT))
                except OSError: pass
            time.sleep(.08)
        end=time.time()+timeout
        while time.time()<end:
            try:
                raw,addr=sock.recvfrom(4096); d=json.loads(raw.decode("utf-8"))
                if d.get("app")=="CRM-Farsi":
                    cfg={"url":f"http://{addr[0]}:{int(d.get('port',API_PORT))}","token":d["token"],"server_name":d.get("server_name") or addr[0],"server_ip":addr[0]}
                    if RemoteStore(cfg).ping(): return cfg
            except socket.timeout:
                continue
            except Exception:
                continue
    finally:
        sock.close()
    return None

def _scan_local_subnets():
    hosts=[]; own=set(local_ipv4_addresses())
    for ip in own:
        try:
            net=ipaddress.ip_network(f"{ip}/24",strict=False)
            for host in net.hosts():
                hs=str(host)
                if hs not in own and hs not in hosts: hosts.append(hs)
        except Exception:
            pass
    if not hosts:
        return None
    result=None
    ex=concurrent.futures.ThreadPoolExecutor(max_workers=56)
    futures={ex.submit(pair_server,ip,API_PORT,.28):ip for ip in hosts}
    try:
        for fut in concurrent.futures.as_completed(futures,timeout=4.5):
            try:
                cfg=fut.result()
                if cfg:
                    result=cfg
                    break
            except Exception:
                pass
    except Exception:
        pass
    finally:
        for f in futures: f.cancel()
        ex.shutdown(wait=False,cancel_futures=True)
    return result

def discover_server(timeout=2.0, deep_scan=True):
    found=_udp_discover(timeout=max(.8,min(timeout,2.2)))
    if found: return found
    return _scan_local_subnets() if deep_scan else None
'''
pattern = re.compile(r'(?ms)^def pair_server\(.*?^def add_server_autostart\(\):')
if not pattern.search(ns):
    raise SystemExit(f'network discovery section not found in {network_path}')
ns = pattern.sub(lambda m: new_network + '\ndef add_server_autostart():', ns, count=1)
network_path.write_text(ns, encoding='utf-8')

s = app_path.read_text(encoding='utf-8')
new_ui = r'''    def choose_client_mode(self):
        self.client_connection_screen(auto_start=True)

    def client_connection_screen(self, auto_start=True):
        self.clear(); self._found_server=None; self._discovering=False
        box=tk.Frame(self,bg="#fff",bd=1,relief="solid"); box.place(relx=.5,rely=.5,anchor="center",width=560,height=430)
        tk.Label(box,text="اتصال خودکار به CRM",bg="#fff",fg=self.TEXT,font=("Tahoma",20,"bold")).pack(pady=(35,7))
        tk.Label(box,text="هیچ تنظیم شبکه‌ای لازم نیست؛ فقط کامپیوتر سرور روشن باشد.",bg="#fff",fg="#64748b",font=("Tahoma",9)).pack()
        status=tk.Label(box,text="● آماده جستجو",bg="#fff",fg="#64748b",font=("Tahoma",11,"bold")); status.pack(pady=(34,5))
        detail=tk.Label(box,text="",bg="#fff",fg="#64748b",font=("Tahoma",9),wraplength=440,justify="center"); detail.pack(pady=4)
        actions=tk.Frame(box,bg="#fff"); actions.pack(pady=(18,4))
        connect_btn=ttk.Button(actions,text="اتصال",state="disabled"); connect_btn.pack(side="right",padx=5)
        retry_btn=ttk.Button(actions,text="جستجوی دوباره"); retry_btn.pack(side="right",padx=5)

        def connect_found():
            found=self._found_server
            if not found:return
            remove_server_autostart(); save_json_file(network_mode_path(),{"mode":"client",**found})
            self.store=RemoteStore(found); self.network_mode="client"; self.after_network_connected()
        connect_btn.configure(command=connect_found)

        def finish(found):
            self._discovering=False; retry_btn.configure(state="normal")
            if found:
                self._found_server=found
                status.configure(text="● سرور پیدا شد",fg="#15803d")
                detail.configure(text=f"کامپیوتر سرور: {found.get('server_name') or 'CRM Server'}\nبرای ورود به اطلاعات مشترک، «اتصال» را بزنید.",fg="#334155")
                connect_btn.configure(state="normal")
            else:
                self._found_server=None
                status.configure(text="● سرور پیدا نشد",fg="#b45309")
                detail.configure(text="مطمئن شوید کامپیوتر اصلی روشن است و هر دو سیستم به یک مودم یا شبکه وصل‌اند. سپس «جستجوی دوباره» را بزنید.",fg="#64748b")
                connect_btn.configure(state="disabled")

        def search():
            if self._discovering:return
            self._discovering=True; self._found_server=None
            status.configure(text="● در حال پیدا کردن سرور CRM…",fg="#2563eb")
            detail.configure(text="معمولاً چند ثانیه طول می‌کشد.",fg="#64748b")
            retry_btn.configure(state="disabled"); connect_btn.configure(state="disabled")
            def worker():
                found=discover_server(1.6,deep_scan=True)
                try:self.after(0,lambda:finish(found))
                except Exception:pass
            threading.Thread(target=worker,daemon=True).start()
        retry_btn.configure(command=search)

        def advanced():
            win=tk.Toplevel(self); win.title("تنظیمات پیشرفته مدیر"); win.geometry("430x285"); win.resizable(False,False); win.transient(self); win.grab_set(); win.configure(bg="#fff")
            tk.Label(win,text="تنظیمات پیشرفته مدیر",bg="#fff",font=("Tahoma",15,"bold")).pack(pady=(24,5))
            tk.Label(win,text="فقط اگر جستجوی خودکار در شبکه خاص شما جواب نداد استفاده شود.",bg="#fff",fg="#64748b",font=("Tahoma",8),wraplength=360).pack()
            ip=tk.StringVar()
            tk.Label(win,text="IP کامپیوتر سرور",bg="#fff",font=("Tahoma",9,"bold")).pack(pady=(20,5))
            ttk.Entry(win,textvariable=ip,justify="center",font=("Tahoma",10)).pack(fill="x",padx=65)
            def manual_connect():
                value=en_digits(ip.get()).strip()
                if not value:return
                found=pair_server(value,timeout=1.5)
                if not found:return messagebox.showwarning("پیدا نشد","CRM روی این آدرس پیدا نشد.",parent=win)
                win.destroy(); self._found_server=found; finish(found)
            ttk.Button(win,text="بررسی سرور",command=manual_connect).pack(pady=18)
            tk.Label(win,text="ⓘ پرسنل معمولاً هیچ نیازی به این بخش ندارند.",bg="#fff",fg="#94a3b8",font=("Tahoma",8)).pack()
        adv=tk.Label(box,text="تنظیمات پیشرفته مدیر",bg="#fff",fg="#64748b",cursor="hand2",font=("Tahoma",8,"underline")); adv.pack(pady=(14,3)); adv.bind("<Button-1>",lambda e:advanced())
        ttk.Button(box,text="بازگشت",command=self.network_setup_screen).pack(pady=7)
        tk.Label(box,text="ⓘ راهنما: روی کامپیوتر اصلی CRM را در حالت «سرور» باز نگه دارید؛ بقیه سیستم‌ها خودکار آن را پیدا می‌کنند.",bg="#fff",fg="#64748b",font=("Tahoma",8),wraplength=470).pack(pady=(6,0))
        if auto_start:self.after(250,search)
'''
ui_pattern = re.compile(r'(?ms)^    def choose_client_mode\(self\):.*?^    def reset_network_mode\(self\):')
if not ui_pattern.search(s):
    raise SystemExit('client connection UI section not found')
s = ui_pattern.sub(lambda m: new_ui + '\n    def reset_network_mode(self):', s, count=1)
s = s.replace('برای سیستم مدیر یا پرسنل. برنامه سرور را داخل همین شبکه به‌صورت خودکار پیدا می‌کند؛ نیاز به IP و تنظیم فنی نیست.', 'برای سیستم مدیر یا پرسنل. فقط این گزینه را بزنید؛ برنامه سرور را خودش پیدا می‌کند و هیچ IP یا تنظیم فنی لازم نیست.', 1)
app_path.write_text(s, encoding='utf-8')

(root / 'version.py').write_text('APP_NAME = "CRM فارسی"\nAPP_VERSION = "1.1.1"\nDB_SCHEMA_VERSION = 3\n', encoding='utf-8')
iss = root / 'installer.iss'
t = iss.read_text(encoding='utf-8').replace('#define MyAppVersion "1.1.0"', '#define MyAppVersion "1.1.1"')
if 'CloseApplications=yes' not in t:
    t = t.replace('WizardStyle=modern\n', 'WizardStyle=modern\nCloseApplications=yes\nRestartApplications=no\n', 1)
if '[Code]' not in t:
    code = '''\n[Code]\nfunction PrepareToInstall(var NeedsRestart: Boolean): String;\nvar\n  ResultCode: Integer;\nbegin\n  Exec(ExpandConstant('{sys}\\\\taskkill.exe'), '/F /IM CRM.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);\n  Result := '';\nend;\n\n'''
    t = t.replace('\n[Dirs]\n', code + '[Dirs]\n', 1)
iss.write_text(t, encoding='utf-8')
print('CRM v1.1.1 patch applied to', network_path)
