# 🐰 RHAR CEP-002 — CPU MVP

**Stav (11. 10. 2026):** první izolovaná implementace a 22 nových CPU unit testů. Žádný nový GPU běh, LoRA trénink ani měřený přínos CEP-002 na Qwenu.

Soubory: `diagnostics/cep002_cpu.py` a `tests/test_cep002_cpu.py`.

## Co testujeme

- **VPS:** předem ručně zkontrolovaný task contract, vstupní fakta, matematické mezikroky a final. Jednoduché výrazy kontroluje bezpečný AST evaluator bez `eval`. Výsledky: VERIFIED / INVALID / UNVERIFIED / TRUNCATED.
- **XP:** loguje původní trace a výsledky do JSONL, uzamyká výhradně VERIFIED a vybírá nejvýše tři různé existující traces. Počet tokenů přebírá pouze z externího měření.
- **REC + Verified Lock:** ověřený trigger může pouze vyžádat přezkoumání; nemůže sám prohlásit starý zamčený trace za chybný. Prokázaná oprava vznikne jako nový záznam. Změna kontraktu nebo verifieru blokuje XP export do manuální revize.

## Výslovná omezení

Verifikátor umí **pouze úzký strojově čitelný aritmetický formát**, nikoliv libovolný přirozený jazyk. Nedokazuje sám správné převedení zadání do task contractu. Pole `reviewed_by` a `overlap_screen_passed` jsou atestace, nikoliv automatické provedení nezávislého auditu. Alternativní matematické strategie ani modelové generace nepřipravuje. JSONL není fyzicky nezměnitelný archiv.

SVAMP, MBPP+, BFCL a IFEval se nikdy nepoužijí jako trénovací data. Žádná nová data, trénink ani oficiální benchmark zatím neproběhly. Starší CEP 001 je jiná, samostatná experimentální metoda.

## Spuštění CPU testů

Z kořene repozitáře:

`python -m unittest tests.test_cep002_cpu -v`

Celý testovací balík (může vyžadovat další závislosti):

`python -m unittest discover -s tests -p 'test_*.py'`

**Bez zelené ani krok.** Po tomto MVP následuje ruční kontrola kontraktů, nezávislý datový audit a teprve po schválení trénink a párové vyhodnocení A/B/C.

## Syntetická dávka 001 (11. 10. 2026)

Přidáno 12 *ručně sestavených syntetických* aritmetických příkladů v `diagnostics/cep002_fixture_batch.py`. Vzorky pokrývají procenta, posloupné slevy, zlomky, zásoby, mzdu, průměr a další jednoduché vztahy. **Nejde o GSM8K, o nová trénovací data ani o skutečné generace Qwenu.** Autor fixtur není nezávislý externí auditor.

Příkazy:
- `python -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch -v`
- `python -m diagnostics.cep002_fixture_batch --dry-run`
- `python -m diagnostics.cep002_fixture_batch --execute --out runs/cep002-fixture-001`

Poslední příkaz zapíše JSONL historii a souhrn, nikdy nepřepisuje existující běh. Všech 12 správných vzorových traces se **očekává** jako VERIFIED, ale nové testy i dávku je nutné nejprve spustit na uživatelově PC. V této fázi jde o testování kontraktů, ne o ověřený přínos pro model. Nevydávat příznak `overlap_screen_passed` u syntetických fixtur za nezávislý audit reálných dat.


## GSM8K Data Intake 001 (11. 10. 2026)

Přidán `diagnostics/cep002_data_intake.py` a deset CPU unit testů v `tests/test_cep002_data_intake.py`. Nástroj čte jen lokální SHA-256 připnutý `GSM8K main/train` a místní soubor oficiálních evaluačních promptů pro kontrolu překryvu (nikdy jako trénovací cíle).

Deterministická posloupnost (`seed=42`) přeskakuje historické pozice: **1 000 původních train + 100 loss validation + 20 Evaluation 005 + 60 Evaluation 006 = 1 180**. Dalších **12 příkladů** nabídne pouze k ručnímu review a **60 následujících** rezervuje bez jejich zadání a odpovědí v souhrnu jako budoucí holdout. Každý review příklad má `contract: null` a `approved_for_training: false`.

