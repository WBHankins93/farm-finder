# Discovery acceptance matrix

The nearby-first explorer is released only when the application, database, and
manual browser checks below pass against the same governed dataset release.

## Automated on every pull request

| Risk | Test layer | Gate |
| --- | --- | --- |
| Query normalization, filter AND semantics, sort selection | Unit | `npm run test:unit` |
| URL round-trip and GPS omission | Unit | `npm run test:unit` |
| Cursor stability and accumulation | Unit + PostGIS | `npm run test:unit`, `npm run db:test` |
| Superseded request cancellation | Unit | `npm run test:unit` |
| Selection clearing and off-page retention | Unit | `npm run test:unit` |
| GPS denial and coordinate rounding | Unit | `npm run test:unit` |
| Zero/invalid coordinates and terminal shared-point clusters | Unit | `npm run test:unit` |
| List/count/map consistency and public-location enforcement | PostGIS | `npm run db:test` |
| Spatial index use | PostGIS `EXPLAIN` assertion | `npm run db:test` |
| Server shell and rollback explorer | Rendered HTML | `npm test` |
| Type safety, including Worker bindings | Static | `npm run typecheck` |

## Browser acceptance before enabling `EXPLORER_V2`

Run at desktop and 390px mobile widths with keyboard, screen reader, reduced
motion, and a throttled network profile:

1. Search for a governed city, deny GPS once, then approve it; verify denied
   GPS returns focus to the city field and no prompt occurs without a click.
2. Toggle List/Map after scrolling and moving the map; verify list scroll, map
   camera, filters, and selection survive both directions.
3. Pan the map; verify results do not change until **Search this area** is used.
4. Hover and keyboard-focus a card; verify only its pin highlights. Use **Show
   on map** and confirm the camera pans without changing zoom.
5. Select a pin outside the loaded page and confirm the pinned **Selected farm**
   row does not reorder results.
6. Open/close filter and profile dialogs with Escape and Tab; verify focus is
   trapped, restored, visible, and all mobile targets are at least 44px.
7. Exercise back/forward across place, radius, filters, view, bounds, and farm
   selection. Confirm GPS coordinates never appear in the URL or analytics.
8. Exercise long names, missing contacts, empty results, API errors, and a tile
   failure. The list must remain usable and prior results stay visible while a
   refresh is pending.

## Release performance gates

- No production request for `/farms.json` with `EXPLORER_V2=true`.
- LCP < 2.5s and INP < 200ms at the 75th percentile.
- Warm list/map API p95 < 300ms.
- Compressed list response < 200KB and map response < 300KB.
- Golden city, product, service, radius, and viewport queries match the
  promoted dataset release before the flag is enabled.

Automated browser performance and visual-regression infrastructure is not yet
present in this repository. Until it is added, the browser and performance
sections are explicit promotion checks rather than claims made by unit tests.
