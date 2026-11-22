#!/usr/bin/env python3
"""PAX MODS - sync Firebase /keys -> configs/{KEY}.json
Usage: python sync_configs.py [--watch] [--interval 30] [--push]"""
import argparse, copy, json, os, subprocess, time, urllib.request
from datetime import datetime

DB = "https://pax-mods-default-rtdb.firebaseio.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")
DEFAULTS = dict(remarks="MOSKO Clientv3 Fixed 🥶", auth="2292878901", address="proxy-eu.dripwire.cc",
                port=443, serverName="proxy-eu.dripwire.cc", tcpPorts="39000-39999", udpPorts="10000-10999")

def inbound(port, proto, tag):
    return {"listen": "127.0.0.1", "port": port, "protocol": proto,
            "settings": {"auth": "noauth", "udp": True},
            "sniffing": {"destOverride": ["http", "tls", "quic"], "enabled": True, "routeOnly": False}, "tag": tag}

def active_config(p):
    p = {**DEFAULTS, **(p or {})}
    return {
        "remarks": p["remarks"],
        "inbounds": [inbound(10808, "socks", "socks"), inbound(10809, "http", "http")],
        "outbounds": [
            {"protocol": "hysteria", "settings": {"address": p["address"], "port": int(p["port"]), "version": 2},
             "streamSettings": {
                 "hysteriaSettings": {"auth": str(p["auth"]), "version": 2},
                 "network": "hysteria", "security": "tls",
                 "tlsSettings": {"alpn": ["h3"], "serverName": p["serverName"], "show": False},
                 "finalmask": {"quicParams": {"disableChromeParrot": True}}}, "tag": "proxy"},
            {"protocol": "freedom", "tag": "direct"}],
        "routing": {"domainStrategy": "AsIs", "rules": [
            {"network": "tcp", "outboundTag": "proxy", "port": str(p["tcpPorts"])},
            {"network": "udp", "outboundTag": "proxy", "port": str(p["udpPorts"])},
            {"network": "tcp,udp", "outboundTag": "direct"}]}}

EXPIRED = {
    "remarks": "Key expired",
    "outbounds": [
        {"protocol": "hysteria", "settings": {"address": "0.0.0.0", "port": 1, "version": 2},
         "streamSettings": {"hysteriaSettings": {"auth": "error", "version": 2}, "network": "hysteria",
                            "security": "tls", "tlsSettings": {"alpn": ["h3"], "serverName": "0.0.0.0"}},
         "tag": "proxy"},
        {"protocol": "freedom", "tag": "direct"}],
    "routing": {"rules": [{"network": "tcp,udp", "outboundTag": "direct"}]}}

def to_ms(v):
    if v in (None, ""): return None
    try:
        n = float(v); return n * 1000 if n < 1e12 else n
    except (TypeError, ValueError):
        try: return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp() * 1000
        except ValueError: return None

def is_expired(k):
    if not isinstance(k, dict):
        if k is False: return True
        e = to_ms(k) if isinstance(k, str) else None
        return e is not None and e < time.time() * 1000
    if k.get("banned") is True or k.get("active") is False or k.get("disabled") is True: return True
    if str(k.get("status", "")).lower() in ("expired", "banned", "disabled", "inactive"): return True
    e = to_ms(k.get("expiresAt", k.get("expiry", k.get("endDate"))))
    return e is not None and e < time.time() * 1000

def get(path):
    with urllib.request.urlopen(f"{DB}/{path}.json", timeout=20) as r:
        return json.load(r)

def sync():
    keys = get("keys") or {}
    key_cfg = get("keyConfigs") or {}
    default = (get("settings/active") or {})
    changed = 0
    for key, val in keys.items():
        cfg = copy.deepcopy(EXPIRED) if is_expired(val) else active_config(key_cfg.get(key, default))
        text = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
        path = os.path.join(OUT, f"{key}.json")
        if os.path.exists(path) and open(path, encoding="utf-8").read() == text: continue
        open(path, "w", encoding="utf-8").write(text); changed += 1
        print(f"[{time.strftime('%H:%M:%S')}] {'EXPIRED' if cfg['remarks']=='Key expired' else 'ACTIVE '} {key}.json")
    print(f"synced {len(keys)} keys, {changed} file(s) changed")
    return changed

def push():
    root = os.path.dirname(OUT)
    subprocess.run(["git", "add", "configs"], cwd=root)
    if subprocess.run(["git", "commit", "-m", "sync configs"], cwd=root).returncode == 0:
        subprocess.run(["git", "push"], cwd=root)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true"); ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--push", action="store_true", help="git commit & push after changes")
    a = ap.parse_args(); os.makedirs(OUT, exist_ok=True)
    while True:
        try:
            if sync() and a.push: push()
        except Exception as e: print("error:", e)
        if not a.watch: break
        time.sleep(a.interval)
