import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import references from "../assets/kaynakca.json";
import { ui } from "../i18n/text";
import { AboutPage, withCitations } from "./AboutPage";

describe("nasıl çalışıyor sayfası", () => {
  it("atıfları kaynakça bağlantısına çevirir", () => {
    render(<p>{withCitations("Model [3] ve veri [1], [2].")}</p>);

    expect(screen.getByRole("link", { name: "[3]" })).toHaveAttribute("href", "#kaynak-3");
    expect(screen.getAllByRole("link")).toHaveLength(3);
  });

  it("metindeki her atıfın kaynakçada karşılığı vardır", () => {
    const numbers = new Set(references.map((r) => r.number));
    const about = ui.about;
    const texts = [
      about.lead,
      ...about.sections.flatMap((s) => s.paragraphs),
      ...about.limitations,
      ...about.glossary.map(([, d]) => d ?? ""),
    ];
    for (const text of texts) {
      for (const [, n] of text.matchAll(/\[(\d+)\]/g))
        expect(numbers.has(Number(n)), text).toBe(true);
    }
  });

  it("sınırlılıkları, terimleri ve DOI bağlantılı kaynakçayı gösterir", () => {
    render(<AboutPage />);

    expect(screen.getByRole("heading", { name: "Sınırlılıklar" })).toBeInTheDocument();
    expect(screen.getByText("Konektom")).toBeInTheDocument();
    const shiu = document.getElementById("kaynak-3");
    expect(shiu).toHaveTextContent("Shiu, P. K.");
    expect(shiu?.querySelector("a")).toHaveAttribute(
      "href",
      "https://doi.org/10.1038/s41586-024-07763-9",
    );
  });
});
