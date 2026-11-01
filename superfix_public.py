import os
import re

ROOT = os.getcwd()

# Possible filenames (emoji + normal)
possible_files = [
    os.path.join(ROOT, ".github", "workflows", "System⚙️.yml"),
    os.path.join(ROOT, ".github", "workflows", "System.yml"),
]

YML = None
for f in possible_files:
    if os.path.exists(f):
        YML = f
        break

if not YML:
    print("❌ System.yml (or System⚙️.yml) not found in .github/workflows/!")
    exit(1)

print(f"✅ Found workflow file: {YML}")

content = open(YML, encoding="utf-8").read()
original = content

# Fix PYTHONPATH
content = content.replace(
    "PYTHONPATH: ${{ runner.temp }}/private_repo\n",
    "PYTHONPATH: ${{ runner.temp }}/private_repo/System_room\n"
)

# Fix URL Testing step if PYTHONPATH missing
if "8. 🌐 Run URL Testing" in content and "private_repo/System_room" not in content.split("8. 🌐 Run URL Testing")[1].split("9.")[0]:
    url_step_pattern = r'(- name: 8\. 🌐 Run URL Testing\n\s+if: [^\n]+\n\s+continue-on-error: true\n)(\s+run: \|\n\s+python [^\n]+run_url_checker\.py)'
    url_step_replacement = r'\1        env:\n          PYTHONPATH: ${{ runner.temp }}/private_repo/System_room\n\2'
    content = re.sub(url_step_pattern, url_step_replacement, content)

if content != original:
    open(YML, "w", encoding="utf-8").write(content)
    print("✅ System.yml updated successfully")
else:
    print("⚠️ System.yml already correct or pattern not found")
