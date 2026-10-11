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
