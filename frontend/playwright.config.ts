import { defineConfig, devices } from "@playwright/test";

/**
 * Uçtan uca testler derlenmiş arayüz üzerinde çalışır (vite preview). API yanıtları testlerde
 * sabit örneklerle taklit edilir; böylece testler veri ve ekran kartı gerektirmez.
 */
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  // 3B testleri WebGL'i yazılımla çizer; çok sayıda paralel işçi işlemciyi tıkar.
  workers: process.env.CI ? 1 : 2,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    // Başsız tarayıcıda WebGL yazılımla çizilir (3B görünüm testleri için).
    launchOptions: {
      args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    },
  },
  webServer: {
    command: "npx vite preview --host 127.0.0.1 --port 4173 --strictPort --outDir dist-e2e",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "masaustu", use: { ...devices["Desktop Chrome"] } },
    { name: "mobil", use: { ...devices["Pixel 7"] } },
  ],
});
