# Tropical Observatory · locked initial direction

Based on `rounds/round-01/01-observatory.png`, selected under delegated autopilot. On 9 September the owner explicitly liked the island artwork and asked to preserve the Tropical Observatory direction while refining the tropical game feeling and clarity. Values below are implementation choices estimated from the image, not sampled pixel measurements.

## Visual language

Quiet, dark, earthy workspace; one warm action; botanical greens; crisp pixel motifs; an illustrated island joining two different shops with an observatory. It should feel like a place worth returning to while making the next everyday task obvious. Never illustrate invented inventory or financial success as if real.

- Background `#10241f`; sidebar `#0d201b`; panel `#162c25`; line `#2c4136`.
- Text `#eee9d9`; body-muted `#a3b3a5`; fine detail `#758b7d`.
- Amber action `#e9b973` with dark ink; mint `#a3c6a1`.
- Day variant uses paper `#f3f0e5`, text `#253d30`, and green boundaries. Same components and information order.
- Day action amber was refined to `#956024` on 9 September for clearer separation, with day status text `#81521f`.
- DM Sans 400/500/600 for interface copy. Cormorant Garamond 500 and italic for editorial titles. Fonts are bundled locally; no runtime third-party font fetch.
- Desktop sidebar 230 px; content padding 40 px; max content 1570 px. Nested spacing predominantly 8–32 px. Panels 8–14 px corner radius; dialogs 17 px desktop / 13 px mobile.
- Hero is two columns on wide screens, stacked below 951 px. Mobile title is 39 px, with the primary action before the artwork. Main navigation becomes an off-canvas drawer below 721 px; closed drawer is hidden from keyboard/assistive access.
- Core controls are at least 44 px where possible; secondary icon controls are generally 38 px. Small meta labels are secondary; consequential instructions and input labels use larger text.
- Motion is limited to short hover/press feedback and a loading spinner. Respect reduced motion. No constant decorative animation or distracting parallax.

## Art

`public/art/island.png`: built-in generated standalone illustration, 1536×1024 PNG with actual RGBA alpha. Metadata inspection confirmed alpha spans 0–254. The image has no baked-in UI text. Transparency is preserved; CSS positions and contains it without mutating the raster. Full generation prompt is in `design/ASSET_PROMPT.md`.

The island is explicitly an illustrated vision, not a literal store map or photograph. Decorative coordinates approximate Panglao and do not claim either store’s exact address. Small pixel glyphs are native CSS; interface icons use Lucide.

## Interaction contract

Home → one primary Add update action → choose store/category → note/files → saved confirmation → Collection → source review. Do not label a click or partial upload as saved. Existing originals stay immutable. Human review is source review, not a financial audit. AI proposals are explicitly marked draft and source-linked.

Collection provides search, store filter, review status, refresh, and source downloads. Our stores contains only founder-reported profiles marked for confirmation. Roadmap phases are planned requirements, not artificial completion bars. Settings exposes actual connection readiness and owner-only export/audit controls.

## Validation

See `docs/VALIDATION.md` and `design/evidence/`. Desktop and phone rendering were inspected and the primary intake/review workflow was exercised with synthetic data. Browser viewport simulation is not a substitute for Moritz's actual device/network check before deployment.

## 9 September · field guide refinement

Implementation within the existing direction, without a new mockup round: the unchanged island appears beside an editorial chapter introduction, followed by four connected route stops. Selection explores requirements; it never advances or unlocks a phase. The selected phase names the responsible people, intended outcome, acceptance requirements and a likely failure with a response.

The overview's first action area now shows one suggested source/review for the selected store, with separate first-sales-source signals for each accessible store. This replaces the generic list of three actions. Warm top-edge pixel details and subtle botanical surface gradients extend the game-like setting through CSS; the original raster was not regenerated, retouched or downscaled. The owner has not yet reviewed the final refined screen.

At phone widths the coverage card uses one column, larger copy and a 44 px minimum action height. Decorative corner pixels are hidden there to avoid colliding with coverage text.

Day/night roadmap, the four phase selections, mobile store-targeted capture, expand/collapse launch guidance, and the recovery form were inspected. Evidence is in `design/evidence/roadmap-*` and `docs/VALIDATION.md`.

## 9 September · owner copy correction

The owner rejected motivational slogans, invitation/password-reset instructions and unsolicited walkthrough copy. This supersedes the earlier editorial chapter-copy choice. Keep Tropical Observatory's island, palette, typography and pixel details; use plain functional labels and short factual descriptions. No "little clarity", "grow together", "put down roots", personalized pep talks or ornamental AI language. Login contains the brand, store names, Email, Password and Sign in. Help remains optional. Technical deployment checks are owner-only; do not surface infrastructure explanations in staff tasks. Keep meaningful save/error feedback and honest data/integration limits.

This is a copy and behavior correction within the existing visual direction, not a new design round. Updated evidence uses the `plain-*` prefix.
