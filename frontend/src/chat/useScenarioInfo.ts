import { useEffect, useState } from "react";
import { getScenarios } from "../api/client";

export interface ScenarioInfo {
  /** Uyarım grubu anahtarı → Türkçe ad (tek kaynak: neuron_groups.toml). */
  names: Record<string, string>;
  /** Hazır senaryo paketi kullanılamıyorsa nedeni; bu durumda her mesaj canlı simüle edilir. */
  packageProblem: string | null;
}

export function useScenarioInfo(): ScenarioInfo {
  const [info, setInfo] = useState<ScenarioInfo>({ names: {}, packageProblem: null });
  useEffect(() => {
    const controller = new AbortController();
    getScenarios(controller.signal)
      .then((data) =>
        setInfo({
          names: Object.fromEntries(data.groups.map((g) => [g.key, g.name_tr])),
          packageProblem: data.package.available
            ? null
            : (data.package.problem ?? "bilinmeyen neden"),
        }),
      )
      .catch(() => {
        // bilgi alınamazsa adlar anahtar olarak gösterilir; sohbet hatası ayrıca raporlanır
      });
    return () => controller.abort();
  }, []);
  return info;
}
