import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api va a la API local (también los WebSockets).
// VITE_DEMO=1 compila la demo con datos de ejemplo en un solo archivo JS.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": { target: "http://localhost:8000", ws: true } } },
  build: process.env.VITE_DEMO === "1" ? { rollupOptions: { output: { inlineDynamicImports: true } } } : {},
});
