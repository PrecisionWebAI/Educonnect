---
name: Kinship UI
colors:
  surface: '#f9f9ff'
  surface-dim: '#cfdaf1'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e7eeff'
  surface-container-high: '#dee8ff'
  surface-container-highest: '#d8e3fa'
  on-surface: '#111c2c'
  on-surface-variant: '#43474e'
  inverse-surface: '#263142'
  inverse-on-surface: '#ebf1ff'
  outline: '#74777f'
  outline-variant: '#c4c6cf'
  surface-tint: '#455f88'
  primary: '#002045'
  on-primary: '#ffffff'
  primary-container: '#1a365d'
  on-primary-container: '#86a0cd'
  inverse-primary: '#adc7f7'
  secondary: '#0061a5'
  on-secondary: '#ffffff'
  secondary-container: '#66affe'
  on-secondary-container: '#004172'
  tertiary: '#321b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#4f2e00'
  on-tertiary-container: '#c6955e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#adc7f7'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#2d476f'
  secondary-fixed: '#d2e4ff'
  secondary-fixed-dim: '#9fcaff'
  on-secondary-fixed: '#001d37'
  on-secondary-fixed-variant: '#00497e'
  tertiary-fixed: '#ffddba'
  tertiary-fixed-dim: '#f2bc82'
  on-tertiary-fixed: '#2b1700'
  on-tertiary-fixed-variant: '#633f0f'
  background: '#f9f9ff'
  on-background: '#111c2c'
  surface-variant: '#d8e3fa'
  surface-muted: '#f7fafc'
  border-subtle: '#e2e8f0'
  success-green: '#2f855a'
  ai-indigo: '#5a67d8'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 64px
    fontWeight: '800'
    lineHeight: 72px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Manrope
    fontSize: 40px
    fontWeight: '800'
    lineHeight: 48px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Manrope
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  caption:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  section-gap-lg: 120px
  section-gap-md: 80px
---

## Brand & Style
The design system is engineered for **EduConnect**, an enterprise-grade AI operating system for educational institutions. The brand personality is rooted in stability, intelligence, and human connection. It must convey the reliability of traditional academia while signaling the efficiency of cutting-edge AI.

The design style follows a **Corporate / Modern** aesthetic with a strong emphasis on **Minimalism**. This approach uses expansive whitespace to reduce cognitive load for administrators and educators. The interface utilizes high-quality typography and a disciplined color application to guide users through complex data and conversion funnels. The visual narrative is one of "Sophisticated Clarity"—stripping away the unnecessary to highlight the essential tools of school management.

## Colors
The palette is dominated by **Kinship Navy (#1a365d)**, providing an authoritative and trustworthy foundation. This is supported by a secondary bright blue for action-oriented elements and a neutral spectrum of blue-greys that maintain a cool, professional temperature throughout the UI.

- **Primary:** Used for headers, hero text, and primary CTAs to establish authority.
- **Secondary:** Used for interactive elements, links, and secondary accents.
- **Neutral:** A refined range of slate and charcoal tones used for body text and structural borders.
- **AI Indigo:** A specialized accent color used sparingly to denote AI-powered features or automated insights.

## Typography
**Manrope** is the sole typeface for this design system, chosen for its modern, geometric construction and exceptional legibility. 

The scale is intentionally dramatic for marketing sections to drive high conversion. Headlines use tighter letter-spacing and heavier weights to command attention, while body text maintains a generous line height (1.5x - 1.6x) to ensure readability during long-form feature explanations. Use the `display-lg` style strictly for hero sections to create a sense of enterprise scale.

## Layout & Spacing
The design system utilizes a **12-column fixed grid** for desktop, centering content within a 1280px container. A strict 8px base unit (the "Kinship Rhythm") governs all padding and margins.

- **Desktop:** 120px vertical gaps between major marketing sections to create a premium, unhurried feel.
- **Tablet:** Transitions to an 8-column fluid grid with 64px section gaps.
- **Mobile:** 4-column fluid grid with 16px side margins.

Content should flow vertically with a strong emphasis on "The Rule of Three" for feature blocks to maintain balance and digestibility.

## Elevation & Depth
Hierarchy is established through **Tonal Layering** and **Ambient Shadows**. 

The system avoids heavy black shadows in favor of "Kinship Shadows"—soft, diffused blurs tinted with the Primary Navy color at very low opacity (5-8%). This prevents the UI from feeling "muddy" and keeps the focus on the content.

- **Level 1 (Base):** Flat white background.
- **Level 2 (Cards):** Subsurface containers with a subtle 1px border (#e2e8f0) and no shadow.
- **Level 3 (Interactive):** Floating elements (like active inputs or hovered cards) use a 16px blur radius shadow with a 4px vertical offset.
- **Level 4 (Modals):** High-depth shadows (32px blur) to isolate the component from the background.

## Shapes
The shape language is **Rounded**, strike a balance between friendly and professional. 

Standard components (buttons, inputs) utilize a **0.5rem (8px)** corner radius. Large containers and marketing cards should scale up to **1rem (16px)** to soften the overall visual footprint. This consistent radius reinforces the "Kinship" concept—smooth, integrated, and modern.

## Components
- **Buttons:** Primary buttons are solid Navy (#1a365d) with white text. Secondary buttons use a subtle blue-grey border. Buttons must have a minimum height of 48px for high-conversion accessibility.
- **Input Fields:** Use a light grey fill (#f7fafc) with a bottom-accented border that transforms to Primary Navy on focus. Labels are always positioned above the field in `label-md`.
- **Cards:** Features are housed in cards with 16px padding and 16px border-radius. Use a 1px border (#e2e8f0) instead of a shadow for resting states.
- **Chips:** Small, pill-shaped indicators for status (e.g., "New," "AI-Powered"). Use light indigo backgrounds with dark indigo text.
- **Trust Bar:** A dedicated component for scrolling or gridded logos of partner schools, presented in grayscale with 50% opacity to maintain focus on the EduConnect brand.
- **KPI Stats:** Large, bold numerical displays using `display-lg` for social proof and conversion metrics.