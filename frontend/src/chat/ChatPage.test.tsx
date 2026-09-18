import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatResponse, ScenariosResponse } from "../api/client";
import { outOfScopeResponse, sugarResponse } from "../test/fixtures";
import { ChatPage } from "./ChatPage";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const scenarios: ScenariosResponse = {
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
};

function mockApi(
  chat: (message: string) => Promise<Response>,
  scenarioOverride: typeof scenarios = scenarios,
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/scenarios") return json(scenarioOverride);
    if (url === "/api/chat") return chat(JSON.parse(String(init?.body)).message);
    throw new Error(`beklenmeyen istek ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("sohbet sayfası", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mesajı gönderir, yanıtı ve dört katmanı gösterir", async () => {
    const user = userEvent.setup();
    let resolve: (r: Response) => void = () => {};
    const fetchMock = mockApi(() => new Promise((r) => (resolve = r)));
    render(<ChatPage />);

    await user.type(screen.getByLabelText("Mesaj"), "Sana bal getirdim{Enter}");

    expect(screen.getByText("Sana bal getirdim")).toBeInTheDocument();
    expect(screen.getByText("Simülasyon sonucu alınıyor…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gönder" })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({ method: "POST" }),
    );

    resolve(json(sugarResponse()));

    const reply = await screen.findByText(/Şekere duyarlı tat nöronları \(120 Hz/, {
      selector: ".bubble__text",
    });
    const bubble = reply.closest("article") as HTMLElement;
    expect(within(bubble).getByText("Şablon metin")).toBeInTheDocument();

    await user.click(within(bubble).getByText("Bu yanıt nasıl üretildi?"));
    expect(within(bubble).getByText("1. Girdi eşleme")).toBeVisible();
    expect(within(bubble).getByText("Şekere duyarlı tat nöronları · orta")).toBeInTheDocument();
    expect(within(bubble).getByText(/120 Hz Poisson, 21 nöron/)).toBeInTheDocument();
    expect(within(bubble).getByText("beslenme (hortum uzatma)")).toBeInTheDocument();
    expect(within(bubble).getByText("%41")).toBeInTheDocument();
    expect(within(bubble).getByText("kalibrasyon yok")).toBeInTheDocument();

    const regions = screen.getByRole("list", { name: "En etkin bölgeler" });
    expect(within(regions).getAllByRole("listitem")[0]).toHaveTextContent("Gnatal gangliyonlar");
  });

  it("kapsam dışı mesajda nedeni ve örnekleri gösterir; örnek mesaj kutusuna yazılır", async () => {
    const user = userEvent.setup();
    mockApi(async () => json(outOfScopeResponse()));
    render(<ChatPage />);

    await user.type(screen.getByLabelText("Mesaj"), "kuru fasulye{Enter}");
    const hint = await screen.findByText("Sinek dil anlamaz; ona bir şey sunmayı deneyin:");
    const bubble = hint.closest("article") as HTMLElement;

    await user.click(within(bubble).getByRole("button", { name: "Sana biraz bal getirdim" }));
    expect(screen.getByLabelText("Mesaj")).toHaveValue("Sana biraz bal getirdim");
    expect(screen.getByLabelText("Mesaj")).toHaveFocus();

    await user.click(within(bubble).getByText("Bu yanıt nasıl üretildi?"));
    expect(
      within(bubble).getByText("Mesajda modelin tanıdığı bir duyusal uyarıcı bulunamadı."),
    ).toBeInTheDocument();
  });

  it("hatayı anlaşılır gösterir ve tekrar denemeye izin verir", async () => {
    const user = userEvent.setup();
    const responses: Array<() => Response> = [
      () => json({ detail: "FlyWire verisi bulunamadı. Önce: uv run sinek indir" }, 503),
      () => json(sugarResponse() satisfies ChatResponse),
    ];
    mockApi(async () => (responses.shift() as () => Response)());
    render(<ChatPage />);

    await user.type(screen.getByLabelText("Mesaj"), "bal{Enter}");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Yanıt alınamadı: FlyWire verisi bulunamadı");

    await user.click(within(alert).getByRole("button", { name: "Tekrar dene" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(
      await screen.findByText(/Şekere duyarlı tat nöronları \(120 Hz/, {
        selector: ".bubble__text",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("bal")).toHaveLength(1);
  });

  it("hazır paket kullanılamıyorsa uyarı gösterilir", async () => {
    mockApi(async () => json(sugarResponse()), {
      ...scenarios,
      package: { available: false, version: null, problem: "Manifest yok" },
    });
    render(<ChatPage />);

    const uyari = await screen.findByRole("status");
    expect(uyari).toHaveTextContent("Manifest yok");
    expect(uyari).toHaveTextContent("canlı simüle");
  });

  it("boş mesaj gönderilmez", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi(async () => json(sugarResponse()));
    render(<ChatPage />);

    await user.type(screen.getByLabelText("Mesaj"), "   {Enter}");

    expect(screen.getByRole("button", { name: "Gönder" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalledWith("/api/chat", expect.anything());
  });
});
