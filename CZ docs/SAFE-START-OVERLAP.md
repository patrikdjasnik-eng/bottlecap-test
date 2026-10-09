# 🛡️ RHAR Safe Start — CPU audit překryvu s evaluačními daty

[🇬🇧 English](../docs/SAFE-START-OVERLAP.en.md) · [GSM8K výběr](SAFE-START-DATA.md) · [DEV-NOTES](DEV-NOTES.md)

**Schválení, 10. 10. 2026:** po potvrzené sadě **61/61 testů na Kali** a zjištění, že `questions/questions.jsonl` neexistuje, jsem schválil **výhradně stažení nezbytných oficiálních evaluačních dat a CPU kontrolu překryvu**. **Neschválil jsem spuštění oficiální evaluace, modelu, GPU ani trénování.**

## 📌 Jaká data prověřím

Auditor `diagnostics/safe_start_overlap.py` používá stejné zdrojové revize jako nezměněný `utils/eval/benchmarks.py`:

| Rodina | Připnutí | Co auditor načte |
| --- | --- | --- |
| SVAMP | Git commit `78e727689e1c1bebfc4be39c446898e8e10b0518` + SHA-256 | `SVAMP.json` — spojení Body + Question |
| MBPP+ | verze `v0.2.0` + SHA-256 rozbaleného obsahu | `MbppPlus.jsonl.gz` — jen pole prompt |
| BFCL | Git commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` | tři BFCL v4 soubory: simple_python, multiple, irrelevance — jen uživatelské zprávy |
| IFEval | Git commit `4700efb9afa54286b0e04473ba80a13e8461e25f` | `input_data.jsonl` — jen pole prompt |

**Šest zdrojových souborů; čtyři rodiny benchmarků.** Pro SVAMP a MBPP+ kontroluji očekávaný obsahový SHA-256 převzatý z oficiálního skriptu v projektu. U BFCL a IFEval jsou URL připnuté Git commitem a vypočtené SHA-256 zapisuji do výstupu, ale nemám v kódu nezávisle předem ověřený obsahový hash.

Jednotlivé zdrojové soubory mohou obsahovat i oficiální odpovědi nebo reference; **používám pouze texty otázek a ostatní pole nezapisuji do výstupu**. Soubory jsou při běhu načteny do paměti a není vytvářena trvalá kopie evaluace nebo trénovací sada. Velikost načtení je omezená.

## 🔍 Co audit dělá

1. Načte stávajících **12 GSM8K kandidátů** z `data/safe-start/questions.jsonl` a ověří všechny jejich ID a SHA-256 vůči `selection-report.json` (tedy beze změny zvoleného výběru).
2. Po výslovném přepínači `--download` načte a ověří všech šest připnutých zdrojů. **Nedostupný soubor, změněný kontrolní hash nebo neznámé schéma = chyba, nikoli falešně zelený výsledek.**
3. Porovná normalizované otázky na **přesnou shodu** a pomocí heuristiky `close_match` na výraznou textovou podobnost.
4. Uloží nový ignorovaný soubor `data/safe-start/overlap-audit.json`, obsahující počty načtených otázek, hash zdrojů, ID případných shod a rozsah prověrky. **Nepřepisuje původní soubory** a bez výslovného povolení nestahuje nic.
5. Vždy hlásí `training_approved=false`, `overlap_audit_exhaustive=false` a `semantic_paraphrases_ruled_out=false`. **Nulové shody nejsou důkaz vyloučení všech parafrází a nezakládají automatické svolení k trénování.**

## 🧪 Jak postupuji na Kali

Nejdřív regresní CPU testy; stávající sada má 61 testů, nový audit přidává **18 testů**, očekávaný počet je **79**:

```bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate
python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan tests.test_safe_start_data tests.test_safe_start_overlap -v
```

**Teprve po zeleném testu** spustím jednorázový audit s výslovným stažením dat:

```bash
python -m diagnostics.safe_start_overlap --download
```

Zpráva se vypíše na terminál a uloží do `data/safe-start/overlap-audit.json`. **Nepouštět `python utils/eval/benchmarks.py`, `evaluate.py` ani trénování.** Pokud skript skončí chybou, nezakládat pozitivní závěr a poslat konkrétní traceback. Opakovaný audit odmítne přepsání již existujícího reportu.

K následné revizi mi stačí výstup `overlap-audit.json`. **Není potřeba posílat obsah `questions.jsonl` ani gold answers.**

## ✅ Stav

- **Předchozí krok skutečně ověřen:** 61/61 CPU testů na Kali (`Ran 61 tests in 0.600s`, `OK`), 12 vybraných GSM8K kandidátů a SHA-256 datasetu.
- **Nový audit:** implementovaný `diagnostics/safe_start_overlap.py` a **18/18 nových unit testů zelených v izolovaném lokálním CPU prostředí**. Testy mockují síť; neověřují skutečné vzdálené soubory.
- **Čeká na Kali:** společných **79/79 testů** a reálné stažení šesti připnutých zdrojů + výsledky překryvu. **Nedošlo k inferenci ani trénování.**

Výzkumné rozhodnutí držím ve vlastních rukou. Na projektu mi pomáhá **ChatGPT (OpenAI, GPT-6)** a lokální agentka **Máša**, které nepřisuzuji neověřené experimenty.
