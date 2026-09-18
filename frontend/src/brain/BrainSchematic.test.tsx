import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import schematic from "../assets/beyin-semasi.json";
import { sugarResponse } from "../test/fixtures";
import { BrainSchematic } from "./BrainSchematic";

describe("beyin şeması", () => {
  it("etkinlik yokken tüm bölgeleri sönük çizer ve açıklama gösterir", () => {
    const { container } = render(<BrainSchematic activity={null} activeReadouts={new Set()} />);

    const regions = container.querySelectorAll("[data-neuropil]");
    expect(regions).toHaveLength(schematic.neuropils.length);
    for (const region of regions) expect((region as SVGElement).dataset.brightness).toBe("0.000");
    expect(screen.getAllByText(/Mesaj gönderildiğinde/).length).toBeGreaterThan(0);
  });

  it("parlaklığı hıza göre verir ve en etkin bölgeleri metin olarak listeler", () => {
    const { container } = render(
      <BrainSchematic activity={sugarResponse().brain} activeReadouts={new Set(["mn9"])} />,
    );

    const gng = container.querySelector('[data-neuropil="GNG"]') as SVGElement;
    const al = container.querySelector('[data-neuropil="AL_R"]') as SVGElement;
    expect(Number(gng.dataset.brightness)).toBeCloseTo(
      Math.log10(1 + 5.8 / 0.5) / Math.log10(401),
      3,
    );
    expect(Number(al.dataset.brightness)).toBe(0);

    const list = screen.getByRole("list", { name: "En etkin bölgeler" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual(["Gnatal gangliyonlar5,8 Hz", "Pruva4,4 Hz"]);
  });

  it("etkin davranış nöronlarını vurgular", () => {
    const { container } = render(
      <BrainSchematic activity={sugarResponse().brain} activeReadouts={new Set(["mn9"])} />,
    );

    const active = container.querySelectorAll(".readout--active");
    const mn9 = schematic.readouts.find((r) => r.group === "mn9");
    expect(active).toHaveLength(mn9?.neurons.length ?? -1);
  });

  it("sineğin sağının ekranın solunda olduğunu yazar", () => {
    render(<BrainSchematic activity={null} activeReadouts={new Set()} />);

    expect(screen.getByText("Sineğin sağı")).toBeInTheDocument();
    expect(screen.getByText("Sineğin solu")).toBeInTheDocument();
  });
});
