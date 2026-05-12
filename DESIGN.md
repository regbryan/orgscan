---
name: OrgScan
description: Forensic Salesforce org health audit — dark, archival, diagnostic.
colors:
  carbon-black: "#141312"
  smoked-walnut: "#1C1A17"
  tarnished-bronze: "#241F1A"
  weathered-copper: "#2A241E"
  iron-filigree: "#2E2822"
  patina-edge: "#3D352D"
  bone-ivory: "#E8DFC9"
  faded-vellum: "#A89A7D"
  aged-parchment: "#6C6254"
  cinnabar: "#C14A3D"
  cinnabar-hover: "#D65A4A"
  verdigris: "#4F8A7C"
  verdigris-hover: "#5DA092"
  parchment-gold: "#B8A77A"
  persimmon: "#D4602A"
  slate-blue: "#7896B0"
typography:
  display:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0"
  body:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "'zero', 'ss02'"
  label:
    fontFamily: "Geist Mono, JetBrains Mono, Menlo, monospace"
    fontSize: "10px"
    fontWeight: 500
    letterSpacing: "0.14em"
    textTransform: "uppercase"
rounded:
  none: "0px"
  hairline: "2px"
  pill: "3px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "22px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.cinnabar}"
    textColor: "{colors.bone-ivory}"
    rounded: "{rounded.hairline}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "{colors.cinnabar-hover}"
    textColor: "{colors.bone-ivory}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.bone-ivory}"
    rounded: "{rounded.hairline}"
    padding: "9px 16px"
  button-success:
    backgroundColor: "{colors.verdigris}"
    textColor: "{colors.carbon-black}"
    rounded: "{rounded.hairline}"
    padding: "9px 16px"
  badge-critical:
    backgroundColor: "{colors.smoked-walnut}"
    textColor: "{colors.cinnabar}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  badge-warning:
    backgroundColor: "{colors.smoked-walnut}"
    textColor: "{colors.persimmon}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  badge-pass:
    backgroundColor: "{colors.smoked-walnut}"
    textColor: "{colors.verdigris}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  card:
    backgroundColor: "{colors.smoked-walnut}"
    rounded: "{rounded.hairline}"
    padding: "20px 22px"
  input:
    backgroundColor: "{colors.smoked-walnut}"
    textColor: "{colors.bone-ivory}"
    rounded: "{rounded.hairline}"
    padding: "8px 11px"
---

# Design System: OrgScan

## 1. Overview

**Creative North Star: "The Oxidized Plate"**

OrgScan is a forensic instrument rendered in oxidized metals and aged paper. The surface reads like a chemically-treated etching plate: warm near-black grounds, hairline iron rules, ivory text that suggests vellum more than screen. Color appears only where a chemical reaction would leave a mark — cinnabar where things are broken, verdigris where they have aged well, parchment where the document has been stamped. Nothing glows. Nothing floats. Everything has been touched by time and use.

The system explicitly rejects the entire vocabulary of contemporary SaaS: no gradient hero metrics, no glassmorphism, no neon-on-black, no celebratory empty states, no Salesforce-Lightning blue. It also rejects the opposite cliché — terminal-green hacker chic — because that's a costume, not a tool. This is the look of an audit report that survives the engagement, not a dashboard that ships a quarterly screenshot.

Density is calm. Geist's neutral-warm serif handles structure; Geist Mono handles every number, ID, and label. Layouts are grid-strict, padding is consistent at 22-32px on major surfaces, and depth comes from one-pixel rules and tonal layering — never from shadows.

**Key Characteristics:**
- Warm near-black surfaces, hue-tinted toward bronze, never `#000`
- Geist + Geist Mono pairing, with mono reserved for IDs / numbers / labels
- Hairline (1px) rules carry every separation; no shadow on any element
- Signal-only color: severity is the only reason a hue appears at saturation
- Numbered findings, section marks (`§`), tabular figures, leading-zero counters — print-document mannerisms applied to a screen
- 2px radii everywhere; corners are barely rounded, never pillowy

## 2. Colors

A palette of oxidation: the colors a metal plate and a paper document accumulate after exposure. Surfaces and ink are tinted toward bronze; signal colors are mineral pigments (cinnabar, verdigris, persimmon, parchment).

