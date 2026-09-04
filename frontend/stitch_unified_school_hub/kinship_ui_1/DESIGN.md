---
name: Kinship UI
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf4'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d4e4fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#43474e'
  inverse-surface: '#223144'
  inverse-on-surface: '#eaf1ff'
  outline: '#74777f'
  outline-variant: '#c4c6cf'
  surface-tint: '#455f88'
  primary: '#002045'
  on-primary: '#ffffff'
  primary-container: '#1a365d'
  on-primary-container: '#86a0cd'
  inverse-primary: '#adc7f7'
  secondary: '#0a6c44'
  on-secondary: '#ffffff'
  secondary-container: '#9ff5c1'
  on-secondary-container: '#167249'
  tertiary: '#3b1500'
  on-tertiary: '#ffffff'
  tertiary-container: '#5d2500'
  on-tertiary-container: '#f57d32'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#adc7f7'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#2d476f'
  secondary-fixed: '#9ff5c1'
  secondary-fixed-dim: '#83d8a6'
  on-secondary-fixed: '#002111'
  on-secondary-fixed-variant: '#005231'
  tertiary-fixed: '#ffdbca'
  tertiary-fixed-dim: '#ffb68f'
  on-tertiary-fixed: '#331100'
  on-tertiary-fixed-variant: '#773200'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d4e4fc'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
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
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  max-width: 1280px
---

## Brand & Style

The design system is built to bridge the gap between classroom and home, fostering a sense of community, clarity, and reliability. The brand personality is **nurturing, organized, and accessible**, ensuring that critical school updates are never missed while maintaining a friendly, non-intimidating atmosphere for younger students.

The visual style follows a **Modern Corporate** approach with a **Tactile** twist. This involves high-legibility layouts, a structured grid, and soft, touchable UI elements that respond to user interaction. It avoids the coldness of pure minimalism by using vibrant role-based colors and gentle, organic shapes that feel welcoming to parents and students alike.

## Colors

This design system utilizes a role-based color architecture to provide immediate visual context for users.

- **Primary (Navy - #1A365D):** Represents authority and the administrative layer. Used for Teacher dashboards, navigation headers, and primary administrative actions.
- **Secondary (Fresh Green - #2F855A):** Represents the student experience. Used for assignments, learning resources, and "Present" status indicators.
- **Tertiary (Warm Orange - #DD6B20):** Represents parental involvement. Used for guardian-specific notifications, permission slips, and urgent alerts.
- **Status Colors:**
  - **Present:** Secondary Green (#2F855A).
  - **Absent:** Crimson Red (#C53030).
  - **Late:** Goldenrod (#D69E2E).

The background uses a soft off-white (#F7FAFC) to reduce eye strain during long reading sessions, while text maintains a high-contrast Slate (#2D3748).

## Typography

The design system prioritizes legibility across all age groups by using **Inter**. The typeface's tall x-height and open apertures ensure that even dense school reports remain readable on small mobile screens.

Headlines use a tighter letter-spacing and heavier weight to provide a strong sense of hierarchy. Body text uses generous line-height to assist users with cognitive load or visual impairments. Label styles are used for metadata like "Date Posted" or "Student ID," utilizing slightly increased tracking for clarity at small sizes.

## Layout & Spacing

The design system employs a **Fluid Grid** for mobile and tablet views, transitioning to a **Fixed Grid** on desktop to maintain information density without overwhelming the user.

- **Mobile:** 4-column grid with 16px margins and 16px gutters.
- **Tablet:** 8-column grid with 24px margins and 16px gutters.
- **Desktop:** 12-column grid centered within a 1280px container.

Spacing follows a strict 4px base unit. Component internal padding should default to `md` (16px) to ensure touch targets are comfortable for both children and adults.

## Elevation & Depth

To create a trustworthy and calm environment, the design system uses **Ambient Shadows** and **Tonal Layers**. 

Depth is used purposefully to indicate interactivity:
- **Level 0 (Surface):** The main background (#F7FAFC).
- **Level 1 (Cards/Content):** Pure white background with a very soft, diffused shadow (15% opacity primary color tint, 8px blur, 2px Y-offset). This is used for message bubbles and assignment cards.
- **Level 2 (Interactive/Floating):** Used for primary action buttons or active modal windows. These have a more pronounced shadow (20% opacity primary color tint, 16px blur, 4px Y-offset).

Avoid harsh black shadows; always tint shadows with the Primary Navy color to keep the UI looking integrated and "premium."

## Shapes

The design system uses a **Rounded** shape language to appear friendly and safe. 

- **Standard Elements:** 0.5rem (8px) radius for buttons, input fields, and small cards.
- **Large Containers:** 1rem (16px) radius for modals, main content sections, and dashboard widgets.
- **Status Indicators:** Fully pill-shaped (rounded-full) to distinguish them from interactive buttons.

This consistent use of curves removes the "institutional" feel often associated with school software, making the app feel more like a modern social tool.

## Components

### Buttons
Primary buttons use the role-specific color (Navy for Teachers, Green for Students, Orange for Parents). They feature a 0.5rem radius and a soft Level 2 shadow. Secondary buttons use a ghost style with a 1px border of the role color.

### Status Indicators (Attendance)
Status indicators are pill-shaped badges with a low-opacity background and a high-contrast text color:
- **Present:** Light Green background, Dark Green text.
- **Absent:** Light Red background, Dark Red text.
- **Late:** Light Gold background, Dark Gold text.

### Input Fields
Inputs feature a subtle 1px gray border that shifts to the role-specific color on focus. They should always include a clear label and optional helper text for accessibility.

### Cards
Cards are the primary container for information. They must use the Level 1 elevation. For specific student or parent updates, a 4px left-border accent in the role color (Green or Orange) can be added to the card to provide instant visual categorization.

### Chips & Tags
Used for grade levels (e.g., "Grade 4") or subjects ("Math"). These are small, rounded-md elements with neutral backgrounds to avoid clashing with primary role colors.