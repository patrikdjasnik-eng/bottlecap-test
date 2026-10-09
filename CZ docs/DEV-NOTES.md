# 🔬 DEV-NOTES — Vývojový deník

[🇨🇿 Česky](DEV-NOTES.md) · [🇬🇧 English](../docs/DEV-NOTES.en.md)

## Pravidla spolupráce

- **O důležitých technických rozhodnutích, experimentech a nových nápadech rozhoduji já.** Než uděláme zásadní změnu, nejprve spolu probereme možnosti, rizika a další postup.
- Bez mého výslovného rozhodnutí neměnit směr výzkumu, model, trénovací strategii, benchmarkové podmínky, strukturu projektu ani neprovádět zásadní změny v repozitáři.
- Běžné, výslovně zadané úpravy dokumentace a technické opravy v odsouhlaseném rozsahu lze provádět, s jasným zápisem do deníku.
- Rozlišovat **provedeno / ověřeno / navrženo / čeká na schválení / chyba**. Nikdy nepředstírat úspěch testů nebo naměřené výsledky.
- Zápisy uvádějí datum, změny, důvod, ověření a další krok. Zásadní rozhodnutí mají explicitní stav schválení.
- **Bez zelených testů ani krok** při změnách kódu; pro dokumentační změny ověřit strukturu a odkazy.

## Deník

### 2026-10-09 — 🐇 RHAR: kompletní checkpoint výzkumu, výsledků a dalších kroků

**Proč tento zápis:** shrnul jsem do jednoho místa vše, co jsem zatím navrhl, schválil, změřil a opravil. Tento deník píšu **z pohledu vývojáře v první osobě**; starší záznamy níže ponechávám jako historii. Jejich „čeká na GPU běh“ nebo „čeká na schválení“ může být mezitím překonané. **Sepsání dokumentace není nový experiment.**

#### 🤝 Jak na projektu pracuji

Na RHAR pracuji společně s **ChatGPT (OpenAI, GPT-6)** a se svou vlastní lokální **GGUF AI agentkou Mášou**. Přístup k AI neskrývám: ChatGPT využívám při debatách o hypotézách, návrhu a revizích kódu, organizaci dokumentace a interpretaci měření; Máša je součást mého vlastního agentního vývojového prostředí. **Konkrétní zásahy Máši do tohoto repozitáře nebo její samostatné výzkumné výsledky nemám zatím v Git historii doložené; nepřipisuji jí proto neověřené commity ani testy.** Směr výzkumu, schválení experimentů a rozhodnutí o vydání si řídím sám. Pro spolupráci přirozeně používám i „my“.

#### 🎯 Cíl ThinkingCap-Test a závazná pravidla

- Výchozí model: **`Qwen/Qwen3-0.6B`**. Chci natrénovat změnu jeho chování tak, aby při podobné správnosti spotřebovával **méně všech generovaných tokenů (reasoning + finální odpověď)**.
- **Neřeším zkrácení prompt engineeringem a nevypínám reasoning.** V diagnostice zůstává `enable_thinking=True`. Pouhá instrukce o formátu výsledku není metoda komprese.
- Na **SVAMP, MBPP+, BFCL ani IFEval netrénuji**; jsou určené k oddělenému oficiálnímu vyhodnocení. Oficiální `evaluate.py`, `compare.py`, zadání, sampling a scoring neměním.
- **„Nikdo na světě to nezkusil“ nelze zaručit.** Novost budu ověřovat rešerší přesných implementací a výsledky, ne dojmem.
- Důležité kroky rozhodnu předem a nepůjdu dál přes červené testy. **Bez zelené ani krok.**

#### 🧬 Výzkumný organismus RHAR

Rozhodl jsem se pro **jeden modulární výzkumný směr**: **RHAR — Rabbit Hollow Adaptive Reasoning**.

