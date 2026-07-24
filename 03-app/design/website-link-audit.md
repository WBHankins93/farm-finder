# Website link audit — July 2026

All 87 farm `website` URLs in the dataset were fetched, followed through redirects, and
re-verified with browser-equivalent request headers. Corrections below were applied to the
demo dataset (`03-app/design/demo/farms.json`). **The same corrections should be made
upstream in the governed workbook** (`research/local_farm_database_final.xlsx`), since the
site's `app/data/farms.json` is generated from it by `scripts/generate-farms.py` and would
otherwise revert on the next build.

## Method note (important for future audits)

A bare automated request returned **403 Forbidden** for 8 sites that are actually live —
they bot-block non-browser user agents (Cloudflare/WAF). Re-checking with a real browser
User-Agent + `Accept` headers returned 200. **A 403/timeout is not proof a link is dead.**
Only DNS-resolution failures (NXDOMAIN), persistent connection failures, and 4xx/5xx that
survive a browser-header retry were treated as broken.

## Result: 87 checked → 69 good, 11 redirect-corrected, 8 removed

### Removed — link does not work (set `website=""`, `hasWebsite=false`, `onlineStore=false`)

| Farm | URL | Reason |
|------|-----|--------|
| Beason Family Farm | beasonfamilyfarm.com | DNS does not resolve (NXDOMAIN) |
| Jot & Tittle Farms | jotandtittlefarms.com | DNS does not resolve (NXDOMAIN) |
| Mitchell Family Farms | mitchellfamilyfarms.com | DNS does not resolve (NXDOMAIN) |
| Shaded Grove Farm Market | shadegrovefarmmarket.com | DNS does not resolve (NXDOMAIN) |
| Sunflower Hill Farm | sunflowerhillfarmllc.com | DNS does not resolve (NXDOMAIN) |
| WS Cattle Co. | wscattleco.com | Resolves but returns no response (000 / prior 404) |
| Inglewood Farm | inglewoodfarm.com | TLS handshake fails, unreachable |
| Blue Harvest Farms | blueharvestfarms.com | Cloudflare 522 — origin server down |

### Redirect-corrected — link works, updated to the URL it actually resolves to

| Farm | Was | Now |
|------|-----|-----|
| Black Jack Ranch | www.blackjackranchms.com | https://blackjackranchms.com/ |
| Butterfield Farm | butterfieldfarms.net | https://www.butterfieldfarms.net/ |
| Coy Bee Company | www.coybeecompany.com | https://coybeecompany.com/ |
| Dowdle Family Farms | dowdlefamilyfarms.com | https://www.dowdlefamilyfarms.com/ |
| Hickory Heal Farm | www.hickoryhealfarm.com | https://hickoryhealfarm.com/ |
| Local Cooling Farms | laughingbuddhanursery.com | https://www.laughingbuddhanursery.com/ |
| Salad Days | www.saladdaysproduce.com | https://saladdaysproduce.com/ |
| Tomkins Farm | tomkinsfarms.com | https://www.tomkinsfarms.com/ |
| VEGGI Co-Op | veggifarmcoop.com | https://www.veggifarmcoop.com/ |
| Weesner Meadow Farm | weesnermeadow.com | https://www.realgrassfedmeat.com/ (their store domain) |
| Honestly Beef | www.honestlybeef.com | https://honestlybeef.com/ (www host refused connection) |

### Worth a human look
- **Weesner Meadow Farm** now points at `realgrassfedmeat.com` — a different brand domain the
  original redirects to. Confirm this is the same business before publishing.
- **Local Cooling Farms** resolves to `laughingbuddhanursery.com` — likely a related/parent
  operation; confirm.

## Reproduce
`scratchpad/check_links.py` fetches + classifies; findings above were re-verified with
`curl -L` using browser headers.
