# 🔬 BottleCapAI — můj experimentální plán od prvního LoRA po porovnání

**Stav:** připravený návrh experimentu; skutečný trénink čeká na moje schválení.

[🗺️ Roadmapa](QUEST-DOKONCENI-PLAN.md) · [✅ Odevzdání](QUEST-ODEVZDANI-CHECKLIST.md) · [🧬 RHAR v0.1](RHAR-V01-PLAN.md)

## Hypotéza

Zkoumám, zda výběr **správných a dostatečně úplných kratších reasoning traces** pro supervised fine-tuning změní Qwen3-0.6B tak, aby při nezměněné evaluaci používal méně **celkových generovaných tokenů**, ale neztrácel správnost.

Pouhý shortest-correct výběr znám jako baseline nápad, nikoli prokázaně novou metodu. RPS, RPD a TPC prozatím nechávám jako budoucí výzkumné moduly, ne povinnou podmínku přijetí.

## 0 — Kontrolní data

- **Výchozí model:** `Qwen/Qwen3-0.6B`, revize `c1899de289a04d12100db370d81485cdf75e47ca`.
- **Think:** zapnutý, obě varianty mají stejný sampling, seed, prompt a max token cap.
- **Metriky:** správné odpovědi / všechny odpovědi, mean total tokens včetně final, tok/s, truncation, domain regression; pro finální porovnání 95% intervaly z `compare.py`.
- **Audit:** každá generace uloží původní token IDs, seed, split status, hash dat a modelovou revizi.

## 1 — Trénovací a validační otázky

Použiju výhradně přípustná zdrojová data, například oficiálně navržená **GSM8K**, **CommonsenseQA**, **ARC Easy** či **Skywork-OR1**. První pilot může mít řádově desítky trénovacích úloh a menší oddělenou validaci; rozsah stanovím po schválení rozpočtu.

- Zafixuju verze, licence, hash, identitu a train/val split **před generováním**.
- Provedu kontrolu překryvů/deduplikaci s chráněnými eval otázkami.
- **Nikdy netrénuju** na SVAMP, MBPP+, BFCL ani IFEval.
- Uchovám původní surová data, odmítnuté vzorky a důvody odmítnutí.

## 2 — Generate → grade → select

1. Pro jednu povolenou train otázku vytvořím více generací se zapnutým thinking.
2. Správnost posoudím pouze proti nezávislému gold answer nebo ověřitelnému testu; žádný self-approval.
3. Vyřadím useknuté, nesprávné, neparsovatelné nebo chybně rozdělené stopy.
4. Ze zbývajících porovnám **celkové tokeny**, nikoli pouze délku thinking textu.
5. Zkontroluju, že zvolené stopy zachovávají podstatné výpočty. Když nelze potvrdit správný a úplný vzorek, vynechám úlohu.
6. Zapíšu výběrové důvody, počty kandidátů, poměr přijatých a případnou selekční bias.

## 3 — První modelový zásah: LoRA SFT

Po samostatném odsouhlasení zkusím supervised fine-tuning na vybraných povolených příkladech. Loss budu počítat na generované části, nikoli na promptu; thinking nezakážu. Budu kontrolovat kompatibilitu Transformers/vLLM, checkpointy, paměť, spotřebu a NaN/Inf.

Ověřím, že výstupem je skutečný LoRA adapter v `.safetensors`, který mění chování modelu. Není dovoleno vydat pouze prompt, GGUF konverzi, offline parser nebo truncation za splnění zadání.

## 4 — Lokální pilotní hodnocení

Porovnám stejný počet vzorků nezměněného modelu a LoRA kandidáta **na oddělených validačních otázkách**. Uvedu nejen průměr tokenů, ale i počty správných odpovědí, useknuté generace, procento změny délky a chyby po doménách.

**Go:** kandidát generuje méně celkových tokenů, zachovává prakticky srovnatelnou správnost a nejde o náhodný výsledek jednoho příkladu.

**No-go:** kandidát pouze ztrácí thinking, odpovídá dřív a častěji špatně; nezlepšuje tokeny, nebo metadata neumožňují férové srovnání. Negativní výsledek zaznamenám a vyhodnotím, co změnit.

## 5 — Oficiální BottleCapAI benchmark

