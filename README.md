# sidestore-source

SideStore/AltStore source for my own apps. Add this URL in SideStore → Sources:

    https://0xpincette.github.io/sidestore-source/apps.json

App repos publish here from their release workflow on a `v*` tag: build an unsigned IPA, run `scripts/add-version.py`, commit, push. Pages serves the result. IPAs are unsigned; SideStore signs them with your Apple ID on install.

SideStore rejects an app with no versions, so add the source URL on the phone only after the app's first tag has published.

To add an app: register its entry (bundle id, name, icon) in `apps.json` with an empty `versions` list, add an icon under `icons/`, then give the app repo the deploy key secret `SIDESTORE_DEPLOY_KEY`.

Everything here is public, including the IPAs.