### Primary
- **Cinnabar Red** (`#C14A3D`): The critical signal. Used on `btn-primary`, critical badges, the active nav-item edge stripe, focus outlines, the active pill-tab underline. Cinnabar means "this is broken and must be addressed." Its presence is information, not decoration.

### Secondary
- **Verdigris** (`#4F8A7C`): The pass signal. Used on success badges, success buttons, the org-connection dot, gauge arcs when health is good. Verdigris means "this aged well." Never used as a decorative accent.
- **Parchment Gold** (`#B8A77A`): The stamp and marker signal. Used on the `§` section mark, finding row counters, badge counts, neutral/stamp badges, sidebar logo icon. Parchment means "this is a label or a numeric marker," never "this is important."

### Tertiary
- **Persimmon** (`#D4602A`): Warning severity only. Reserved for badge-warning. Distinct from cinnabar in hue (warmer, more orange) so the two never collapse for color-blind users.
- **Slate Blue** (`#7896B0`): Info severity only. The single cool note in an otherwise warm palette. Reserved for badge-info; never used elsewhere.

### Neutral (the oxidized-plate substrate)
- **Carbon Black** (`#141312`): App background. Not pure black — tinted toward bronze (hue ~30°) so cinnabar and verdigris read as belonging.
- **Smoked Walnut** (`#1C1A17`): Card and sidebar surface.
- **Tarnished Bronze** (`#241F1A`): Card headers, table-head, hover surfaces, sidebar logo plate.
- **Weathered Copper** (`#2A241E`): Active nav-item background. The deepest tonal lift.
- **Iron Filigree** (`#2E2822`): The standard 1px rule color. Every border and divider in the system.
- **Patina Edge** (`#3D352D`): The strong 1px rule color. Used at the bottom of page headers (double-rule), table-head separators, and the strong outline on secondary buttons.
- **Bone Ivory** (`#E8DFC9`): Default text on dark. Warm white tinted toward parchment.
- **Faded Vellum** (`#A89A7D`): Secondary text and inactive nav-item labels.
- **Aged Parchment** (`#6C6254`): Tertiary text — small-caps mono labels, placeholder text, faint metadata.

### Named Rules

**The No-Pure-Black Rule.** `#000` and `#fff` are prohibited. Every neutral carries a measurable warm tint toward the bronze hue. If a tool ever auto-fills `#000` for a background or `#fff` for text, replace it with `--base` and `--ivory` before commit.

**The Signal-Only Rule.** Cinnabar, verdigris, persimmon, slate-blue, and parchment-gold are reserved. Each carries exactly one meaning across the entire app. Cinnabar may not appear on a non-critical surface for any reason. Parchment may not be used to "warm up" a button. If the meaning isn't present, the color isn't either.

**The Color-Mix Rule.** Tinted backgrounds for badges are always `color-mix(in srgb, var(--signal) 12-14%, var(--surface))`, never opaque pastels. The substrate must show through. The point is a patina, not a fill.

## 3. Typography

**Display / Body Font:** Geist (with Inter, system-ui fallback)
**Mono / Label Font:** Geist Mono (with JetBrains Mono, Menlo fallback)

**Character:** A typographic pair built for technical documents that need to feel composed. Geist's slightly closed apertures and even rhythm read as institutional without being stiff; Geist Mono is the project's voice for every number, ID, and stamp. The two fonts do different jobs and never trade places.

### Hierarchy
- **Display** (Geist 500, 32px, line-height 1.1, letter-spacing -0.015em): page titles only — "Findings", "Org Health".
- **Headline** (Geist 500, 22px, line-height 1.2): primary section headings.
- **Title** (Geist 500, 17px, line-height 1.3): card titles, section titles (with `§` mark prepended).
- **Body** (Geist 400, 14px, line-height 1.55, font-features `'zero' 'ss02'`): default prose, finding descriptions, table cells. Cap line length at 65–75ch where prose runs long.
- **Label** (Geist Mono 500, 10–10.5px, letter-spacing 0.14em, UPPERCASE): page subtitles, table headers, metric labels, kicker text. The system's "small-caps voice."

### Named Rules

