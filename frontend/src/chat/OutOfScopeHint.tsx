import type { ChatResponse } from "../api/client";

interface Props {
  hint: NonNullable<ChatResponse["hint"]>;
  onPick: (example: string) => void;
}

/** Kapsam dışı mesajlarda yönlendirme. Simülasyonun parçası değildir (tr.json metni). */
export function OutOfScopeHint({ hint, onPick }: Props) {
  return (
    <div className="hint-box">
      <p>{hint.title}</p>
      <ExampleChips examples={hint.examples} onPick={onPick} />
    </div>
  );
}

export function ExampleChips({
  examples,
  onPick,
}: {
  examples: readonly string[];
  onPick: (example: string) => void;
}) {
  return (
    <ul className="chips">
      {examples.map((example) => (
        <li key={example}>
          <button type="button" className="chip chip--button" onClick={() => onPick(example)}>
            {example}
          </button>
        </li>
      ))}
    </ul>
  );
}
