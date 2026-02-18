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
        primary: "#4F46E5",
        secondary: "#10B981",
      },
    },
  },
  plugins: [],
};
