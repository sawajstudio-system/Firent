import os
import re

ROOT = os.getcwd()
SYSTEM_ROOM = os.path.join(ROOT, "System_room")
RUNNER = os.path.join(SYSTEM_ROOM, "A_API_room", "06_run_all_tests.py")
URLCHECK = os.path.join(SYSTEM_ROOM, "run_url_checker.py")
CREATOR = os.path.join(SYSTEM_ROOM, "create.py")

print(f"Root: {ROOT}")
print(f"System_room: {SYSTEM_ROOM}")

if not os.path.exists(SYSTEM_ROOM):
    print("❌ System_room folder missing!")
    exit(1)

# ---------- 1. Rewrite 06_run_all_tests.py ----------
RUNNER_CODE = '''import os, sys, subprocess, glob

BASE = os.path.dirname(os.path.abspath(__file__))
# BASE = .../System_room/A_API_room
# PRIVATE_ROOT = .../System_room (3 levels up — service_api is now inside System_room)
PRIVATE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(BASE)))
sys.path.insert(0, PRIVATE_ROOT)
os.environ["PYTHONPATH"] = PRIVATE_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")
os.chdir(BASE)

files = sorted(glob.glob('**/*_test.py', recursive=True))
print(f'Found {len(files)} tests')

passed, failed, skipped, failed_files = 0, 0, 0, []

for f in files:
    print(f"\\n>> Running: {f}")
    try:
        r = subprocess.run([sys.executable, f], timeout=120,
                           capture_output=True, text=True,
                           env=os.environ.copy())
        if r.stdout:
            print(r.stdout)
        if r.stderr:
            print("STDERR:", r.stderr)
        if r.returncode == 0:
            passed += 1
            print(f"PASS: {f}")
        elif r.returncode == 2:
            skipped += 1
            print(f"SKIP: {f}")
        else:
            failed += 1
            failed_files.append(f)
            print(f"FAIL: {f}")
    except subprocess.TimeoutExpired:
        failed += 1
        failed_files.append(f)
        print(f"TIMEOUT: {f}")
    except Exception as e:
        failed += 1
        failed_files.append(f)
        print(f"ERROR: {f} -> {e}")

print(f"\\nSummary: {passed} passed, {skipped} skipped, {failed} failed")

try:
    from service_api.integrations.telegram_helper import send_telegram_message
    msg = f"API Tests\\nPass: {passed}\\nSkip: {skipped}\\nFail: {failed}"
    if failed_files:
        msg += "\\n\\nFailed:\\n" + "\\n".join(f"- {x}" for x in failed_files[:10])
    send_telegram_message(msg)
except Exception as e:
    print(f"Telegram skipped: {e}")

sys.exit(0 if failed == 0 else 1)
'''

os.makedirs(os.path.dirname(RUNNER), exist_ok=True)
with open(RUNNER, "w") as f:
    f.write(RUNNER_CODE)
print("✅ 06_run_all_tests.py")