| Oblast | Můj výzkumný záměr | Aktuální realita |
| --- | --- | --- |
| **RPS — Reasoning Progress Signature** | Rozlišovat užitečný informační pokrok od opakování a stagnace | Výzkumná hypotéza; signál ani trénovací mechanismus neověřen |
| **RPD — Reversible Proof Distillation** | Zachovat v kratší úvaze to, co je nutné k rekonstrukci správného výsledku | Hypotéza; rekonstrukční metrika i cena zatím neotestovány |
| **TPC — Transfer-Protected Compression** | Chránit přesnost napříč matematikou, kódem, funkcemi, instrukcemi i dalšími obory | Hypotéza; ochranný trénovací mechanismus zatím není implementovaný |
| **HRM — Hallucination Risk Monitor** | Zjišťovat riziko chybné/nepodložené odpovědi a možné předzvěsti selhání | **Pouze navržený kandidát**, nikoli schválený čtvrtý modul ani kalibrovaná pravděpodobnost |

HRM by mohl využít neshodu odpovědí, slabý pokrok, špatnou rekonstruovatelnost a případné ověření vůči zdroji. Chybu v aritmetice ale automaticky nenazývám faktickou halucinací. Pro pravděpodobnost bude potřeba nezávislé značení, kalibrace a např. Brier score, ECE a AUROC. **Zatím jsem natrénoval 0 RHAR modelů; žádné zlepšení ani novost nemám prokázané.** Dříve diskutovaná LoRA destilace je možná srovnávací metoda, **ne zvolený algoritmus**.

#### 🖥️ Co jsem skutečně rozběhl

- Kali Linux ve WSL2, Python **3.11.17** v `.venv`, původní `~/bottlecap-test`.
- GPU **GTX 1070 Ti 8 GB** (compute capability **6.1**), CPU **Intel i5-3450**, RAM **16 GB**.
- PyTorch **2.6.0+cu118**, CUDA runtime **11.8**; `torch.cuda.is_available()` ukázalo `True` a reálný GPU výpočet skončil číslem **512.0**.
- Na GPU jsem přes Transformers ve `float16` skutečně spustil původní **Qwen3-0.6B**. Dřívější warning chybějícího NumPy nebyl důkazem nefunkční CUDA; kompletní audit všech závislostí ale nemám.
- Na Pascal `sm_61` nepředpokládám podporu současného oficiálního **vLLM** evaluačního běhu. Pro plný benchmark budu potřebovat kompatibilní GPU.
- Původní testy hlásily nedostupný **bubblewrap**. Před spuštěním modelového kódu v MBPP+ je nutné bezpečné oddělení, ne jen resource limit.

#### ✅ Stav testů

| Ověření | Skutečně doložený stav |
| --- | --- |
| Starší testy původního repozitáře | **87 OK, 2 skipped** (chyběly EvalPlus/BFCL podklady) |
| První diagnostická sada | Dříve hlášeno **9/9 CPU testů** a úspěšný `--dry-run` |
| Aktuální diagnostika po opravě | V kódu je **10 definovaných testů**; kompletní nové **10/10 z mého Kali zatím nemám doložené** |
| Izolovaný test opravené instrukce | Starší deník uvádí **1/1**; neberu to jako potvrzení celé sady |
| Kontrolní GPU běh po opravě | **Zatím neproveden / výsledek nemám** |
| Oficiální benchmark BottleCap AI | **Neproveden**, `results.json` ani párové statistiky zatím nemám |

#### 📊 Dva naměřené průzkumné běhy původního Qwenu

| Metrika | První inference | Experiment 002 |
| --- | ---: | ---: |
| Odpověď | **43, správně** | **42, nesprávně** (očekáváno 43) |
| Vygenerovaných tokenů | **371** | **325** |
| Reasoning tokeny | samostatně nezjištěny | **317** |
| Tokeny finální odpovědi | samostatně nezjištěny | **8** |
| Podíl reasoning | neznámý | **97,54 %** |
| Doba inference | **61,45 s** | **51,3 s** |
| Průměrná rychlost | **6,04 tokenu/s** | **6,33 tokenu/s** |
| Paměť PyTorch | **1,12 GiB alokováno** | v poslaném souhrnu neznámá |

**Nesmím vydávat 371 → 325 tokenů za zlepšení RHAR.** Oba běhy použily **nezměněný model**, s odlišnou formulací zadání/promptu a nejvýše jedním vzorkem na běh. Nemám statistický důkaz zlepšení, robustnosti nebo pravděpodobnosti halucinace.

