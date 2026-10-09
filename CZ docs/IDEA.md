# IDEA.md — RHAR: Rabbit Hollow Adaptive Reasoning

**Stav (9. 10. 2026):** vlastník projektu **schválil RHAR jako společný modulární výzkumný směr**. Schválení se týká koncepce, nikoli konkrétního trénování, změn architektury v kódu, finančních nákladů nebo úprav vah modelu.

[🇬🇧 Anglická verze](../IDEA.md) · [Vývojový deník](DEV-NOTES.md)

## Motivace

Původní Qwen3-0.6B může generovat mnoho nepotřebných reasoning tokenů. Chceme snížit **celkový počet generovaných tokenů (uvažování + finální odpověď)** bez významné ztráty přesnosti napříč různými úlohami. Zkracování pouze promptem nebo vypnutí uvažování jsou výslovně nepřípustné metody.

## Hypotéza

**RHAR** zkoumá, zda se model může naučit efektivnějšímu uvažování, pokud trénink společně zohlední **informační pokrok (RPS)**, **rekonstruovatelnost zásadních informací (RPD)** a **ochranu obecných schopností (TPC)**.

Jde o *neověřenou výzkumnou hypotézu*. Příbuzné metody již existují; netvrdíme světové prvenství ani prokázané zlepšení.

## Tři moduly

| Modul | Předpokládaná funkce | Výzkumná otázka | Stav |
| --- | --- | --- | --- |
| **RPS — Reasoning Progress Signature** | Měřit informační pokrok oproti opakování v krocích uvažování, případně i pomocí skrytých stavů modelu | Dokáže se model naučit omezit neproduktivní uvažování? | Koncepce schválena, implementace neurčena |
| **RPD — Reversible Proof Distillation** | Prověřovat, zda zkrácené uvažování zachovává dost informací pro nezávislou rekonstrukci nebo ověření | Zachová stručné řešení zásadní důkazní informace? | Koncepce schválena, implementace neurčena |
| **TPC — Transfer-Protected Compression** | Sledovat a omezovat zhoršení schopností v matematice, programování, volání funkcí a dodržování instrukcí | Bude komprese obecně použitelná, nebo se přeučí na jednu oblast? | Koncepce schválena, implementace neurčena |

Tyto mechanismy mají v ideálním případě ovlivňovat **učení samotného modelu**, nikoli vyžadovat drahé dodatečné kontrolní agenty při každé inferenci. Proveditelnost a režijní náklady jsou otevřené otázky.

## Modulární výzkumný plán (navržené experimenty, dosud neschválené)

1. Změřit nezměněný model: správnost, počet reasoning/final/celkových tokenů, čas, variabilitu a selhání.
2. Zkoumat **RPS samostatně** a ověřit, zda jsou signály pokroku/redundance spolehlivé i mimo jedinou úlohu.
3. Zkoumat **RPD samostatně** na povolených výzkumných či trénovacích datech; měřit rekonstruovatelnost a výpočetní náklady.
4. Zkoumat **TPC samostatně** na oddělených povolených trénovacích/validačních datech z několika oblastí, bez přizpůsobování na oficiální testovací sady.
5. Provést **ablační srovnání** baseline, samostatně testovatelných modulů, RPS+RPD a RPS+RPD+TPC při shodném nastavení.
6. **Po dalším souhlasu vlastníka** vybrat trénovací cíl a data, určit LoRA nebo jinou úpravu modelu, výpočetní rozpočet a spustit trénování.
7. Vyhodnotit natrénované kandidáty nezměněným oficiálním `evaluate.py` a párově porovnat baseline/kandidáta pomocí `compare.py`.

Původní nápad destilace krátkých správných postupů zůstává **možnou trénovací baseline**, nikoli schváleným nebo implementovaným algoritmem RHAR.

## Metriky a evaluace

- **Hlavní:** správnost a celkový počet generovaných tokenů včetně uvažování a finální odpovědi.
- **Diagnostické:** poměr reasoning/final, opakování, nedokončené odpovědi, čas, variabilita, náročnost GPU, zhoršení podle oblasti a úspěšnost rekonstrukce.
- **Kontrolní podmínky:** shodné prompty/sampling/seedy pro porovnání, oddělení trénovacích/validačních dat, ablační testy a evidence chyb.
- **Oficiální oddělená evaluace:** SVAMP, MBPP+, BFCL a IFEval s dodanými pravidly a intervaly nejistoty. **Nikdy na těchto benchmarcích netrénovat.**
- **Originalita:** před tvrzením o novosti srovnat konkrétní implementovanou metodu s nejbližšími publikacemi; neveřejný výzkum nelze vyloučit.

## Omezení

- Výchozí model: `Qwen/Qwen3-0.6B`. Finální model přibližně 0.6B a **nadále skutečně uvažuje**.
- **Nikdy nezkracovat thinking pouze prompt engineeringem ani nevypínat uvažování.**
- Neměnit oficiální prompty benchmarků, nastavení generování, limity tokenů ani hodnocení.
- Zachovat kompatibilitu s běžnými Hugging Face Transformers/vLLM pro finální odevzdání.
- Nevymýšlet výsledky benchmarků, zlepšení, originalitu ani neprovedené testy.
- **Důležitá rozhodnutí vyžadují výslovný souhlas vlastníka**; zápis schválené koncepce neznamená povolení nových experimentů.

## Aktuální stav a pozorování

- **Průzkumná inference ověřená uživatelem:** správně `Final answer: 43`, 371 generovaných tokenů, 61,45 sekundy, 6,04 tokenu/s a 1,12 GiB alokované paměti PyTorch na GTX 1070 Ti. **Jedna neoficiální otázka, nikoli naměřené zlepšení.**
- **Diagnostika bez zásahu do modelu:** existuje `diagnostics/reasoning_probe.py` s vlastními testy; výstup prvního diagnostického běhu uživatele na GPU stále nemáme.
- **RHAR:** směr schválen, mechanismy a trénování neimplementovány, **zatím žádné výsledky RHAR**.

## Hardware

Viz [HARDWARE.md](HARDWARE.md). Lokální počítač: GTX 1070 Ti 8 GB (compute capability 6.1), i5-3450, ASUS P8B75-M, 16 GB RAM. Lokální inference přes PyTorch CUDA funguje; oficiální vyhodnocení ve vLLM vyžaduje podporovanou GPU. Proveditelnost analýzy skrytých stavů a trénování zatím není potvrzena.

## Co fungovalo / nefungovalo

Skutečné běhy, negativní výsledky, hardware a rozhodnutí zapisujeme do [DEV-NOTES.md](DEV-NOTES.md). Žádný trénovací experiment RPS/RPD/TPC zatím neproběhl.