**The Mono-For-Identity Rule.** Geist Mono is reserved for: record IDs, API names, counts, severity badges, labels, kickers, table headers, and the `§` section mark. It is never used for body prose, paragraph text, or buttons (except the kicker inside a button). If a value can be measured or quoted, it's mono.

**The Tabular-Figures Rule.** Every number that appears in a count, score, percentage, or ID must use `font-variant-numeric: tabular-nums` and `font-feature-settings: 'zero', 'tnum'`. The slashed zero is a feature, not a bug.

**The Section-Mark Rule.** Section titles lead with a parchment-colored `§` in mono. The mark is the project's visual signature; it appears nowhere else.

## 4. Elevation

OrgScan is flat. There are no shadows, no backdrop-filters, no glow, no elevation transitions. Depth is conveyed by **tonal layering** alone: `carbon-black → smoked-walnut → tarnished-bronze → weathered-copper` is the entire stack, and the difference between adjacent layers is intentionally small (≤8 lightness points). The only allowed `box-shadow` token is `inset 0 0 0 1px var(--rule)` — a hairline edge, not a lift.

State changes that would conventionally use a shadow use **hairline inset rings** instead. Focus on inputs is conveyed by a 1px inset cinnabar ring. The active pill-tab announces itself with a 2px inset cinnabar underline. The active nav-item carries a 3px cinnabar edge-stripe on its left side — the **one exception** to the side-stripe ban, justified because it's a navigation affordance, not a decorative accent.

### Named Rules

**The Flat-By-Default Rule.** Surfaces sit on the page. They do not float, lift, or hover. Any `box-shadow` value outside the allowed inset-1px hairline is prohibited and must be rewritten as a tonal layer or an inset ring.

**The No-Blur Rule.** `backdrop-filter`, `filter: blur()`, and frosted-glass treatments are forbidden. The interface is etched, not photographed.

## 5. Components

### Buttons
- **Shape:** 2px radius (`{rounded.hairline}`). Padded at 9px × 16px (sm: 6px × 11px).
- **Primary:** Cinnabar fill on ivory text. Hover lifts to `cinnabar-hover`. The default destructive-or-decisive action.
- **Secondary:** Transparent background, ivory text, `patina-edge` border. Hover deepens the border to `faded-vellum` and shifts background to `tarnished-bronze`.
- **Success:** Verdigris fill on `carbon-black` text (weight 600 for contrast). Reserved for confirmations like "Connection verified."
- **Danger:** Transparent background, cinnabar text and border. Hover inverts to cinnabar fill on ivory.
- **Focus:** 2px solid cinnabar outline with 2px offset. Never a glow.

### Badges (severity pills)
- **Style:** Mono uppercase, 10px, letter-spacing 0.1em, 3px radius, 1px tinted border, `color-mix` translucent background.
- **States:** `critical` (cinnabar), `warning` (persimmon), `info` (slate-blue), `pass` (verdigris), `neutral` (parchment). Severity is always icon + label + color, never color alone.

### Cards
- **Corner Style:** 2px radius. Barely rounded.
- **Background:** `smoked-walnut` body, `tarnished-bronze` header.
- **Shadow Strategy:** None. See Elevation.
- **Border:** 1px `iron-filigree` all around.
- **Internal Padding:** 20px × 22px body; 16px × 22px header.

### Inputs / Fields
- **Style:** `smoked-walnut` background, 1px `iron-filigree` border, 2px radius, 8px × 11px padding. Body inputs are Geist serif; selects are Geist Mono at 12px / letter-spacing 0.02em (they read as machine input).
- **Focus:** Border shifts to cinnabar AND an inset 1px cinnabar ring. No outer glow.
- **Placeholder:** `aged-parchment`.

### Navigation (Sidebar)
- **Width:** 232px fixed (`--col-sidebar`), `smoked-walnut` background, `iron-filigree` right rule.
- **Item Style:** Geist 14px, ivory-dim default, ivory on hover (with `tarnished-bronze` background), ivory on active (with `weathered-copper` background and a 3px cinnabar inset edge-stripe on the left).
- **Badges:** Mono 10px count chips, parchment text, `patina-edge` border. On active item, border and text shift to cinnabar.
- **Logo plate:** A 34px square `tarnished-bronze` tile with a `patina-edge` border; logo glyph in parchment.

