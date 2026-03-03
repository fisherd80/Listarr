# UI Colour Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace ~700 hardcoded Tailwind colour classes across all templates and JS with a consistent 22-token semantic system, delivering a correct dark-first (navy/near-black) and clean light (slate) colour scheme throughout.

**Architecture:** Expand `tailwind.src.css` with 22 semantic CSS variables for both light/dark modes, register 7 new token aliases in `tailwind.config.js`, then do a file-by-file substitution pass replacing every hardcoded `gray-xxx`/`white`/`black` class with the appropriate token class. Rebuild CSS after each logical group of files.

**Tech Stack:** Tailwind CSS (compiled via `./build-css.sh`), Jinja2 templates, vanilla JS, Flask.

---

## Verification Command

After every rebuild, check for any remaining raw colour classes:
```bash
grep -rn "bg-white\b\|bg-gray-\|text-gray-\|border-gray-\|divide-gray-\|hover:bg-gray-\|dark:bg-gray-\|dark:text-gray-\|dark:border-gray-\|dark:hover:bg-gray-" listarr/templates/ listarr/static/js/
```
Goal: zero matches by Task 12.

---

## Task 1: Update CSS Tokens and Tailwind Config

**Files:**
- Modify: `listarr/static/css/tailwind.src.css`
- Modify: `tailwind.config.js`

**Step 1: Replace the entire `:root` and `.dark` blocks in `tailwind.src.css`**

Replace everything from `:root {` through the closing `}` of `.dark {` with:

```css
:root {
  --color-primary-rgb: 13 148 136;
  --color-primary-hover-rgb: 15 118 110;
  --color-bg-base: #f1f5f9;
  --color-bg-panel: #ffffff;
  --color-bg-table-head: #f8fafc;
  --color-bg-elevated: #ffffff;
  --color-bg-hover: #f1f5f9;
  --color-border: #cbd5e1;
  --color-text-base: #0f172a;
  --color-text-muted: #64748b;
  --color-text-heading: #0f172a;
  --color-success: #16a34a;
  --color-error: #dc2626;
  --color-warning: #d97706;
  --color-input-bg: #ffffff;
  --color-input-border: #cbd5e1;
  --color-nav-bg: #ffffff;
  --color-btn-secondary-bg: #e2e8f0;
  --color-btn-secondary-text: #334155;
  --color-btn-secondary-hover: #cbd5e1;
  --color-badge-movie: #0369a1;
  --color-badge-tv: #0d9488;
}

.dark {
  --color-primary-rgb: 45 212 191;
  --color-primary-hover-rgb: 38 191 170;
  --color-bg-base: #0f1117;
  --color-bg-panel: #1a1d27;
  --color-bg-table-head: #141720;
  --color-bg-elevated: #1a1d27;
  --color-bg-hover: #22263a;
  --color-border: #2a2d3a;
  --color-text-base: #e2e8f0;
  --color-text-muted: #94a3b8;
  --color-text-heading: #f1f5f9;
  --color-success: #22c55e;
  --color-error: #ef4444;
  --color-warning: #f59e0b;
  --color-input-bg: #0f1117;
  --color-input-border: #2a2d3a;
  --color-nav-bg: #0f1117;
  --color-btn-secondary-bg: #22263a;
  --color-btn-secondary-text: #94a3b8;
  --color-btn-secondary-hover: #2a2d3a;
  --color-badge-movie: #38bdf8;
  --color-badge-tv: #2dd4bf;
}
```

**Step 2: Add 7 new token entries to `tailwind.config.js`**

Inside the `colors:` block, after `"nav-bg"`, add:

```js
"bg-elevated":         "var(--color-bg-elevated)",
"bg-hover":            "var(--color-bg-hover)",
"btn-secondary-bg":    "var(--color-btn-secondary-bg)",
"btn-secondary-text":  "var(--color-btn-secondary-text)",
"btn-secondary-hover": "var(--color-btn-secondary-hover)",
"badge-movie":         "var(--color-badge-movie)",
"badge-tv":            "var(--color-badge-tv)",
```

**Step 3: Rebuild CSS**

```bash
./build-css.sh
```
Expected: exits 0, `listarr/static/css/tailwind.css` updated.

**Step 4: Commit**