| Benchmark | Otázek |
| --- | ---: |
| SVAMP | 1 000 |
| MBPP+ | 378 |
| BFCL | 840 |
| IFEval | 541 |
| **Celkem** | **2 759** |

Plný protokol má **8 vzorků na otázku = 22 072 odpovědí na jeden model**. Oficiální nástroje a parametry neměním.

`python utils/eval/benchmarks.py` → `python evaluate.py --out runs/base` → `python evaluate.py --out runs/mine --adapter ./my-lora` → `python compare.py runs/base runs/mine`.

Nejdřív mohu na podporovaném hardwaru použít `--smoke`, který ale **nevytváří oficiální skóre**. Pokud je plný běh nemožný, doložím rozsah a omezení; upstream umožňuje i neúplné odevzdání.

## 6 — Interpretace bez přehánění

**Nehodnotím jen rychlost:** hlavní metrika je celkový počet tokenů při zachované správnosti. Délka za checkpointem RHAR 007 sama není úspora. Když zkrátím text bez změny vah, nesplnil jsem účel soutěže.

Dokumentuji všechny meziverze a můžu předat více checkpointů, pokud ukazují vztah délky a přesnosti.

## 7 — Můj stop/go checklist

- [ ] Zelený CI i lokální testy.
- [ ] Přesně vymezená data, licence, nepřekrývající se evaluace.
- [ ] Schválený výpočetní rozpočet a hyperparametry.
- [ ] Dokončený pilotní training run.
- [ ] Načitatelný LoRA adapter, tokenové stopy a kontrola integrity.
- [ ] Férová baseline/adapter validace.
- [ ] Schválená oficiální evaluace nebo zdokumentované limity.


### 2026-10-10 — 🐇 RHAR Pilot 001: tři skutečné generace na GSM8K

**Provedeno a doloženo lokálními výstupy:** po 241 zelených testech (`OK (skipped=2)`) jsem spustil schválený GPU pilot `--execute --pilot-3 --confirm-gpu-3` na jedné otázce `gsm8k-train-06982`, se třemi seedy, do `runs/rhar-pilot-001/`. CPU dry-run předtím ověřil kompletní vstupní plán 12 otázek / 36 pokusů; audit překryvu hlásil `potential_match_count=0`, ale zůstává `review_only`, `overlap_audit_exhaustive=false`, `training_approved=false`.

| Seed | Správná odpověď | Celkové tokeny | Reasoning tokeny | Dokončeno |
| --- | --- | ---: | ---: | --- |
| 9001 | Ne, generace useknutá | 512 | Neurčeno | Ne |
| 9002 | Ano | 433 | 425 | Ano |
| 9003 | Ano | 374 | 366 | Ano |

**Souhrn:** 3 generování, 2 správné a dokončené, 1 truncation na limitu 512; průměr 439,667 celkových tokenů a 76,854 s na generaci. U dokončených výstupů bylo průměrně 395,5 reasoning tokenů a 8 final tokenů.

**Moje zjištění:** mezi dvěma správnými řešeními stejné otázky je rozdíl **59 tokenů**, tedy **13,63 % vůči delšímu správnému běhu (433 tokenů)**. Jde o přirozenou variabilitu samplingů původního Qwenu, **nikoliv naměřenou úsporu způsobenou RHAR**. Jedna otázka a dvě správné odpovědi nestačí k hodnocení generalizace ani kvality trénovaného modelu.

**Co zatím není hotové:** úplný ruční audit reasoning trace 9003, kompatibilní převod polí z `safe_start_generate.py` (`generated_text`, `total_generated_tokens`, `reasoning_split_status`, `gold_answer`) pro `training_candidates.py` (`full_generated_text`, `total_tokens`, `split_status`, `prompt`), větší různorodý trénovací soubor, LoRA běh a baseline/candidate porovnání. Formát záznamů nesmím pouze domýšlet; je třeba ho otestovat proti skutečnému artefaktu. Žádné trénování ani oficiální benchmark neproběhlo.

**Další rozhodnutí:** nejdřív ověřit úplnost kandidáta 9003, bezpečně sjednotit datový formát a otestovat selektor. Až po dostatečném rozšíření povolených dat schválit konkrétní trénovací běh.

