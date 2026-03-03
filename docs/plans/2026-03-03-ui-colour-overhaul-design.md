# UI Colour Overhaul Design

**Date:** 2026-03-03
**Scope:** Full UI overhaul — token palette expansion, dark/light mode consistency, component styling

---

## Problem

The codebase has a semantic CSS token system in `tailwind.src.css` but templates bypass it with ~700+ hardcoded raw Tailwind colour classes (`gray-300`, `gray-700`, `bg-white`, `dark:bg-gray-700`, etc.). This produces:

- Inconsistent dark mode (different shades of gray patched together per-component)
- Broken light mode (some components hardcode dark colours, others use tokens)
- Unmaintainable colour decisions spread across 19 template files and JS

---

## Approach: Token-First Migration (Option A)

Expand the semantic token vocabulary in `tailwind.src.css`, register new tokens in `tailwind.config.js`, then do a systematic substitution pass across every template and JS file replacing raw colour classes with token-based equivalents.

All colour decisions live in `tailwind.src.css`. Changing the theme requires editing one file.

---

## Section 1: Token Palette

### Light Mode

| Token | Value | Purpose |
|---|---|---|
| `--color-primary-rgb` | `13 148 136` | teal-600 |
| `--color-primary-hover-rgb` | `15 118 110` | teal-700 |
| `--color-bg-base` | `#f1f5f9` | slate-100 page background |
| `--color-bg-panel` | `#ffffff` | card/panel surface |
| `--color-bg-table-head` | `#f8fafc` | table header row |
| `--color-bg-elevated` | `#ffffff` | nav, dropdowns, footer |
| `--color-bg-hover` | `#f1f5f9` | row/item hover state |
| `--color-border` | `#cbd5e1` | slate-300 |
| `--color-text-base` | `#0f172a` | slate-900 |
| `--color-text-muted` | `#64748b` | slate-500 |
| `--color-text-heading` | `#0f172a` | slate-900 |
| `--color-input-bg` | `#ffffff` | form input background |
| `--color-input-border` | `#cbd5e1` | form input border |
| `--color-nav-bg` | `#ffffff` | nav background |
| `--color-btn-secondary-bg` | `#e2e8f0` | slate-200 |
| `--color-btn-secondary-text` | `#334155` | slate-700 |
| `--color-btn-secondary-hover` | `#cbd5e1` | slate-300 |
| `--color-success` | `#16a34a` | green-600 |
| `--color-error` | `#dc2626` | red-600 |
| `--color-warning` | `#d97706` | amber-600 |
| `--color-badge-movie` | `#0369a1` | sky-700 (Radarr) |
| `--color-badge-tv` | `#0d9488` | teal-600 (Sonarr) |

### Dark Mode

| Token | Value | Purpose |
|---|---|---|
| `--color-primary-rgb` | `45 212 191` | teal-400 |
| `--color-primary-hover-rgb` | `38 191 170` | teal-500 |
| `--color-bg-base` | `#0f1117` | near-black page background |
| `--color-bg-panel` | `#1a1d27` | dark navy panel |
| `--color-bg-table-head` | `#141720` | slightly deeper than panel |
| `--color-bg-elevated` | `#1a1d27` | nav, dropdowns, footer |
| `--color-bg-hover` | `#22263a` | row/item hover state |
| `--color-border` | `#2a2d3a` | subtle border |
| `--color-text-base` | `#e2e8f0` | slate-200 |
| `--color-text-muted` | `#94a3b8` | slate-400 |
| `--color-text-heading` | `#f1f5f9` | slate-100 |
| `--color-input-bg` | `#0f1117` | form input background |
| `--color-input-border` | `#2a2d3a` | form input border |
| `--color-nav-bg` | `#0f1117` | nav background |
| `--color-btn-secondary-bg` | `#22263a` | |
| `--color-btn-secondary-text` | `#94a3b8` | slate-400 |
| `--color-btn-secondary-hover` | `#2a2d3a` | |
| `--color-success` | `#22c55e` | green-500 |
| `--color-error` | `#ef4444` | red-500 |
| `--color-warning` | `#f59e0b` | amber-500 |
| `--color-badge-movie` | `#38bdf8` | sky-400 (Radarr) |
| `--color-badge-tv` | `#2dd4bf` | teal-400 (Sonarr) |

### New `tailwind.config.js` entries (7 additions)

```js
"bg-elevated":         "var(--color-bg-elevated)",
"bg-hover":            "var(--color-bg-hover)",
"btn-secondary-bg":    "var(--color-btn-secondary-bg)",
"btn-secondary-text":  "var(--color-btn-secondary-text)",
"btn-secondary-hover": "var(--color-btn-secondary-hover)",
"badge-movie":         "var(--color-badge-movie)",
"badge-tv":            "var(--color-badge-tv)",
```

---

## Section 2: Template Migration Mapping

### Universal substitutions (all templates + JS files)

| Remove | Replace with |
|---|---|
| `bg-white` | `bg-bg-elevated` |
| `bg-gray-50` | `bg-bg-base` |
| `bg-gray-100` | `bg-bg-hover` |
| `bg-gray-700` / `bg-gray-800` | `bg-bg-elevated` |
| `text-gray-900` / `dark:text-gray-100` | `text-text-heading` |
| `text-gray-700` / `dark:text-gray-200` | `text-text-base` |
| `text-gray-600` / `dark:text-gray-300` | `text-text-muted` |
| `text-gray-500` / `dark:text-gray-400` | `text-text-muted` |
| `text-gray-400` | `text-text-muted` |
| `border-gray-200` / `dark:border-border-subtle` | `border-border-subtle` |
| `border-gray-300` / `dark:border-input-border` | `border-input-border` |
| `divide-gray-200` / `dark:divide-border-subtle` | `divide-border-subtle` |
| `hover:bg-gray-100` / `dark:hover:bg-gray-600/700` | `hover:bg-bg-hover` |
| `hover:text-gray-700` / `dark:hover:text-gray-200` | `hover:text-text-heading` |