```bash
git add listarr/static/css/tailwind.src.css tailwind.config.js listarr/static/css/tailwind.css
git commit -m "feat(ui): expand CSS token palette to 22 semantic variables for dark-navy/slate scheme"
```

---

## Task 2: Fix `base.html` — Nav, Footer, Dropdowns, Body

**Files:**
- Modify: `listarr/templates/base.html`

**Step 1: Fix `<body>` tag — remove redundant dark: variants**

```
OLD: class="bg-bg-base dark:bg-bg-base text-text-base dark:text-text-base"
NEW: class="bg-bg-base text-text-base"
```

**Step 2: Fix nav element**

```
OLD: class="bg-nav-bg dark:bg-nav-bg border-b border-gray-200 dark:border-border-subtle"
NEW: class="bg-nav-bg border-b border-border-subtle"
```

**Step 3: Fix nav link inactive state**

```
OLD: text-gray-500 dark:text-gray-300 hover:text-primary
NEW: text-text-muted hover:text-text-heading
```

Active state (both nav links):
```
OLD: bg-primary text-white
NEW: bg-primary/10 text-primary
```

**Step 4: Fix user dropdown button**

```
OLD: text-gray-700 dark:text-gray-200 hover:text-primary
NEW: text-text-base hover:text-text-heading
```

**Step 5: Fix user dropdown panel**

```
OLD: bg-white dark:bg-gray-700 border border-gray-200 dark:border-border-subtle
NEW: bg-bg-elevated border border-border-subtle
```

Dropdown items:
```
OLD: text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600
NEW: text-text-base hover:bg-bg-hover
```

**Step 6: Fix Login link (unauthenticated nav)**

```
OLD: text-gray-700 dark:text-gray-200 hover:text-primary
NEW: text-text-base hover:text-primary
```

**Step 7: Fix flash toast colours**

Replace the entire flash toast class string pattern. For each category, replace the paired `light/dark:` classes with token-based opacity variants:

```
SUCCESS:
OLD: bg-green-100 dark:bg-green-900 border-green-200 dark:border-green-800
NEW: bg-success/10 border border-success/30
OLD: text-green-500 dark:text-green-400   (icon)
NEW: text-success
OLD: text-green-800 dark:text-green-200   (message)
NEW: text-success

WARNING:
OLD: bg-yellow-100 dark:bg-yellow-900 border-yellow-200 dark:border-yellow-800
NEW: bg-warning/10 border border-warning/30
OLD: text-yellow-500 dark:text-yellow-400 → text-warning
OLD: text-yellow-800 dark:text-yellow-200 → text-warning

ERROR:
OLD: bg-red-100 dark:bg-red-900 border-red-200 dark:border-red-800
NEW: bg-error/10 border border-error/30
OLD: text-red-500 dark:text-red-400 → text-error
OLD: text-red-800 dark:text-red-200 → text-error

INFO:
OLD: bg-blue-100 dark:bg-blue-900 border-blue-200 dark:border-blue-800
NEW: bg-primary/10 border border-primary/30
OLD: text-blue-500 dark:text-blue-400 → text-primary
OLD: text-blue-800 dark:text-blue-200 → text-primary
```

**Step 8: Fix footer**

```
OLD: class="bg-white dark:bg-gray-800 text-sm py-4 text-gray-500 dark:text-gray-400"
NEW: class="bg-bg-elevated border-t border-border-subtle text-sm py-4 text-text-muted"
```

Footer GitHub link:
```
OLD: text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200
NEW: text-text-muted hover:text-text-heading
```

Dark mode toggle button:
```
OLD: text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700
NEW: text-text-muted hover:text-text-heading hover:bg-bg-hover
```

**Step 9: Rebuild and commit**

```bash
./build-css.sh
git add listarr/templates/base.html listarr/static/css/tailwind.css
git commit -m "feat(ui): fix base.html nav, footer, and flash toasts to use semantic tokens"
```

---

## Task 3: Fix Macros — `ui.html`, `status.html`, `forms.html`

**Files:**
- Modify: `listarr/templates/macros/ui.html`
- Modify: `listarr/templates/macros/status.html`
- Modify: `listarr/templates/macros/forms.html`

### `ui.html`

**Step 1: Fix loading spinner muted text**
```
OLD: text-sm text-gray-500 dark:text-gray-400
NEW: text-sm text-text-muted
```

