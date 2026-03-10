/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./listarr/templates/**/*.html",
    "./listarr/static/js/**/*.js",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "rgb(var(--color-primary-rgb) / <alpha-value>)",
        "primary-hover": "rgb(var(--color-primary-hover-rgb) / <alpha-value>)",
        "bg-base": "var(--color-bg-base)",
        "bg-panel": "var(--color-bg-panel)",
        "bg-table-head": "var(--color-bg-table-head)",
        "border-subtle": "var(--color-border)",
        "text-base": "var(--color-text-base)",
        "text-muted": "var(--color-text-muted)",
        "text-heading": "var(--color-text-heading)",
        "input-bg": "var(--color-input-bg)",
        "input-border": "var(--color-input-border)",
        "nav-bg": "var(--color-nav-bg)",
        "bg-elevated":         "var(--color-bg-elevated)",
        "bg-hover":            "var(--color-bg-hover)",
        "btn-secondary-bg":    "var(--color-btn-secondary-bg)",
        "btn-secondary-text":  "var(--color-btn-secondary-text)",
        "btn-secondary-hover": "var(--color-btn-secondary-hover)",
        "badge-movie":         "rgb(var(--color-badge-movie-rgb) / <alpha-value>)",
        "badge-tv":            "rgb(var(--color-badge-tv-rgb) / <alpha-value>)",
        success: "rgb(var(--color-success-rgb) / <alpha-value>)",
        error:   "rgb(var(--color-error-rgb) / <alpha-value>)",
        warning: "rgb(var(--color-warning-rgb) / <alpha-value>)",
      },
      borderRadius: {
        DEFAULT: "4px",
        none: "0",
        sm: "2px",
        md: "4px",
        lg: "4px",
        xl: "4px",
        "2xl": "4px",
        "3xl": "4px",
        full: "4px",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont",
          '"Segoe UI"', "Roboto", '"Helvetica Neue"', "Arial", "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
