import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { analyzeSavePlugin } from "./analyzePlugin.js";

export default defineConfig({
  plugins: [react(), analyzeSavePlugin()],
  server: {
    port: 5177,
    host: "127.0.0.1",
  },
  preview: {
    port: 5177,
    host: "127.0.0.1",
  },
});