### Component-specific substitutions

| Component | Remove | Replace with |
|---|---|---|
| Secondary buttons | `bg-bg-table-head text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600` | `bg-btn-secondary-bg text-btn-secondary-text hover:bg-btn-secondary-hover border border-border-subtle` |
| Form inputs | `bg-white dark:bg-input-bg border-gray-300 dark:border-input-border text-gray-900 dark:text-text-base` | `bg-input-bg border-input-border text-text-base` |
| Filter selects | same as form inputs | `bg-input-bg border-input-border text-text-base` |
| Nav dropdown panel | `bg-white dark:bg-gray-700` | `bg-bg-elevated border border-border-subtle` |
| Footer | `bg-white dark:bg-gray-800` | `bg-bg-elevated border-t border-border-subtle` |
| Table headers | raw gray text classes | `text-text-muted` |
| Table row dividers | `divide-gray-200 dark:divide-border-subtle` | `divide-border-subtle` |
| Empty state headings | `text-gray-900 dark:text-gray-100` | `text-text-heading` |
| Empty state icons | `text-gray-400` | `text-text-muted` |
| Radarr badge | hardcoded teal classes | `bg-badge-movie/15 text-badge-movie border border-badge-movie/30` |
| Sonarr badge | hardcoded teal classes | `bg-badge-tv/15 text-badge-tv border border-badge-tv/30` |

### Dark mode class cleanup
After substitution, redundant `dark:` variants on semantic tokens are removed. Any remaining `dark:` classes that override semantic tokens are eliminated in the same pass.

### Affected files
- `listarr/static/css/tailwind.src.css`
- `tailwind.config.js`
- `listarr/templates/base.html`
- `listarr/templates/macros/ui.html`
- `listarr/templates/macros/status.html`
- `listarr/templates/macros/forms.html`
- `listarr/templates/lists.html`
- `listarr/templates/jobs.html`
- `listarr/templates/activity_run_detail.html`
- `listarr/templates/settings.html`
- `listarr/templates/list_wizard.html`
- `listarr/templates/lists_create.html`
- `listarr/templates/lists_create_preset.html`
- `listarr/templates/lists_create_custom.html`
- `listarr/templates/edit_list.html`
- `listarr/templates/auth/login.html`
- `listarr/templates/auth/setup.html`
- `listarr/templates/errors/404.html`
- `listarr/templates/errors/500.html`
- `listarr/static/js/*.js` (colour class references in JS-rendered HTML)

---

## Section 3: Component Styling

### Navigation (`base.html`)
- Background: `bg-nav-bg border-b border-border-subtle`
- Nav links: `text-text-muted hover:text-text-heading` inactive; `bg-primary/10 text-primary` active
- User dropdown button: `text-text-base hover:text-text-heading`
- Dropdown panel: `bg-bg-elevated border border-border-subtle` with items `hover:bg-bg-hover`

### Footer (`base.html`)
- `bg-bg-elevated border-t border-border-subtle text-text-muted`
- Dark mode toggle: `hover:bg-bg-hover`

### Buttons
- **Primary**: `bg-primary text-white hover:bg-primary-hover` (unchanged)
- **Secondary**: `bg-btn-secondary-bg text-btn-secondary-text hover:bg-btn-secondary-hover border border-border-subtle`
- **Danger**: `bg-red-600 text-white hover:bg-red-700`
- **Warning**: `bg-warning text-white hover:opacity-90`

### Cards / Panels
- `bg-bg-panel border border-border-subtle rounded`

### Tables
- Container: `bg-bg-panel border border-border-subtle overflow-hidden`
- Header row: `bg-bg-table-head`
- Header cells: `text-text-muted uppercase tracking-wider text-xs font-medium`
- Body dividers: `divide-border-subtle`
- Row hover: `hover:bg-bg-hover transition-colors`

### Form Inputs & Selects
- `bg-input-bg border border-input-border text-text-base rounded focus:ring-1 focus:ring-primary focus:border-primary`
- Labels: `text-text-base font-medium`
- Helper text: `text-text-muted text-xs`

### Badges
- Radarr: `bg-badge-movie/15 text-badge-movie border border-badge-movie/30 text-xs font-medium px-2 py-0.5 rounded`
- Sonarr: `bg-badge-tv/15 text-badge-tv border border-badge-tv/30 text-xs font-medium px-2 py-0.5 rounded`
- Status (success/failed/running): `bg-success/15 text-success border border-success/30` etc.

### Toast Notifications
- Success: `bg-success/10 border-success/30 text-success`
- Error: `bg-error/10 border-error/30 text-error`
- Warning: `bg-warning/10 border-warning/30 text-warning`
- Info: `bg-primary/10 border-primary/30 text-primary`

### Auth Pages
- Page: `bg-bg-base` full-height
- Card: `bg-bg-panel border border-border-subtle` centred

### Error Pages
- `bg-bg-base text-text-heading` token treatment throughout
