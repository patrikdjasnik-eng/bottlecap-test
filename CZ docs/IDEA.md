# IDEA.md — RHAR: Rabbit Hollow Adaptive Reasoning

**Stav (9. 10. 2026):** **rozhodl jsem se pro RHAR jako společný modulární výzkumný směr**. Schválení se týká koncepce, nikoli konkrétního trénování, změn architektury v kódu, finančních nákladů nebo úprav vah modelu.

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

## HRM — Hallucination Risk Monitor (výzkumný kandidát)

**Stav:** dne 9. 10. 2026 jsem **schválil zápis nápadu do Markdown dokumentace**. HRM je **navržené rozšíření pro diagnostiku rizika**, **nikoli zatím formálně schválený čtvrtý modul RHAR**, trénovací komponenta nebo provedený experiment.

**Výzkumná otázka:** Mohou signály sledované v RHAR předpovídat riziko chybné nebo nepodložené odpovědi **ještě před** nezávislým ověřením správnosti? Chyba v numerické úloze nemusí být faktická halucinace; při měření oba jevy odlišovat.

**Navržené signály (dosud neimplementované):**

| Signál | Navržené pozorování | Omezení |
| --- | --- | --- |
| Nestabilita odpovědí | Rozdíly ve finálních odpovědích při opakovaném generování | Shoda nezaručuje pravdivost; další generování stojí čas |
| Falešný pokrok RPS | Vysoká aktivita či opakování v reasoning procesu bez měřitelného posunu | Metriku pokroku je nutné nejprve ověřit, nestačí délka textu |
| Ztráta informace RPD | Rozpory nebo nemožnost rekonstruovat podstatné kroky a výsledek | Samotné ověřování může být chybové a výpočetně drahé |
| Ověření vůči zdroji | Tvrzení odporující poskytnutému zdroji, známému výpočtu nebo spustitelnému testu | Vyžaduje vhodný důkaz; neznámý fakt nelze automaticky označit za chybný |

**Navržené měření a ověření:**
1. Začít **rizikovým skóre**, nikoli tvrzením o pravděpodobnosti halucinace.
2. Připravit samostatná data s ověřitelným správným výsledkem. Vést oddělené štítky **chybná odpověď** a **nepodložené faktické tvrzení**.
3. Kalibrovat pravděpodobnosti pouze na oddělené kalibrační sadě a ověřit je na další nezávislé sadě. Sledovat **Brierovo skóre**, **expected calibration error (ECE)** a rozlišovací schopnost (např. **AUROC**, pokud jsou zastoupeny obě třídy).
4. Srovnat s jednoduchými baseline, například stabilitou finálních odpovědí. Ablačně ověřit přínos signálů RPS/RPD/TPC.
5. Započítat dodatečnou výpočetní a paměťovou cenu. Na GTX 1070 Ti upřednostnit lehké měření z jediné generace; opakované generování vyžaduje samostatné odůvodnění.
6. Nepřizpůsobovat HRM podle testovacích dat SVAMP, MBPP+, BFCL a IFEval. Neměnit oficiální evaluaci.

**Současná diagnostika:** `diagnostics/reasoning_probe.py` eviduje správnost několika ručně připravených úloh, tokeny a opakování, ale **neměří riziko, kalibrovanou pravděpodobnost halucinace, faktickou oporu, ECE ani Brierovo skóre**.

**Čeká na další schválení:** architektura HRM, výběr signálů, prahy, kalibrační data, kontrola zdrojů, trénovací integrace a změny kódu. Nápad nevydávat za světovou novinku, naměřené zlepšení ani funkční predikční systém.

## RHAR v0.1 — schválený směr a navržený protokol

První zvolený trénovací směr je **Correctness-Gated Reasoning Compression**. Znamená to nejprve hledat **správné, úplné a relativně krátké reasoning traces**, teprve po dalších rozhodnutích zkoušet, zda se model tento vzor naučí. **Směr jsem schválil, ale konkrétní implementaci, sběr dat, GPU rozpočet a trénování zatím ne.** Podrobnosti mám v [RHAR-V01-PLAN.md](RHAR-V01-PLAN.md). Samotný jednoduchý výběr nejkratší správné odpovědi není ověřenou vědeckou novinkou.

## Modulární výzkumný plán (další experimenty zatím neschválené)

1. Změřit nezměněný model: správnost, počet reasoning/final/celkových tokenů, čas, variabilitu a selhání.
2. Zkoumat **RPS samostatně** a ověřit, zda jsou signály pokroku/redundance spolehlivé i mimo jedinou úlohu.
3. Zkoumat **RPD samostatně** na povolených výzkumných či trénovacích datech; měřit rekonstruovatelnost a výpočetní náklady.
4. Zkoumat **TPC samostatně** na oddělených povolených trénovacích/validačních datech z několika oblastí, bez přizpůsobování na oficiální testovací sady.
5. Provést **ablační srovnání** baseline, samostatně testovatelných modulů, RPS+RPD a RPS+RPD+TPC při shodném nastavení.
6. **Až po mém dalším rozhodnutí** vybrat trénovací cíl a data, určit LoRA nebo jinou úpravu modelu, výpočetní rozpočet a spustit trénování.
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
- **Důležité kroky si výslovně odsouhlasím**; zápis schválené koncepce neznamená povolení nových experimentů.

## Aktuální stav a pozorování

- **Moje ověřená průzkumná inference:** správně `Final answer: 43`, 371 generovaných tokenů, 61,45 sekundy, 6,04 tokenu/s a 1,12 GiB alokované paměti PyTorch na GTX 1070 Ti. **Jedna neoficiální otázka, nikoli naměřené zlepšení.**
- **Diagnostika bez zásahu do modelu:** existuje `diagnostics/reasoning_probe.py` s vlastními testy; první GPU diagnostika již proběhla: 325 tokenů, chybná odpověď 42 místo 43 (Experiment 002).
- **RHAR:** směr schválen, mechanismy a trénování neimplementovány, **zatím žádné výsledky RHAR**.

## Hardware

Viz [HARDWARE.md](HARDWARE.md). Lokální počítač: GTX 1070 Ti 8 GB (compute capability 6.1), i5-3450, ASUS P8B75-M, 16 GB RAM. Lokální inference přes PyTorch CUDA funguje; oficiální vyhodnocení ve vLLM vyžaduje podporovanou GPU. Proveditelnost analýzy skrytých stavů a trénování zatím není potvrzena.

## Co fungovalo / nefungovalo

Skutečné běhy, negativní výsledky, hardware a rozhodnutí zapisujeme do [DEV-NOTES.md](DEV-NOTES.md). Žádný trénovací experiment RPS/RPD/TPC zatím neproběhl.
