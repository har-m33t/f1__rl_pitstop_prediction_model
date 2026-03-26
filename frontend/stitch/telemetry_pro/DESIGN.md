# Design System Strategy: Technical Precision & High-Performance Analytics

## 1. Overview & Creative North Star: "The Kinetic Monolith"
The Creative North Star for this design system is **The Kinetic Monolith**. This is not a standard dashboard; it is a high-pressure mission control interface. It rejects the "softness" of modern consumer web design in favor of aggressive, structural brutalism. 

To achieve an "Editorial Technical" look, we move beyond the template by using **Zero-Radius Hard Edges** and **Intentional Asymmetry**. Layouts should feel like a custom-machined carbon fiber chassis—rigid, precise, and devoid of excess. We break the grid by overlapping technical readouts over 3D surface plots, using high-contrast typography scales to create a sense of urgent authority.

---

## 2. Colors: Tonal Depth & The "No-Line" Rule
The palette is rooted in `#111111` (Carbon Black) and `#E8002D` (F1 Red). The goal is to create depth without traditional borders.

*   **Primary Accent (`primary_container`):** `#E8002D` (F1 Red). Reserved for critical alerts, "Live" race status, and primary action triggers.
*   **Secondary Accent (`secondary`):** `#C6C6C7` (Silver/White). Used for secondary data streams and structural metadata.
*   **The "No-Line" Rule:** 1px solid borders are strictly prohibited for sectioning. Separation of concerns must be achieved through background shifts. For example, a `surface_container_low` panel sits on a `surface` background. The eye should perceive the change in depth through color value, not a line.
*   **Surface Hierarchy & Nesting:** Use the `surface_container` tiers to create a "stepped" cockpit feel:
    *   **Level 0 (Base):** `surface` (#131313) for the main application canvas.
    *   **Level 1 (Modules):** `surface_container_low` (#1C1B1B) for the main telemetry modules.
    *   **Level 2 (Active Data):** `surface_container_high` (#2A2A2A) for focused or hovered data cells.
*   **Signature Textures:** Apply a 2% opacity "Carbon Weave" pattern or subtle noise texture to the `surface` layer to eliminate flat "digital" black and provide a premium, material feel.

---

## 3. Typography: The Engineering Dichotomy
We utilize two distinct typefaces to separate "Interface Instruction" from "Real-Time Data."

*   **UI Labels (Inter):** Used for navigation, button labels, and instructional text. It is clean and readable, providing a neutral backdrop to the data.
*   **Numeric Data (JetBrains Mono):** All lap times, tire degradation percentages, and coordinates must use this monospaced font. It conveys a "terminal" aesthetic and ensures that numbers align perfectly in dense grids, allowing for instant vertical scanning of multi-car comparisons.
*   **Scale Dynamics:** Use `display-lg` (Space Grotesk - 3.5rem) for the "Current Lap" or "Position" to create a massive visual anchor, contrasting sharply with `label-sm` (Inter - 0.6875rem) for technical metadata.

---

## 4. Elevation & Depth: Tonal Layering
In a high-performance environment, shadows are distracting. We achieve hierarchy through **Tonal Stacking**.

*   **The Layering Principle:** Stack `surface_container_lowest` for background gutters and `surface_container_highest` for active analytical overlays. This creates a "machined" look where components appear to be milled out of a single block of carbon fiber.
*   **The "Ghost Border" Fallback:** If high-density data grids require separation, use the `outline_variant` token at **15% opacity**. This creates a "light-leak" effect on the edge rather than a hard stroke.
*   **Glassmorphism for Overlays:** Floating pit-stop predictors or strategy pop-overs should use a semi-transparent `surface_container_highest` with a `backdrop-blur` of 20px. This allows the race trajectory or 3D surface plot to remain visible beneath the UI, maintaining situational awareness.

---

## 5. Components: Precision Primitives

*   **Zero-Radius Buttons:**
    *   **Primary:** Background `#E8002D`, Text White, 0px radius. On hover, shift to `on_primary_container`.
    *   **Tertiary:** No background. 1px "Ghost Border" (15% opacity White). Use for non-critical telemetry toggles.
*   **Data Grids (The Grid System):**
    *   Forbid horizontal/vertical divider lines. Use `1.3rem` (Spacing 6) gutters. 
    *   Highlight the "Active Driver" row using a 2px left-border of `primary` (#E8002D) instead of a full row highlight.
*   **Technical Timelines:** 
    *   The "Time" axis must use `surface_container_highest`. 
    *   Events (Pit stops, Yellow Flags) are marked with sharp-edged vertical blocks of `primary`, never icons.
*   **Input Fields:**
    *   Underline-only style using `outline_variant`. On focus, the underline transitions to `primary` (#E8002D). 
    *   All helper text must be JetBrains Mono to match the technical nature of the inputs.
*   **Status Chips:** 
    *   Rectangular, no radius. Use `primary_fixed_dim` for "DRS Active" and `secondary_container` for "Staged."

---

## 6. Do’s and Don’ts

### Do:
*   **Do** lean into extreme density. In F1 analytics, more data is better than "clean" whitespace if it is organized via the Typography Scale.
*   **Do** use asymmetric layouts. A large 3D surface plot on the left can be balanced by a very dense, narrow telemetry strip on the right.
*   **Do** ensure all monospaced numbers are tabular-aligned so decimals line up vertically.

### Don’t:
*   **Don’t** use a single pixel of border-radius. Even a 2px radius destroys the "Technical Precision" aesthetic.
*   **Don’t** use standard "Drop Shadows." They feel too organic/soft. If a panel needs to pop, use a higher `surface_container` value.
*   **Don’t** use traditional icons (like a trash can or gear). Use text labels (e.g., "DEL" or "CFG") in JetBrains Mono to maintain the "Engineer's Console" feel.