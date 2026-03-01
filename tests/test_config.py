"""Quick smoke test for tenant_config loader."""
import json
import os
import tempfile

from core.tenant_config import load_config, get_config, reset_config
from core.exceptions import ConfigNotFoundError, ConfigValidationError

passed = 0

# Test 1: File not found
reset_config()
try:
    load_config("nonexistent.json")
    print("FAIL: Should have raised ConfigNotFoundError")
except ConfigNotFoundError:
    print("PASS: ConfigNotFoundError on missing file")
    passed += 1

# Test 2: Missing required fields
reset_config()
bad = {"tenant_id": "x"}
fd, path = tempfile.mkstemp(suffix=".json")
os.write(fd, json.dumps(bad).encode())
os.close(fd)
try:
    load_config(path)
    print("FAIL: Should have raised ConfigValidationError")
except ConfigValidationError as e:
    print(f"PASS: ConfigValidationError — {e}")
    passed += 1
finally:
    os.unlink(path)

# Test 3: Invalid JSON
reset_config()
fd, path = tempfile.mkstemp(suffix=".json")
os.write(fd, b"not json at all")
os.close(fd)
try:
    load_config(path)
    print("FAIL: Should have raised ConfigValidationError")
except ConfigValidationError as e:
    print(f"PASS: ConfigValidationError on bad JSON — {e}")
    passed += 1
finally:
    os.unlink(path)

# Test 4: Real config loads correctly
reset_config()
c = load_config("config/tenant.json")
assert c.tenant_id == "mtu"
assert c.login_url == "https://obs.ozal.edu.tr/oibs/std/login.aspx"
assert c.grades_url == "https://obs.ozal.edu.tr/oibs/std/not_listesi_op.aspx"
assert c.schedule_url == "https://obs.ozal.edu.tr/oibs/std/caller.aspx?curPage=108"
assert c.food_menu_url == "https://sksdb.ozal.edu.tr/yemek_listesi"
assert c.selectors["CAPTCHA_IMG"] == "imgCaptchaImg"
assert c.selectors["GRADES_TABLE"] == "grd_not_listesi"
assert c.default_referer == "https://obs.ozal.edu.tr/oibs/std/index.aspx?curOp=0"
assert c.obs_domain == "https://obs.ozal.edu.tr"
assert c.scraper.timeout_seconds == 10
assert "CAPTCHA" in c.error_strings
assert c.default_headers["User-Agent"].startswith("Mozilla")
print("PASS: Real config loaded and all assertions passed")
passed += 1

# Test 5: Singleton behavior via get_config()
c2 = get_config()
assert c is c2, "get_config() should return cached instance"
print("PASS: get_config() returns cached singleton")
passed += 1

print(f"\n{passed}/5 tests passed")