#### 🔎 Experiment 002: co se skutečně pokazilo

Spustil jsem `python -m diagnostics.reasoning_probe --limit 1`. Artefakty zůstaly lokálně v `runs/diagnostics/20261009T210123Z/`; `runs/` je ignorován Gitem. Terminál hlásil `responses=1`, `correct_responses=0`, `exploratory_accuracy=0.0`, `reasoning_split_successes=1`, `mean_total_tokens=325`, `mean_reasoning_tokens=317`, `mean_final_tokens=8`, `mean_seconds=51.3`, `mean_tokens_per_second=6.33`, `official_benchmark=false`.

V `records.jsonl` jsem poté ověřil: `id='arithmetic_apples'`, `expected='43'`, `final_text='\\n\\nFinal answer: 42'`, `correct=False`, `grading_error=None`, `truncated=False`, `split_status='generated_think_block'`. **Odpověď byla věcně chybná, nikoli chybně formátovaná nebo uříznutá.** Původní formátová nápověda v promptu obsahovala `Final answer: 42` a výsledek také byl `42`. **Může jít o vliv příkladu, ale příčina zatím není prokázaná.** Kompletní reasoning trace v deníku nepublikuji.

[📊 Experiment 002 — detailní report](experiments/002-reasoning-baseline.md) · [SVG přehled](../assets/reports/rhar-exp-002-cz.svg)

#### 🩹 Schválená oprava a důvod

V `diagnostics/reasoning_probe.py` jsem odstranil konkrétní vzorovou odpověď. Nová instrukce zní **`On the last line, write 'Final answer:' followed by your answer.`** a nic nepřikazuje o délce úvahy. Přidal jsem test `test_prompt_has_no_example_answer_or_answer_leakage`. **Thinking zůstává zapnutý, oficiální evaluační prompty beze změny.** Starý Experiment 002 nepřepisuji. **Opravu ještě nemám doloženou novým kompletním během 10/10 ani kontrolní inferencí.**

#### 🛡️ Nápad pro doplňkový cybersecurity test (čeká na rozhodnutí)

Chci ověřovat i **obranné kyberbezpečnostní uvažování**, protože TPC má měřit obecnost a ne jen aritmetiku. **Zatím navrhuji** v mé malé ručně vytvořené diagnostice **nahradit triviální úlohu `logic_triangle`** jednoduchým jednoznačně hodnotitelným příkladem z analýzy bezpečnostních logů:

> V logu je patnáct neúspěšných SSH přihlášení ke stejnému účtu ze stejné adresy během minuty a pak jedno úspěšné. Jaký je nejrozumnější obranný závěr? **A:** označit událost k bezpečnostnímu prověření; **B:** automaticky smazat logy; **C:** zdroj bez kontroly označit za důvěryhodný. **Očekáváno: A.**

Tento příklad je **jen koncept, nikoli spuštěný test nebo prokázaný bezpečnostní incident**. Neměl by vytlačit všechny základní matematické/kódové/logické kontroly a **nenahrazuje žádný oficiální benchmark**. Před změnou `CASES` si rozhodnu přesné zadání, vyváženost a kontrolu správné odpovědi; případné doplnění izolovaného doménového testu je také možnost. **Žádná cybersecurity úloha se nyní do Python kódu nepřidala.**

#### 📁 Dokumentace a další plán

- Repo mám na `feat/reasoning-compression`. Česká dokumentace je v `CZ docs/`, anglické varianty v kořeni a `docs/`.
- Experimentální reporty vedu **CZ/EN 1:1** se skutečnými tabulkami a případně tmavými SVG kartami. V grafu vždy přiznávám správnost a nejistoty.
- **Následující krok:** `git pull --ff-only origin feat/reasoning-compression` → `python -m unittest tests.test_reasoning_probe -v`. Při selhání stop. Teprve po zeleném výsledku znovu `python -m diagnostics.reasoning_probe --limit 1`, do nového adresáře. Pak zaznamenám výsledky, nikoli domnělé zlepšení.
- Následně samostatně upřesním RPS/RPD/TPC, rozhodnu o cybersecurity zadání a případně HRM; trénovací technika i data zatím čekají. Před MBPP+ vyřeším sandbox, před plným benchmarkem GPU.