**Step 2: Fix empty state heading**
```
OLD: text-sm font-medium text-gray-900 dark:text-gray-100
NEW: text-sm font-medium text-text-heading
```

**Step 3: Fix empty state description**
```
OLD: text-sm text-gray-500 dark:text-gray-400
NEW: text-sm text-text-muted
```

### `status.html`

**Step 4: Replace the entire `colors` dict in `status_badge` macro**

```jinja
{%- set colors = {
  'online':         'bg-success/15 text-success border border-success/30',
  'connected':      'bg-success/15 text-success border border-success/30',
  'active':         'bg-success/15 text-success border border-success/30',
  'completed':      'bg-success/15 text-success border border-success/30',
  'scheduled':      'bg-success/15 text-success border border-success/30',
  'running':        'bg-primary/15 text-primary border border-primary/30',
  'pending':        'bg-warning/15 text-warning border border-warning/30',
  'paused':         'bg-warning/15 text-warning border border-warning/30',
  'failed':         'bg-error/15 text-error border border-error/30',
  'offline':        'bg-error/15 text-error border border-error/30',
  'inactive':       'bg-bg-hover text-text-muted border border-border-subtle',
  'not_configured': 'bg-bg-hover text-text-muted border border-border-subtle',
  'manual_only':    'bg-bg-hover text-text-muted border border-border-subtle',
} -%}
{%- set color = colors.get(status|lower, 'bg-bg-hover text-text-muted border border-border-subtle') -%}
```

**Step 5: Replace `service_badge` macro body**

```jinja
{%- if service|lower == 'radarr' -%}
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-badge-movie/15 text-badge-movie border border-badge-movie/30">
  {{ service|title }}
</span>
{%- else -%}
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-badge-tv/15 text-badge-tv border border-badge-tv/30">
  {{ service|title }}
</span>
{%- endif -%}
```

### `forms.html`

**Step 6: Fix Import Settings toggle button**
```
OLD: bg-gray-100 dark:bg-gray-700 ... text-gray-900 dark:text-gray-100 ... hover:bg-gray-200 dark:hover:bg-gray-600
NEW: bg-btn-secondary-bg text-btn-secondary-text hover:bg-btn-secondary-hover border border-border-subtle
```

**Step 7: Fix skeleton loading bars**
```
OLD: bg-gray-200 dark:bg-gray-700
NEW: bg-bg-hover
```
(Apply to all skeleton `<div>` elements in the macro — there are 5-6 of them.)

**Step 8: Fix all form selects and inputs in the macro**
```
OLD: border-gray-300 dark:border-input-border bg-white dark:bg-input-bg text-gray-900 dark:text-text-base
NEW: border-input-border bg-input-bg text-text-base
```
(Applies to every `<select>` and `<input>` in the macro — there are ~6.)

**Step 9: Fix labels and helper text**
```
OLD: text-gray-700 dark:text-gray-300
NEW: text-text-base

OLD: text-gray-500 dark:text-gray-400
NEW: text-text-muted
```

**Step 10: Also fix the `border-t` separator on the wrapper div**
```
OLD: class="border-t pt-4 mt-4 max-w-lg"
NEW: class="border-t border-border-subtle pt-4 mt-4 max-w-lg"
```

**Step 11: Rebuild and commit**

```bash
./build-css.sh
git add listarr/templates/macros/ listarr/static/css/tailwind.css
git commit -m "feat(ui): fix macros (ui, status, forms) to use semantic colour tokens"
```

---

## Task 4: Fix `lists.html`

**Files:**
- Modify: `listarr/templates/lists.html`

**Step 1: Fix filter selects**
```
OLD: bg-white dark:bg-input-bg border border-gray-300 dark:border-input-border text-gray-900 dark:text-text-base
NEW: bg-input-bg border border-input-border text-text-base
```

**Step 2: Fix table container border**
```
OLD: border border-gray-200 dark:border-border-subtle
NEW: border border-border-subtle
```

**Step 3: Fix table dividers**
```
OLD: divide-y divide-gray-200 dark:divide-border-subtle
NEW: divide-y divide-border-subtle
```
(Applies to `<table>` and `<tbody>` elements.)

