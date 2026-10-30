import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api va a la API local (también los WebSockets).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": { target: "http://localhost:8000", ws: true } } },
});
