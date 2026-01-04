# The Combine UI Constitution (v2.0)

## 0. Purpose

The Combine is a knowledge factory, not a content app.

Its UI exists to:

- Communicate truth about state, risk, and readiness
- Support deliberate human judgment
- Gate execution safely
- Remain trustworthy under stress

Aesthetic appeal is secondary to clarity, correctness, and durability.

---

## 1. Prime Directive

The UI must remain truthful, legible, and semantically correct under all supported system environments, including system-level dark mode.

**This is non-negotiable.**

If a UI element only works in one color scheme, it is defective.

---

## 2. Dark Mode Requirement

Dark mode is required, not optional.

This does **not** mean:

- Designing two themed UIs
- Maintaining parallel color systems

This **does** mean:

- All UI semantics survive background polarity inversion
- No meaning is conveyed solely through color
- Contrast, hierarchy, and structure remain intact in both modes

Dark mode is treated as a design integrity test, not a stylistic variant.

---

## 3. Color as Reinforcement, Never Dependency

Color may reinforce meaning, but must never be required to infer it.

Every semantic state must be understandable through:

- Iconography
- Text
- Position
- Shape
- Hierarchy

**If color is removed entirely, the UI must still function correctly.**

### Forbidden

- Color-only status indicators
- Colored background fills used for semantic sections
- Section backgrounds distinguished primarily by hue
- Decorative gradients
- Color-coded meaning without text or icon backup

### Required Pattern: Border-Left Semantic Indicator

Semantic color is applied as a **left border** on neutral surfaces, not as background fills.

```
┌─────────────────────────────┐
│▌ Section with semantic      │
│▌ meaning indicated by       │
│▌ colored left border        │
└─────────────────────────────┘
```

This provides:

- Visual scanning affordance
- Color reinforcement without dependency
- Dark mode survival (border color inverts cleanly)
- Reduced visual noise

---

## 4. Color Budget (Strict)

The Combine UI operates under a fixed color budget.

### Allowed Colors

| Role | Purpose | Application |
|------|---------|-------------|
| **Accent** | Primary actions, focus, brand identity | Buttons, links, active states |
| **Success** | Ready, complete, valid, in-scope | Status indicators, confirmations |
| **Warning** | Attention needed, constraints, stale | Alerts, open questions |
| **Error** | Blocked, failed, risks, out-of-scope | Error states, critical alerts |

### Application Rules

1. **Primary use:** Left borders on semantic sections
2. **Secondary use:** Icons and small indicators
3. **Tertiary use:** Text (sparingly, for inline status)
4. **Forbidden:** Large background fills

Any new color requires an explicit semantic justification.

**If a color cannot be named as a state, it does not belong in the UI.**

---

## 5. Neutral-First Surface Design

All layouts must be built on neutral surfaces.

### Rules

- **Backgrounds:** Neutral (white/near-white in light mode, near-black in dark mode)
- **Panels:** Separation via spacing, borders, or elevation—not color
- **Semantic sections:** Neutral background + colored left border
- **Hierarchy expressed through:**
  - Typography
  - Weight
  - Spacing
  - Grouping

Visual warmth is not a goal. Clarity is.

---

## 6. Status Communication Rules

For any status-bearing element (documents, workflows, gates):

1. Status must be **explicit**
2. Status must be **redundant** (icon + text + position)
3. Status must be **scannable** at a glance
4. Status must **not rely** on hover, tooltip, or color alone

The two-indicator system (e.g., readiness + acceptance) is the canonical pattern.

---

## 7. Accessibility Baseline

Accessibility is a design constraint, not an enhancement.

### Required

- Sufficient contrast in light and dark mode (WCAG AA minimum)
- Icon + text redundancy for all semantic indicators
- Keyboard navigability for all interactive elements
- Screen-reader-readable semantics
- Focus states visible in both color modes

**If an element requires explanation to be accessible, it is incorrectly designed.**

---

## 8. Professional Tone Standard

The Combine UI must feel:

- Calm
- Precise
- Intentional
- Serious

It must **not** feel:

- Friendly
- Playful
- Decorative
- Trend-driven

**If a design choice makes the UI feel "nice" but less clear, it is wrong.**

---

## 9. Design Review Litmus Tests

Every UI change must answer **yes** to all of the following:

1. Does this read correctly in dark mode?
2. Does this make sense without color?
3. Does this reduce or increase cognitive load?
4. Does this help the user make a safer decision?
5. Is this reinforcing truth, not aesthetics?

**A single "no" blocks the change.**

---

## 10. Closing Principle

The Combine does not persuade. It reveals.