**Step 4: Fix table header cells**
```
OLD: text-gray-600 dark:text-gray-300 ... hover:text-gray-900 dark:hover:text-gray-100
NEW: text-text-muted hover:text-text-heading
```
(Applies to all `<th>` elements — there are 8.)

**Step 5: Rebuild and commit**

```bash
./build-css.sh
git add listarr/templates/lists.html listarr/static/css/tailwind.css
git commit -m "feat(ui): fix lists.html to use semantic colour tokens"
```

---

## Task 5: Fix `jobs.html`

**Files:**
- Modify: `listarr/templates/jobs.html`

**Step 1: Fix page heading**
```
OLD: text-gray-900 dark:text-gray-100
NEW: text-text-heading

OLD: text-gray-500 dark:text-gray-400  (subtitle)
NEW: text-text-muted
```

**Step 2: Fix filter section panel**
```
OLD: border border-gray-200 dark:border-border-subtle
NEW: border border-border-subtle
```

**Step 3: Fix filter labels**
```
OLD: text-gray-700 dark:text-gray-300
NEW: text-text-base
```

**Step 4: Fix filter selects**
```
OLD: border border-gray-300 dark:border-input-border bg-white dark:bg-input-bg text-gray-900 dark:text-text-base
NEW: border border-input-border bg-input-bg text-text-base
```

**Step 5: Fix table container, dividers, header cells**

Same pattern as Task 4, Steps 2–4.

**Step 6: Rebuild and commit**

```bash
./build-css.sh
git add listarr/templates/jobs.html listarr/static/css/tailwind.css
git commit -m "feat(ui): fix jobs.html to use semantic colour tokens"
```

---

## Task 6: Fix `activity_run_detail.html`

**Files:**
- Modify: `listarr/templates/activity_run_detail.html`

Read the full file first, then apply the universal substitution rules from the design doc:
- `text-gray-900 dark:text-gray-100` → `text-text-heading`
- `text-gray-700 dark:text-gray-200` → `text-text-base`
- `text-gray-500 dark:text-gray-400` → `text-text-muted`
- `border-gray-200 dark:border-border-subtle` → `border-border-subtle`
- `bg-white dark:bg-...` → `bg-bg-elevated` or `bg-bg-panel` depending on context
- `hover:bg-gray-100 dark:hover:bg-gray-600` → `hover:bg-bg-hover`

**Rebuild and commit:**

```bash
./build-css.sh
git add listarr/templates/activity_run_detail.html listarr/static/css/tailwind.css
git commit -m "feat(ui): fix activity_run_detail.html to use semantic colour tokens"
```

---

## Task 7: Fix `settings.html`

**Files:**
- Modify: `listarr/templates/settings.html`

Read the full file first. Key patterns to fix:

**Step 1: Fix tab nav border**
```
OLD: border-b border-gray-200 dark:border-border-subtle
NEW: border-b border-border-subtle
```

**Step 2: Fix all form inputs and selects** (same pattern throughout)
```
OLD: border border-gray-300 dark:border-input-border bg-white dark:bg-input-bg text-gray-900 dark:text-text-base
NEW: border border-input-border bg-input-bg text-text-base
```

**Step 3: Fix "Test Connection" secondary buttons**
```
OLD: bg-bg-table-head dark:bg-bg-table-head text-gray-700 dark:text-gray-300 ... hover:bg-gray-300 dark:hover:bg-gray-600
NEW: bg-btn-secondary-bg text-btn-secondary-text hover:bg-btn-secondary-hover border border-border-subtle
```

**Step 4: Fix labels and helper text**
```
OLD: text-gray-700 dark:text-gray-300 (labels) → text-text-base
OLD: text-text-muted dark:text-text-muted → text-text-muted  (remove redundant dark: prefix)
OLD: text-gray-500 dark:text-gray-400 → text-text-muted
```

**Step 5: Fix panel borders**
```
OLD: border border-gray-200 dark:border-border-subtle
NEW: border border-border-subtle
```

**Rebuild and commit:**

```bash
./build-css.sh
git add listarr/templates/settings.html listarr/static/css/tailwind.css
git commit -m "feat(ui): fix settings.html to use semantic colour tokens"
```

---

## Task 8: Fix List Wizard and Create Templates

**Files:**
- Modify: `listarr/templates/list_wizard.html`
- Modify: `listarr/templates/lists_create.html`
- Modify: `listarr/templates/lists_create_preset.html`
- Modify: `listarr/templates/lists_create_custom.html`
- Modify: `listarr/templates/edit_list.html`

