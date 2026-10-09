# 🔬 Diagnostika reasoning procesu — Qwen3-0.6B

[🇨🇿 Čeština](REASONING-DIAGNOSTIC.md) · [🇬🇧 English](../docs/REASONING-DIAGNOSTIC.en.md)

## Cíl

**Pouze pozorovat** původní model Qwen3-0.6B: oddělit reasoning a finální odpověď, zaznamenat správnost, čas, tokeny, opakování a paměť GPU. Nejde o trénování, vylepšení modelu ani o oficiální benchmark BottleCap AI.

## Pravidla BottleCap AI

- Uvažování je **zapnuté** (`enable_thinking=True`).
- Prompt specifikuje pouze formát výsledku (`Final answer: ...`) — **nevyžaduje kratší úvahu**.
- Skript nemění váhy, nevytváří adaptér a neupravuje oficiální `evaluate.py`, `compare.py` ani nastavení evaluace.
- Použité otázky jsou ručně vytvořené příklady (matematika, logika, porozumění kódu), **ne** otázky ze SVAMP, BFCL, MBPP+ ani IFEval.
- Budoucí algoritmus pro kompresi reasoning procesu **si předem výslovně odsouhlasím**.

## Spuštění ve WSL2 / Kali

V projektu se zapnutou `.venv` (PyTorch a Transformers již připravené):

~~~bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate

# 1. Rychlé CPU testy (bez modelu a bez internetu)
python -m unittest tests.test_reasoning_probe -v

# 2. Ukázat parametry a otázky (bez stahování modelu)
python -m diagnostics.reasoning_probe --dry-run

# 3. První skutečné měření (jedna otázka, jedno generování)
python -m diagnostics.reasoning_probe --limit 1

# 4. Po schválení dalších měření: 3 kategorie, 2 vzorky
python -m diagnostics.reasoning_probe --limit 3 --samples 2
~~~

Výchozí běh: 3 otázky × 1 generování, limit 512 nových tokenů; seed 9001, temperature 0.6, top-p 0.95, top-k 20, `float16` při CUDA. Používá přesně zafixovanou revizi základního modelu podle oficiálního `evaluate.py`.

## Výstup

V `runs/diagnostics/<UTC čas>/` vzniknou:

- `config.json` — model, revize, parametry, zařízení a počet vzorků.
- `records.jsonl` — jednotlivé odpovědi, délka reasoning i finální části, časy, správnost, opakování a údaj o paměti PyTorch.
- `summary.json` — souhrnné **průzkumné** hodnoty.

Složka `runs/` je ignorována Gitem: surové výstupy modelu (včetně uvažování) se automaticky **nepublikují**.

## Interpretace

- `total_tokens`: všechny generované tokeny.
- `reasoning_tokens`: úsek uvažování včetně oddělovacích tokenů; `final_tokens`: finální úsek včetně případného EOS. Součet odpovídá `total_tokens`, **pokud se podaří rozdělení**.
- `split_status`: u chybějících nebo rozbitých značek se počty reasoning/final zapisují jako `null`, nikoli jako vymyšlená nula.
- `truncated`: generování neukončilo standardním koncovým tokenem; taková odpověď je hodnocena jako nesprávná.
- `repeated_reasoning_fourgrams`: velmi hrubý indikátor opakování čtyř slov, **nikoli** ukazatel kvality reasoning procesu.
- `pytorch_allocated_gib` a `pytorch_peak_allocated_gib`: pouze alokace sledované PyTorchem, ne celkové obsazení VRAM.
- `exploratory_accuracy`: podíl správných odpovědí pouze v těchto diagnostických úlohách. **Není to oficiální přesnost BottleCap AI.**

## Kontrolovaná oprava formátu (2026-10-09)

Po diagnostickém běhu Experimentu 002 jsme zjistili, že prompt obsahoval doslovný příklad `Final answer: 42`, přestože správná odpověď byla `43`. Model odpověděl `42`; příčinná souvislost s ukázkou **není prokázaná**.

**Schválil jsem** odstranění zavádějícího příkladu z `diagnostics/reasoning_probe.py`. Diagnostika nyní instruuje pouze: `On the last line, write 'Final answer:' followed by your answer.` Neobsahuje vzorové číslo ani možnost výběru a **nevyžaduje kratší uvažování**.

- Ostatní parametry, `enable_thinking=True`, otázky i vyhodnocení zůstávají beze změn.
- Nový regresní test v `tests/test_reasoning_probe.py` kontroluje přesnou neutrální instrukci pro všechny diagnostické otázky, bez prozrazení očekávané odpovědi.
- **Ověření před commitem:** jedna cílená izolovaná zkouška nové funkce sadu předem známých příkladů prošla. Kompletní projektové testy po změně **čekají na spuštění v Kali**; nový GPU běh také ještě nebyl proveden.
- Experiment 002 se **nepřepisuje**. Výstup `42` je historicky správně zaznamenán jako nesprávná odpověď; po opravě se zakládá nový běh s novým identifikátorem.

## Stav

- [x] Jednotkové testy diagnostiky: **9/9** úspěšných v lokálním CPU testovacím prostředí.
- [x] Režim `--dry-run` lokálně ověřen.
- [x] První GPU diagnostika: **Experiment 002** dokončen (1 odpověď, nesprávné číslo 42, 325 tokenů).
- [x] Neutrální diagnostický prompt po schválení opraven; regresní test přidán.
- [ ] Spuštění aktualizovaných jednotkových testů na Kali a následný **nový kontrolní GPU běh**.
- [ ] Rozhodnutí o dalších experimentech: **čeká na moje rozhodnutí**.

Poznámky a výsledky ukládáme také do [vývojového deníku](DEV-NOTES.md).
