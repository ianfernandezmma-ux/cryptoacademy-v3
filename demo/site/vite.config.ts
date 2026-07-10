import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" keeps the build relocatable (GitHub Pages subpath, Vercel, local file preview).
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 5173 },
});