Read each file. Apply the universal substitution mapping from the design doc. Key patterns:

- All form inputs/selects: `bg-input-bg border-input-border text-text-base`
- All labels: `text-text-base`
- All helper/muted text: `text-text-muted`
- All panel borders: `border-border-subtle`
- All heading text: `text-text-heading`
- Step badges (inactive): `bg-bg-hover text-text-muted` (replace `bg-gray-600 text-gray-300`)
- Card borders: `border-border-subtle`
- Secondary buttons: `bg-btn-secondary-bg text-btn-secondary-text hover:bg-btn-secondary-hover border border-border-subtle`

**Rebuild and commit:**

```bash
./build-css.sh
git add listarr/templates/list_wizard.html listarr/templates/lists_create.html \
        listarr/templates/lists_create_preset.html listarr/templates/lists_create_custom.html \
        listarr/templates/edit_list.html listarr/static/css/tailwind.css
git commit -m "feat(ui): fix wizard and create templates to use semantic colour tokens"
```

---

## Task 9: Fix Auth and Error Templates

**Files:**
- Modify: `listarr/templates/auth/login.html`
- Modify: `listarr/templates/auth/setup.html`
- Modify: `listarr/templates/errors/404.html`
- Modify: `listarr/templates/errors/500.html`

### `auth/login.html`

**Step 1: Fix `<body>` tag**
```
OLD: class="bg-bg-base dark:bg-bg-base text-text-base dark:text-text-base"
NEW: class="bg-bg-base text-text-base"
```

**Step 2: Fix card border**
```
OLD: border border-gray-200 dark:border-border-subtle
NEW: border border-border-subtle
```

**Step 3: Fix error alert**
```
OLD: bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200
NEW: bg-error/10 border border-error/30 text-error
```

**Step 4: Fix form inputs**
```
OLD: border border-gray-300 dark:border-input-border ... bg-white dark:bg-input-bg text-gray-900 dark:text-text-base
NEW: border border-input-border bg-input-bg text-text-base
```

**Step 5: Fix checkbox border**
```
OLD: border-gray-300
NEW: border-input-border
```

### `auth/setup.html`

Apply same fixes as login.html — read the file first.

### `errors/404.html` and `errors/500.html`

**Fix `<body>` tag:**
```
OLD: class="bg-bg-base dark:bg-bg-base text-text-base dark:text-text-base"
NEW: class="bg-bg-base text-text-base"
```

**Fix large error number text (404.html):**
```
OLD: text-gray-300 dark:text-gray-600
NEW: text-text-muted
```

**Fix muted description text:**
```
OLD: text-text-muted dark:text-text-muted
NEW: text-text-muted
```

**Rebuild and commit:**

```bash
./build-css.sh
git add listarr/templates/auth/ listarr/templates/errors/ listarr/static/css/tailwind.css
git commit -m "feat(ui): fix auth and error templates to use semantic colour tokens"
```

---

## Task 10: Fix JS Files

**Files:**
- Modify: `listarr/static/js/jobs.js`
- Modify: `listarr/static/js/lists.js`
- Modify: `listarr/static/js/activity_detail.js`
- Modify: `listarr/static/js/create.js`

### `jobs.js`

**Line ~187 — rerun menu item:**
```
OLD: text-text-base dark:text-gray-300 hover:bg-bg-table-head dark:hover:bg-bg-table-head
NEW: text-text-base hover:bg-bg-hover
```

**Line ~191-193 — overflow button and menu:**
```
OLD: text-text-muted dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-100
NEW: text-text-muted hover:text-text-heading

OLD: bg-bg-panel dark:bg-bg-panel border border-gray-300 dark:border-border-subtle
NEW: bg-bg-panel border border-border-subtle

OLD: text-text-base dark:text-gray-300 hover:bg-bg-table-head dark:hover:bg-bg-table-head  (View link)
NEW: text-text-base hover:bg-bg-hover
```

**Lines ~214-226 — table row cells:**
```
OLD: text-gray-900 dark:text-gray-100
NEW: text-text-heading

OLD: text-gray-500 dark:text-gray-400
NEW: text-text-muted
```

