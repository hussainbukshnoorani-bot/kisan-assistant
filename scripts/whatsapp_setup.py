"""Run from the my-project folder: .venv/Scripts/python scripts/whatsapp_setup.py

Connect the live Kisan Assistant to WhatsApp Cloud API. Never prints secrets.

Reads my-project/.env.whatsapp (user-filled) and .env.vercel-demo (verify token), then:
1. stores WhatsApp settings as Vercel production env vars,
2. redeploys production,
3. registers the webhook for the app (object whatsapp_business_account, field messages),
4. subscribes the app to the WhatsApp Business Account,
5. checks the verify handshake against the live URL.
"""
import subprocess
import sys
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")
GRAPH = "https://graph.facebook.com/v21.0"
LIVE = "https://kisan-assistant.vercel.app"


def read_env(path: str) -> dict[str, str]:
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


wa = read_env(".env.whatsapp")
missing = [k for k, v in wa.items() if not v]
if missing:
    sys.exit(f"Still empty in .env.whatsapp: {', '.join(missing)}")
verify = read_env(".env.vercel-demo")["WHATSAPP_VERIFY_TOKEN"]


def show(response: httpx.Response) -> object:
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text[:200]


def vercel_env(name: str, value: str) -> None:
    subprocess.run(["vercel", "env", "rm", name, "production", "--yes"], capture_output=True,
                   shell=True)
    r = subprocess.run(["vercel", "env", "add", name, "production"], input=value, text=True,
                       capture_output=True, shell=True)
    print(f"  {name}: {'set' if r.returncode == 0 else 'FAILED'}")


print("1. Vercel environment")
vercel_env("WHATSAPP_APP_SECRET", wa["META_APP_SECRET"])
vercel_env("WHATSAPP_ACCESS_TOKEN", wa["WHATSAPP_ACCESS_TOKEN"])
vercel_env("WHATSAPP_PHONE_NUMBER_ID", wa["WHATSAPP_PHONE_NUMBER_ID"])

print("2. Redeploy")
r = subprocess.run(["vercel", "deploy", "--prod", "--yes"], capture_output=True, text=True,
                   shell=True)
print("  deployed" if r.returncode == 0 else "  deploy FAILED:\n" + r.stderr[-500:])

print("3. Register webhook")
app_token = f"{wa['META_APP_ID']}|{wa['META_APP_SECRET']}"
r = httpx.post(f"{GRAPH}/{wa['META_APP_ID']}/subscriptions", data={
    "object": "whatsapp_business_account", "callback_url": f"{LIVE}/webhooks/whatsapp",
    "verify_token": verify, "fields": "messages", "access_token": app_token}, timeout=60)
print(f"  HTTP {r.status_code}: {show(r)}")

print("4. Subscribe app to the WhatsApp Business Account")
r = httpx.post(f"{GRAPH}/{wa['WHATSAPP_BUSINESS_ACCOUNT_ID']}/subscribed_apps",
               headers={"Authorization": f"Bearer {wa['WHATSAPP_ACCESS_TOKEN']}"}, timeout=60)
print(f"  HTTP {r.status_code}: {show(r)}")

print("5. Verify handshake on the live URL")
r = httpx.get(f"{LIVE}/webhooks/whatsapp", params={
    "hub.mode": "subscribe", "hub.verify_token": verify, "hub.challenge": "kisan-check"},
    timeout=60)
ok = r.status_code == 200 and r.text == "kisan-check"
print("  OK" if ok else f"  FAILED: HTTP {r.status_code}")