The UI does not tell users what to do. It tells them what is safe, what is risky, and what is missing.

Everything else is noise.

---
---

# Implementation Addendum: Design Tokens

This addendum defines the concrete values for implementing the UI Constitution.

## A. Color Palette

### Semantic Colors

| Role | Light Mode | Dark Mode | Tailwind Class |
|------|------------|-----------|----------------|
| **Accent** | `#7C3AED` (violet-600) | `#8B5CF6` (violet-500) | `violet-600` / `dark:violet-500` |
| **Success** | `#059669` (emerald-600) | `#10B981` (emerald-500) | `emerald-600` / `dark:emerald-500` |
| **Warning** | `#D97706` (amber-600) | `#F59E0B` (amber-500) | `amber-600` / `dark:amber-500` |
| **Error** | `#DC2626` (red-600) | `#EF4444` (red-500) | `red-600` / `dark:red-500` |

### Neutral Palette

| Use | Light Mode | Dark Mode | Tailwind Class |
|-----|------------|-----------|----------------|
| **Page background** | `#FFFFFF` | `#111827` (gray-900) | `bg-white dark:bg-gray-900` |
| **Card/Panel background** | `#F9FAFB` (gray-50) | `#1F2937` (gray-800) | `bg-gray-50 dark:bg-gray-800` |
| **Elevated surface** | `#FFFFFF` | `#374151` (gray-700) | `bg-white dark:bg-gray-700` |
| **Border** | `#E5E7EB` (gray-200) | `#4B5563` (gray-600) | `border-gray-200 dark:border-gray-600` |
| **Border (subtle)** | `#F3F4F6` (gray-100) | `#374151` (gray-700) | `border-gray-100 dark:border-gray-700` |
| **Primary text** | `#111827` (gray-900) | `#F9FAFB` (gray-50) | `text-gray-900 dark:text-gray-50` |
| **Secondary text** | `#6B7280` (gray-500) | `#9CA3AF` (gray-400) | `text-gray-500 dark:text-gray-400` |
| **Muted text** | `#9CA3AF` (gray-400) | `#6B7280` (gray-500) | `text-gray-400 dark:text-gray-500` |

---

## B. Typography

### Font Stack

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; /* code */
```

### Type Scale

| Element | Size | Weight | Line Height | Tailwind Class |
|---------|------|--------|-------------|----------------|
| **Page title** | 2.25rem (36px) | 700 | 1.2 | `text-4xl font-bold` |
| **Section heading** | 1.25rem (20px) | 600 | 1.4 | `text-xl font-semibold` |
| **Card heading** | 1.125rem (18px) | 600 | 1.4 | `text-lg font-semibold` |
| **Body** | 0.875rem (14px) | 400 | 1.5 | `text-sm` |
| **Small/Caption** | 0.75rem (12px) | 400 | 1.4 | `text-xs` |
| **Label (uppercase)** | 0.75rem (12px) | 500 | 1.4 | `text-xs font-medium uppercase tracking-wider` |
| **Code/Mono** | 0.75rem (12px) | 400 | 1.4 | `text-xs font-mono` |

---

## C. Spacing

Base unit: `4px` (Tailwind default)

| Use | Value | Tailwind |
|-----|-------|----------|
| **Tight (inline)** | 4px | `gap-1`, `space-x-1` |
| **Default** | 8px | `gap-2`, `space-x-2`, `p-2` |
| **Comfortable** | 12px | `gap-3`, `p-3` |
| **Spacious** | 16px | `gap-4`, `p-4` |
| **Section gap** | 24px | `gap-6`, `mb-6` |
| **Page section** | 32px | `gap-8`, `mb-8` |

---

## D. Border & Radius

| Element | Border | Radius | Tailwind |
|---------|--------|--------|----------|
| **Card/Panel** | 1px | 8px | `border rounded-lg` |
| **Button** | 1px | 8px | `border rounded-lg` |
| **Input** | 1px | 6px | `border rounded-md` |
| **Badge/Tag** | 0 | 4px | `rounded` |
| **Pill** | 0 | 9999px | `rounded-full` |
| **Semantic border** | 4px left | 0 top-left, 8px others | `border-l-4 rounded-r-lg` |

---

## E. Component Patterns

### Semantic Section (Border-Left Pattern)

```html
<!-- Success/Ready -->
<div class="border-l-4 border-emerald-600 dark:border-emerald-500 bg-gray-50 dark:bg-gray-800 p-4 rounded-r-lg">
    <h4 class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
        In Scope
    </h4>
    <p class="text-sm text-gray-900 dark:text-gray-50">Content here</p>