**Lines ~274, ~281 — status color map (skipped/unknown):**
```
OLD: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
NEW: "bg-bg-hover text-text-muted border border-border-subtle"
```

**Lines ~385-386 — filter button active/inactive:**
```
OLD: activeClass  = "bg-primary text-white border border-gray-600 ..."
NEW: activeClass  = "bg-primary text-white border border-primary/50 ..."

OLD: inactiveClass = "text-gray-300 hover:bg-gray-600 border border-gray-600 ..."
NEW: inactiveClass = "text-text-muted hover:bg-bg-hover border border-border-subtle ..."
```

### `lists.js`

**Line ~158 — disabled badge:**
```
OLD: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
NEW: 'bg-bg-hover text-text-muted border border-border-subtle'
```

**Line ~184 — inline style (remove it, replace with class):**
```
OLD: btn.style.backgroundColor = '#4b5563';
NEW: btn.classList.add('bg-bg-hover');
     btn.style.backgroundColor = '';
```

### `activity_detail.js`

**Line ~93 — meta row:**
```
OLD: 'flex flex-wrap gap-x-4 gap-y-1 mb-2 text-gray-400'
NEW: 'flex flex-wrap gap-x-4 gap-y-1 mb-2 text-text-muted'
```

**Lines ~103, 105, 107 — bullet separators:**
```
OLD: 'text-gray-500'
NEW: 'text-text-muted'
```

**Line ~122 — skipped item color:**
```
OLD: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
NEW: 'bg-bg-hover text-text-muted border border-border-subtle'
```

**Line ~162 — table header cell class:**
```
OLD: 'px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider'
NEW: 'px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider'
```

**Lines ~165, 169 — table/thead dividers:**
```
OLD: 'min-w-full divide-y divide-gray-700'
NEW: 'min-w-full divide-y divide-border-subtle'

OLD: 'border-b border-gray-700'
NEW: 'border-b border-border-subtle'
```

**Lines ~184, 192-199 — row and cell classes:**
```
OLD: 'px-4 py-8 text-center text-gray-400 text-sm'   (empty)
NEW: 'px-4 py-8 text-center text-text-muted text-sm'

OLD: 'border-b border-gray-700 last:border-0'         (row)
NEW: 'border-b border-border-subtle last:border-0'

OLD: 'px-4 py-3 text-sm text-gray-100'               (title cell)
NEW: 'px-4 py-3 text-sm text-text-base'

OLD: 'px-4 py-3 text-sm text-gray-400'               (reason cell)
NEW: 'px-4 py-3 text-sm text-text-muted'

OLD: 'px-4 py-3 text-sm text-gray-500'               (tmdb cell)
NEW: 'px-4 py-3 text-sm text-text-muted'
```

### `create.js`

**Lines ~62-76 — tab toggle active/inactive:**
```
OLD (inactive): 'border-transparent', 'text-gray-400'
NEW (inactive): 'border-transparent', 'text-text-muted'
```

**Lines ~221-226 — step badge active/inactive:**
```
OLD (inactive): 'bg-gray-600', 'text-gray-300'
NEW (inactive): 'bg-bg-hover', 'text-text-muted'
```

**Lines ~232-236 — step title active/inactive:**
```
OLD: 'text-gray-400' (inactive) / 'text-gray-100' (active)
NEW: 'text-text-muted' (inactive) / 'text-text-heading' (active)
```

**Lines ~275, ~279, ~282, ~352, ~361 — card border:**
```
OLD: 'border-gray-600'
NEW: 'border-border-subtle'
```

**Lines ~352, ~361, ~384 — pill/button inactive:**
```
OLD: 'border-gray-600', 'text-gray-400'  or  'border-gray-600', 'text-gray-300', 'bg-transparent'
NEW: 'border-border-subtle', 'text-text-muted', 'bg-transparent'
```

**Lines ~438, ~463 — preview panel loading/empty text:**
```
OLD: 'text-sm text-gray-500 text-center py-8'
NEW: 'text-sm text-text-muted text-center py-8'

OLD: 'text-sm text-gray-400 text-center py-8 px-4'
NEW: 'text-sm text-text-muted text-center py-8 px-4'
```

**Line ~470 — list divider:**
```
OLD: '<ul class="divide-y divide-gray-700">'
NEW: '<ul class="divide-y divide-border-subtle">'
```

