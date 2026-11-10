# ruff: noqa: E501
"""Licence policy: only free, properly licensed dependencies (docs/LICENSES.md).

Allowed: permissive licences (MIT, BSD, Apache-2.0, ISC, PSF, Zlib, 0BSD, Unlicense, CC-BY for data) and
file-level weak copyleft (MPL-2.0) when unmodified. Refused: GPL, AGPL, SSPL, Commons Clause and
proprietary terms. Reviewed exceptions are listed below with the reason.
"""

import json
from importlib import metadata
from pathlib import Path

REFUSED = (
    "AGPL",
    "GNU AFFERO",
    "SSPL",
    "SERVER SIDE PUBLIC",
    "COMMONS CLAUSE",
    "PROPRIETARY",
    "ELASTIC LICENSE",
    "BUSL",
    "BUSINESS SOURCE",
)
GPL = "GPL"  # plain and LGPL both contain it; LGPL is only allowed for the reviewed packages below

# npm: reviewed exceptions, each with the reason it is acceptable
NPM_LGPL_OK_PREFIX = (
    "@img/sharp-"  # Next.js's optional image libraries: separate, unmodified shared libraries
)
NPM_CUSTOM_OK = {
    "gsap": "GSAP standard no-charge licence: free for commercial use; we do not build competing animation tools"
}

LOCK = Path(__file__).resolve().parents[2] / "web" / "package-lock.json"


def _text(md) -> str:
    return " ".join(
        filter(
            None,
            [
                md.get("License-Expression"),
                (md.get("License") or "").splitlines()[0] if md.get("License") else "",
                *[c for c in (md.get_all("Classifier") or []) if c.startswith("License ::")],
            ],
        )
    ).upper()


def test_python_dependencies_are_free_and_permissive() -> None:
    bad = []
    for d in metadata.distributions():
        t = _text(d.metadata)
        if (
            any(r in t for r in REFUSED)
            or (GPL in t and "LGPL" not in t)
            or ("LGPL" in t and d.metadata["Name"].lower() not in {"psycopg2", "psycopg2-binary"})
        ):
            bad.append((d.metadata["Name"], t[:80]))
    assert not bad, f"Disallowed licences: {bad}. See docs/LICENSES.md for the policy."


# Packages whose metadata has no licence field but whose bundled LICENSE file was read (MIT).
LICENCE_FILE_REVIEWED = {"py-rust-stemmers"}


def test_every_python_package_declares_a_licence() -> None:
    missing = [
        d.metadata["Name"]
        for d in metadata.distributions()
        if not _text(d.metadata).strip()
        and d.metadata["Name"].lower().replace("_", "-") not in LICENCE_FILE_REVIEWED
    ]
    assert not missing, f"No licence information for: {missing}"


def test_web_dependencies_are_free_and_permissive() -> None:
    lock = json.loads(LOCK.read_text())
    bad = []
    for path, pkg in lock["packages"].items():
        if not path:
            continue
        name = path.split("node_modules/")[-1]
        lic = str(pkg.get("license", "")).upper()
        if not lic:
            bad.append((name, "no licence field"))
        elif (
            any(r in lic for r in REFUSED)
            or ("GPL" in lic and "LGPL" not in lic)
            or ("LGPL" in lic and not name.startswith(NPM_LGPL_OK_PREFIX))
            or ("STANDARD" in lic and name not in NPM_CUSTOM_OK)
        ):
            bad.append((name, lic))
    assert not bad, f"Disallowed or unreviewed licences: {bad}. See docs/LICENSES.md."


def test_the_reviewed_exceptions_still_exist_so_the_list_stays_honest() -> None:
    lock = json.loads(LOCK.read_text())
    names = {p.split("node_modules/")[-1] for p in lock["packages"] if p}
    assert "gsap" in names  # remove the exception when the package goes
    assert any(n.startswith(NPM_LGPL_OK_PREFIX) for n in names)
