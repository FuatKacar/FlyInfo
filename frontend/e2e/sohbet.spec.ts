import { expect, type Page, test } from "@playwright/test";
import {
  experimentResult,
  job,
  labOptions,
  outOfScopeResponse,
  sugarResponse,
} from "../src/test/fixtures";

async function mockApi(page: Page) {
  await page.route("/api/scenarios", (route) =>
    route.fulfill({
      json: {
        groups: [
          {
            key: "sugar",
            name_tr: "Şekere duyarlı tat nöronları",
            description_tr: "",
            neuron_count: 21,
            circuit_only: false,
            citations: [3],
          },
        ],
        package: { available: true, version: "1", problem: null },
        scenarios: [],
      },
    }),
  );
  await page.route("/api/lab/options", (route) => route.fulfill({ json: labOptions() }));
  await page.route("/api/lab/run", (route) =>
    route.fulfill({ status: 202, json: job({ state: "running", progress: 0.3 }) }),
  );
  await page.route(/\/api\/lab\/jobs\/.*/, (route) =>
    route.fulfill({ json: job({ state: "done", experiment: experimentResult() }) }),
  );
  await page.route("/api/chat", async (route) => {
    const { message } = route.request().postDataJSON() as { message: string };
    await route.fulfill({ json: /bal/i.test(message) ? sugarResponse() : outOfScopeResponse() });
  });
}

const input = (page: Page) => page.getByRole("textbox", { name: "Mesaj", exact: true });

const GORUNUM_ANAHTARI = "sinek-beyin-gorunum";

/** Testler varsayılan olarak 2B'de koşar: WebGL yazılımla çizildiğinden paralel koşumda ağırdır. */
async function gorunumSec(page: Page, view: "2d" | "3d") {
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key as string, value as string),
    [GORUNUM_ANAHTARI, view],
  );
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await gorunumSec(page, "2d");
  await page.goto("/");
});

test("mesaj gönderilir; yanıt, katmanlar ve beyin etkinliği görünür", async ({ page }) => {
  await input(page).fill("Sana bal getirdim");
  await input(page).press("Enter");

  const reply = page.locator("article.bubble--fly").last();
  await expect(reply.locator(".bubble__text")).toContainText("Şekere duyarlı tat nöronları");
  await reply.getByText("Bu yanıt nasıl üretildi?").click();
  await expect(reply.getByText("Şekere duyarlı tat nöronları · orta")).toBeVisible();

  const regions = page.getByRole("list", { name: "En etkin bölgeler" });
  await expect(regions.getByRole("listitem").first()).toContainText("Gnatal gangliyonlar");
  await expect(page.locator('[data-neuropil="GNG"]')).not.toHaveAttribute(
    "data-brightness",
    "0.000",
  );
});

test("kapsam dışı yanıtta örnek mesaj seçilip gönderilebilir", async ({ page }) => {
  await input(page).fill("kuru fasulye");
  await input(page).press("Enter");

  const example = page
    .locator("article.bubble--fly")
    .last()
    .getByRole("button", { name: "Sana biraz bal getirdim" });
  await example.click();
  await expect(input(page)).toHaveValue("Sana biraz bal getirdim");
  await page.getByRole("button", { name: "Gönder" }).click();
  await expect(page.locator("article.bubble--fly")).toHaveCount(2);
});

test("sekmeler klavyeyle gezilebilir", async ({ page }) => {
  await page.getByRole("tab", { name: "Sohbet" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Laboratuvar" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("tab", { name: "Laboratuvar" })).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("tab", { name: "Sohbet" })).toHaveAttribute("aria-selected", "true");
});

test("tema seçimi uygulanır ve yeniden yüklemede korunur", async ({ page }) => {
  await page.getByRole("combobox", { name: "Tema" }).selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("sayfa yatay kaydırma oluşturmaz", async ({ page }) => {
  await input(page).fill("Sana bal getirdim");
  await input(page).press("Enter");
  await expect(page.locator("article.bubble--fly")).toHaveCount(1);

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("hareket azaltma tercihinde animasyon yoktur", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await input(page).fill("Sana bal getirdim");
  await input(page).press("Enter");
  await expect(page.locator("article.bubble--fly")).toHaveCount(1);

  const durations = await page
    .locator('[data-neuropil="GNG"]')
    .evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(durations.split(",").every((d) => Number.parseFloat(d) === 0)).toBe(true);
});

test("beyin 3B olarak gösterilir, 2B'ye geçilebilir ve seçim korunur", async ({ page }) => {
  await gorunumSec(page, "3d");
  await page.goto("/");
  await expect(page.locator(".brain3d canvas")).toBeVisible();
  await expect(page.locator("svg [data-neuropil]").first()).toBeHidden();

  await page.getByRole("button", { name: "Görünüm: 2B" }).click();
  await expect(page.locator("svg [data-neuropil]").first()).toBeVisible();
  await expect(page.locator(".brain3d")).toHaveCount(0);

  // Seçim sonraki açılışlar için saklanır (başlangıç betiği yeniden yüklemede 3B'yi zorladığı
  // için depolanan değer doğrudan okunur).
  expect(await page.evaluate((key) => localStorage.getItem(key), GORUNUM_ANAHTARI)).toBe("2d");

  await page.getByRole("button", { name: "Görünüm: 3B" }).click();
  await expect(page.locator(".brain3d canvas")).toBeVisible();
});

test("3B görünüm sol tıkla döndürülür", async ({ page }) => {
  await gorunumSec(page, "3d");
  await page.goto("/");
  const alan = page.locator(".brain3d");
  await expect(alan.locator("canvas")).toBeVisible();
  const kutu = await alan.boundingBox();
  if (!kutu) throw new Error("3B alanı ölçülemedi");

  const once = await alan.screenshot();
  await page.mouse.move(kutu.x + kutu.width / 2, kutu.y + kutu.height / 2);
  await page.mouse.down();
  await page.mouse.move(kutu.x + kutu.width / 2 + 180, kutu.y + kutu.height / 2 + 60, {
    steps: 15,
  });
  await page.mouse.up();
  await page.waitForTimeout(800);

  expect(Buffer.compare(once, await alan.screenshot())).not.toBe(0);
});

test("laboratuvar sekmesinde deney çalıştırılır ve karşılaştırma gösterilir", async ({ page }) => {
  await page.getByRole("tab", { name: "Laboratuvar" }).click();

  await expect(page.getByRole("heading", { name: "Laboratuvar" })).toBeVisible();
  await expect(page.getByLabel("Hazır grup", { exact: true })).toHaveValue("sugar");

  await page.getByRole("button", { name: "Deneyi çalıştır" }).click();

  const tablo = page.getByRole("table");
  await expect(tablo).toBeVisible();
  await expect(tablo.getByRole("row").nth(1)).toContainText("88,3 Hz");
  await expect(page.getByText("Susturulan nöron: 1")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sinyal yolları" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Deney raporu" })).toBeVisible();
});