**Aktuální závěr:** CUDA a původní Qwen lokálně fungují, mám dvě skutečné průzkumné inference a opravený diagnostický prompt. **Nemám natrénovaný RHAR, doloženou úsporu tokenů, 10/10 po poslední změně ani oficiální benchmark.**

---
**Poznámka k historii:** starší deníkové položky níže zachycují tehdejší stav. Aktuální shrnutí a přehled čekajících testů je v checkpointu nahoře.

### 2026-10-09 — Schválená oprava formátové ukázky (diagnostika)

**Moje rozhodnutí:** odsouhlasil jsem úprava zavádějícího příkladu `Final answer: 42` v diagnostickém promptu, po analýze Experimentu 002.

**Změna:** `prompt_for()` v `diagnostics/reasoning_probe.py` už neuvádí žádnou vzorovou odpověď a pro všechny diagnostické příklady stanovuje pouze neutrální formát finálního řádku: `On the last line, write 'Final answer:' followed by your answer.`. Přidán regresní test bez prozrazování odpovědí. **Nijak se nezkracuje thinking, nevypíná reasoning a nemění oficiální BottleCap AI prompty.**

**Ověření:** cílený izolovaný lokální test nové formátové instrukce **1/1 prošel**. Kontrola zdrojových změn a odkazů dokumentace proběhla. Celá sada testů repozitáře a kontrolní GPU inference v mém Kali **zatím nebyly zopakovány**.

**Historie:** původní Experiment 002 zůstává nedotčen (325 tokenů, finální odpověď 42 místo 43). **Hypotéza o ovlivnění hodnotou 42 není potvrzena**. Následující kontrolní běh musí vytvořit nový výstupní adresář a nesmí být vydáván za trénovací zlepšení.

### 2026-10-09 — Diagnostika 002: první výstup na GTX 1070 Ti

![RHAR — grafický report Experimentu 002](../assets/reports/rhar-exp-002-cz.svg)

[📊 Kompletní grafický report a tabulky](experiments/002-reasoning-baseline.md)

**Stav:** měření jsem provedl v Kali / WSL2; **neoficiální diagnostika**, nikoli benchmark BottleCap AI.

**Moje lokální artefakty:** `runs/diagnostics/20261009T210123Z/`. Surové soubory uchovávám na svém stroji; v dokumentaci mám jejich souhrn a relevantní pole.

**Výsledek jedné odpovědi:** `responses=1`, `correct_responses=0`, `exploratory_accuracy=0.0`, `reasoning_split_successes=1`, `mean_total_tokens=325`, `mean_reasoning_tokens=317`, `mean_final_tokens=8`, `mean_seconds=51.3`, `mean_tokens_per_second=6.33`, `official_benchmark=false`. Podíl reasoning tokenů: **317/325 = přibližně 97,54 %**.

**Moje doplnění po kontrole `records.jsonl`:** `id=arithmetic_apples`, `expected=43`, `final_text="\n\nFinal answer: 42"`, `correct=false`, `grading_error=null`, `truncated=false`, `split_status=generated_think_block`. Tím se potvrdila **nesprávná číselná odpověď**, nikoli chyba formátu či předčasné ukončení. Souvislost s formátovým příkladem `42` v promptu zůstává **hypotézou, nikoli prokázanou příčinou**.

**Co již víme:** kontrola záznamu potvrdila nesprávné číslo 42 a validní formát i konec generování. **Co nevíme:** zda model chyboval výpočtem nebo převzal příklad 42 z promptu; jediný vzorek nedokládá 0% skutečnou přesnost modelu.

**Podezření ze zdrojového kódu:** `prompt_for()` používá u číselných úloh formátový příklad `Final answer: 42`, avšak u první otázky s jablky je správná odpověď `43`. Možný matoucí vliv ilustrativní hodnoty, **zatím nepotvrzená příčina**.

**Další krok (čeká na schválení):** metadata uloženého záznamu byla přečtena. Navrhnout opravu matoucího formátového příkladu a případný kontrolní běh; bez změny trénování, modelu nebo oficiální evaluace.

### 2026-10-09 — Návrh HRM zapsán, implementace odložena

