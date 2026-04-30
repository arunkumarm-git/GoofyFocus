"""
diagnose_supabase.py
Run this from your project root (where your .env lives):
    python diagnose_supabase.py
"""

import os, sys, socket, traceback

# ── 1. Load .env ────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[✓] dotenv loaded")
except ImportError:
    print("[✗] python-dotenv not installed — run: pip install python-dotenv")
    sys.exit(1)

# ── 2. Check env vars ────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print()
print("── Env Variables ──────────────────────────────────────────────────────")
if not SUPABASE_URL:
    print("[✗] SUPABASE_URL is missing or empty in your .env")
else:
    print(f"[✓] SUPABASE_URL = {SUPABASE_URL}")

if not SUPABASE_KEY:
    print("[✗] SUPABASE_KEY is missing or empty in your .env")
else:
    masked = SUPABASE_KEY[:8] + "..." + SUPABASE_KEY[-4:]
    print(f"[✓] SUPABASE_KEY = {masked}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n→ Fix your .env file first, then re-run this script.")
    sys.exit(1)

# ── 3. Validate URL format ───────────────────────────────────────────────────
print()
print("── URL Format Check ───────────────────────────────────────────────────")
if not SUPABASE_URL.startswith("https://"):
    print("[✗] SUPABASE_URL must start with 'https://'")
elif not SUPABASE_URL.endswith(".supabase.co"):
    print(f"[!] SUPABASE_URL doesn't end with '.supabase.co' — double-check: {SUPABASE_URL}")
else:
    print("[✓] URL format looks correct")

# ── 4. DNS / network reachability ───────────────────────────────────────────
print()
print("── Network Reachability ───────────────────────────────────────────────")
from urllib.parse import urlparse
host = urlparse(SUPABASE_URL).hostname
print(f"    Resolving host: {host}")
try:
    ip = socket.gethostbyname(host)
    print(f"[✓] DNS resolved → {ip}")
except socket.gaierror as e:
    print(f"[✗] DNS resolution FAILED: {e}")
    print("    → No internet, wrong URL, or firewall blocking DNS.")
    sys.exit(1)

# ── 5. HTTPS connectivity ────────────────────────────────────────────────────
print()
print("── HTTPS Ping ─────────────────────────────────────────────────────────")
try:
    import urllib.request
    req = urllib.request.urlopen(SUPABASE_URL, timeout=8)
    print(f"[✓] HTTP status: {req.status}")
except Exception as e:
    print(f"[!] HTTP check: {e}  (this may be normal — continuing)")

# ── 6. supabase-py import ────────────────────────────────────────────────────
print()
print("── supabase-py Import ─────────────────────────────────────────────────")
try:
    from supabase import create_client, __version__ as sb_ver
    print(f"[✓] supabase-py version: {sb_ver}")
except ImportError as e:
    print(f"[✗] Cannot import supabase: {e}")
    print("    → Run: pip install supabase")
    sys.exit(1)

# ── 7. create_client ────────────────────────────────────────────────────────
print()
print("── create_client() ────────────────────────────────────────────────────")
try:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[✓] create_client() succeeded")
except Exception as e:
    print(f"[✗] create_client() FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# ── 8. Actual table insert (dry-run select first) ────────────────────────────
print()
print("── Table: feedback (select) ───────────────────────────────────────────")
try:
    resp = sb.table("feedback").select("id").limit(1).execute()
    print(f"[✓] SELECT succeeded — rows returned: {len(resp.data)}")
except Exception as e:
    print(f"[✗] SELECT on 'feedback' FAILED: {e}")
    traceback.print_exc()
    print("""
    Common reasons:
      • Table 'feedback' doesn't exist yet — create it in Supabase SQL editor:
            CREATE TABLE feedback (
                id      bigserial PRIMARY KEY,
                email   text,
                rating  int,
                message text,
                created_at timestamptz DEFAULT now()
            );
      • Row Level Security (RLS) is ON with no INSERT policy for anon role.
            Go to Supabase → Authentication → Policies → feedback table
            and add an INSERT policy for the anon role, or disable RLS for testing.
      • SUPABASE_KEY is the 'anon' key but table needs 'service_role' key.
    """)
    sys.exit(1)

# ── 9. Test insert ───────────────────────────────────────────────────────────
print()
print("── Table: feedback (insert test) ──────────────────────────────────────")
try:
    resp = sb.table("feedback").insert({
        "email":   "diagnostic@test.local",
        "rating":  5,
        "message": "[diagnostic test — safe to delete]",
    }).execute()
    print(f"[✓] INSERT succeeded — inserted id(s): {[r.get('id') for r in resp.data]}")
    print("    → Your Supabase connection is fully working!")
except Exception as e:
    print(f"[✗] INSERT FAILED: {e}")
    traceback.print_exc()
    print("""
    Likely cause: Row Level Security is blocking inserts from the anon key.
    Fix in Supabase dashboard:
      Table Editor → feedback → RLS Policies → New Policy
      → "Enable insert for all users" (or authenticated users if you use auth)
    """)
    sys.exit(1)

print()
print("══ All checks passed. Supabase is connected and the feedback table works. ══")
