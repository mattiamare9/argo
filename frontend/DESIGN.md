---
name: Argo
description: Light-only access dashboard where every access is a key on a porter's board, drawn in a lilac line.
colors:
  primary: "#6e52a3"
  primary-foreground: "#ffffff"
  line: "#6e52a3"
  line-soft: "#ece7f5"
  secondary: "#ece7f5"
  secondary-foreground: "#4a3678"
  background: "#f6f5f9"
  card: "#fdfcff"
  foreground: "#1d1b26"
  muted: "#eeebf3"
  muted-foreground: "#5f5a70"
  border: "#e3dfec"
  input: "#d8d2e5"
  pending: "#c98a12"
  pending-foreground: "#7a5106"
  pending-soft: "#fbf1dc"
  destructive: "#b8382c"
typography:
  display:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.03em"
  display-mobile:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
    lineHeight: 1.111
    letterSpacing: "-0.03em"
  lead:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.556
  title:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.43
  wordmark:
    fontFamily: "Hanken Grotesk Variable, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.556
    letterSpacing: "-0.025em"
rounded:
  md: "0.4rem"
  lg: "0.5rem"
  xl: "0.7rem"
  full: "9999px"
spacing:
  gutter-mobile: "16px"
  gutter-desktop: "48px"
  stack-sm: "12px"
  stack-md: "24px"
  board-pad-mobile: "24px"
  board-pad-desktop: "32px"
  sidebar-width: "232px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.lg}"
    padding: "0 10px"
    height: "32px"
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.secondary-foreground}"
    rounded: "{rounded.lg}"
    padding: "0 10px"
    height: "32px"
  nav-item:
    textColor: "{colors.muted-foreground}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  nav-item-hover:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.foreground}"
  nav-item-active:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.secondary-foreground}"
  board:
    backgroundColor: "{colors.muted}"
    rounded: "{rounded.xl}"
    padding: "32px"
  brand-tile:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.md}"
    size: "28px"
  key-swatch:
    backgroundColor: "{colors.line}"
    width: "12px"
    height: "20px"
---

# Design System: Argo

## Overview

**Creative North Star: "The Porter's Key Board, drawn in Linea Argo"**

Argo reads like the key board in a building's porter lodge, redrawn as a transit line. Every access is a key: hung on its hook means active, an empty hook means returned, an amber key means a return that has not completed. Above the board, the services run as a thin lilac line with stations; while every station answers, the line runs whole. The structure comes from the key board, the palette from the line.

The world is quiet on purpose. One typeface, one hue family, flat panels on a lilac-tinted paper. Nothing is neutral gray: every neutral carries a trace of the line's lilac. Colour that is not lilac means something, and only two things: amber for a key that has not come back, red for a service that has failed. When everything works, the page is one large sentence and a calm board. The system is light theme only, by decision: the dashboard is used in the office or on a phone during the day.

Density is low and the hierarchy is carried by scale, not ornament. A single status sentence at manifesto size owns each screen; everything else steps down to body and label sizes in the same face. Phone and desktop are equal: the sidebar collapses into a top bar, the board stacks into one column.

**Planned, not shipped (Phase 2, pending real employee data):** the populated key board with an employee name plate per person and one labelled key per application; the full-screen mass-deactivation confirmation on phone; and the signature motion, where keys detach from their hooks one at a time as revocations confirm and the one that fails stays amber. Until then the board ships as an honest empty state with its legend. Do not fake these with placeholder data.

**Key Characteristics:**
- Tinted neutrals only; lilac line hue in every gray.
- One face (Hanken Grotesk), hierarchy by size and weight.
- Status sentence at display scale; one per screen.
- Key metaphor: hung, empty hook, amber.
- Services as a line with stations that breaks when a station fails.
- Flat panels; the board is the only recessed surface.
- Light theme only.

## Colors

A single lilac hue family over lilac-tinted paper, with amber and red held back as signals.

### Primary
- **Linea Lilac** (`primary`, `line`): the brand and the line. The brand tile, the active key, the unbroken service line, operational station rings, focus rings, text selection, caret, and native form accents. `line` is the same value as `primary` and is used where the meaning is "the line" (service line, hung key) rather than "the action".
- **Paper White on Lilac** (`primary-foreground`): text and letters set on Linea Lilac.

### Secondary
- **Lilac Wash** (`secondary`, `line-soft`): the active navigation item and secondary buttons. A selection tint, never a page fill.
- **Deep Lilac Ink** (`secondary-foreground`): text on Lilac Wash; the active nav label.

