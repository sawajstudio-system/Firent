import os
import re

ROOT = os.getcwd()
YML = os.path.join(ROOT, ".github", "workflows", "System.yml")

print(f"Public root: {ROOT}")
print(f"System.yml: {YML}")

if not os.path.exists(YML):
    print("❌ System.yml not found!")
    exit(1)

content = open(YML).read()
original = content

# Fix: Replace old PYTHONPATH with new System_room path
content = content.replace(
    "PYTHONPATH: ${{ runner.temp }}/private_repo\n",
    "PYTHONPATH: ${{ runner.temp }}/private_repo/System_room\n"
)

# Fix URL Testing step — ensure PYTHONPATH env is present
if "8. 🌐 Run URL Testing" in content and "private_repo/System_room" not in content.split("8. 🌐 Run URL Testing")[1].split("9.")[0]:
    # Add PYTHONPATH to URL Testing step
    url_step_pattern = r'(- name: 8\. 🌐 Run URL Testing\n\s+if: [^\n]+\n\s+continue-on-error: true\n)(\s+run: \|\n\s+python [^\n]+run_url_checker\.py)'
    url_step_replacement = r'\1        env:\n          PYTHONPATH: ${{ runner.temp }}/private_repo/System_room\n\2'
    content = re.sub(url_step_pattern, url_step_replacement, content)

if content != original:
    open(YML, "w").write(content)
    print("✅ System.yml updated")
else:
    print("⚠️ System.yml already correct or pattern not found")

# Show updated step 8 & 9 for verification
lines = content.split("\n")
for i, line in enumerate(lines):
    if "Run URL Testing" in line or "Run API Testing" in line:
        print(f"\n--- Line {i+1}: ---")
        for j in range(i, min(i+8, len(lines))):
            print(lines[j])
