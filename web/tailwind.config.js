/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Google-Finance-style surfaces. Light = white / light-grey; dark = near-black.
        surface: {
          DEFAULT: "#ffffff", // light: page background
          alt: "#f8f9fa", // light: cards / sidebar
          dark: "#202124", // dark: page background
          "dark-alt": "#2a2b2e", // dark: cards / sidebar
        },
        edge: {
          DEFAULT: "#dadce0", // light border
          dark: "#3c4043", // dark border
        },
        content: {
          DEFAULT: "#202124", // light primary text
          muted: "#5f6368", // light secondary text
          dark: "#e8eaed", // dark primary text
          "dark-muted": "#9aa0a6", // dark secondary text
        },
        brand: "#1a73e8", // Google blue accent
        // Up/down are theme-INDEPENDENT (must read in both light and dark).
        up: "#1a7f37",
        down: "#d1242f",
      },
      borderRadius: {
        xl: "0.875rem", // 14px — soft card corners
        "2xl": "1.125rem",
      },
      boxShadow: {
        // Layered soft shadows for surfaces (light theme). Dark relies on borders.
        card: "0 1px 2px rgba(60,64,67,0.06), 0 1px 3px rgba(60,64,67,0.10)",
        "card-hover":
          "0 2px 6px rgba(60,64,67,0.10), 0 4px 12px rgba(60,64,67,0.12)",
      },
      keyframes: {
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        shimmer: "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};