**Moje rozhodnutí:** schválil jsem **zápis** nápadu **Hallucination Risk Monitor (HRM)** do obou verzí `IDEA.md`, nikoli jeho implementace nebo definitivní rozšíření RHAR na čtyři moduly.

**Navržený účel:** zkoumat riziko chybné a nepodložené odpovědi pomocí nestability odpovědí, signálů RPS, rekonstruovatelnosti RPD a případného ověření vůči externímu zdroji. Oddělovat faktické halucinace od jiných typů chyb.

**Metodická podmínka:** rizikové skóre není automaticky pravděpodobnost. Kalibrace na samostatných datech, Brier/ECE/AUROC, porovnání baseline, ablace a evidence výpočetní ceny jsou **návrhy pro budoucí schválení**, nikoli hotové výsledky.

**Kontrola dosavadního stavu:** aktuální `reasoning_probe.py` tuto predikci neprovádí. Výstupy HRM ani validace zatím neexistují. Kód, váhy modelu, prompty benchmarků i trénování beze změn.

**Stav:** pouze zdokumentovaný kandidát. O případném čtvrtém modulu, implementaci a experimentu se rozhodnu zvlášť.

### 2026-10-09 — RHAR schváleno jako jeden modulární organismus

**Moje rozhodnutí:** zvolil jsem jeden propojený organismus složený z RPS, RPD a TPC. Přijatý pracovní název: **RHAR — Rabbit Hollow Adaptive Reasoning**.

**Rozsah schválení:** společný **výzkumný směr a modulární koncept**. RPS má zkoumat informační pokrok, RPD zachování rekonstruovatelné informace a TPC ochranu ostatních schopností. Každý modul musí jít vyhodnotit samostatně; jejich kombinace je zatím hypotéza. Koncept nezavazuje k neefektivnímu řetězení dalších modelů během inference.

**Dokumentace:** aktualizovány `IDEA.md` a `CZ docs/IDEA.md` na shodnou dvojjazyčnou strukturu. Původní nápad LoRA destilace zůstává možnou výchozí metodou, **ne** zvoleným algoritmem.

**Co NENÍ schváleno:** konkrétní RPS/RPD/TPC výpočet, loss funkce, volba dat, nová změna modelu, trénování, GPU rozpočet, spuštění velké evaluace ani tvrzení o vědecké novosti.

**Stav měření:** už dříve zaznamenaná jedna inference 371 tokenů / správná odpověď 43; diagnostika `reasoning_probe.py` dosud čeká na první výstup z mé GPU. Žádné RHAR modelové metriky nemáme.

**Další krok k projednání:** nejdřív provést již připravenou diagnostiku baseline; potom samostatně upřesnit design a testovatelné hypotézy RPS, RPD a TPC, před každou implementací vyžádat souhlas.

### 2026-10-09 — Výběr tří výzkumných hypotéz (preferované, neschválené pro realizaci)

**Můj výběr:** pro další výzkum jsem zvolil tři směry: **Reasoning Progress Signature (RPS)**, **Reversible Proof Distillation (RPD)** a **Transfer-Protected Compression (TPC)**.

**Pracovní význam:**
- **RPS:** měřit, zda jednotlivé kroky reasoning procesu přinášejí informační pokrok, nebo jen opakování.
- **RPD:** ověřovat, zda krátký reasoning stále zachovává dost důkazní informace pro odvození správného výsledku.
- **TPC:** hlídat, že komprese nezhoršuje výrazně matematiku, práci s kódem, funkcemi ani dodržování instrukcí.

**Návrh k diskusi (dosud neschválený):** samostatně vyhodnotit tři mechanismy a teprve podle výsledků zvažovat společný prototyp. Možné pořadí RPS → RPD → TPC vyjadřuje závislost měření → zachování informace → robustnost, nikoli rozhodnutí o implementaci.

**Omezení:** Nesmíme vydávat nepodloženou světovou novost za ověřený fakt; nelze vyloučit neveřejný výzkum. Zůstává zákaz zkracování pomocí promptu, vypínání thinking režimu a trénování na oficiálních evaluačních datech.

**Stav:** pouze zapsaná preference, **žádný nový algoritmus, trénink ani experiment tímto není schválen**. Na GPU měření z diagnostického skriptu se stále čeká.

