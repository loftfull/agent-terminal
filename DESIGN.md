---
name: Agent Terminal
description: A light review workbench for project evidence and AI handoff.
colors:
  ink: "#182a32"
  muted: "#53676e"
  line: "#dce5e5"
  teal: "#176e70"
  canvas: "#f5f7f6"
  sidebar: "#edf2f0"
  surface: "#ffffff"
  action: "#203b39"
  action-hover: "#315550"
  action-soft-hover: "#e3efeb"
  nav-hover: "#e0e9e5"
  nav-active-ink: "#173f3b"
  phase-accent: "#39877b"
  empty-surface: "#f5f8f7"
typography:
  next-action:
    fontFamily: "Manrope, Segoe UI, sans-serif"
    fontSize: "clamp(19px, 2.1vw, 29px)"
    fontWeight: 620
    lineHeight: 1.45
    letterSpacing: "-.025em"
  headline:
    fontFamily: "Manrope, Segoe UI, sans-serif"
    fontSize: "26px"
    lineHeight: 1.25
    letterSpacing: "-.035em"
  section:
    fontFamily: "Manrope, Segoe UI, sans-serif"
    fontSize: "28px"
    letterSpacing: "-.03em"
  action-label:
    fontFamily: "Manrope, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 600
  context-body:
    fontFamily: "Manrope, sans-serif"
    fontSize: "12px"
    lineHeight: 1.7
rounded:
  control: "9px"
  field: "10px"
  panel: "14px"
spacing:
  compact: "4px"
  action-gap: "10px"
  field: "16px"
  panel: "20px"
  section: "28px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.surface}"
    typography: "{typography.action-label}"
    rounded: "{rounded.control}"
    padding: "10px 13px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  image-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "20px"
  context-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.context-body}"
    rounded: "{rounded.field}"
    padding: "16px"
---

# Design System: Agent Terminal

## Overview

The implemented direction is a light review workbench: restrained green-gray surfaces, dark green actions, compact Russian labels, and generous space around the next useful action. Premium quality is expressed through hierarchy and legibility. This description records the user-requested redesign; it does not introduce a separately approved brand metaphor.

Source basis: `PRODUCT.md`, `web/hub.css`, `web/hub_ui.js`, and `web/hub_model.js`. This is a source-only snapshot, not screenshot review or visual acceptance. Browser verification was blocked; source review found and corrected four defects. No fresh verified interface screenshot is available.

Key characteristics:
- Next action before statistics.
- Saved evidence remains distinct from live activity and acceptance.
- Russian navigation and task-scoped handoff.

## Colors

A cool neutral canvas and pale green sidebar establish the work surface. White highlights selected navigation and evidence panels. Dark green identifies the primary next action; teal supports interaction accents. Ink, muted text, and thin line colors carry hierarchy without a saturated dashboard palette. Frontmatter values are extracted from the hub stylesheet; they are not a complete inventory of inherited application styles.

## Typography

Manrope is the local font, with Segoe UI and sans-serif fallbacks. The stylesheet declares a variable 200–800 face and `font-display: swap`; its data-URI font slot is populated by the application build. Numerals use tabular figures.

The next-action sentence is the principal display text, limited to 58ch. Page headings use 26px text; context and connector-directory headings use 28px. Panel headings use 17px. Actions and context text use 12px; stage metadata uses 10px with 1.5 line-height. Balanced wrapping applies to headings. Do not invent a global body size from these local component rules.

## Layout

Desktop uses a 224px sticky, viewport-height sidebar and a flexible main column. The main region has a 1520px maximum width and `28px clamp(22px,3vw,48px)` padding. Six primary routes are Панорама, План, Исполнители, Версии, Контекст, and Подключения. Secondary destinations remain available in the additional-sections disclosure.

The overview runs from next action to five project phases, then a saved-version image panel and attention list in a 1.7:1 grid with a minimum 230px secondary column and 28px gap. Context content is limited to 960px.

At 1050px and below, the sidebar becomes 190px, the main padding becomes 24px, and the overview becomes one column. At 700px and below, navigation becomes a horizontal scrolling row above the content; the sidebar loses sticky positioning, project details are hidden, secondary links use two columns, and main padding becomes 22px 17px. Phase navigation also scrolls horizontally with minimum 105px items. The next-action size becomes 23px at the first breakpoint and 21px with 1.5 line-height on mobile.

## Elevation & Depth

The hub is primarily flat: tonal separation and thin borders establish depth. White evidence panels sit against the subdued canvas. The studio orb explicitly has no shadow. These hub overrides do not establish a new global shadow scale for all inherited screens.

The next-action reveal lasts .65s. Phase underlines transition over .4s; received-data activity pulses over 1.6s. These indicate interface activity, not project readiness. The pause control pauses animation and disables phase transitions. `prefers-reduced-motion: reduce` removes the reveal and phase animation/transition; it does not remove every color transition in the application.

## Shapes

Controls and active navigation use 9px corners, context textareas use 10px, and evidence/studio panels use 14px. Phase cells and attention rows use flat edges and dividing lines. Outline icons are normally 21px with 1.7 stroke width; mobile navigation reduces them to 17px. Empty evidence uses a larger 42px icon.

## Components

- **Next action:** one prominent sentence sourced from focus or handoff, an explicit no-step fallback, review/blocker status, and primary “Продолжить с AI” plus task navigation. Primary actions are dark green with white text, 42px minimum height and 10px 13px padding.
- **Navigation:** the selected route uses white, dark green text, weight 750, and `aria-current=page`. Hover uses a pale green fill. Six primary destinations remain compact; secondary destinations are disclosed.
- **Phase navigation:** Замысел, План, Реализация, Проверка, Версия each route to relevant records. Numbered stages and counts describe recorded evidence, not percentage completion. A 3px underline responds to hover and keyboard focus.
- **Saved-version evidence:** a real checkpoint image uses `object-fit: contain`, full available width and a 350px maximum height. Its caption separates checked file evidence from the reported build association. Without a screenshot, show the instructional empty state and materials action; never substitute an illustration as proof.
- **Attention list:** review, blocked and contradiction counts link to relevant destinations. An explanation disclosure describes evidence and correction semantics.
- **Scoped context:** a labeled task selector updates a read-only textarea, character count comparison and explicit omissions. Copy has status feedback and manual-selection fallback. Full archive download remains separate. Character reduction is not a measured token or money saving. Amendment proposals are requested, unapplied downloads; they do not silently rewrite history.
- **Connections:** icon, description, explicit connection state and action form divided rows. External tools marked unconnected are not presented as working integrations.
- **Disabled actions:** opacity .5 and a not-allowed cursor. Preserve the application's inherited focus affordances; hub phase links add their own focus underline.

## Do's and Don'ts

- Do place a useful next action above counts.
- Do preserve readable mobile horizontal navigation and visible evidence labels.
- Do distinguish requested, reported, observed and verified information.
- Do keep omissions and full-archive access visible in scoped context.
- Do retain reduced-motion and manual animation-pause behavior.
- Don't equate phase record counts with readiness or acceptance.
- Don't describe an unverified screenshot/build association as verified visual acceptance.
- Don't present disconnected external tools as integrated or characterize this source-only review as browser validation.
