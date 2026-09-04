---
name: Kinship UI
colors:
  surface: '#f8f9ff'
  surface-dim: '#d1dbec'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eef4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dfe9fa'
  surface-container-highest: '#d9e3f4'
  on-surface: '#121c28'
  on-surface-variant: '#434655'
  inverse-surface: '#27313e'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#712ae2'
  on-secondary: '#ffffff'
  secondary-container: '#8a4cfc'
  on-secondary-container: '#fffbff'
  tertiary: '#006243'
  on-tertiary: '#ffffff'
  tertiary-container: '#007d57'
  on-tertiary-container: '#bdffdc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d2bbff'
  on-secondary-fixed: '#25005a'
  on-secondary-fixed-variant: '#5a00c6'
  tertiary-fixed: '#85f8c4'
  tertiary-fixed-dim: '#68dba9'
  on-tertiary-fixed: '#002114'
  on-tertiary-fixed-variant: '#005137'
  background: '#f8f9ff'
  on-background: '#121c28'
  surface-variant: '#d9e3f4'
typography:
  display-lg:
    fontFamily: manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  body-md:
    fontFamily: inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-caps:
    fontFamily: jetbrainsMono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  grade-display:
    fontFamily: manrope
    fontSize: 24px
    fontWeight: '800'
    lineHeight: 24px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  viz-gap: 8px
---

## Brand & Style
The design system is built for the educational sector, focusing on the relationship between educators, students, and data. The brand personality is **nurturing yet analytical**, aiming to evoke a sense of clarity, encouragement, and professional reliability. 

The aesthetic follows a **Modern Corporate** style with **Minimalist** influences. It prioritizes high readability and functional elegance, ensuring that complex academic data feels approachable. The UI uses generous whitespace and a systematic approach to density to prevent cognitive overload during data-heavy workflows.

## Colors
This design system employs a refined palette designed for multi-modal use. The **Primary** (Blue) signifies action and trust, while the **Tertiary** (Emerald) is used for success and positive academic outcomes.

### Specialized Data Palette
For educational visualization, a semantic scale is used for grades:
- **Success (A/B):** Cool tones (Emerald/Blue) to signal mastery.
- **Warning (C):** Amber to signal a need for attention.
- **Critical (D/F):** Warm reds to signal urgent intervention.

In **Dark Mode**, background surfaces shift to deep charcoal (#111827) while primary accents maintain a higher luminance to ensure AA accessibility standards are met for text-on-background contrast.

## Typography
Typography is structured to balance modern aesthetics with technical precision. 
- **Manrope** is used for headlines and academic metrics (like Grade letters) to provide a friendly, rounded, yet professional appearance.
- **Inter** handles all body copy and administrative data for maximum legibility.
- **JetBrains Mono** is reserved for metadata, trend percentages, and small labels to provide a technical "data-first" feel.

All grade displays (A-F) should use `grade-display` to ensure the letter grade is the focal point of the student profile or card.

## Layout & Spacing
The design system utilizes a **12-column fluid grid** for desktop and a **4-column fluid grid** for mobile. A strict 4px baseline shift is applied to all elements to ensure vertical rhythm.

### Visualization Layouts
- **Bar Charts:** Use `viz-gap` (8px) between individual bars in a class average chart.
- **Progress Rings:** Center-aligned within container modules with a minimum padding of 16px from container edges.
- **Dashboards:** Use a "Card-First" layout where each metric is encapsulated in a surface with 24px internal padding.

## Elevation & Depth
Depth is communicated through **Tonal Layers** and subtle **Ambient Shadows**.

1.  **Level 0 (Background):** The base canvas color.
2.  **Level 1 (Cards/Modules):** Raised using a very soft, diffused shadow (0px 4px 20px rgba(0,0,0,0.05)) to separate data widgets from the background.
3.  **Level 2 (Overlays/Modals):** Increased shadow spread and a 1px low-contrast border to define boundaries.

In Dark Mode, elevation is depicted by increasing the lightness of the surface color (Surface-Container tiering) rather than increasing shadow opacity.

## Shapes
A **Rounded** (0.5rem) strategy is applied to provide a welcoming, modern feel.
- **Cards & Inputs:** 0.5rem (8px).
- **Progress Ring Tracks:** Use "Round" stroke caps for the progress indicator.
- **Bar Charts:** Apply 4px top-corner rounding to vertical bars to soften the data visualization.
- **Trend Indicators:** Encapsulated in a pill-shaped (1rem) container.

## Components

### Educational Data Visualization
- **Grade Scales:** Rendered as a bold letter (Manrope 800) inside a colored circle or as a text-label with the corresponding semantic color (e.g., Grade A in Emerald).
- **Progress Rings:** Use a thickness of 8px for the stroke. The track should be 10% opacity of the primary color, while the progress indicator uses the full color weight.
- **Bar Charts:** For class averages, the "User's Class" bar should use the Primary color, while comparison bars use a neutral grey.
- **Trend Indicators:** 
    - **Up:** Primary/Emerald icon with a "+" prefix.
    - **Down:** Red icon with a "-" prefix.
    - **Stable:** Neutral grey horizontal line or tilde.
- **Input Fields:** Use a 1px border. On focus, the border thickens to 2px using the Primary color with a subtle outer glow.
- **Buttons:** All primary buttons are fully filled with 0.5rem rounding. Secondary buttons use the "Ghost" style with a 1px border.