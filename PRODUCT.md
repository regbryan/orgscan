# Product

## Register

product

OrgScan's primary surface is a consultant/admin tool — the design serves the workflow. A separate marketing/landing surface will be built later to sell OrgScan (direct site and AppExchange listing); that work runs in the **brand** register and will override this default per task.

## Users

**Primary:** Salesforce admins. Two profiles share the same UI:

- **Consultants** running paid health audits against client orgs mid-engagement. They live in the app for hours at a time, comparing findings across multiple orgs.
- **Client-side admins** running OrgScan on their own org, either to prep for an external audit or to self-diagnose. Less consulting experience, more org context.

Both are technical enough to read flow metadata and permission sets, but neither is a developer. They want a defensible answer to "what's wrong with this org and what do I do about it," fast.

**Secondary (read-only):** the consultant's client (often a Salesforce-adjacent exec or IT lead) who receives the exported PDF. They never touch the app — the report is the client-facing artifact.

## Product Purpose

Surface real, actionable problems in a Salesforce org — dead licensed users, flows missing API-version bumps or descriptions, hard-coded record IDs in flows, unused custom fields, over-permissioned profiles, validation rules without descriptions — and turn them into a client-ready audit report.

Success: a consultant runs OrgScan against a new client org, walks out with a prioritized findings list and a PDF the client signs off on, in under an hour. The findings are specific enough to act on without further investigation.

## Brand Personality

**Honest, diagnostic, calm.** Trustworthy mechanic in language; lab instrument in visuals. The tool names problems plainly, shows the evidence, and stops talking. No reassurance theater, no marketing voice inside the product.

Voice rules:
- Findings are stated as facts with counts and records, never as warnings or pleas.
- Severity language is concrete (`Critical / Warning / Info / Pass`), not emotional (`urgent`, `attention needed`).
- "AI" appears in the product only where Claude actually wrote something; never as a feature badge.

## Anti-references

What this should NOT look like:

- Salesforce Lightning clones — the blue, the cards, the cluttered ribbon. OrgScan inspects Salesforce; it does not cosplay as Salesforce.
- Generic SaaS dashboards built on the gradient-hero-metric template (big number, small label, gradient accent, repeating identical cards).
- AppExchange listing aesthetic — stock illustrations, "trust us" badges, marketing-tone microcopy.
- Glassmorphism, glow, neon-on-black, decorative gradients, playful illustrations.
- Celebratory empty states or "great job!" reassurance. A passing check is a quiet checkmark.

## Design Principles

1. **Refine, don't reinvent.** The current "Oxidized Plate" aesthetic — dark archival surfaces, Geist + Geist Mono, cinnabar/verdigris/parchment signal palette, no glows or gradients — is the spec. Design work tightens it, never replaces it.
2. **Findings, not vibes.** Every screen names a concrete problem with a count, a record reference, and an action. If a section can't pass that test, it doesn't earn the pixels.
3. **The PDF is the deliverable.** The app produces a defensible report. UI choices that don't survive the export (clever hovers, motion-only affordances) are second-class.
4. **Admin-legible, expert-precise.** A working admin should understand the finding without jargon; an expert should trust the methodology. No dumbing down, no flexing.
5. **Signal-only color and motion.** Cinnabar means critical, verdigris means pass, parchment means stamp. Motion exists to confirm a state change. If a color or animation doesn't carry information, it doesn't ship.

## Accessibility & Inclusion

- Target: **WCAG 2.1 AA** for the product surface. Marketing surface will target the same.
- Severity is never carried by color alone. Every severity has an icon, a label, and a color, in that order of reliability.
- Honor `prefers-reduced-motion`: state-change motion collapses to instant or to opacity-only fades.
- Body text minimum 14px at default zoom; never below 12px even for metadata.
- Dark surface is the default and the only theme for v1. A light theme is not in scope unless an admin explicitly requests it for accessibility reasons.
- Mono is reserved for record IDs, API names, and counts; never for body prose (low readability at length).