### Findings Table (signature component)
- **Frame:** Bordered top and bottom only, with `patina-edge` 1px rules. No outer card.
- **Head:** Mono uppercase, 10.5px, 0.12em letter-spacing, `ivory-dim` on `tarnished-bronze`, separated from body by `patina-edge`.
- **Rows:** 14px serif body on ivory; hover lifts to `tarnished-bronze`; rows are separated by `iron-filigree` hairlines.
- **Numbering:** Each row's first cell carries a CSS-counter-driven `decimal-leading-zero` index in parchment mono (`01`, `02`, `03`), absolutely positioned to the left. Findings are numbered like clauses in a legal document.
- **Finding Title:** Geist 500, 14px, with a 1px dashed `patina-edge` underline that shifts to parchment on hover.

### Page Header (signature component)
- **Treatment:** A title in display type, a mono uppercase kicker subtitle, and a **double-rule editorial break** at the bottom — accomplished via `border-bottom: 1px var(--rule)` plus a layered `box-shadow: 0 3px 0 0 var(--base), 0 4px 0 0 var(--rule-strong)`. The double rule is the page's letterhead.

### Section Title (signature component)
- **Treatment:** A parchment-colored `§` in mono followed by a Geist 500 17px title. The mark is project signature and must precede every section title.

## 6. Do's and Don'ts

### Do:
- **Do** use cinnabar (`#C14A3D`) only where something is broken or destructive. If you want a "highlight color" for anything else, the answer is parchment-gold or nothing.
- **Do** prepend the `§` mark to every section title.
- **Do** use `font-variant-numeric: tabular-nums` on every count, score, percentage, and ID. Slashed zeros are a feature.
- **Do** number findings rows with `counter(finding, decimal-leading-zero)` so they read like clauses (`01`, `02`, `03`).
- **Do** convey severity with icon + label + color, in that order of reliability.
- **Do** use 1px hairline rules and tonal lifts for separation. The system's depth is `carbon-black → smoked-walnut → tarnished-bronze → weathered-copper`.
- **Do** reserve Geist Mono for IDs, numbers, kickers, labels, table headers, and the `§` mark.
- **Do** honor `prefers-reduced-motion` — state-change motion collapses to instant or opacity-only fades.
- **Do** keep buttons and cards at 2px radius. Anything rounder reads as SaaS.

### Don't:
- **Don't** use `#000` or `#fff`. Every neutral is hue-tinted toward bronze. (See PRODUCT.md: "Honest, diagnostic, calm.")
- **Don't** introduce gradients, glow, drop-shadows, or `backdrop-filter`. The interface is etched, not photographed.
- **Don't** ship Salesforce-Lightning blue (`#0070D2`, `#1589EE`) or any cool-blue accent. OrgScan inspects Salesforce; it does not cosplay as Salesforce. (See PRODUCT.md anti-references.)
- **Don't** use the gradient-hero-metric template (big number + gradient + repeated identical cards). Metric cards are mono labels and ivory numbers on flat surfaces. (See PRODUCT.md anti-references.)
- **Don't** use celebratory empty states or "great job!" copy. A passing check is a quiet verdigris checkmark with the label `PASS`. (See PRODUCT.md: "No reassurance theater.")
- **Don't** use color-only severity. Color-blind users must be able to read severity from icon and label alone.
- **Don't** use side-stripe borders (`border-left > 1px` as a colored accent) anywhere except the active sidebar nav-item edge-stripe — that one is a wayfinding affordance and is explicitly allowed.
- **Don't** use glassmorphism, frosted panels, neon-on-black, or any decorative accent that would not survive the PDF export. (See PRODUCT.md: "The PDF is the deliverable.")
- **Don't** name severities with emotional language ("urgent", "attention needed"). Use `Critical / Warning / Info / Pass` and let cinnabar do the work.
- **Don't** use Geist Mono for body prose. Mono is identity-voice only.
- **Don't** invent new accent colors. The five mineral signals (cinnabar / persimmon / slate-blue / verdigris / parchment) are the complete vocabulary.
