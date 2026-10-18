import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#05060f",
        panel: "rgba(15, 18, 36, 0.6)",
        line: "rgba(120, 140, 255, 0.14)",
        neon: {
          cyan: "#22d3ee",
          violet: "#8b5cf6",
          magenta: "#e879f9",
          lime: "#a3e635",
          amber: "#fbbf24",
          rose: "#fb7185",
          blue: "#60a5fa",
          teal: "#2dd4bf",
          orange: "#fb923c",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      animation: {
        aurora: "aurora 18s ease-in-out infinite alternate",
        "aurora-slow": "aurora 26s ease-in-out infinite alternate-reverse",
        "pulse-ring": "pulseRing 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float-y": "floatY 7s ease-in-out infinite",
        shimmer: "shimmer 2.8s linear infinite",
        "grid-pan": "gridPan 30s linear infinite",
        "fade-up": "fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
      },
      keyframes: {
        aurora: {
          "0%": { transform: "translate(-8%, -6%) scale(1) rotate(0deg)" },
          "50%": { transform: "translate(10%, 8%) scale(1.15) rotate(12deg)" },
          "100%": { transform: "translate(-4%, 10%) scale(0.95) rotate(-8deg)" },
        },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 rgba(34, 211, 238, 0.35)" },
          "70%": { boxShadow: "0 0 0 12px rgba(34, 211, 238, 0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(34, 211, 238, 0)" },
        },
        floatY: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        gridPan: {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "60px 60px" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
