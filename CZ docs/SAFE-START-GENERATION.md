# 🐇 RHAR Safe Start — příprava 36 generací Qwen3-0.6B

[🇬🇧 English](../docs/SAFE-START-GENERATION.en.md) · [Safe Start](SAFE-START.md) · [Audit překryvu](SAFE-START-OVERLAP.md) · [DEV-NOTES](DEV-NOTES.md)

**Rozhodnutí (10. 10. 2026):** schválil jsem **přípravu generovacího skriptu a CPU testy, nikoli skutečné spuštění GPU, inference, stažení modelu nebo trénování**.

## 🔬 Záměr a konfigurace

Z 12 již zafixovaných GSM8K train otázek chci získat **3 samostatné generace pro každou, celkem 36**. Srovnávat budu **správnost i skutečně generované tokeny**. Dosud nemám důkaz o úspoře tokenů ani algoritmus, který by měnil váhy modelu.

| Parametr | Zafixovaná hodnota |
| --- | --- |
| Model | `Qwen/Qwen3-0.6B`, revize `c1899de289a04d12100db370d81485cdf75e47ca` |
| Seedy | `9001`, `9002`, `9003` pro každou otázku |
| Thinking | `enable_thinking=True` |
| Sampling | `temperature=0.6`, `top_p=0.95`, `top_k=20` |
| Limit | `max_new_tokens=512` |
| Budoucí GPU prostředí | CUDA / float16, model výhradně z lokální cache |
| Trénování / oficiální evaluace | **Neprovádí se** |

`diagnostics/safe_start_generate.py` validuje před začátkem všech 12 původních otázek a hashe proti `selection-report.json`; samostatně ověřuje `overlap-audit.json` včetně všech šesti zdrojů oficiálních evaluačních textů, nuly nalezených heuristických shod a jejich metadat. **To neznamená úplné vyloučení parafrází a nepovoluje automaticky trénování.**

Prompt je identický se schváleným `build_prompt` — bez gold odpovědi a bez požadavku na zkrácení uvažování. Generátor ukládá seed, tokeny, skutečnou délku reasoning i final, strict přepočtenou správnost, prompt hash a dobu inference. Započítává jen opravdu **generované tokeny**; případný předvyplněný `<think>` nepočítá jako generaci. Bez správného EOS je záznam označen `truncated`, chybějící markery dávají neznámý rozpad, nikoli falešnou nulu. Formát je určen k další offline kontrole `diagnostics/offline_selector.py`.

## 🧪 Pouze CPU: další bezpečný krok

```bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate

python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan tests.test_safe_start_data tests.test_safe_start_overlap tests.test_safe_start_generate -v

python -m diagnostics.safe_start_generate --dry-run
```

**Očekávám 103 testů** (předchozích 79 + 24 nových) a ve dry-runu `status=plan_only`, `planned_generations=36`, `gpu_used=false`, `model_loaded=false`, `training_performed=false`. `--dry-run` nestahuje žádná data, neimportuje torch/Transformers, nezapíná GPU a nezakládá output složku.

## 🚫 GPU zatím NESPOUŠTĚT

Budoucí GPU cesta technicky existuje, ale vyžaduje **oba** explicitní přepínače `--execute` a `--confirm-gpu-36` a **samostatný pozdější souhlas**. Teď je nepoužívám. Model lze případně načíst pouze z místní cache (`local_files_only=True`), bez automatického downloadu.

Při pozdějším odsouhlaseném spuštění vytvoří nový, Git ignorovaný adresář `runs/safe-start/<UTC>/` s `config.json`, postupnými `records.jsonl` a `summary.json` pouze při dokončení všech 36 odpovědí. Nepřepisuje předchozí pokusy; neúspěšný běh se automaticky neobnoví. Vše zůstává `review_only` — nikoli schválené trénovací příklady.

**Nově skutečně ověřeno v Kali (10. 10. 2026):** kompletní sada **103/103 testů za 0,917 s** (`Ran 103 tests in 0.917s`, `OK`). Spuštěný `python -m diagnostics.safe_start_generate --dry-run` potvrdil **12 otázek, 36 plánovaných generací a 3 seedy**, všechny tři vstupní SHA-256 a `gpu_used=false`, `model_loaded=false`, `model_downloaded=false`, `training_performed=false`, `model_generations_performed=0`. Vstupní hashe: otázky `ebb3595c677ec6a660da3ff8731448182674967beab4d5e7f5256347541d32bc`, výběrový report `0760c4825de4e18bbbfcb6429dd543dcfa7fcc9e18dae83a118bccdf2b3cb89a`, audit `7b9443abf9e2960084bfaf6472ddf049ff057d4f4e1c889a4c01902a2ccc7ca4`. **Nejde o GPU experiment ani o naměřenou úsporu tokenů.**

Na projektu spolupracuji s **ChatGPT (OpenAI, GPT-6)** a lokální AI agentkou **Mášou**. Neověřené experimenty nikomu nepřisuzuji.