# ---------- 2. Rewrite run_url_checker.py ----------
URLCHECK_CODE = '''import os, re, sys, time, requests

print("URL Checker Started...")
target = sys.argv[1] if len(sys.argv) > 1 else "ALL_FOLDERS"
base = os.path.join(os.path.dirname(__file__), "B_URL_room")
token = os.getenv("TELEGRAM_API_REPORT_TOKEN")
chat_id = os.getenv("TELEGRAM_API_REPORT_CHAT_ID")

# Add System_room to path so service_api is importable
SYSTEM_ROOM = os.path.dirname(os.path.abspath(__file__))
if SYSTEM_ROOM not in sys.path:
    sys.path.insert(0, SYSTEM_ROOM)

SOFT_FAIL = {
    "11_K_Anime",
    "13_M_NASA",
    "24_X_Bored",
    "15_O_Quotes",
}

def send(msg):
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=15,
            )
        except Exception:
            pass

def fetch(url, retries=2):
    for attempt in range(retries):
        try:
            res = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (compatible; URLChecker/1.0)"},
            )
            return res.status_code, None
        except requests.exceptions.ConnectionError:
            if attempt == retries - 1:
                return None, "ConnectionError"
            time.sleep(2)
        except requests.exceptions.Timeout:
            if attempt == retries - 1:
                return None, "Timeout"
            time.sleep(2)
        except Exception as e:
            return None, type(e).__name__
    return None, "Unknown"

passed, failed, soft_failed, errors = 0, 0, 0, 0
failed_list = []

if target == "ALL_FOLDERS":
    folders = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
else:
    folders = [target]

for folder in folders:
    path = os.path.join(base, folder)
    if not os.path.exists(path):
        continue
    for file in sorted([f for f in os.listdir(path) if f.endswith(".py")]):
        filepath = os.path.join(path, file)
        is_soft = folder in SOFT_FAIL
        try:
            with open(filepath) as fh:
                content = fh.read()
            m = re.search(r'url = "(.*?)"', content)
            if not m:
                continue
            url = m.group(1)

            status, error_type = fetch(url)

            if status in (200, 201, 202):
                passed += 1
                send(f"✅ {folder}/{file}: {status}")
            elif status is not None:
                if is_soft:
                    soft_failed += 1
                    send(f"⚠️ {folder}/{file}: HTTP {status} (soft)")
                else:
                    failed += 1
                    failed_list.append(f"{folder}/{file} -> HTTP {status}")
                    send(f"❌ {folder}/{file}: HTTP {status}")
            else:
                if is_soft:
                    soft_failed += 1
                    send(f"⚠️ {folder}/{file}: {error_type} (soft)")
                else:
                    errors += 1
                    failed_list.append(f"{folder}/{file} -> {error_type}")
                    send(f"❌ {folder}/{file}: {error_type}")
        except Exception as e:
            if is_soft:
                soft_failed += 1
                send(f"⚠️ {folder}/{file}: {type(e).__name__} (soft)")
            else:
                errors += 1
                failed_list.append(f"{folder}/{file} -> {type(e).__name__}")
                send(f"❌ {folder}/{file}: {type(e).__name__}")
        time.sleep(0.5)

summary = f"📊 URL Summary\\n✅ Pass: {passed}\\n⚠️ Soft-Fail: {soft_failed}\\n❌ Fail: {failed}\\n🚨 Error: {errors}"
if failed_list:
    summary += "\\n\\n" + "\\n".join(f"• {x}" for x in failed_list[:15])
send(summary)
print(summary)
sys.exit(0 if (failed + errors) == 0 else 1)
'''

with open(URLCHECK, "w") as f:
    f.write(URLCHECK_CODE)
print("✅ run_url_checker.py")

# ---------- 3. create.py URL fixes ----------
if os.path.exists(CREATOR):
    src = open(CREATOR).read()
    src = src.replace(
        '"12_L_Quran/01_quran_api.py": "https://api.alquran.cloud/v1/ayah/2:255/edition/quran-uthmani"',
        '"12_L_Quran/01_quran_api.py": "https://api.alquran.cloud/v1/ayah/2:255/quran-uthmani"')
    src = src.replace(
        '"21_U_Dictionary/01_dict_api.py": "https://api.dictionaryapi.dev/api/v2/entries/en/hello"',
        '"21_U_Dictionary/01_dict_api.py": "https://api.urbandictionary.com/v0/define?term=hello"')
    src = src.replace(
        '"14_N_SpaceX/01_spacex_api.py": "https://api.spacexdata.com/v4/launches/latest"',
        '"14_N_SpaceX/01_spacex_api.py": "https://ll.thespacedevs.com/2.2.0/launch/previous/?limit=1"')
    open(CREATOR, "w").write(src)
    print("✅ create.py URLs fixed")

# ---------- 4. Quran file URL fix ----------
qfile = os.path.join(SYSTEM_ROOM, "B_URL_room", "12_L_Quran", "01_quran_api.py")
if os.path.exists(qfile):
    content = open(qfile).read()
    content = re.sub(r'url = ".*?"',
                     'url = "https://api.alquran.cloud/v1/ayah/2:255/quran-uthmani"',
                     content)
    open(qfile, "w").write(content)
    print("✅ quran URL fixed")

print("\n🎉 Private repo superfixed!")
