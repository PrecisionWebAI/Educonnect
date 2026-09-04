---
name: Kinship Landing System
colors:
  surface: '#faf8ff'
  surface-dim: '#d1dbec'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f2ff'
  surface-container: '#ebedff'
  surface-container-high: '#e5e7fa'
  surface-container-highest: '#e0e1f4'
  on-surface: '#181b28'
  on-surface-variant: '#43474e'
  inverse-surface: '#2d303e'
  inverse-on-surface: '#eff0ff'
  outline: '#74777f'
  outline-variant: '#c4c6cf'
  surface-tint: '#455f88'
  primary: '#002045'
  on-primary: '#ffffff'
  primary-container: '#1a365d'
  on-primary-container: '#86a0cd'
  inverse-primary: '#adc7f7'
  secondary: '#1652ce'
  on-secondary: '#ffffff'
  secondary-container: '#3c6de8'
  on-secondary-container: '#fefcff'
  tertiary: '#2b0066'
  on-tertiary: '#ffffff'
  tertiary-container: '#45009b'
  on-tertiary-container: '#b089ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#adc7f7'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#2d476f'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#eaddff'
  tertiary-fixed-dim: '#d2bbff'
  on-tertiary-fixed: '#25005a'
  on-tertiary-fixed-variant: '#5a00c6'
  background: '#faf8ff'
  on-background: '#181b28'
  surface-variant: '#e0e1f4'
  surface-blue: '#f8f9ff'
  success-emerald: '#006243'
  warning-amber: '#f59e0b'
  error-red: '#ba1a1a'
typography:
  display-xl:
    fontFamily: manrope
    fontSize: 64px
    fontWeight: '800'
    lineHeight: 72px
    letterSpacing: -0.03em
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
  headline-md:
    fontFamily: manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: jetbrainsMono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.08em
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
  base: 4px
  section-gap-lg: 120px
  section-gap-md: 80px
  container-max: 1280px
  gutter: 24px
  margin-desktop: 40px
  margin-mobile: 16px
---

## Brand & Style

The design system is engineered for the high-stakes world of educational institutional sales, where trust, clarity, and "enterprise-grade" reliability are paramount. The brand personality is **authoritative yet accessible**, positioning the product as a sophisticated partner for schools and universities. 

The design style is **Modern Corporate Minimalism**. It leverages expansive white space to create a "breathable" high-end feel, preventing the information density of educational data from becoming overwhelming. The visual language utilizes a disciplined color application and high-quality grotesque typography to convey technical precision, while subtle surface-on-surface layering provides a contemporary sense of depth and tactile quality.

## Colors

The palette is anchored by **Deep Navy (#1a365d)**, providing an institutional, executive foundation. This is contrasted against **Clean Light Blue surfaces (#f8f9ff)**, which replace traditional stark whites to reduce eye strain and add a layer of brand sophistication. 

- **Primary:** Deep Navy for navigation, primary headings, and high-level structural elements.
- **Secondary:** Action Blue for primary CTAs and interactive indicators.
- **Neutral:** A range of slate-greys for body text and metadata to maintain hierarchy.
- **Semantic Accents:** Reserved strictly for data visualization and status indicators (Emerald for success, Amber for warnings, Red for critical intervention).

## Typography

The typography system creates a clear distinction between **Display** (Marketing & Narrative) and **Data** (Functional & Informational). 

- **Manrope** is the voice of the brand, used for expressive headlines and high-level academic metrics. It should be typeset with tight letter-spacing for large displays to maintain a cohesive, "locked-in" look.
- **Inter** provides the functional backbone. Use `body-lg` for landing page section introductions and `body-md` for standard explanatory text.
- **JetBrains Mono** is used sparingly for technical metadata, labels, and "Data-First" attributes to signal precision to the user.

## Layout & Spacing

The design system employs a **12-column fixed grid** for desktop (max-width 1280px) centered in the viewport. 

- **Vertical Rhythm:** Sections are separated by generous `section-gap-lg` (120px) to reinforce the premium, "uncluttered" aesthetic. 
- **Content Density:** In data-heavy areas, the grid switches to a sub-grid of 8px increments to ensure tight alignment of widgets and metrics.
- **Mobile Reflow:** For mobile, the layout collapses to a single-column fluid grid with 16px side margins. Large display type should scale down to `headline-lg-mobile` to maintain legibility.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** supplemented by ultra-soft **Ambient Shadows**. 

- **Base Layer:** The light blue surface (`#f8f9ff`) serves as the canvas.
- **Component Layer (Cards/Tabs):** White (`#ffffff`) surfaces are used for cards, raised by a subtle shadow: `0px 4px 20px rgba(26, 54, 93, 0.04)`. Note the use of the Primary color in the shadow tint to maintain color harmony.
- **Interactive Layer (Dropdowns/Modals):** These use a higher elevation with a more pronounced shadow and a 1px `outline-variant` border to ensure clear boundaries against the content below.

## Shapes

The design system uses a **Rounded** (0.5rem) language to soften the institutional feel of the Deep Navy color palette. 

- **Standard Elements:** Buttons, input fields, and cards utilize a consistent 0.5rem (8px) radius.
- **Large Components:** Feature hero sections and benefit containers may use `rounded-xl` (1.5rem) to create a distinct, modern "frame" effect.
- **Pills:** All status tags, trend indicators, and small badges should be fully rounded (pill-shaped) to distinguish them from actionable buttons.

## Components

### Buttons & Interaction
- **Primary Button:** Solid Deep Navy background, white text, 8px rounding. Heavy 16px vertical / 32px horizontal padding.
- **Secondary Button:** Action Blue ghost style (1px border).
- **Lead Capture Form:** Inputs use a white background with a 1px `surface-dim` border. Focus states use a 2px Action Blue border with a 4px soft outer glow.

### Feature Cards & Pricing
- **Feature Cards:** White background, 16px internal padding, Manrope `headline-md` for titles. Icons should be housed in a 48px light blue circular container.
- **Pricing Tables:** The "Recommended" tier should use a 2px Deep Navy border to stand out. Feature lists within tables use custom checkmark icons in `success-emerald`.

### Benefit Tabs
- **Tab Headers:** Horizontal layout with a 2px bottom border on the active state. Active state uses Deep Navy text; inactive states use `neutral-color` at 60% opacity.

### Institutional Trust Elements
- **Logo Clouds:** Monochromatic (Primary color at 40% opacity) to maintain a professional, non-distracting look.
- **Data Snapshots:** Small, encapsulated dashboard-style widgets (e.g., a progress ring or grade scale) used as illustrative graphics alongside marketing copy.