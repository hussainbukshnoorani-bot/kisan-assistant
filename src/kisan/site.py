"""Public business website: home, privacy policy, terms of use.

Needed for Meta business verification and as the WhatsApp app's privacy-policy URL. Business
details come from data/business.yaml; empty fields render as "To be added", never a guess.
"""

from __future__ import annotations

import html
from pathlib import Path
from string import Template
from typing import Any

import yaml

MISSING = '<span class="missing">To be added</span>'
UPDATED = "28 September 2026"


def load_business(path: Path) -> dict[str, str]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        data = {}
    return {str(k): str(v or "") for k, v in data.items()}


def _fields(business: dict[str, Any]) -> dict[str, str]:
    keys = ("name", "name_ur", "legal_name", "address", "phone", "email", "whatsapp_number")
    out = {k: html.escape(str(business.get(k) or "")) or MISSING for k in keys}
    if not business.get("name"):
        out["name"] = "Kisan Assistant"
    if not business.get("name_ur"):
        out["name_ur"] = "کسان اسسٹنٹ"
    email = str(business.get("email") or "")
    out["email_link"] = (f'<a href="mailto:{html.escape(email)}">{html.escape(email)}</a>'
                         if email else MISSING)
    return out


def render_page(page: str, business: dict[str, Any], domain_verification: str | None) -> str:
    fields = _fields(business)
    body = Template(_PAGES[page][1]).substitute(fields, updated=UPDATED)
    meta = (f'<meta name="facebook-domain-verification" '
            f'content="{html.escape(domain_verification)}">' if domain_verification else "")
    return Template(_LAYOUT).substitute(fields, title=_PAGES[page][0], body=body, meta=meta)


_LAYOUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
$meta
<title>$title</title>
<meta name="description" content="Kisan Assistant answers Pakistani farmers' mandi price questions on WhatsApp and SMS, in Urdu and Roman Urdu.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Nastaliq+Urdu:wght@500&display=swap">
<style>
  :root {
    --bg: #F5F6F1; --surface: #FFFFFF; --ink: #1B2420; --muted: #56645C; --line: #DCE2D8;
    --accent: #1F4D3A; --accent-ink: #FFFFFF; --wheat: #9A6B12; --wheat-soft: #F5EBD3;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #111614; --surface: #19201D; --ink: #E4EBE6; --muted: #9DAAA2; --line: #2B3631;
      --accent: #8CCBA5; --accent-ink: #0E1A14; --wheat: #E2B458; --wheat-soft: #33291A;
      color-scheme: dark;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.6 "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  }
  a { color: var(--accent); }
  a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .wrap { max-width: 920px; margin: 0 auto; padding-inline: 20px; }
  header.site { border-bottom: 1px solid var(--line); background: var(--surface); }
  header.site .wrap { display: flex; align-items: center; justify-content: space-between;
    gap: 16px; flex-wrap: wrap; padding-block: 14px; }
  .brand { display: flex; align-items: baseline; gap: 12px; text-decoration: none; color: var(--ink); }
  .brand strong { font-size: 18px; font-weight: 600; }
  .ur { font-family: "Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", serif; direction: rtl;
    line-height: 2; color: var(--muted); }
  nav { display: flex; gap: 18px; font-size: 15px; }
  nav a { text-decoration: none; }
  main { padding-block: 40px 56px; display: grid; gap: 44px; }
  h1 { margin: 0; font-size: clamp(28px, 4.4vw, 40px); line-height: 1.15; font-weight: 600;
    text-wrap: balance; max-width: 22ch; }
  h2 { margin: 0 0 10px; font-size: 21px; font-weight: 600; }
  h3 { margin: 0 0 4px; font-size: 16px; font-weight: 600; }
  p { margin: 0; max-width: 68ch; }
  .lead { color: var(--muted); font-size: 18px; margin-top: 14px; }
  .label { font: 500 12px/1 "IBM Plex Mono", ui-monospace, monospace; letter-spacing: .08em;
    text-transform: uppercase; color: var(--wheat); }
  .steps { list-style: none; margin: 0; padding: 0; display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
  .steps li { display: grid; gap: 6px; align-content: start; }
  .num { font: 500 13px "IBM Plex Mono", ui-monospace, monospace; color: var(--wheat); }
  .sample { background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
    padding: 18px; display: grid; gap: 10px; max-width: 560px; }
  .bubble { padding: 9px 12px; border-radius: 14px; max-width: 90%; font-size: 15px; }
  .farmer { background: var(--wheat-soft); justify-self: end; }
  .bot { background: var(--bg); border: 1px solid var(--line); }
  .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; }
  dl.contact { display: grid; grid-template-columns: max-content 1fr; gap: 8px 18px; margin: 0; }
  dl.contact dt { color: var(--muted); }
  dl.contact dd { margin: 0; overflow-wrap: anywhere; }
  .missing { color: var(--wheat); font-style: italic; }
  .doc { display: grid; gap: 22px; max-width: 72ch; }
  .doc section { display: grid; gap: 8px; }
  .doc ul { margin: 0; padding-left: 20px; display: grid; gap: 6px; }
  .muted { color: var(--muted); }
  footer { border-top: 1px solid var(--line); padding-block: 22px; color: var(--muted); font-size: 14px; }
  footer .wrap { display: flex; gap: 18px; flex-wrap: wrap; justify-content: space-between; }
  @media (max-width: 520px) { dl.contact { grid-template-columns: 1fr; gap: 2px; }
    dl.contact dd { margin-bottom: 10px; } }
</style>
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="/"><strong>$name</strong><span class="ur">$name_ur</span></a>
  <nav><a href="/">Home</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a></nav>
</div></header>
<main class="wrap">
$body
</main>
<footer><div class="wrap">
  <span>$name · $legal_name</span>
  <span><a href="/privacy">Privacy policy</a> · <a href="/terms">Terms of use</a></span>
</div></footer>
</body>
</html>
"""

_HOME = """
<section>
  <span class="label">Mandi rates on WhatsApp and SMS</span>
  <h1 style="margin-top:12px">Today's crop prices, asked in your own words</h1>
  <p class="lead">Kisan Assistant answers Pakistani farmers' questions about mandi prices. Send a
    message in Urdu or Roman Urdu and get the latest rate per 40 kg, with its source and date.</p>
  <p style="margin-top:8px"><span class="ur" style="font-size:18px">اپنی زبان میں منڈی کا ریٹ پوچھیں</span></p>
</section>

<section>
  <h2>How it works</h2>
  <ol class="steps">
    <li><span class="num">Step 1</span><h3>Send a question</h3>
      <p>Write the crop and the mandi, for example "Multan mandi mein gandum ka rate?", on
        WhatsApp or by SMS.</p></li>
    <li><span class="num">Step 2</span><h3>We look up the price</h3>
      <p>Prices come from published market data, with the source named in every reply. If a crop
        or mandi is missing, we ask one short question instead of guessing.</p></li>
    <li><span class="num">Step 3</span><h3>Get the rate</h3>
      <p>The reply gives the price range per 40 kg, the mandi, the source and the date. If no
        recent price exists, we say so.</p></li>
  </ol>
</section>

<section>
  <h2>Example</h2>
  <div class="sample">
    <div class="bubble farmer">Multan mandi mein gandum ka rate kya hai?</div>
    <div class="bubble bot">Multan mandi, Gandum: Rs 3,900-4,050 fi 40 kg. Zariya: Test data, 26 Sep.</div>
  </div>
  <p class="muted" style="margin-top:8px;font-size:14px">A real reply from our test service. The service is in testing and currently uses illustrative sample prices; live mandi prices will be added once our data source is confirmed.</p>
</section>

<section class="facts">
  <div><h3>Crops</h3><p>Wheat, cotton (phutti), Basmati paddy, IRRI paddy, maize.</p></div>
  <div><h3>Mandis</h3><p>Lahore, Multan, Faisalabad, Gujranwala, Rawalpindi, Sahiwal,
    Bahawalpur, Sargodha, Okara and Rahim Yar Khan.</p></div>
  <div><h3>Languages</h3><p>Urdu script and Roman Urdu. Replies come back in the script you used.</p></div>
</section>

<section>
  <h2>Contact</h2>
  <dl class="contact">
    <dt>Business</dt><dd>$legal_name</dd>
    <dt>Address</dt><dd>$address</dd>
    <dt>Phone</dt><dd>$phone</dd>
    <dt>Email</dt><dd>$email_link</dd>
    <dt>WhatsApp</dt><dd>$whatsapp_number</dd>
  </dl>
</section>
"""

_PRIVACY = """
<article class="doc">
  <header style="display:grid;gap:6px">
    <h1>Privacy policy</h1>
    <p class="muted">Last updated $updated</p>
  </header>
  <section>
    <p>This policy explains what $name ("we") does with information when you message our mandi
      price service on WhatsApp or by SMS. The service is operated by $legal_name, $address.</p>
  </section>
  <section>
    <h2>What we receive</h2>
    <ul>
      <li>The text of the messages you send us.</li>
      <li>Your phone number, which WhatsApp or your mobile operator passes to us so we can reply.</li>
    </ul>
    <p>We do not ask for your CNIC, bank or card details, PIN, OTP or password, and you should never
      send them to us.</p>
  </section>
  <section>
    <h2>What we store, and for how long</h2>
    <ul>
      <li><strong>Your phone number is not stored.</strong> We keep only a one-way coded identifier
        made from it, so we can remember an unfinished question for 30 minutes and count how many
        people use the service. The code cannot be turned back into your number.</li>
      <li><strong>Message text</strong> is stored so we can check and improve our answers. Before it
        is stored, any CNIC number is replaced with [CNIC] and any phone number with [PHONE].</li>
      <li>Stored messages are <strong>deleted automatically after 90 days</strong>.</li>
      <li>Our system logs record technical events (for example, which kind of reply was sent). They
        do not contain your phone number or the text of your messages.</li>
    </ul>
  </section>
  <section>
    <h2>How we use it</h2>
    <p>Only to answer your price questions, to ask a follow-up when a question is incomplete, to
      limit abuse (at most 10 replies per person per minute), and to improve how well we understand
      questions. We do not sell your information and do not use it for advertising.</p>
  </section>
  <section>
    <h2>Who else handles it</h2>
    <ul>
      <li><strong>WhatsApp (Meta)</strong> or your <strong>mobile operator</strong> carries your
        messages to us and our replies to you, under their own privacy policies.</li>
      <li>Our hosting providers run the service and store the data described above on our behalf:
        Vercel (application hosting) and Neon (database).</li>
    </ul>
  </section>
  <section>
    <h2>Your choices</h2>
    <p>You can stop using the service at any time by not messaging us. To ask us to delete the
      messages we hold from your number, email $email_link from any address and tell us the phone
      number you used. We will find the coded identifier for that number and delete its messages
      within 30 days.</p>
  </section>
  <section>
    <h2>Changes and contact</h2>
    <p>If this policy changes, we will update the date above. Questions: $email_link, $phone.</p>
  </section>
</article>
"""

_TERMS = """
<article class="doc">
  <header style="display:grid;gap:6px">
    <h1>Terms of use</h1>
    <p class="muted">Last updated $updated</p>
  </header>
  <section>
    <h2>The service</h2>
    <p>$name, operated by $legal_name, gives information about agricultural market (mandi) prices in
      Punjab, Pakistan, in reply to messages sent on WhatsApp or by SMS.</p>
  </section>
  <section>
    <h2>Prices are for information only</h2>
    <ul>
      <li>Every price we send names its source and the date it applies to. Prices change during the
        day and differ between buyers, qualities and lots.</li>
      <li>A price older than 3 days is marked as not current or not shown.</li>
      <li>Our replies are not financial or trading advice. Please confirm the rate at the mandi before
        you buy or sell.</li>
    </ul>
  </section>
  <section>
    <h2>Using the service</h2>
    <ul>
      <li>We do not charge for replies. Your WhatsApp data or SMS charges from your mobile operator
        may apply.</li>
      <li>Please do not send personal documents or numbers such as your CNIC, bank details, PIN or OTP.</li>
      <li>To keep the service available for everyone, we reply to at most 10 messages per person per
        minute.</li>
      <li>We may change or stop the service, or the crops and mandis it covers, at any time.</li>
    </ul>
  </section>
  <section>
    <h2>Liability</h2>
    <p>We take care to report prices accurately from their source, but we cannot guarantee that
      source data is complete or error-free. To the extent the law allows, we are not responsible for
      losses from decisions made using the service.</p>
  </section>
  <section>
    <h2>Law and contact</h2>
    <p>These terms are governed by the laws of Pakistan. Questions: $email_link, $phone, $address.</p>
    <p>See also our <a href="/privacy">privacy policy</a>.</p>
  </section>
</article>
"""

_PAGES: dict[str, tuple[str, str]] = {
    "home": ("Kisan Assistant", _HOME),
    "privacy": ("Privacy policy · Kisan Assistant", _PRIVACY),
    "terms": ("Terms of use · Kisan Assistant", _TERMS),
}
