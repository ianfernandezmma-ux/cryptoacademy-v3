import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" keeps the build relocatable (GitHub Pages subpath, Vercel, local file preview).
export default defineConfig({
  plugins: [react()],
  base: "./",
  // PORT lets the Claude Code preview harness assign a free port (autoPort).
  server: { port: Number(process.env.PORT) || 5173 },
});
