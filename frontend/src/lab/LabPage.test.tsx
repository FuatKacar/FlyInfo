import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  experimentReport,
  experimentResult,
  job,
  labOptions,
  pathwayResponse,
} from "../test/fixtures";
import { LabPage } from "./LabPage";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface Yanitlar {
  run?: Response;
  jobs?: Response[];
  pathways?: Response;
  report?: Response;
  replay?: Response;
}

function mockApi(yanitlar: Yanitlar = {}) {
  const jobs = [...(yanitlar.jobs ?? [])];
  const cagrilar: string[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    cagrilar.push(url);
    if (url === "/api/lab/options") return json(labOptions());
    if (url === "/api/lab/examples")
      return json([{ name: "seker-yolu-susturma", title_tr: "Şeker yolunda susturma (şekil 1F)" }]);
    if (url === "/api/lab/examples/seker-yolu-susturma") return json(experimentReport());
    if (url.startsWith("/api/neurons/search"))
      return json([{ cell_type: "CB0701", neuron_count: 2 }]);
    if (url === "/api/lab/run")
      return yanitlar.run ?? json(job({ state: "running", progress: 0.2 }), 202);
    if (url === "/api/lab/pathways")
      return yanitlar.pathways ?? json(job({ kind: "pathways", state: "running" }), 202);
    if (url === "/api/lab/report")
      return yanitlar.report ?? json(job({ kind: "report", state: "running" }), 202);
    if (url === "/api/lab/replay")
      return yanitlar.replay ?? json(job({ kind: "replay", state: "running" }), 202);
    if (url.startsWith("/api/lab/jobs/")) return jobs.shift() ?? json(job());
    throw new Error(`beklenmeyen istek: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, cagrilar };
}

describe("laboratuvar ekranı", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("seçenekleri yükler ve varsayılan uyarımı gösterir", async () => {
    mockApi();
    render(<LabPage />);

    const secim = await screen.findByLabelText("Hazır grup");
    expect(secim).toHaveDisplayValue("Şekere duyarlı tat nöronları (21 nöron)");
    expect(screen.getByLabelText("Frekans (Hz)")).toHaveValue(200);
    expect(screen.getByLabelText("Deneme sayısı")).toHaveValue(30);
  });

  it("deneyi çalıştırır ve karşılaştırma tablosunu gösterir", async () => {
    const user = userEvent.setup();
    const { cagrilar } = mockApi({
      jobs: [json(job({ state: "done", experiment: experimentResult() }))],
    });
    render(<LabPage />);

    await user.click(await screen.findByRole("button", { name: "Deneyi çalıştır" }));

    const tablo = await screen.findByRole("table");
    const satir = within(tablo).getAllByRole("row")[1] as HTMLElement;
    expect(within(satir).getByText("88,3 Hz")).toBeInTheDocument();
    expect(within(satir).getByText("12,1 Hz")).toBeInTheDocument();
    expect(within(satir).getByText(/-76,2 Hz/)).toBeInTheDocument();
    expect(within(satir).getByText("anlamlı")).toBeInTheDocument();
    expect(cagrilar).toContain("/api/lab/run");
    expect(screen.getByText(/Susturulan nöron: 1/)).toBeInTheDocument();
  });

  it("hata durumunda kullanıcıya bildirir", async () => {
    const user = userEvent.setup();
    mockApi({ jobs: [json(job({ state: "error", error_tr: "Bilinmeyen nöron grubu: yok" }))] });
    render(<LabPage />);

    await user.click(await screen.findByRole("button", { name: "Deneyi çalıştır" }));

    const uyari = await screen.findByRole("alert");
    expect(uyari).toHaveTextContent("Bilinmeyen nöron grubu");
  });

  it("sinyal yollarını sınırlılık notuyla gösterir", async () => {
    const user = userEvent.setup();
    mockApi({
      jobs: [
        json(job({ state: "done", experiment: experimentResult() })),
        json(job({ kind: "pathways", state: "done", pathways: pathwayResponse() })),
      ],
    });
    render(<LabPage />);
    await user.click(await screen.findByRole("button", { name: "Deneyi çalıştır" }));
    await screen.findByRole("table");

    await user.click(screen.getByRole("button", { name: "Yolları bul" }));

    expect(await screen.findByText(/Hedef nöron: 2000/)).toBeInTheDocument();
    expect(screen.getByText("LB3")).toBeInTheDocument();
    expect(screen.getByText("CB0701")).toHaveAttribute("title", "FlyWire 2000");
    expect(screen.getByText(/nedensellik kanıtı değildir/)).toBeInTheDocument();
  });

  it("raporu indirir", async () => {
    const user = userEvent.setup();
    mockApi({
      jobs: [
        json(job({ state: "done", experiment: experimentResult() })),
        json(job({ kind: "report", state: "done", report: experimentReport() })),
      ],
    });
    const createUrl = vi.fn(() => "blob:sahte");
    vi.stubGlobal("URL", { ...URL, createObjectURL: createUrl, revokeObjectURL: vi.fn() });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<LabPage />);
    await user.click(await screen.findByRole("button", { name: "Deneyi çalıştır" }));
    await screen.findByRole("table");

    await user.click(screen.getByRole("button", { name: "Raporu indir" }));

    await waitFor(() => expect(click).toHaveBeenCalled());
    expect(createUrl).toHaveBeenCalled();
    click.mockRestore();
  });

  it("örnek deney açılınca kayıtlı sonuç ve ayarlar gösterilir", async () => {
    const user = userEvent.setup();
    const { cagrilar } = mockApi();
    render(<LabPage />);

    await user.click(
      await screen.findByRole("button", { name: "Şeker yolunda susturma (şekil 1F)" }),
    );

    expect(await screen.findByText(/Kayıtlı örnek rapor gösteriliyor/)).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByLabelText("Frekans (Hz)")).toHaveValue(200);
    expect(cagrilar).not.toContain("/api/lab/run"); // simülasyon koşulmadı
  });

  it("susturma seçimi eklenip kaldırılabilir", async () => {
    const user = userEvent.setup();
    mockApi();
    render(<LabPage />);
    await screen.findByLabelText("Hazır grup");

    const ekle = screen.getAllByRole("button", { name: "Ekle" })[1] as HTMLElement;
    await user.click(ekle);
    expect(screen.getAllByLabelText("Seçim türü")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: "Kaldır" }));
    expect(screen.getAllByLabelText("Seçim türü")).toHaveLength(1);
  });
});