Důležité: kontrola ostatních dřívějších pilotů / ručně vybraných úloh není úplná; blízké duplicity a sémantický překryv mohou uniknout. **Žádný z připravených příkladů není automaticky schválen pro CEP trénink**. Zveřejnění nebo prohlížení budoucího holdoutu jej může znehodnotit.

Lokální spuštění (z worktree, v prostředí s `pyarrow`, cesty výslovně na původní repozitář):

`python -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch tests.test_cep002_data_intake -v`

`python -m diagnostics.cep002_data_intake --dry-run --raw-parquet /home/rabbithollow/bottlecap-test/data/safe-start/raw/gsm8k-train.parquet --eval-questions /home/rabbithollow/bottlecap-test/questions/questions.jsonl --out runs/cep002-data-intake-001`

Po zeleném dry-runu lze výslovně spustit `--execute`; výstupní složka se nikdy nepřepisuje. Neprovádí se model inference ani trénink.


## Návrhy reálných kontraktů 001 (11. 10. 2026)

První tři z `runs/cep002-data-intake-001/candidates-review.jsonl` (pouze lokální *GSM8K main/train*, nikoli soutěžní benchmark) převedeny do přísně omezených matematických návrhů pomocí `diagnostics/cep002_real_contract_drafts.py`. Zkontrolují se předem známé SHA-256 původních otázek, původ/split/revize, referenční výsledek a přesná aritmetika přes `fractions.Fraction`.

- `gsm8k-train-00664`: `dog_years=2.5*4=10`, `fish_years=10+2=12`.
- `gsm8k-train-06718`: z `1/3+1/4=7/12`, při spotřebě `1/12` denně => **7 dní**. Kontrola s přesnými celočíselnými dvanáctinami bez zaokrouhlení.
- `gsm8k-train-03644`: `240+500=740`, Twitter `370`, TikTok `1110`, YouTube `1620`, součet `3840`.

**Přísná hranice:** návrhy jsou **UNVERIFIED**, `reviewed_by=""`, `overlap_screen_passed=false`, `approved_for_training=false`. Z předem napsaných referenčních postupů nevzniká žádný Qwen trace, XP lock ani učicí příklad. Samostatná matematická kontrola ověřuje početní konzistenci, **neautomatizuje nezávislou sémantickou kontrolu přepisu zadání do kontraktu**. Všechny tři úlohy jsou nyní viděné a nelze je později označit za neviděný holdout.

Nových 11 CPU testů: `python -m unittest tests.test_cep002_real_contract_drafts -v`. Dry-run `python -m diagnostics.cep002_real_contract_drafts --dry-run`, poté výslovné `--execute`. Výstup nesmí přepsat existující složku.


## Ruční sémantická revize 001 (11. 10. 2026)

Přidán `diagnostics/cep002_review_packet.py` a 12 CPU testů `tests/test_cep002_review_packet.py`. Skript spojí přes původní ID a SHA-256 soubor `runs/cep002-data-intake-001/candidates-review.jsonl` s `runs/cep002-contract-drafts-001/contract-drafts.jsonl`. Odmítá změněný původní text, nesouhlasící draft, předčasné schválení a přepsání výstupního protokolu.

Vytváří **pouze** `runs/cep002-contract-drafts-001/review-packet.md` se všemi třemi původními zadáními, definovanými veličinami, potřebnými výpočty, konkrétními riziky a nezaškrtnutými položkami pro lidskou kontrolu. Všechny závěry zůstávají `PENDING`; **0 nezávisle schválených kontraktů, 0 XP locků, 0 exportovaných trénovacích záznamů**. Review packet je podklad, nikoliv důkaz samostatné správnosti nebo autorizace tréninku.

Testy před spuštěním: `python -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch tests.test_cep002_data_intake tests.test_cep002_real_contract_drafts tests.test_cep002_review_packet -v`. Nových testů je 12 (očekávaný součet 67). Poté `python -m diagnostics.cep002_review_packet --dry-run` a `python -m diagnostics.cep002_review_packet --execute`. Nové testy dosud uživatel v Kali nespustil.
