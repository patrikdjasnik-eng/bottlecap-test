# 🐇 RHAR Safe Start — CPU výběr prvních 12 otázek

[🇬🇧 English](../docs/SAFE-START-DATA.en.md) · [Safe Start plán](SAFE-START.md) · [DEV-NOTES](DEV-NOTES.md)

**Rozhodnutí (10. 10. 2026):** schválil jsem pouze stažení `GSM8K main/train` a přípravu 12 úloh na CPU. **Neodsouhlasil jsem žádné generování, GPU, LoRA ani trénování.**

## Přesný zdroj a kontrola integrity

- Zdroj: [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) / konfigurace `main` / split `train`.
- Zafixovaná revize datasetu: `740312add88f781978c0658806c59bc2815b9866`.
- Jediný stahovaný soubor: `main/train-00000-of-00001.parquet` (přibližně 2,31 MB).
- Očekávané SHA-256 celé stažené Parquet přílohy: `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`.
- Skript `diagnostics/safe_start_data.py` odmítne poškozený či změněný soubor; nevyžaduje GPU. **Sadu `test` nestahuji.**
- Knihovna `pyarrow` čte lokální Parquet; patří do závislostí stávajícího `datasets`.

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
- **Dříve ověřeno na Kali:** původních **45/45** CPU testů. Současná celá sada **61/61 na Kali zatím čeká** na skutečný výpis.
- **Neprovedeno:** skutečné stažení GSM8K na Kali v rámci tohoto kroku, výběr skutečných 12 ID, úplný overlap audit, jakékoliv GPU generování, trénování nebo zlepšení modelu.

Na projektu spolupracuji s **ChatGPT (OpenAI, GPT-6)** a vlastní agentkou **Mášou**; všechny výsledky uvádím jen tehdy, když jsou doložené.
