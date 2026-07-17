import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/v1": {
        target: process.env.VITE_HOST_PROXY || "http://127.0.0.1:3006",
        changeOrigin: true,
      },
      "/health": {
        target: process.env.VITE_HOST_PROXY || "http://127.0.0.1:3006",
        changeOrigin: true,
      },
    },
  },
});

