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


## Historický audit přes skutečné běhy (11. 10. 2026)

Uživatel potvrdil **70/70 zelených CPU testů** a lokálně v Kali našel `data/safe-start/questions.jsonl`, `runs/rhar-validation-005/records.jsonl`, `runs/rhar-validation-006/records.jsonl` i množství dalších záznamů pilotních experimentů a diagnostiky.

Přidán **`diagnostics/cep002_history_overlap.py`** a **18 syntetických CPU regresních testů** `tests/test_cep002_history_overlap.py`. Skript čte **pouze** 12 již vybraných a prohlédnutých úloh z CEP-002 Data Intake 001 a 60 rezervovaných dvojic `(ID,SHA256)` bez zadání či odpovědí. Porovnává je s původními Safe Start otázkami a všemi `runs/**/records.jsonl` v původním research repo. Návrhy a holdout manifesty v izolovaném novém worktree nejsou považovány za starší zdroje. Kontroluje identitu ID, přímo uložený SHA-256 otázky, SHA-256 samotného textu, normalizovanou shodu a vložení celého textu do uživatelského promptu. Modelové výstupy, referenční odpovědi a generated reasoning ignoruje.

Vyhodnocení je **fail-closed** pro chybějící kritické běhy, nesprávnou strukturu vstupních manifestů, prázdné či poškozené JSONL a přepis existujícího výstupu. Neznámé schema a řádky pouze s ID jsou v metrikách uvedeny jako nepokryté textové kontroly; i nulová shoda znamená pouze `partial_historical_screen_no_match`, **nikoliv schválená trénovací data**. Zpráva používá jen identifikátory a názvy souborů, neverbatim eval otázky či odpovědi. Heuristika neumí spolehlivě zachytit parafráze a sémantické duplicity.

Použij z Windows PowerShellu s funkcí `cep`:

```powershell
cep -m unittest tests.test_cep002_cpu tests.test_cep002_fixture_batch tests.test_cep002_data_intake tests.test_cep002_real_contract_drafts tests.test_cep002_review_packet tests.test_cep002_history_overlap -q
cep -m diagnostics.cep002_history_overlap --dry-run --safe-start /home/rabbithollow/bottlecap-test/data/safe-start/questions.jsonl --history-root /home/rabbithollow/bottlecap-test/runs
```

Po zelených testech a úspěšném `--dry-run` lze výslovně spustit stejné CLI s `--execute`. Výstup `runs/cep002-history-audit-001/summary.json` a `overlaps.jsonl` se nikdy automaticky nepřepisuje. **Zatím žádný nový auditní běh ani jeho 18 nových testů uživatel nespustil**; očekáváme 88 CPU testů. Žádný GPU běh, LoRA učení nebo export trénovacích vzorů.


## Rekonstrukce původu validací 005/006 (11. 10. 2026)

Uživatel potvrdil z uloženého `runs/cep002-history-audit-001/summary.json`, že 160/205 historických záznamů bez textu zadání pochází z `rhar-validation-005` (40 řádků = 20 × 2 modely) a `rhar-validation-006` (120 řádků = 60 × 2 modely). Dalších **45 řádků** bez textu z jiných běhů ještě nemá úplně určený původ.

Nový **`diagnostics/cep002_validation_provenance.py`** rekonstruuje validace 005/006 z originálního SHA-256 připnutého GSM8K `main/train` pomocí `prepare_pool(rows, 1000, 180, seed=42)`. Ověří přesná ID a GSM8K gold referenční čísla a vyžaduje právě jedno `sft` a jedno `cep` měření pro každou z 20 a 60 úloh; chybějící/přebývající ID či varianta audit zablokují. Zároveň opakuje předchozí kontrolu ID/hash překryvu pro 12 review kandidátů a 60 budoucích rezervací. Z ostatních `records.jsonl` jen agreguje typy známých ID a souborové počty, nikoliv texty/odpovědi.

Čtení originálního train Parquet načte do operační paměti všechny trénovací řádky včetně budoucí holdout oblasti, avšak do ověřované validační množiny vybere jen **prvních 1180 historických pozic**; budoucí 60 otázek nevybírá do výstupu, neukazuje a neexportuje. Proto se metadata vztahují přesně k `reserved_holdout_questions_selected=false` a `reserved_holdout_texts_exported=false`, nikoli k tvrzení, že se Parquet holdout bytes nikdy nečetly.

Nových **11 unit testů** v `tests/test_cep002_validation_provenance.py` (celkem očekávaných **99 CPU testů**), dosud uživatel nespustil. Dry-run bez zápisu:

```powershell
cep -m diagnostics.cep002_validation_provenance --dry-run --raw-parquet /home/rabbithollow/bottlecap-test/data/safe-start/raw/gsm8k-train.parquet --safe-start /home/rabbithollow/bottlecap-test/data/safe-start/questions.jsonl --history-root /home/rabbithollow/bottlecap-test/runs
```

Jen po zelených testech lze spustit se `--execute`, vytvoří nepřepisovaný `runs/cep002-validation-provenance-001/summary.json` a `other-file-coverage.json`. Klasifikace starších 45 záznamů a sémantické podobnosti zůstává **částečná**, nikdy neznamená schválení pro trénink, GPU ani automatickou produkci XP.


## Residual History 001 — šest GSM8K ID + 39 dalších (11. 10. 2026)

Nový `diagnostics/cep002_residual_history.py` řadí zbylých 45 historických záznamů bez zadání podle ID do původních známých GSM8K partition. **Skutečné přiřazení zdrojového indexu je slabší důkaz než shoda originální otázky**, pokud starší záznam neobsahuje otázku. Ostatních 39 ID nejsou automaticky bezpečná data. Výstup obsahuje počty a přehled souborů, nikdy zdrojové zadání, odpovědi ani modelové generace. Vyžaduje původní lokální SHA-256 připnutý GSM8K train Parquet, prohlédnutých 12 kandidátů a 60 holdout referencí (holdout pouze ID/hash). Nových 9 unit testů, očekává se 108; uživatelský běh zatím neproběhl.


## Oprava počtu neuzavřených historických řádků (11. 10. 2026)

Při skutečném dry-runu bylo nalezeno 6 validních GSM8K indexových ID mimo první známé partition a 39 ostatních ID-only záznamů, avšak původní `requires_investigation_count` chybně uváděl 0. Metrika nyní počítá všechny dosud sémanticky nedoložené ID-only záznamy z reziduálních běhů, **očekáváno 45**. Oprava zahrnuje kontrolu úplnosti kategorizace a 3 regresní CPU testy. To neznamená 45 chybných úloh ani neosvědčuje jejich čistotu; ani šest platných GSM8K indexů bez textu zadání není nezávislá kontrola obsahu. Očekávaný počet CPU testů **111**, dosud nespouštěno.