### Tertiary (signals)
- **Pending Amber** (`pending`): the outline of a key whose return has not completed. Reserved for "in attesa / non riconsegnata".
- **Amber Ink** (`pending-foreground`): amber-family text; the amber fill is not legible as text, so text uses this darker step.
- **Amber Wash** (`pending-soft`): the fill inside a pending key.
- **Fault Red** (`destructive`): a station that does not answer (its ring and its status word) and destructive actions. Reserved for faults.

### Neutral
- **Lilac Paper** (`background`): the page.
- **Panel White** (`card`): the sidebar/top bar and the service-line band; panels sit one step lighter than the page.
- **Line Ink** (`foreground`): all primary text; a near-black with a violet cast.
- **Board Well** (`muted`): the key board surface, skeletons, nav hover.
- **Quiet Ink** (`muted-foreground`): secondary text, station details, the lead sentence under the status headline, inactive nav items, the dashed outline of an empty hook.
- **Hairline** (`border`): the default 1px divider between bar, band and page.
- **Rule Lilac** (`input`): a stronger rule: the divider inside the board, the broken segment of the service line, an unverifiable station's ring, scrollbar thumb, input borders.

### Named Rules
**The Tinted Neutral Rule.** There is no neutral gray in Argo. Every background, border and secondary text carries the line's lilac hue (around 295-303 degrees in OKLCH). A new gray is a new token in this family, never `#888` or a Tailwind `gray-*`.

**The Reserved Signal Rule.** Amber means only "a key that has not come back"; red means only "a service or action at fault". Neither is ever a page or panel background, and neither appears when everything works.

**The State Does Not Repaint Rule.** A fault changes the element that failed (a station ring, a line segment, a key), not the page. The headline changes words, not colour.

## Typography

**Display Font:** Hanken Grotesk Variable (with sans-serif)
**Body Font:** Hanken Grotesk Variable (with sans-serif)

**Character:** A single humanist grotesk carries everything from the manifesto-scale status sentence to the station labels. It is plain enough to read as serious about access decisions and warm enough to avoid the technical-console look.

### Hierarchy
- **Display** (700, 3.75rem desktop / 2.25rem mobile, line-height 1 / 1.11, tracking -0.03em, balanced wrap): the status sentence ("Tutto in ordine", "L'archivio non risponde"). One per screen; it owns the page.
- **Lead** (400, 1.125rem desktop / 1rem mobile, Quiet Ink, max 60ch): the sentence under the display line: what to do, or when it was last checked.
- **Title** (600, 1rem): section names ("Quadro accessi") and empty-state headings.
- **Body** (400, 1rem, line-height 1.5, max 60ch): explanatory text.
- **Label** (600 for names, 400 for details, 0.875rem): station names, legend entries, navigation. Station details step down to 13px in Quiet Ink.
- **Wordmark** (700, 1.125rem, tracking -0.025em): "Argo" beside its lettered tile.

Times, tables and data use tabular figures globally.

### Named Rules
**The One Face Rule.** Hanken Grotesk is the only typeface. Hierarchy comes from size, weight (400/600/700) and tight negative tracking at display size, never from a second family.

**The Sentence First Rule.** Display size is reserved for one sentence per screen that states its condition in words. No eyebrow or kicker label above it.

## Layout

A two-zone shell: a 232px panel-white sidebar on the left from 768px up; below that, the same content becomes a top bar (wordmark left, navigation right) with a hairline bottom border. Main content fills the rest with no max-width container.

Content runs in full-width horizontal bands with page gutters of 16px on phone and 48px on desktop:
1. The service-line band (Panel White, hairline below), 20px top padding.
2. The status band: display headline and lead, 32px top on phone / 56px on desktop, 12px between headline and lead.
3. The board band: section title, then the board well, 48px bottom.

Text measures are capped at 60ch. The legend runs as a row on desktop (32px gaps) and stacks to one column on phone (12px gaps). The single breakpoint in use is 768px.

## Elevation & Depth

Argo is flat. Panels separate from the page by a one-step tonal lift (Panel White over Lilac Paper) and 1px hairlines, never by drop shadows. The only depth in the system is inward: the key board is a recessed well, a soft lilac-tinted inner shadow that reads as the board set into the wall.

### Shadow Vocabulary
- **Board recess** (`box-shadow: inset 0 2px 6px rgb(74 54 120 / 0.08)`): the key board well only.

