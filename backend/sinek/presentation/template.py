"""Şablon tabanlı Türkçe yanıt: LLM yokken veya LLM çıktısı reddedildiğinde kullanılır.

Deterministiktir; yalnızca `DecoderOutput` içindeki bilgiyi, tarafsız üçüncü şahıs anlatımla verir.
"""

from sinek.decoder.schema import DecoderOutput
from sinek.presentation.locale import format_number, join_tr, lower_first_tr, texts

MAX_NEUROPILS = 3


def render_template(output: DecoderOutput) -> str:
    t = texts()["template"]
    sentences = []

    components = output.stimulus.components
    if components:
        items = [
            t["stimulus_component"].format(
                name=c.name_tr if position == 0 else lower_first_tr(c.name_tr),
                rate=format_number(c.rate_hz, 0),
                count=c.neuron_count,
            )
            for position, c in enumerate(components)
        ]
        sentences.append(t["stimulus"].format(items=join_tr(items)))
    else:
        sentences.append(t["no_stimulus"])

    if components:
        active = output.active_behaviors
        if active:
            items = [
                (t["behavior_item"] if b.score is not None else t["behavior_item_unscored"]).format(
                    behavior=texts()["behaviors"][b.behavior.value],
                    score=format_number(100 * b.score, 0) if b.score is not None else "",
                    neuron=texts()["readout_neurons"][b.readout_group],
                    rate=format_number(b.rate_hz, 1),
                )
                for b in active
            ]
            sentences.append(t["behaviors_active"].format(items=join_tr(items)))
        else:
            sentences.append(t["behaviors_none"])
        if output.circuit_only:
            sentences.append(t["circuit_only"])

        top = output.top_neuropils[:MAX_NEUROPILS]
        if top:
            items = [
                t["neuropil_item"].format(name=n.neuropil, share=format_number(100 * n.share, 0))
                for n in top
            ]
            sentences.append(t["neuropils"].format(items=join_tr(items)))

    return " ".join(sentences)
