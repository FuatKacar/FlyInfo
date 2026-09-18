import { Fragment, type ReactNode } from "react";
import references from "../assets/kaynakca.json";
import { ui } from "../i18n/text";

const about = ui.about;

/** Metindeki [n] atıflarını kaynakça bağlantısına çevirir. */
export function withCitations(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let offset = 0; // parçanın metindeki konumu: kararlı ve benzersiz anahtar
  for (const part of text.split(/(\[\d+\])/g)) {
    const match = /^\[(\d+)\]$/.exec(part);
    nodes.push(
      match ? (
        <a key={offset} href={`#kaynak-${match[1]}`} className="citation">
          {part}
        </a>
      ) : (
        <Fragment key={offset}>{part}</Fragment>
      ),
    );
    offset += part.length;
  }
  return nodes;
}

export function AboutPage() {
  return (
    <article className="about">
      <h2>{about.title}</h2>
      <p className="about__lead">{about.lead}</p>

      {about.sections.map((section) => (
        <section key={section.id} aria-labelledby={`bolum-${section.id}`}>
          <h3 id={`bolum-${section.id}`}>{section.title}</h3>
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph}>{withCitations(paragraph)}</p>
          ))}
        </section>
      ))}

      <section aria-labelledby="bolum-sinirliliklar">
        <h3 id="bolum-sinirliliklar">{about.limitations_title}</h3>
        <ul>
          {about.limitations.map((item) => (
            <li key={item}>{withCitations(item)}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="bolum-terimler">
        <h3 id="bolum-terimler">{about.glossary_title}</h3>
        <dl className="glossary">
          {about.glossary.map(([term, definition]) => (
            <div key={term}>
              <dt>{term}</dt>
              <dd>{withCitations(definition ?? "")}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="bolum-kaynakca">
        <h3 id="bolum-kaynakca">{about.references_title}</h3>
        <ol className="references">
          {references.map((r) => (
            <li key={r.key} id={`kaynak-${r.number}`} value={r.number}>
              {r.authors} ({r.year}). {r.title}. <em>{r.journal}</em>
              {r.volume ? `, ${r.volume}` : ""}
              {r.issue ? `(${r.issue})` : ""}
              {r.pages ? `, ${r.pages}` : ""}.{" "}
              <a href={`https://doi.org/${r.doi}`} target="_blank" rel="noreferrer">
                doi:{r.doi}
              </a>
            </li>
          ))}
        </ol>
      </section>
    </article>
  );
}
