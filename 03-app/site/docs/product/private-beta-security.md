# Private web beta dependency checkpoint — 2026-10-19

This checkpoint applies to the Cloudflare Worker build and owner-only web beta.
It is not a penetration test or a claim that the dependency tree is vulnerability-free.

The MapLibre attribution sanitizer patch is installed at 6.4.1, including its
Vite-bundled module worker. React, React DOM and react-server-dom-webpack are
updated together to 19.2.8; Next and eslint-config-next are updated to 16.3.8.
The versions are pinned and the site build, typecheck and application tests pass.

A fresh npm audit reports 28 affected package entries: 0 critical, 21 high,
6 moderate and 1 low. Entries can propagate one advisory into multiple parents;
they are not a count of independently exploitable application vulnerabilities.
MapLibre, Next and react-server-dom-webpack no longer appear as vulnerable entries.

## Remaining exposure and remediation

- Vite/Cloudflare plugin/Wrangler/Miniflare, glob/schema parsers and lint tooling
  remain affected. They run in the build/development toolchain; do not expose a
  development server as the beta or accept untrusted build inputs. Patch these
  in the next serial dependency PR rather than running audit fix with force.
- vinext's image-size dependency is imported by metadata-route-build-data.js.
  The inspected server output has no image-size or sharp import/reference.
  The Worker uses vinext's image handler and Cloudflare IMAGES binding or its
  static-asset fallback, not Next's Node image optimizer. Installed sharp
  advisories therefore do not establish exposure through this Worker path.
  Reassess if changing hosting target, image handling or metadata build inputs.
- Moderate/low entries also remain; runtime consumers such as compressed map
  data must be evaluated in the follow-up, not hidden with omit-dev audit.

The release owner must re-audit the exact final dependency lock before expanding
access beyond the private beta. This checkpoint expires when the runtime,
lockfile or hosting target changes, or before public launch, whichever is first.
Public feedback remains disabled; it has separate operational activation gates.

## Verification limits

General tests skip optional feedback database suites without disposable DB URLs.
A separate required-integration CI change is in progress. Browser checks use
Chrome WebGL with desktop and mobile viewports, not physical-device certification.
The final hosted version must pass authenticated discovery smoke tests and deny
anonymous access before it is shared. Merge/build success alone does not prove
that a particular version is running.