### 2026-10-09 — Diagnostický skript pro reasoning (schváleno)

**Moje rozhodnutí:** odsouhlasil jsem vytvoření diagnostického skriptu a výslovně trvám na tom, že prompt engineering ani vypínání uvažování nenahrazují výzkumný algoritmus.

**Implementace:** `diagnostics/reasoning_probe.py` a `tests/test_reasoning_probe.py`. Diagnostika má 6 ručně vytvořených otázek ze tří oblastí, defaultně měří první 3. Fixuje revizi původního `Qwen/Qwen3-0.6B`, používá `enable_thinking=True`, standardní sampling (temperature 0.6, top-p 0.95, top-k 20), jen požaduje formát `Final answer: ...`. Změny vah, adaptérů a oficiální evaluace: **žádné**.

**Výstupy:** `runs/diagnostics/<UTC>/config.json`, `records.jsonl`, `summary.json`. Měření: počet celkových/reasoning/final tokenů, správnost, čas, tokeny/s, PyTorch alokace a orientační opakování. Při chybných reasoning značkách se počty nezamlčují jako nula, ale vrací se neznámá hodnota.

**Ověření:** **9/9 nových CPU jednotkových testů úspěšných** v odděleném lokálním testovacím prostředí; `--dry-run` ověřen. **Nový skript ještě nebyl spuštěn na mé GTX 1070 Ti; počet 9 se netýká plné oficiální sady testů.**

**Stav:** implementováno a popsáno CZ/EN. Čeká na první lokální GPU měření z mého lokálního běhu; o trénovacím algoritmu se dosud nerozhodovalo.

### 2026-10-09 — První inference Qwen3-0.6B (baseline průzkum)

**Stav:** ověřeno v mém prostředí (Kali Linux / WSL2; GTX 1070 Ti); zatím **nejde** o oficiální evaluaci BottleCap AI.

**Postup:** načten originální `Qwen/Qwen3-0.6B` pomocí Transformers na GPU ve `torch.float16`. Jedna jednoduchá matematická úloha: 5 krabic × 12 jablek − 17 prodaných. Režim uvažování zapnut; předchozí připravený skript používal seed 9001, temperature 0.6, top-p 0.95, top-k 20 a max_new_tokens 512.

**Naměřeno v mém terminálu:**
- Finální odpověď: `Final answer: 43` (**správně**).
- Celkem vygenerováno **371 tokenů** (včetně odpovědi a případného reasoning).
- Doba generování **61,45 s**.
- Průměrná rychlost **6,04 tokenu/s**.
- `torch.cuda.memory_allocated()`: **1,12 GiB** (alokace PyTorch, nikoli celková VRAM nebo peak).

**Omezení:** pouze jedna otázka a jeden běh. V deníku jsem zachoval koncovou část odpovědi a metriky, ne úplný reasoning trace; délku čistě reasoning úseku proto nemáme změřenou. Nejde o výsledky benchmarků SVAMP/MBPP+/BFCL/IFEval ani o výsledek trénování či optimalizace modelu.

**Další návrh (čeká na schválení):** vytvořit reprodukovatelné měření rozdělené na reasoning/finální odpověď pro několik různých tréninkově nezávislých příkladů. Neměnit zatím model ani benchmarková pravidla.

### 2026-10-09 — Uspořádání jazykových souborů

**Schválený rozsah:** podle svého rozhodnutí přesunout všechny české MD dokumenty do `CZ docs/`. Anglické `README.md` ponechat v kořeni pro snadné čtení při posuzování BottleCap AI. Python, model a evaluační nastavení beze změn.

**Ověření:** všechny relativní odkazy a zachování dokumentů zkontrolovat po přesunu. **Odevzdání projektu:** postup vysvětlen, nic nebylo odesláno.


### 2026-10-09 — CUDA výpočet ověřen na lokální GPU

**Stav:** ověřeno v mém prostředí v Kali Linux / WSL2.

**Provedeno:** v aktivovaném `.venv` (Python 3.11) byl spuštěn jednoduchý PyTorch CUDA test s `torch.ones(256, device="cuda")` a součtem `(tensor * 2).sum()`.

