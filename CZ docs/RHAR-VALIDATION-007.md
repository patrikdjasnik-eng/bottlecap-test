# 🧪 RHAR Validation 007 — BASE vs SFT003 vs SFT004

**Záznam uzávěrky: 12. 10. 2026.** **Status: dokončený lokální exploratorní GPU běh podle terminálového výstupu uživatele; žádný oficiální BottleCapAI benchmark.**  
[🇬🇧 English](../docs/RHAR-VALIDATION-007.en.md) · [DEV-NOTES](DEV-NOTES.md) · [CEP 002](CEP-002.md)

## Co bylo skutečně doloženo

V uživatelově Kali/WSL2 prošlo **10 CPU testů**: `Ran 10 tests in 0.057s`, `OK`. Následně byl spuštěn `python -m diagnostics.rhar_validation_007 --dry-run --out runs/rhar-validation-007`; vypsal plán **40 úloh × 3 varianty = 120 generování**, `status=plan_only`, `gpu_used=false` a `training_performed=false`. Poté proběhl výslovně spuštěný lokální GPU běh s `--execute --approve-gpu`, `HF_HUB_OFFLINE=1` a `TRANSFORMERS_OFFLINE=1`. Terminál vypsal všech **120 jednotlivých výsledků** a finální `status=completed_exploratory`.

**Pozor na rozsah nezávislé verifikace:** výpis dodal uživatel; nejsou zde k dispozici lokální `runs/rhar-validation-007/records.jsonl`, `summary.json`, trénovací log SFT004 ani surové reasoning traces. Ke dni tohoto zápisu nebyly `diagnostics/rhar_validation_007.py`, odpovídající testy ani SFT004 training skript v prohlížené GitHub větvi `feat/reasoning-compression`. Neprohlašujeme jejich implementaci za vzdáleně auditovanou ani nesimulujeme opakovaný běh.

## Parametry podle skutečného dry-runu

- Zdroj: **GSM8K/main/train**, vybraných **40** matematických příkladů; jeden seed **9001**, `max_new_tokens=512`, `temperature=0.6`, `top_p=0.95`, `top_k=20`.
- Model: `Qwen/Qwen3-0.6B`; revize `c1899de289a04d12100db370d81485cdf75e47ca`; varianty **base**, **SFT003** (`runs/rhar-training-003`) a **SFT004 / long-SFT** (`runs/rhar-training-004-long-sft`).
- Fingerprint vybrané validace: `256adfdeddf9c73371893573c71af9698d11116c525b884cd5f79e276f3bf175`; seed výběru **7007**.
- Dry-run hlásil `training004_train_and_loss_validation_excluded=true`, `training004_train_ids_excluded=2500`, `training004_loss_validation_ids_excluded=100`, `training004_total_ids_excluded=2600`, `validation_used_for_loss_in_training004=false`, `protected_unique_ids=1262`, `historical_partition_ids=1180`, `historical_run_gsm8k_ids=82`, `safe_start_review_ids=12`, `cep002_review_ids=12`, `cep002_holdout_ids=60`, `fresh_candidates_available=3611`.
- Skript dále nahlásil screening **2 759** oficiálních evaluačních promptů a `heuristic_eval_overlap_screen_only=true`. Jde o **heuristickou** kontrolu: nevylučuje sémantické parafráze ani absolutně nezaručuje nepřítomnost kontaminace.

## Skutečně reportované výsledky

| Metrika | Původní Qwen (base) | SFT003 | SFT004 |
| --- | ---: | ---: | ---: |
| Strict correct | **6/40 (15 %)** | **14/40 (35 %)** | **17/40 (42,5 %)** |
| Complete | 8/40 | 38/40 | 39/40 |
| Truncated | **32/40** | 2/40 | 1/40 |
| Průměr vygenerovaných tokenů | 496,50 | 122,12 | **115,28** |
| Všechny vygenerované tokeny | 19 860 | 4 885 | **4 611** |

**SFT004 vs. base:** o **11 správných odpovědí více** (+27,5 procentního bodu) a **15 249 tokenů méně** (o ~76,8 % z reportovaného součtu). Párově **12 opravilo a 1 pokazilo**. **Důležitá výhrada:** base dosáhl limitu 512 tokenů u **32/40** úloh; snížení počtu vygenerovaných tokenů je tedy srovnáním s výrazně **cenzorovanou baseline**, nikoli důkazem stejných schopností či efektivity mimo tokenový limit.

**SFT004 vs. SFT003:** o **3 správné více** (+7,5 procentního bodu), **274 tokenů méně** (o ~5,6 % z 4 885), párově **6 opravilo a 3 pokazilo**. Jde o **40 úloh s jedním seedem** a možný rozdíl v trénovacích datech/rozpočtu SFT003 a SFT004, takže **nelze připsat rozdíl konkrétnímu algoritmu nebo potvrdit statisticky stabilní přínos** bez dalšího kontrolovaného srovnání. Případy nesprávných a truncated výstupů zůstávají ve spotřebě tokenů.

Finální program výslovně hlásí `quality_preservation_demonstrated=false`, `generalization_demonstrated=false`, `official_benchmark=false`. Respektujeme to; žádné SVAMP/MBPP+/BFCL/IFEval oficiální skóre z tohoto měření nevyvozujeme.

## Co jsme se naučili a co nás čeká příště

1. **Změna vah má měřitelný vliv na tento lokální test:** oba SFT adaptéry produkují výrazně více dokončených odpovědí než tato cenzorovaná baseline; SFT004 na zvolené sadě vykazuje lepší poměr správnosti/tokenů než SFT003. To je výsledek testu **běžných SFT adaptérů, nikoli CEP 002**.
2. **Správnost neobětovat délce:** rozdíl +3/40 je pozitivní pozorování, ne důkaz obecného zlepšení. Prověřit párově šest oprav a tři zhoršení vůči SFT003 na **lokálně uložených, nezměněných** záznamech.
3. **Reprodukovatelnost:** před dalšími zásahy ověřit lokální `git status` / commity Validation 007 a SFT004; zachovat `plan.json`, `records.jsonl` a `summary.json` beze změn a zkontrolovat jejich existenci, fingerprint, validní řádky a adapter metadata.
4. **Oddělení dat:** pro CEP002 (VPS + XP + REC + Verified Lock) chránit review/holdout, nevytvářet pozitivní trénovací zkušenosti z již hodnocených 40 ani 60 dřívějších případů, pokud je chceme vydávat za nezávislé. Zvláštní GPU či LoRA experiment až po výslovném schválení.
5. **Férový další test:** SFT kontrola proti CEP 002 se srovnatelnými trénovacími příklady a rozpočtem; nové neviděné otázky, více seedů a následně oficiální `evaluate.py` / `compare.py` na kompatibilním hardwaru.

**Uzávěrka:** dnes už žádné nové generování, trénování ani přepínání checkpointů. Tento zápis je **dokumentace uživatelem vykonaného lokálního experimentu**, nikoli nový běh. 🐇🛡️
