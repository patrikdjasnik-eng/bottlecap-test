# 🐇 BottleCapAI — můj plán dokončení přijímacího questu

**Stav:** plán, ne tvrzení o hotovém trénování. **Datum:** 10. 10. 2026. **Větev:** `feat/reasoning-compression`.

[✅ Checklist](QUEST-ODEVZDANI-CHECKLIST.md) · [🔬 Experimenty](QUEST-EXPERIMENTALNI-PLAN.md) · [🧠 Hypotézy](HYPOTEZY-A-ZJISTENI.md) · [📔 DEV-NOTES](DEV-NOTES.md) · [📋 Původní zadání](../docs/UPSTREAM-README.md)

## 🎯 Co přesně chci splnit

Moje zadání od BottleCapAI: vyjít z **Qwen3-0.6B**, **změnit chování modelu** tak, aby generoval méně **celkových** tokenů (thinking + final), a zachovat pokud možno stejnou správnost. Thinking zůstane aktivní; prompt-only zkrácení není řešením. Nesáhnu na oficiální evaluační data při trénování a nebudu měnit metodiku hodnocení.

**Cíl odevzdání:** funkční upravený model nebo LoRA adapter; reprodukovatelný kód; poctivé výsledky z `evaluate.py`; srovnání `compare.py`, pokud mám kompatibilní baseline; stručné finální `IDEA.md` včetně negativních zjištění.

## ✅ Co už mám hotové

- [x] Funkční inference Qwen3-0.6B na GTX 1070 Ti; připnutá revize `c1899de289a04d12100db370d81485cdf75e47ca`.
- [x] RHAR 003–007: analýzy textu, opakovaných operací, checkpointů a zpětné tokenizace.
- [x] RHAR 008: ukládám skutečná generovaná tokenová ID; Canary 003 správně odpověděl 43, uložil 423 ID a ověřil roundtrip i SHA-256.
- [x] Poslední potvrzený lokální testovací běh: **227 testů, OK, skipped=2**.
- [x] Vlastní pracovní hypotéza RHAR / Correctness-Gated Reasoning Compression popsaná v `IDEA.md`.
- [ ] Nemám zatím natrénovaný RHAR adapter ani srovnávací oficiální výsledek.

## 🚦 Krátká kritická cesta

| Fáze | Výsledek, který potřebuji | Brána pro pokračování |
| --- | --- | --- |
| 0. Fixnout scope | Jedna první trénovací metoda; žádné další moduly před pilotem | Výslovně schválím data, algoritmus, GPU rozpočet |
| 1. RHAR 009 | Přesná analýza původních tokenových ID a checkpointu | Zelené testy, platné tokenové stopy |
| 2. Data | Povolený train/val split, bez překryvu se SVAMP/MBPP+/BFCL/IFEval | Původ, licence, revize, hash, audit úniků |
| 3. Pilot | Malý offline correctness-gated výběr správných kratších řešení | Audit výběru a záznam zamítnutých vzorků |
| 4. Training | První skutečný LoRA adapter Qwen3-0.6B | Ověřím načtení, průběh loss, integritu artefaktu |
| 5. Měření | Stejný prompt, seed/sampling a token cap pro base/adapter | Správnost + celkové tokeny, žádné cherry-picking |
| 6. Oficiální eval | `results.json` z předepsaného `evaluate.py`, případně `compare.py` | Stejná konfigurace pro oba modely |
| 7. Odevzdání | Bundle, `.safetensors`, results, `IDEA.md`, ZIP/link | Reprodukční a velikostní kontrola, schválení odeslání |

## ⏳ Realistické plánování

**Moje pracovní orientace:** do **1–2 týdnů intenzivní práce** zkusit získat prvního skutečně natrénovaného kandidáta a pilotní srovnání. Není to potvrzený termín od BottleCapAI ani garance výsledků. Plné hodnocení může vyžadovat další výpočetní zdroje.

Nechci strávit týdny dalším přidáváním parserů, pokud tím neposunu hlavní zadání: **model se musí opravdu změnit**.

## ⚙️ Hardware a rizika

Na GTX 1070 Ti (8 GB VRAM, Pascal) mi funguje malá diagnostická inference, neznamená to ale automaticky kompatibilitu s moderními trénovacími kernely ani vLLM. Oficiální test uvádí možnost Colab T4 16 GB pro opatrný LoRA trénink; pro plnou evaluaci doporučuje rychlejší Ampere+ GPU. Zatím žádný cloudový výpočet ani placený provoz nespouštím bez schválení.

Pokud nezvládnu úplnou oficiální evaluaci, BottleCapAI výslovně umožňuje odevzdat práci i s neúplným měřením. **Nikdy však nebudu prezentovat malé lokální canary jako oficiální benchmark.**

## 🧷 Zásady

**Bez zelené ani krok.** Zaznamenám přesné commity, datasety, configy, hashe a chyby. Každá změna parametrů evaluace by znehodnotila přímé srovnání. Neprohlašuji zatím žádnou úsporu tokenů, novou metodu ani zachovanou přesnost.

**Další konkrétní úkol:** dokončit pouze RHAR 009 / token trace audit, zkontrolovat datasetový pipeline a potom předložit ke schválení pilotní training config. Žádné váhy bez mého rozhodnutí.