**Rebuild and commit:**

```bash
./build-css.sh
git add listarr/static/js/jobs.js listarr/static/js/lists.js \
        listarr/static/js/activity_detail.js listarr/static/js/create.js \
        listarr/static/css/tailwind.css
git commit -m "feat(ui): fix JS-rendered HTML colour classes to use semantic tokens"
```

---

## Task 11: Final Cleanup Pass

**Step 1: Run the verification grep**

```bash
grep -rn "bg-white\b\|bg-gray-\|text-gray-\|border-gray-\|divide-gray-\|hover:bg-gray-\|dark:bg-gray-\|dark:text-gray-\|dark:border-gray-\|dark:hover:bg-gray-" listarr/templates/ listarr/static/js/
```

**Step 2: Fix any remaining hits**

For each match, apply the appropriate substitution from the design doc mapping table. Common stragglers:
- Any remaining `dark:text-text-muted` / `dark:text-text-base` etc. — remove the redundant `dark:` prefix (token handles it)
- Any `dark:bg-bg-panel` / `dark:bg-bg-base` — remove `dark:` prefix
- Any `dark:border-border-subtle` — remove `dark:` prefix

**Step 3: Rebuild**

```bash
./build-css.sh
```

**Step 4: Run tests to confirm no regressions**

```bash
pytest tests/routes/ -q
```
Expected: all route tests pass (templates render without errors).

**Step 5: Commit**

```bash
git add -A
git commit -m "feat(ui): final cleanup — remove all remaining hardcoded colour classes"
```

---

## Task 12: Verify in Both Modes

**Step 1: Start the dev server**

```bash
python run.py
```

**Step 2: Open `http://localhost:5000` in a browser**

Check each page in **dark mode** and **light mode** (toggle via footer button):

| Page | Check |
|---|---|
| Login | Card border visible, inputs readable, button correct |
| Lists | Table header contrast, badges correct, filter selects |
| Activity | Row colours, status badges, overflow menu |
| Settings | Tab nav, form inputs, Test Connection button, Save button |
| List Wizard | Step badges, card selection, preset pills |
| 404/500 | Large number readable in both modes |

**Step 3: Commit any last fixes found during visual review**

```bash
git add -A
git commit -m "fix(ui): visual review corrections after colour overhaul"
```

---

## Quick Reference: Substitution Cheatsheet

| Raw class(es) | Token replacement |
|---|---|
| `bg-white` / `dark:bg-gray-700/800` | `bg-bg-elevated` or `bg-bg-panel` |
| `bg-gray-100` / `dark:bg-gray-700` | `bg-bg-hover` |
| `bg-gray-200` / `dark:bg-gray-700` (skeleton) | `bg-bg-hover` |
| `text-gray-900` / `dark:text-gray-100` | `text-text-heading` |
| `text-gray-700` / `dark:text-gray-200` | `text-text-base` |
| `text-gray-600` / `dark:text-gray-300` | `text-text-muted` |
| `text-gray-500` / `dark:text-gray-400` | `text-text-muted` |
| `text-gray-400` | `text-text-muted` |
| `border-gray-200` / `dark:border-border-subtle` | `border-border-subtle` |
| `border-gray-300` / `dark:border-input-border` | `border-input-border` |
| `divide-gray-200/700` / `dark:divide-border-subtle` | `divide-border-subtle` |
| `hover:bg-gray-100` / `dark:hover:bg-gray-600/700` | `hover:bg-bg-hover` |
| `hover:text-gray-700` / `dark:hover:text-gray-200` | `hover:text-text-heading` |
| Secondary button bg/text/hover | `bg-btn-secondary-bg text-btn-secondary-text hover:bg-btn-secondary-hover` |
| Form inputs/selects | `bg-input-bg border-input-border text-text-base` |
| Radarr badge | `bg-badge-movie/15 text-badge-movie border border-badge-movie/30` |
| Sonarr badge | `bg-badge-tv/15 text-badge-tv border border-badge-tv/30` |
| Status success | `bg-success/15 text-success border border-success/30` |
| Status error | `bg-error/15 text-error border border-error/30` |
| Status warning | `bg-warning/15 text-warning border border-warning/30` |
| Status inactive/neutral | `bg-bg-hover text-text-muted border border-border-subtle` |
