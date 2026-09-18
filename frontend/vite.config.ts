import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const backendLocale = fileURLToPath(new URL("../backend/sinek/locales/tr.json", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Davranış ve arayüz metinlerinin tek kaynağı arka uçtaki tr.json dosyasıdır.
    alias: { "@yerel": backendLocale },
  },
  server: {
    fs: { allow: [".", "../backend/sinek/locales"] },
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    // FastAPI derlenmiş arayüzü bu dizinden sunar; son kullanıcı Node.js'e ihtiyaç duymaz.
    outDir: "../backend/sinek/web",
    emptyOutDir: true,
    // three.js (3B beyin) ayrı ve tembel yüklenen bir parçadır; ~560 KB beklenen boyuttur.
    chunkSizeWarningLimit: 600,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["src/test/kurulum.ts"],
    css: false,
  },
});