</div>

<!-- Warning/Attention -->
<div class="border-l-4 border-amber-600 dark:border-amber-500 bg-gray-50 dark:bg-gray-800 p-4 rounded-r-lg">
    <h4 class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
        Open Questions
    </h4>
    <p class="text-sm text-gray-900 dark:text-gray-50">Content here</p>
</div>

<!-- Error/Risk -->
<div class="border-l-4 border-red-600 dark:border-red-500 bg-gray-50 dark:bg-gray-800 p-4 rounded-r-lg">
    <h4 class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
        Risks
    </h4>
    <p class="text-sm text-gray-900 dark:text-gray-50">Content here</p>
</div>

<!-- Accent/Info -->
<div class="border-l-4 border-violet-600 dark:border-violet-500 bg-gray-50 dark:bg-gray-800 p-4 rounded-r-lg">
    <h4 class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
        Architecture Notes
    </h4>
    <p class="text-sm text-gray-900 dark:text-gray-50">Content here</p>
</div>
```

### Status Indicator (Redundant)

```html
<!-- Always: icon + text -->
<div class="flex items-center gap-2 text-sm">
    <i data-lucide="check-circle" class="w-4 h-4 text-emerald-600 dark:text-emerald-500"></i>
    <span class="text-gray-900 dark:text-gray-50">Ready</span>
</div>

<div class="flex items-center gap-2 text-sm">
    <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-600 dark:text-amber-500"></i>
    <span class="text-gray-900 dark:text-gray-50">Needs Review</span>
</div>

<div class="flex items-center gap-2 text-sm">
    <i data-lucide="x-circle" class="w-4 h-4 text-red-600 dark:text-red-500"></i>
    <span class="text-gray-900 dark:text-gray-50">Blocked</span>
</div>
```

### Primary Button

```html
<button class="px-4 py-2 bg-violet-600 hover:bg-violet-700 dark:bg-violet-500 dark:hover:bg-violet-600 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900">
    Generate Document
</button>
```

### Secondary Button

```html
<button class="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-gray-50 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900">
    Cancel
</button>
```

### Card

```html
<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg p-6">
    <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">Card Title</h3>
    <p class="text-sm text-gray-500 dark:text-gray-400">Card content</p>
</div>
```

### Badge/Tag

```html
<!-- Neutral -->
<span class="px-2 py-0.5 text-xs font-mono bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
    EPIC-001
</span>

<!-- Accent -->
<span class="px-2 py-0.5 text-xs font-medium bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300 rounded">
    MVP
</span>
```

---

## F. Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class', // Enables manual dark mode toggle
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // Semantic aliases (optional, for clarity)
        accent: {
          DEFAULT: '#7C3AED', // violet-600
          dark: '#8B5CF6',    // violet-500
        },
        success: {
          DEFAULT: '#059669', // emerald-600
          dark: '#10B981',    // emerald-500
        },
        warning: {
          DEFAULT: '#D97706', // amber-600
          dark: '#F59E0B',    // amber-500
        },
        error: {
          DEFAULT: '#DC2626', // red-600
          dark: '#EF4444',    // red-500
        },
      },
    },
  },
}
```

---

## G. Dark Mode Toggle Implementation

```html
<!-- Toggle button -->
<button 
    onclick="toggleDarkMode()"
    class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
    aria-label="Toggle dark mode">
    <i data-lucide="sun" class="w-5 h-5 dark:hidden"></i>
    <i data-lucide="moon" class="w-5 h-5 hidden dark:block"></i>
</button>

<script>
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', 
        document.documentElement.classList.contains('dark') ? 'dark' : 'light'
    );
}

// Initialize on page load
if (localStorage.getItem('darkMode') === 'dark' || 
    (!localStorage.getItem('darkMode') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
}
</script>
```

---

## H. Migration Checklist

When updating existing templates:

- [ ] Replace `bg-{color}-50` backgrounds with `border-l-4 border-{color}-600 bg-gray-50 dark:bg-gray-800`
- [ ] Add `dark:` variants to all color classes
- [ ] Ensure all status indicators have icon + text
- [ ] Replace `text-gray-900` with `text-gray-900 dark:text-gray-50`
- [ ] Replace `text-gray-500` with `text-gray-500 dark:text-gray-400`
- [ ] Replace `bg-white` with `bg-white dark:bg-gray-800` (cards) or `bg-white dark:bg-gray-900` (page)
- [ ] Replace `border-gray-200` with `border-gray-200 dark:border-gray-600`
- [ ] Test in both light and dark mode
- [ ] Verify contrast ratios meet WCAG AA
