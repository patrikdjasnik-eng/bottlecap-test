# 🐇 RHAR Safe Start — CPU výběr prvních 12 otázek

[🇬🇧 English](../docs/SAFE-START-DATA.en.md) · [Safe Start plán](SAFE-START.md) · [DEV-NOTES](DEV-NOTES.md)

**Rozhodnutí (10. 10. 2026):** schválil jsem pouze stažení `GSM8K main/train` a přípravu 12 úloh na CPU. **Neodsouhlasil jsem žádné generování, GPU, LoRA ani trénování.**

## Přesný zdroj a kontrola integrity

- Zdroj: [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) / konfigurace `main` / split `train`.
- Zafixovaná revize datasetu: `740312add88f781978c0658806c59bc2815b9866`.
- Jediný stahovaný soubor: `main/train-00000-of-00001.parquet` (přibližně 2,31 MB).
- Očekávané SHA-256 celé stažené Parquet přílohy: `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`.
- Skript `diagnostics/safe_start_data.py` odmítne poškozený či změněný soubor; nevyžaduje GPU. **Sadu `test` nestahuji.**
- Knihovna `pyarrow` je **přímá závislost** čtečky Parquet; po prvním skutečném pokusu chyběla v mé `.venv`. Doplnil jsem `pyarrow==16.1.0` do `requirements.txt`. V Kali ji lze doinstalovat cíleně přes `uv pip install --python .venv/bin/python pyarrow` (bez instalace celého CUDA/vLLM balíku). Stahovací skript ověří již uložený Parquet a nemusí ho znovu přenášet.

## Jak vyberu 12 úloh

1. Z již staženého `main/train` čtu jen otázku a odpověď. U správné odpovědi vezmu pouze číslo za `####`; **referenční postup uvažování nepřidávám do modelového promptu**.
2. Odmítnu prázdné nebo nečíselné odpovědi, příliš krátké otázky a případný únik příkladu `Final answer:` do původní otázky.
3. Pořadí fixuji pomocí SHA-256 **konstantní soli a normalizovaného textu otázky**. Zvlášť nevybírám jednodušší úlohy ani takové, které už Qwen vyřešil.
4. Odmítnu přesné a nápadně podobné otázky v rámci výběru. Pokud mám lokálně `questions/questions.jsonl` z původní evaluační přípravy, zkusím také **pouze čtecí porovnání** proti jeho uživatelským promptům. Nečtu jeho gold answers, neměním oficiální evaluaci a nestahuji eval sady.
5. Výsledných **12 kandidátů** ověřím stávajícím `safe_start_plan.py`, který pro ně připraví **36 plánovaných** samplingů. Žádné generování ale nespustím.

**Důležité omezení:** normalizace a porovnávání podobnosti **nedokazují**, že žádná úloha není parafrází z oficiálních SVAMP/MBPP+/BFCL/IFEval. Pokud neexistuje místní eval korpus, report výslovně uvede `pending_local_eval_corpus`. I když existuje, status zůstane `local_partial_only` a `overlap_audit_exhaustive=false`. Kandidáty tedy **neschvaluji do trénování automaticky**.

## Ověření a spuštění v Kali

Nejdřív testy, které nic nestahují:

```bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate
python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan tests.test_safe_start_data -v
python -c "import pyarrow.parquet; print('pyarrow OK')"
```

**Teprve po zelených testech** spustím schválené stažení:

```bash
python -m diagnostics.safe_start_data --download
python -m diagnostics.safe_start_plan --dry-run --questions data/safe-start/questions.jsonl
```

Skript ukládá pouze do Git ignorovaného `data/safe-start/`:

| Soubor | Obsah |
| --- | --- |
| `raw/gsm8k-train.parquet` | Jen train; ověřený SHA-256 |
| `questions.jsonl` | 12 úloh, stabilní ID, gold answer, zafixovaná revize |
| `selection-report.json` | Důvody, rozsah kontroly překryvu, hashe, `review_only`, `training_approved=false`, `gpu_used=false` |

Existující výstup se **nepřepíše**; opakované spuštění bez předchozího vyřešení výsledků se zastaví. **Nedávat raw data ani gold answers veřejně do repozitáře.**

## Stav ověření

- **Provedeno:** 16/16 nových CPU unit testů stahovacího/výběrového modulu + dosavadních 15 testů plánovače, dohromady **31/31 OK v izolovaném prostředí**. Stažení bylo v testech simulováno, včetně správného a nesprávného SHA-256.
- **Kompletní sada nyní ověřena na Kali:** **61/61 OK za 0,600 s** (`Ran 61 tests in 0.600s`, `OK`). Předchozí běhy 45/45 a 16/16 zůstávají doloženou historií.
- **Nově potvrzeno na Kali:** 16/16 testů nového modulu za 0,512 s; ověřená cache GSM8K main/train s SHA-256 `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`; **7473 načtených train řádků, 12 skutečně vybraných ID, 36 validovaných plánovaných pokusů**. Přesné identifikátory jsou v `selection-report.json` a CZ/EN DEV-NOTES.
- **Stále chybí:** `questions/questions.jsonl` neexistuje (`Eval otázky chybí`), takže nebyla provedena kontrola překryvu s oficiálními evaluačními otázkami (`pending_local_eval_corpus`; `local_eval_audit_performed=false`). GPU generování, LoRA a měření úspor nejsou schválené ani provedené. Dataset je stále `review_only`.

Na projektu spolupracuji s **ChatGPT (OpenAI, GPT-6)** a vlastní agentkou **Mášou**; všechny výsledky uvádím jen tehdy, když jsou doložené.