**Výsledek:** PyTorch `2.6.0+cu118`, CUDA runtime `11.8`, `torch.cuda.is_available(): True`, GPU `NVIDIA GeForce GTX 1070 Ti`, compute capability `(6, 1)`, výsledek GPU výpočtu `512.0`.

**Upozornění:** při importu se objevilo `Failed to initialize NumPy: No module named 'numpy'`; tento warning test CUDA nezastavil.

**Co to neprokazuje:** model Qwen3-0.6B nebyl spuštěn ani trénován, oficiální benchmark nebyl proveden.

**Další návrh (čeká na schválení):** doinstalovat kompatibilní NumPy, znovu ověřit běh a poté projednat první inferenční pokus s Qwen3-0.6B.


### 2026-10-09 — Pravidla spolupráce a jazykové klony

**Stav:** pravidla jsem si nastavil; dokumentace se doplňuje na vývojové větvi.

**Provedeno:** zaznamenáno, že DEV-NOTES je vývojový deník, nikoli jen seznam úkolů. Doplněna pravidla schvalování významných kroků. Dokončeny české a anglické jazykové protějšky dokumentace: README, IDEA, HARDWARE, DEV-NOTES a oficiální zadání. Opraveny relativní odkazy ve zkopírovaném originálu.

**Ověření dokumentace:** zkontrolováno 10 souborů; všechny relativní odkazy fungují a české zadání zachovává 19 nadpisů, všechny řádky tabulek a 8 nezměněných bloků ukázkového kódu.

**Ověření:** můj předchozí běh jednotkových testů 87 OK, 2 přeskočené; pro novou dokumentaci nebylo provedeno nové trénování ani spuštění benchmarku.

**Čeká na schválení:** konkrétní algoritmus komprese reasoning procesu, způsob trénování, první GPU experiment a případné změny v kódu.

## Přehled dosavadního stavu

## Stav — 9. 10. 2026

- [x] Založen samostatný repozitář a vývojová větev `feat/reasoning-compression`.
- [x] Převzaty oficiální Python skripty, testy a licence BottleCapAI.
- [x] Popsána skutečná PC konfigurace a limity GPU.
- [x] Připraven výzkumný plán `IDEA.md`.
- [x] Spuštěny lokální unit testy (Kali Linux / WSL2, Python 3.14.7): **87 testů OK, 2 přeskočeny** (EvalPlus a BFCL zatím nejsou stažené), běh 0,321 s.
- [x] Zprovozněn izolovaný Python **3.11.17** v `.venv` na Kali Linux / WSL2; ověřil jsem 9. 10. 2026.
- [x] `nvidia-smi` ve WSL2 detekuje **NVIDIA GeForce GTX 1070 Ti (8192 MiB)**, driver 582.78, nvidia-smi 580.178.01; v okamžiku kontroly 882 MiB obsazeno. Zobrazené `CUDA Version: 13.0` udává schopnost driveru, nikoli funkčnost PyTorch.
- [x] Ověřeny CUDA výpočty v **PyTorch 2.6.0 + cu118** na GPU (GTX 1070 Ti, compute capability 6.1, testovací výsledek 512.0).
- [x] Připraveny knihovny Transformers/Accelerate pro první úspěšnou inferenci Qwen3-0.6B (ověřeno mým během).
- [ ] Prověřit bubblewrap sandbox před evaluací MBPP+ (varování: dostupný jen slabší fallback s resource limity).
- [ ] Připravit tréninková data mimo eval benchmarky.
- [ ] Provést baseline smoke test a uložit run artefakty.
- [ ] Vygenerovat správné, krátké reasoning traces.
- [ ] Trénovat LoRA adaptér a provést validaci.
- [ ] Porovnat plnou evaluaci baseline vs kandidát na podporované GPU.
- [ ] Sepsat reprodukovatelný závěrečný report včetně negativních výsledků.

## Poznámky

Benchmarky v projektu dávají úlohám osm samplů na otázku při plném běhu. Plná sada obsahuje 2 759 zadání. Nezaměňovat syntetické metriky s oficiální evaluací.

Po vývoji na feature větvi otevřít PR do `main` až po validaci.