### Named Rules
**The Recessed Board Rule.** Nothing in Argo floats. The board sinks; panels lift only by tone. Do not add outer shadows to cards, bars or buttons.

## Shapes

Gently softened rectangles throughout: 0.4rem (`md`) for nav items, the brand tile and skeletons; 0.5rem (`lg`) for buttons; 0.7rem (`xl`) for the board well. Stations are full circles with a thick 5px ring on a Panel White core. The key is the one bespoke silhouette: a 12x20px shape with a fully rounded top and 3px bottom corners, a key tag hanging from a hook. Dashed strokes mean absence (empty hook, broken line); solid strokes and fills mean presence.

## Components

### Buttons
Restrained shadcn base-nova buttons; not yet used on a shipped surface.
- **Shape:** gently rounded (0.5rem), 1px transparent border, 32px tall by default (24/28/36px for xs/sm/lg), 14px medium label.
- **Primary:** Linea Lilac fill, white text; hover drops the fill to 80%.
- **Secondary:** Lilac Wash fill, Deep Lilac Ink text; hover mixes 5% ink into the wash.
- **Outline / Ghost:** page-coloured or transparent; hover to Board Well with Line Ink text.
- **Destructive:** Fault Red at 10% fill with red text, 20% on hover. Never solid red.
- **Focus / Active:** ring border plus a 3px ring at 50% Linea Lilac; pressed state nudges down 1px. Disabled at 50% opacity.

### Navigation
- **Style:** 14px label with a 16px Lucide icon, 8px 12px padding, 0.4rem corners.
- **Default:** Quiet Ink, transparent. **Hover:** Board Well fill, Line Ink text. **Active:** Lilac Wash fill, Deep Lilac Ink, 600 weight.
- **Mobile:** the items move into the top bar, in a horizontal row beside the wordmark.
- Items are added only when their feature exists.

### Brand Mark
A 28px Linea Lilac tile with a white "A" in the wordmark face, beside "Argo" in bold. The app name is the only brand.

### Service Line (signature)
A horizontal ordered line of stations across the top band. Each station is an 18px circle with a 5px ring: Linea Lilac when operational, Fault Red when it does not answer, Rule Lilac when it cannot be checked. Below each sits its name (label, 600) and a status word (13px, Quiet Ink; Fault Red and 500 weight when down). The segment between two operational stations is a solid 4px Linea Lilac bar; any other segment becomes a dashed Rule Lilac bar (8px dash, 6px gap). End labels align to their edges, middle labels centre. Only real services appear as stations.

The direction contract called for the break to show in amber; the build uses red for the failed station and a dashed lilac-gray gap for the break, keeping amber exclusive to keys.

### Key Board
- **Corner Style:** 0.7rem.
- **Background:** Board Well with the board recess.
- **Border:** none outside; an internal Rule Lilac divider above the legend.
- **Internal Padding:** 24px phone / 32px desktop, 24px between blocks.
- **Shipped state:** empty state (title plus 60ch body) and a fixed legend. Name plates and per-app keys are planned for Phase 2.

### Key (KeySwatch)
- **Hung (active):** solid Linea Lilac.
- **Returned (empty hook):** 2px dashed Quiet Ink outline, no fill.
- **Pending (not returned):** 2px Pending Amber outline over Amber Wash.
- Every key is decorative (`aria-hidden`) and always paired with a text label; state never relies on colour alone.

### Skeleton
Board Well fill, 0.4rem corners, pulsing, sized to the content it replaces (the service line, the headline).

## Do's and Don'ts

### Do:
- **Do** tint every new neutral with the line's lilac hue; extend the existing tokens rather than reaching for gray.
- **Do** state the screen's condition in one display-scale sentence (700, -0.03em tracking) before anything else.
- **Do** pair every state colour with a shape difference (solid, dashed, outlined) and a word.
- **Do** keep panels flat and separated by tone and 1px hairlines; reserve the inset recess for the key board.
- **Do** use the key vocabulary (hung, empty hook, amber) for access state, and the line-with-stations for service health.
- **Do** design every flow for phone and desktop equally; stack to one column below 768px.

### Don't:
- **Don't** use amber or red when everything works, and never as a page or panel background.
- **Don't** use amber for service faults; amber belongs to keys that have not come back.
- **Don't** introduce a second typeface or a gray from the default Tailwind palette.
- **Don't** add drop shadows to cards, bars or buttons.
- **Don't** add a dark theme or rely on `dark:` variants; Argo is light theme only.
- **Don't** fill the board with invented employees, numbers or names before real data exists.
