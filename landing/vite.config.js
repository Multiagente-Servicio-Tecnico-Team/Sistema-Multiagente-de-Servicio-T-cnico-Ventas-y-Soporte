import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.js"],
    include: ["tests/**/*.test.{js,jsx}"],
    // Las pruebas no dependen del landing/.env local: siempre arrancan en modo demostración.
    env: { VITE_API_URL: "", VITE_CHAT_URL: "" },
  },
});
