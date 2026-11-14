#!/usr/bin/env python3
"""Add an IPA to the SideStore source.

Reads bundle id and version from the IPA's Info.plist, copies the IPA into
ipa/, and prepends a version entry to that app in apps.json. The app must
already be registered in apps.json (name, icon, description).

Usage: add-version.py APP.ipa --base-url URL [--notes TEXT] [--keep N]
"""

import argparse
import datetime
import json
import os
import plistlib
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "apps.json")
IPA_DIR = os.path.join(ROOT, "ipa")
APP_PLIST = re.compile(r"^Payload/[^/]+\.app/Info\.plist$")


def read_info(ipa_path):
    with zipfile.ZipFile(ipa_path) as z:
        names = [n for n in z.namelist() if APP_PLIST.match(n)]
        if len(names) != 1:
            sys.exit(f"expected one Payload/*.app/Info.plist in {ipa_path}, found {len(names)}")
        return plistlib.loads(z.read(names[0]))


def sort_key(v):
    parts = tuple(int(x) if x.isdigit() else 0 for x in v["version"].split("."))
    build = int(v["buildVersion"]) if v["buildVersion"].isdigit() else 0
    return parts, build


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ipa")
    p.add_argument("--base-url", required=True, help="public URL this repo is served from")
    p.add_argument("--notes", default="", help="release notes shown in SideStore")
    p.add_argument("--keep", type=int, default=5, help="versions kept per app; older IPAs are deleted")
    args = p.parse_args()
    if args.keep < 1:
        sys.exit("--keep must be at least 1")

    info = read_info(args.ipa)
    bundle_id = info["CFBundleIdentifier"]
    version = info["CFBundleShortVersionString"]
    build = str(info["CFBundleVersion"])
    min_os = info.get("MinimumOSVersion", "")

    with open(SOURCE) as f:
        source = json.load(f)

    app = next((a for a in source["apps"] if a["bundleIdentifier"] == bundle_id), None)
    if app is None:
        sys.exit(f"{bundle_id} is not registered in apps.json; add its app entry first")

    versions = app.setdefault("versions", [])
    if any(v["version"] == version and v["buildVersion"] == build for v in versions):
        print(f"{bundle_id} {version} ({build}) is already published; nothing to do")
        return

    filename = f"{bundle_id}-{version}-{build}.ipa"
    os.makedirs(IPA_DIR, exist_ok=True)
    dest = os.path.join(IPA_DIR, filename)
    shutil.copyfile(args.ipa, dest)

    entry = {
        "version": version,
        "buildVersion": build,
        "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "localizedDescription": args.notes or f"Version {version} ({build})",
        "downloadURL": f"{args.base_url.rstrip('/')}/ipa/{filename}",
        "size": os.path.getsize(dest),
    }
    if min_os:
        entry["minOSVersion"] = min_os
    versions.append(entry)
    # Newest first: SideStore treats versions[0] as the latest release, and tags
    # can publish out of order.
    versions.sort(key=sort_key, reverse=True)

    for old in versions[args.keep:]:
        old_file = os.path.join(IPA_DIR, old["downloadURL"].rsplit("/", 1)[-1])
        if os.path.exists(old_file):
            os.remove(old_file)
    del versions[args.keep:]

    # Legacy app-level fields for older AltStore/SideStore clients.
    latest = versions[0]
    app["version"] = latest["version"]
    app["versionDate"] = latest["date"]
    app["versionDescription"] = latest["localizedDescription"]
    app["downloadURL"] = latest["downloadURL"]
    app["size"] = latest["size"]

    with open(SOURCE, "w") as f:
        json.dump(source, f, indent=2)
        f.write("\n")

    print(f"published {bundle_id} {version} ({build}) -> {entry['downloadURL']}")


if __name__ == "__main__":
    main()
