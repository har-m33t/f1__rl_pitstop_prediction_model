# Design System Document: Precision Velocity

## 1. Overview & Creative North Star: "The Kinetic Command"
The Creative North Star for this design system is **"The Kinetic Command."** This is not a static dashboard; it is a high-performance instrument designed for split-second decision-making. We are moving away from the "web app" aesthetic and toward a "tactical HUD" (Heads-Up Display). 

The system rejects the softness of modern consumer apps in favor of **Aggressive Precision**. By utilizing a 0px border-radius (Sharp Angularity) and high-density data layouts, we mirror the engineering of an F1 chassis. Visual interest is generated not through decoration, but through the tension between deep carbon surfaces and "light-speed" accents.

## 2. Colors: High-Contrast Telemetry
The palette is built on a foundation of extreme depth, using the `surface` tokens to simulate a carbon-fiber environment where information "glows" rather than sits on top.

*   **The Primary Engine:** `primary_container` (#e10600) is our "Racing Red." It is reserved for critical path actions and active status.
*   **The Neon Status:** `tertiary` (#00e639) functions as a digital "Green Light." Use this for positive deltas, pit-stop readiness, and "Go" signals.
*   **The "No-Line" Rule:** Do not use 1px solid borders to separate race data. Instead, use the shift from `surface_container_low` (#1b1c1d) to `surface_container` (#1f2021) to define modules. A module should feel like a machined part of the dashboard, not a box drawn on it.
*   **The Glass & Gradient Rule:** For real-time overlays (e.g., driver radio pop-ups), use a background of `surface_container_highest` (#343536) at 80% opacity with a `backdrop-blur` of 12px. Apply a subtle linear gradient from `primary` to `primary_container` at a 45-degree angle for progress bars to simulate mechanical motion.

## 3. Typography: Technical Editorial
We utilize two distinct families to balance readability with a high-tech "Mission Control" feel.

*   **Display & Headlines (Space Grotesk):** This is our "Engineering" font. Its wide stance and technical apertures provide an authoritative, editorial feel. Use `display-lg` for lap counts and `headline-md` for driver names.
*   **Body & Labels (Inter):** Inter provides the necessary legibility for dense telemetry. For data-heavy tables, utilize `label-md` and `label-sm`. 
*   **The Signature Scale:** To emphasize the "F1" feel, use `label-sm` in all-caps with a `letter-spacing` of 0.05rem for non-critical metadata (e.g., TIRE TEMPERATURE). This creates a "blueprint" aesthetic that feels intentional and premium.

## 4. Elevation & Depth: Tonal Layering
In a dashboard designed for speed, traditional shadows are too "soft." We achieve depth through atmospheric perspective.

*   **The Layering Principle:** 
    *   **Base:** `surface_dim` (#121314) - The track/background.
    *   **Level 1 (Main Modules):** `surface_container_low` (#1b1c1d).
    *   **Level 2 (Active Data Cells):** `surface_container_high` (#292a2b).
*   **Ambient Shadows:** If a module must float (e.g., a strategy modal), use a shadow color of `surface_container_lowest` (#0d0e0f) with a 40px blur at 15% opacity. This creates a "dark glow" rather than a muddy drop shadow.
*   **The "Ghost Border" Fallback:** For ultra-dense data grids where tonal shifts aren't enough, use `outline_variant` (#5e3f3a) at 15% opacity. It should be felt, not seen.

## 5. Components: Machined Precision

### Buttons
*   **Primary:** Solid `primary_container` (#e10600) with `on_primary_container` (#fff2f0) text. 0px radius. Use for "Confirm Strategy" or "Box This Lap."
*   **Secondary:** Ghost style. `outline` (#af8781) at 30% opacity with a sharp 45-degree clipped corner (achieved via CSS clip-path) to reinforce the angular theme.

### Data Chips
*   **Status Chips:** Use `tertiary_container` (#00821c) for "Optimal" and `error_container` (#93000a) for "Critical." No rounded corners; use a strict rectangle or a parallelogram shape.

### Input Fields
*   **Text Inputs:** Background `surface_container_highest`. Instead of a full border, use a 2px bottom-border of `outline_variant`. On focus, the bottom border "energizes" into `primary`.

### Cards & Telemetry Lists
*   **Rule:** Forbid divider lines.
*   **Implementation:** Separate driver rows using a `2.5` (0.5rem) spacing gap. The background of each row should alternate between `surface_container_low` and `surface_container_lowest` to create a "zebra-stripe" effect that guides the eye without clutter.

### Specialty Component: The "Apex Indicator"
*   **Purpose:** A custom vertical gauge for fuel or tire wear.
*   **Styling:** A vertical bar using `surface_container_highest` as the track, with a `primary` fill that has a neon outer glow (`box-shadow: 0 0 10px #ffb4a8`).

## 6. Do's and Don'ts

### Do:
*   **Do** use asymmetrical layouts. Place the main race feed (High Priority) in a large container and offset the secondary telemetry (Pit Strategy) to a narrower, taller sidebar.
*   **Do** use `0px` radius for everything. Sharpness equals speed.
*   **Do** use `tertiary` (#00e639) sparingly as a "system heart-beat" (e.g., a small pulsing dot next to live timing).

### Don't:
*   **Don't** use standard "Web Blue" or "Success Green." Stick strictly to the neon and racing-red tokens provided.
*   **Don't** add "padding" for the sake of white space. F1 is about efficiency; data should be dense, but organized through the spacing scale (e.g., use `1.5` for internal padding and `4` for module separation).
*   **Don't** use 100% opaque borders. They clutter the UI and break the "Machined HUD" aesthetic.