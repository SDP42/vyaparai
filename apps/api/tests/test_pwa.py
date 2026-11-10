"""The installable app: manifest, icons, service worker rules, and complete translations."""

import json
import re
from pathlib import Path

from PIL import Image

WEB = Path(__file__).resolve().parents[2] / "web"
PUBLIC = WEB / "public"


def test_manifest_is_installable() -> None:
    m = json.loads((PUBLIC / "manifest.webmanifest").read_text())
    assert m["display"] == "standalone"
    assert m["start_url"] == "/app"
    assert m["name"]
    assert m["short_name"]
    sizes = {(i["sizes"], i["purpose"]) for i in m["icons"]}
    assert ("192x192", "any") in sizes
    assert ("512x512", "any") in sizes
    assert ("512x512", "maskable") in sizes
    for i in m["icons"]:
        img = Image.open(PUBLIC / i["src"].lstrip("/"))
        assert f"{img.width}x{img.height}" == i["sizes"]
    assert (PUBLIC / "icons" / "apple-touch-icon.png").exists()


def test_the_service_worker_never_caches_sessions_uploads_or_writes() -> None:
    sw = (PUBLIC / "sw.js").read_text()
    assert 'req.method !== "GET"' in sw  # writes pass straight through
    never = re.search(r"const NEVER = /(.*)/;", sw)
    assert never
    for word in ("auth", "stream", "import", "export", "download", "pdf", "csv"):
        assert word in never.group(1)
    readable = re.search(r"const READABLE = /(.*)/;", sw)
    assert readable
    assert "auth" not in readable.group(1)
    assert "clear" in sw  # sign-out wipes the saved numbers
    assert "x-vyapar-offline" in sw  # the app can tell saved numbers from live ones


def test_the_read_allow_list_matches_real_endpoints_only() -> None:
    sw = (PUBLIC / "sw.js").read_text()
    pattern = re.compile(re.search(r"const READABLE = /(.*)/;", sw).group(1).replace("\\/", "/"))
    ws = "e5e39909-dc87-4ce2-ab60-77d6802b898e"
    for ok in (
        "analytics/overview",
        "alerts/summary",
        "udhaar/summary",
        "inventory/overview",
        "forecasts/latest",
    ):
        assert pattern.search(f"/api/v1/workspaces/{ws}/{ok}")
    for no in ("auth/login", "documents/search", "assistant/ask", "bills", "campaigns/contacts"):
        assert not pattern.search(f"/api/v1/workspaces/{ws}/{no}")


def test_sign_out_clears_the_saved_numbers_in_the_app_code() -> None:
    assert "vyapar-data-v1" in (WEB / "lib" / "session.ts").read_text()


def test_every_translation_key_exists_in_all_three_languages() -> None:
    src = (WEB / "lib" / "i18n.tsx").read_text()
    blocks = {
        name: set(re.findall(r'"([a-z]+\.[A-Za-z]+)":', body))
        for name, body in re.findall(r"const (en|hinglish|hi)[^=]*= \{(.*?)\n\}", src, re.S)
    }
    assert set(blocks) == {"en", "hinglish", "hi"}
    assert blocks["en"]
    assert blocks["en"] == blocks["hinglish"] == blocks["hi"]
    hindi = "".join(re.findall(r'"nav\.[a-z]+": "([^"]+)"', src.split("const hi: Dict")[1]))
    assert re.search(r"[ऀ-ॿ]", hindi)  # the Hindi dictionary really is in Devanagari
