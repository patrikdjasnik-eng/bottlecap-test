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

### 2026-10-10 — 📚 Co jsem se dnes naučil: od SFT k bezpečnému CEP 002 (souhrn dne)

**Typ záznamu:** vlastní poučení z dnešní práce; souhrn již provedených experimentů a samostatně **navrženého** algoritmu, nikoli nové měření nebo implementace CEP 002.

- **Model nemusí selhat kvůli neznalosti čísla, ale kvůli ztrátě vztahů mezi podmínkami.** U úlohy s kódem 536 obyčejné SFT 003 správně odvodilo `(Y+2)+3Y=14` a skončilo za 139 tokenů. CEP Pilot 001 s vyšší lexikální vahou čísel a operátorů spotřeboval 244 tokenů, sice zmínil správné řešení, ale nakonec vybral chybných 312. Samotné zvýhodnění číslic, kratší text ani „správný mezivýsledek někde v reasoning“ proto nestačí; musí sedět celý postup i finální odpověď.
- **Úspěšnost a tokeny musím sledovat společně a párově.** Na 6 diagnostických úlohách vyšlo SFT 3/6 vs. CEP 2/6, na další sadě 20 úloh 9/20 vs. 9/20. V Evaluation 006 (60 jiných matematických úloh, jeden seed) pak SFT dosáhlo 19/60 a 5 769 tokenů, zatímco CEP 001 23/60 a 5 266 tokenů (o 503 / 8,72 % méně). CEP opravilo 8 odpovědí, ale 4 původně správné pokazilo. **Tento lokální vzorek je povzbudivý, ne důkaz přenosu na nové domény, oficiálního skóre ani stabilního zlepšení.**
- **Čistota experimentu je stejně důležitá jako algoritmus.** Při porovnávání LoRA jsem se naučil hlídat aktivní adapter: opakovaně dekorovaný PEFT backbone může znehodnotit srovnání. Evaluation 006 používá pro každý adapter čistý samostatný model. Zapisovat seed, stejné prompty, tokenový limit, dokončení i průběžné artefakty; již prohlédnutých 60 otázek nesmí zpětně sloužit jako nový nezávislý holdout nebo trénovací data.
- **CEP 002 není „pamatuj si každou odpověď“.** Chci Qwen učit *ověřenou proceduru*: fakta ze zadání → nezbytné vztahy → kontrola použitelnosti a všech podmínek → výsledek. **VPS** nezávisle kontroluje kroky, **XP** uchovává správné i chybné postupy s důvodem a může vybrat maximálně tři ověřené použitelné varianty, **REC** dovoluje po novém důkazu znovu posoudit starší trénovací případ. Pokud řešení 10 ukáže chybu u řešení 3, není to samo o sobě důkaz: původní případ se musí ověřit znovu.
- **Novější odpověď není automaticky pravdivější.** **Verified Lock** chrání nezávisle ověřené původní řešení před chybnou „opravou“. Nové tvrzení vyvolá jen přezkum; zámek lze verzovaně opravit pouze na základě samostatného důkazu. Rozpor nebo selhání verifieru znamená pozastavení a vyloučení sporného případu z nového tréninku, nikoli přepsání historie. Ani verifier není neomylný.
- **Chci měnit váhy modelu, ne stavět kolem něj zbytečnou aplikaci.** CEP 002 je zatím návrh offline přípravy přípustných trénovacích dat a následné standardní LoRA. Qwen má fungovat i bez zvláštní externí paměti nebo inference orchestrátoru; oficiální BottleCapAI evaluace se nesmí upravovat. Podobné směry již existují, takže originalita ani zlepšení nejsou prokázané.

**Co jsem skutečně ověřil:** existující SFT 003 a CEP Pilot 001 byly lokálně porovnány; CPU/GPU práce a konkrétní výsledky jsou rozepsané níže. **Co jsem dnes jen navrhl:** CEP 002 (VPS + XP + REC + Verified Lock); žádná jeho implementace, LoRA CEP 002, nové CEP 002 CPU testy ani nezávislý experiment zatím neproběhly. Starší níže uvedený záznam „Konec dne“ zachycuje pouze dřívější fázi CPU preflightu, **ne konečný stav celého 10. října**.

**Další krok — zatím plán, vyžaduje samostatné schválení:** malý CPU prototyp verifieru na 10–20 ručně ověřených povolených trénovacích případech, testy falešné opravy a konfliktu důkazů; až pak kontrolované A/B/C srovnání obyčejného SFT, VPS+XP a VPS+XP+REC na novém nedotčeném výběru. Pravidlo **„bez zelené ani krok“** platí dál. 🐇🛡️

### 2026-10-10 — 🛡️ CEP 002 v0.3: Verified Lock — ochrana správně ověřených zkušeností

**Rozhodnutí uživatele:** do CEP 002 zahrnout pojistku proti tomu, aby Qwen přijal pozdější špatný výsledek jako pravdu a zpětně „opravil“ dřívější správné řešení.

**Zapsaný návrh:** Verified Lock **není čtvrtá architektonická služba**. Jde o stav a kontrolní pravidlo ve VPS + REC. Kompletní řešení získá VERIFIED_LOCKED jen po nezávislém ověření původních faktů, mezikroků, finální odpovědi a dokončení, s verzí verifieru a hashem kontraktu. Nový výstup Qwenu smí pouze vyvolat RECHECK_PENDING. Původní řešení znovu projde → REJECTED_CORRECTION; prokazatelně chybné a nově ověřené řešení → neztrátová verzovaná oprava; spor v kontraktu/verifieru → LOCK_DISPUTED / REVIEW_REQUIRED, automaticky nic nepředat do tréninku. Zámek není důkazem neomylnosti samotného verifieru.

**Dokumentace:** aktualizovány český [CEP-002.md](CEP-002.md), anglický [CEP-002.en.md](../docs/CEP-002.en.md) a oba IDEA soubory. Pseudokód vylučuje sporné záznamy z nového trénovacího výběru. Navrženy CPU testy falešné opravy, nejistého důkazu, konfliktu verifierů, nesprávné derivace a zachování historie. Počítat false_correction_proposals, accepted_verified_repairs a disputed_locks.

**Stav:** **POUZE NÁVRH**, žádný funkční Verified Lock, žádné nové modelové odpovědi, CPU unit testy nové funkce, GPU ani LoRA trénink. Implementaci a experiment uživatel schválí samostatně. Návaznost na BottleCapAI: jen offline zpracování přípustných trénovacích dat, finální model bez externí runtime paměti a beze změn oficiální evaluace.

### 2026-10-10 — 🧠 RHAR-CEP 002 v0.2: jednoduchý algoritmus VPS + XP + REC (pouze návrh)

**Rozhodnutí uživatele:** podrobně dopracovat nový směr CEP 002 včetně mého návrhu ochrany nezbytných odvozovacích kroků, ale **bez zbytečné systémové složitosti**. Vysvětlit algoritmus přímo v konverzaci a zapsat jej dvojjazyčně do repozitáře.

**Skutečně provedeno:** nový [CEP-002.md](CEP-002.md) a [English](../docs/CEP-002.en.md), odkazy z obou IDEA.md i obou README. Verze 0.2 určuje **VPS** (deterministická kontrola kroků a vazeb na zadání), **XP** (maximálně tři reálně existující ověřené postupy) a **REC** (nově ověřená zkušenost spustí opětovnou kontrolu starší *trénovací* úlohy, původní trace zůstává neměnný). Důraz na učicí trace **fakta → nutné vztahy → kontrola podmínek → finální odpověď**, nikoli pouhé zkrácení textu.

**Záměrná jednoduchost:** jeden dávkový CPU verifier, JSONL evidence, 10–20 ručně zkontrolovaných testovacích trénovacích příkladů pro budoucí implementaci, standardní LoRA. Žádná vektorová databáze, multi-agentní runtime, RL/DPO, automatický online trénink ani zvláštní inference orchestrátor.

**Experiment, pouze návrh:** A = obyčejné SFT, B = VPS+XP, C = VPS+XP+REC, porovnat C vs. B za odpovídajících podmínek na **nových neviděných příkladech**; zaznamenat správnost, tokeny, dokončení a falešné opravy. Starých 60 prohlédnutých otázek z Evaluation 006 dál nepředstírat jako nezávislý holdout. Nepoužít SVAMP, MBPP+, BFCL ani IFEval pro trénink. Oficiální test musí zůstat nezměněný a Qwen/LoRA standardně načitatelný.

**Stav:** dokumentace hotová; CEP 002 algoritmus **není implementován ani ověřen**, nejde o prokázaně originální metodu a nemáme žádný jeho naměřený přínos. **Nebyly spuštěny CPU testy CEP 002, GPU, nové inference ani trénování.** Implementace a experiment až po dalším výslovném souhlasu.

### 2026-10-10 — 🧠 CEP 002: přidán návrh REC (zpětná oprava zkušeností)

**Rozhodnutí uživatele:** rozšířit nový výzkumný směr CEP 002 o **REC — Retroactive Experience Correction**. Nový postup ověřený při pozdější *trénovací* úloze může vyvolat přezkum staršího uloženého řešení (např. úloha 10 → opětovné ověření úlohy 3). Model se o chybě nedozví automaticky: je potřeba historie příkladů, spouštěč přezkumu a nezávislý verifier. Nejde o automatické přeučování vah během inference.

**Navržené komponenty:** verzovaná paměť řešení, maximálně tři reálně existující ověřené použitelné postupy, kontrola skutečných mezikroků, historie původní chyby i opravy (XP+, XP−, REC), zobecnění na další povolené trénovací varianty a až pak případné LoRA učení s novým holdoutem. Původní odpovědi nepřepisovat. LLM hodnotitel sám nestačí jako důkaz.

**Kontrola souladu s BottleCapAI:** prostudováno původní zadání v `docs/UPSTREAM-README.md`. Vlastní post-training metoda a LoRA jsou povoleny; při oficiálním testování musí standardně načitatelný Qwen3-0.6B/LoRA běžet bez REC runtime doplňku, s thinking zapnutým a beze změn hodnoticího protokolu. Žádné trénování na SVAMP, MBPP+, BFCL ani IFEval. Již prohlédnutých 60 úloh z Evaluation 006 nesmí současně sloužit jako trénink a nezávislý holdout. Bezpečnější je připravit REC na jiných přípustných trénovacích otázkách.

**Skutečně provedeno:** návrh doplněn do českého `CZ docs/IDEA.md` a anglického `IDEA.md`; tento zápis do DEV-NOTES. **Neprovedeno:** REC implementace, CPU/GPU testování REC, modelové generování ani trénování CEP 002. Další kroky vyžadují zvláštní souhlas.

### 2026-10-10 — 🐇 GPU Canary 002 a RHAR 003–007: poučení, chyby a opravy

**Stav:** dokumentační souhrn skutečných lokálních výstupů a implementovaných změn. Žádné trénování, úprava vah, oficiální BottleCapAI benchmark ani prokázaná úspora tokenů. Původní artefakty v `runs/` nechávám nedotčené.

#### 🖥️ Preflight a první správná inference

- V Kali/WSL2 prošlo `Ran 190 tests`, `OK (skipped=2)`. Později po opravách RHAR 006 prošlo `Ran 213 tests in 1.255s`, `OK (skipped=2)`. Dva skipy nejsou dvě chyby, jejich důvod je vhodné před oficiální evaluací samostatně prověřit.
- GTX 1070 Ti 8 GB: PyTorch `2.6.0+cu118`, CUDA dostupná, compute capability `6.1`, skutečný FP16 výpočet OK. Lokální cache obsahuje připnutý Qwen3-0.6B snapshot `c1899de289a04d12100db370d81485cdf75e47ca`.
- GPU Canary 002 (`runs/canary-002/20261010T102914Z/`) doběhl s exit code 0: `arithmetic_apples`, seed 9001, správná odpověď 43, `correct=true`, `truncated=false`, **423 tokenů = 415 reasoning + 8 final**, 82,552 s, 5,124 tok/s, PyTorch peak 1,185 GiB. Dřívější Experiment 002 měl chybných 42, 325 tokenů a 51,3 s; nelze z nich vyvozovat zlepšení nebo zhoršení za nesrovnatelných podmínek.
- Když po spuštění nebyl hned výstup, kontrolovali jsme `nvidia-smi`; pozdější klidová VRAM sama neprokazovala zaseknutí. Rozhodující byl uložený report a exit code 0. Poučení: neinterpretovat jeden snapshot GPU ani ticho terminálu jako selhání.

#### 🧠 Offline výzkum a skutečná zjištění

- **RHAR 003:** 265 slov, 5 odstavců, 3 opakované čtyřslovné sekvence; podíl reasoningu 98,11 %. Lexikální opakování samo nedokazuje nadbytečný reasoning.
- **RHAR 004:** text byl rozdělen na kroky; heuristika označila 4 úseky k ruční kontrole. Původně 27 kroků, po opravě oddělování vět se stejný text rozpadá na 33 kroků. Počet kroků proto závisí na segmentaci a není měřítkem tokenů.
- **RHAR 005:** detekováno 6 explicitních matematických operací a 2 opakování (např. `5 times 10` / `10*5` a `5 times 2` / `2*5`). Parser nerozpozná každou přirozenojazyčnou formu; absence označení neznamená absenci opakování.
- **RHAR 006:** všech 6 rozpoznaných výpočtů je aritmeticky konzistentních. Kandidátní checkpoint: `43 apples remaining`, znakový offset konce 646; dalších 616 znaků uvažování. Jde o kandidátní textový bod, ne prokázané bezpečné předčasné ukončení.
- **RHAR 007:** offline retokenizace připnutým tokenizerem dává 423 tokenů stejně jako uložený počet; checkpoint odpovídá hranici po 200 zpětně tokenizovaných tokenech, 223 jich následuje. Stav `retokenized_boundary_only`, původní ID tokenů nemáme. **223 není naměřená ani zaručená úspora.** `measured_token_savings=null`, `early_stop_safety_verified=false`.

#### 🐛 Konkrétní regresní chyby a jejich opravy

1. `test_arithmetic_consistency` vracel `[None, None]` místo `[True, True]` a `test_detect_wrong_arithmetic` `None` místo `False`: regex pro výsledek odmítal číselnou hodnotu následovanou tečkou na konci věty. Upravil jsem hranici regexu, aby tečka nebránila rozpoznání výsledku; správný i nesprávný výpočet pak lze hodnotit.
2. `test_arithmetic_and_repeat` očekával 3 kroky, dostal 2: rozdělovač vět akceptoval po tečce pouze velké písmeno, nikoli číslo. Rozšířil jsem hranici segmentace o číslice. To zároveň změnilo indexování kroků ve starších reportech — nezaměňovat 27 a 33 kroků za změnu modelu.
3. V RHAR 004 samotné regexy rovnic s `=` neodhalovaly přirozenojazyčné operace. RHAR 005 proto přidal normalizaci zápisů `times`, `*`, `×`, `minus` atd. a explicitní označení opakovaných výskytů, ale bez tvrzení o sémantické nadbytečnosti.
4. RHAR 006 musel zpřesnit fráze checkpointu (např. `43 apples remaining`) a ignorovat nejednoznačnou identifikaci správného výsledku. RHAR 007 přidal fail-closed stav pro neodpovídající počet tokenů, nejednoznačné offsety a checkpoint uvnitř tokenu.
5. Vždy jsem po opravách vyžadoval kompletní lokální regresní sadu; při červené sadě `Ran 213 tests`, `FAILED (failures=3, skipped=2)` jsme nepokračovali k experimentu, dokud následný běh nebyl zelený.

#### ✅ Co si odnáším a co dál

- Délka odpovědi, počet odstavců, znaků ani heuristických opakování nejsou automaticky úsporou generovaných tokenů. Správnost a skutečné tokeny musím posuzovat společně.
- Přesná revize modelu, seed, lokální artefakty a oddělení GPU inference od CPU analýzy udržují pokusy dohledatelné.
- **Následující návrh RHAR 008:** do budoucích diagnostických záznamů ukládat originální vygenerovaná tokenová ID a validační metadata, přidat testy integrity a teprve poté dělat závěry o přesných hranicích. Dosud neschváleno ani neimplementováno.
- Automatické CPU CI je přidané na feature větev; lokální testy prošly, ale tento zápis netvrdí nový zelený CI běh bez jeho doložení.

**Bilance:** 213 spuštěných testů (2 přeskočené), 1 správný GPU canary, offline RHAR 003–007, 3 regresní chyby opravené, **0 prokázaných tokenových úspor, 0 trénování**. 🐇🛡️



### 🌙 2026-10-10 — Konec dne / Co jsme se dnes naučili

**Stav dne: práce pro dnešek končí.** Dnešní cíl nebyl trénovat Qwen, ale postavit bezpečnou, reprodukovatelnou přípravu výzkumu **RHAR — Rabbit Hollow Adaptive Reasoning**. Začali jsme CPU plánovačem a skončili plně zelenou sadou **103/103 testů** (`Ran 103 tests in 0.917s`, `OK`) a ověřeným generovacím `--dry-run`. To je skutečný výsledek dne, **ne** naměřená úspora tokenů.

**Co jsme dnes reálně zvládli:** z připnuté revize `openai/gsm8k` jsme na Kali ověřili SHA-256 trénovacího Parquet souboru, načetli **7 473** záznamů a deterministicky vybrali **12 kandidátních matematických úloh**. Připravili jsme přesný plán **12 × 3 = 36** budoucích generací modelu `Qwen/Qwen3-0.6B`, seedy `9001, 9002, 9003`, zapnutý thinking, temperature `0.6`, top_p `0.95`, top_k `20` a limit `512` nových tokenů. Před skutečným během generátor ověřuje vybraných 12 ID, hashe lokálních vstupů a dokončený audit překryvu. Naše testovací brány dnes postupně narostly z **45 → 61 → 79 → 103** a každá kompletní sada byla po dokončení příslušného kroku zelená.

**Co jsme se naučili z chyb:** 
- **Reprodukovatelnost není detail.** Bez připnuté revize datasetu/modelu, SHA-256, pevných seedů a přesného promptu by výsledky nešly férově porovnat. Gold odpovědi patří do kontroly správnosti, **nikoli do promptu**.
- **Závislosti mohou zablokovat i zdánlivě jednoduchý CPU krok.** `pyarrow` nejprve chybělo a pak jeho novější verze vyžadovala NumPy 2.x, zatímco Kali mělo NumPy `1.26.4`. Naučili jsme se řešit konflikt cíleně: kompatibilní `pyarrow==16.1.0`, ne nekontrolovaný upgrade celé AI sestavy.
- **Nulový počet nalezených shod neznamená dokonalý důkaz čistoty.** Samostatně jsme porovnali našich 12 GSM8K otázek s **2 759** texty ze šesti připnutých zdrojových souborů SVAMP, MBPP+, BFCL a IFEval. Audit našel **0 přesných či výrazně podobných textových shod**, ale **nevylučuje sémantické parafráze**, a proto výsledné kandidáty ponecháváme jen jako `review_only`.
- **U reasoning modelu rozhodují skutečně vygenerované tokeny.** Rozlišujeme reasoning a final, správně pracujeme s předvyplněným `<think>`, hranicemi `</think>` a ukončovacími tokeny. `reasoning_tokens + final_tokens` musí odpovídat celkovému počtu vygenerovaných tokenů. Neznámý rozpad není nula; useknutý nebo nesprávný výstup nesmíme vydávat za úspěšný.
- **Zelené CPU testy ověřují přípravu, ne kvalitu modelu.** `--dry-run` ověřil všechny tři lokální vstupy i plán, ale **nenačetl model, nepoužil GPU, negeneroval odpovědi a nic netrénoval**. Zatím nemáme srovnání efektivity ani důkaz zlepšení RHAR. Nezaměňujeme krátkou odpověď za správnou.

**Technické poučení pro další vývoj:** malý, auditovatelný experiment s jasnými stop podmínkami je lepší než drahý běh bez kontroly. Důležitá jsou oddělená oprávnění pro **přípravu → CPU validaci → GPU inferenci → případné trénování**. Vytvořené skripty umí budoucí GPU běh jen po dvou explicitních přepínačích; bez mého samostatného schválení se nic nespouští.

**Zítra / příště (plán, nikoli provedená práce):** nejprve pouze CPU kontrola dostupnosti lokální cache Qwenu, kompatibility CUDA/FP16, volné VRAM a návrh časového limitu, ukládání průběžných dat a podmínek zastavení. Teprve potom se samostatně rozhodnu, zda dovolit krátký canary test nebo celých **36 generací**. **GPU inference, LoRA/trénování a oficiální benchmark dnes neproběhly ani nejsou pro další krok automaticky schválené.**

**Dnešní bilance:** **103/103 CPU testů OK · 12 ověřených kandidátů · 2 759 porovnaných evaluačních zadání · 0 heuristických shod · 36 pouze naplánovaných generací · 0 GPU běhů · 0 trénování.** 🐇🛡️

### 2026-10-10 — ✅ Safe Start generátor: 103/103 CPU testů zelených v Kali

**Skutečně ověřeno v mém Kali/WSL2:** společná sada `tests.test_offline_selector`, `tests.test_reasoning_probe`, `tests.test_safe_start_plan`, `tests.test_safe_start_data`, `tests.test_safe_start_overlap` a `tests.test_safe_start_generate` skončila `Ran 103 tests in 0.917s`, `OK`. Tím je potvrzena nová regresní brána, nikoli skutečný GPU experiment.

**Skutečný příkaz:** `python -m diagnostics.safe_start_generate --dry-run` potvrdil `status=plan_only`, model `Qwen/Qwen3-0.6B` revize `c1899de289a04d12100db370d81485cdf75e47ca`, `thinking_enabled=true`, 12 přesně původních GSM8K train kandidátů × 3 seedy (`9001,9002,9003`) = **36 plánovaných generací**, sampling temperature 0.6 / top_p 0.95 / top_k 20 a `max_new_tokens=512`.

**SHA-256 lokálních vstupů z ověřeného dry-runu:** `questions=ebb3595c677ec6a660da3ff8731448182674967beab4d5e7f5256347541d32bc`; `selection_report=0760c4825de4e18bbbfcb6429dd543dcfa7fcc9e18dae83a118bccdf2b3cb89a`; `overlap_audit=7b9443abf9e2960084bfaf6472ddf049ff057d4f4e1c889a4c01902a2ccc7ca4`. Tyto hashe vážou dry-run na konkrétní lokální soubory a obsah auditu, ale nejsou důkazem absence všech sémantických parafrází.

**Výslovné hranice:** `gpu_used=false`, `model_loaded=false`, `model_downloaded=false`, `training_performed=false`, `training_approved=false`, `official_benchmark=false`, `model_generations_performed=0`. **Nebyly vyrobeny nové modelové odpovědi ani změřena tokenová úspora.**

**Další rozhodnutí čeká na mé schválení:** před skutečnými 36 CUDA generacemi samostatně probrat časový/GPU rozpočet, předběžné ověření lokální cache a stop podmínky, případně krátký canary běh jen po výslovném povolení. Nic nyní nespouštět; záznamy zůstávají `review_only`.


### 2026-10-10 — 🐇 RHAR Safe Start: GPU skript připraven, spuštění NEschváleno

**Moje schválení:** po `Ran 79 tests in 0.832s` / `OK` a kontrolním auditu 12 GSM8K train kandidátů proti 2 759 oficiálním zadáním (0 nalezených heuristických textových shod, parafráze nevyloučené) jsem odsouhlasil **výhradně implementaci budoucího GPU skriptu a jednotkových CPU testů**. **Žádný nový GPU běh, inference, download modelu ani trénování nebyly povoleny nebo provedeny.**

**Přidané soubory:** `diagnostics/safe_start_generate.py` a `tests/test_safe_start_generate.py` (**24 nových testovacích metod**). Generátor předem ověřuje 12 přesných otázek, SHA-256 obou review manifestů i všech šest záznamů auditu; bez aktuálního úspěšného screeningu odmítá pokračovat. Z konfigurace `safe_start_plan.py` přebírá model Qwen3-0.6B, připnutou revizi, tři seedy 9001/9002/9003, thinking zapnutý, sampling 0.6/0.95/20 a 512-tokenový limit. Prompty neobsahují gold odpověď ani instrukci ke zkrácení uvažování.

**Ochrany:** `--dry-run` zůstává CPU-only, bez modelu, sítí či GPU. Budoucí generování vyžaduje oba explicitní přepínače `--execute` a `--confirm-gpu-36` **a můj samostatný pozdější souhlas**. V GPU režimu je povolen jen místní již uložený model (`local_files_only=True`), CUDA float16, žádný automatický download. Délky reasoning + final musí dát skutečně generované tokeny; nesprávné a truncated odpovědi neuznávám za správné. Nekompletní výsledek se nevydává za dokončených 36 vzorků; každé spuštění vytváří novou ignorovanou složku a nesmí přepsat předchozí data. Záznamy lze předat `diagnostics/offline_selector.py`, ne přímo trénování.

**Ověření:** v izolovaném lokálním prostředí prošlo **23 CPU testů prototypu**, s lehkými kopiemi závislostí; **novou přesnou sadu 24 testů na GitHub větvi ani všech 103 společně jsem ještě nepotvrdil na Kali**. Počet 103 je plánovaných 79 + 24. Bez zeleného skutečného Kali výstupu žádný další krok.

**Dokumentace:** [SAFE-START-GENERATION.md](SAFE-START-GENERATION.md) / [English](../docs/SAFE-START-GENERATION.en.md). Další jediný doporučený příkaz: všech 103 CPU testů a `python -m diagnostics.safe_start_generate --dry-run`; nikoli GPU.


### 2026-10-10 — ✅ RHAR Safe Start: 79/79 CPU testů zelených na Kali

**Skutečný výstup terminálu:** `Ran 79 tests in 0.832s` a `OK`. Potvrzuji společný běh všech 79 CPU unit testů: offline selektor, reasoning diagnostika, plánovač Safe Start, výběr GSM8K dat a nový audit překryvu. Toto je první doložený **celý společný** běh aktualizované sady na mém Kali/WSL2.

**Předchozí doložený audit:** `python -m diagnostics.safe_start_overlap --download` úspěšně porovnal 12 připnutých GSM8K kandidátů se **2 759 zadáními** ze šesti souborů SVAMP, MBPP+, BFCL a IFEval a nahlásil **0 textových shod** podle implementované heuristiky. `semantic_paraphrases_ruled_out=false` a `overlap_audit_exhaustive=false`, takže ani tento výsledek neprokazuje vyloučení všech sémantických parafrází.

**Uzavřená brána:** CPU příprava, 12 kandidátů, 36 budoucích plánovaných pokusů, kontrola integrity souborů a regresní testy jsou zelené. Neproběhlo žádné nové generování Qwen3-0.6B, použití GPU, trénování, ani oficiální benchmark. `review_only` a `training_approved=false` zatím zůstávají beze změny.

**Další rozhodnutí (dosud neschváleno):** samostatně projít rozpočet, stop podmínky a implementaci první GPU generovací fáze **12 otázek × 3 seedy = 36 generací**, bez LoRA a bez automatického použití výstupů pro trénování. **Bez mého souhlasu GPU nespouštět.**


### 2026-10-10 — ✅ Skutečný CPU audit překryvu: 0 shod v 2 759 evaluačních otázkách

**Skutečně provedeno na Kali / WSL2:** `python -m diagnostics.safe_start_overlap --download` doběhl úspěšně a vypsal `audit_result=no_matches_in_screened_sources`. Porovnal **12 původních GSM8K train kandidátů** (připnutá revize `740312add88f781978c0658806c59bc2815b9866`) s texty **2 759 zadání** ze všech šesti deklarovaných souborů a čtyř rodin benchmarků.

**Rozpad skutečného auditu:** SVAMP 1 000, MBPP+ 378, BFCL simple_python 400, BFCL multiple 200, BFCL irrelevance 240, IFEval 541. **Nalezeno 0 potenciálních přesných nebo heuristicky podobných shod**, `potential_matches=[]`. Zdrojové soubory SVAMP a MBPP+ prošly předem známou kontrolou SHA-256. Skutečné SHA-256 připnutých BFCL souborů: `82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991`, `aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a`, `2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6`; IFEval: `67ffeee0fcb87c317c5b08a2de85557b4a7e96ada6178aa645b4954fe4b53d49`. U BFCL/IFEval jsou tyto hashe pouze **zaznamenané**, bez nezávislé předem fixované kontroly (`known_sha256_pin_checked=false`).

**Interpretace:** výsledek platí **jen pro šest deklarovaných souborů a dané pravidlo podobnosti**. `semantic_paraphrases_ruled_out=false` a `overlap_audit_exhaustive=false`: neprokazuje nulovou kontaminaci ani nevylučuje sémantické parafráze. `status=review_only`, `training_approved=false`; dataset ani původní výběr nebyly změněny. **Žádná inference, GPU, trénování ani oficiální evaluace** (`gpu_used=false`, `model_generations_performed=0`, `training_performed=false`, `official_benchmark_run=false`).

**Testovací brána:** předchozích 61/61 testů bylo potvrzeno, ale **samostatný kombinovaný běh 79/79 v uživatelově novém terminálovém výstupu zatím není doložen**. O schválení generování ani trénování nyní nerozhoduji. Nejprve získám zelený výstup všech 79 CPU testů, pak se zvlášť rozhodnu o další experimentální fázi.

### 2026-10-10 — 🛡️ Schválena CPU kontrola překryvu 12 GSM8K kandidátů vůči oficiálním otázkám

**Rozhodnutí:** po úspěšném **61/61 CPU testů v Kali (`Ran 61 tests in 0.600s`, `OK`)** a zjištění, že nemám lokální `questions/questions.jsonl`, jsem výslovně schválil **pouze přípravu a stažení připnutých oficiálních evaluačních textů kvůli decontamination screeningu**. Nepovolil jsem inference, GPU, trénování ani oficiální evaluační běh.

**Implementace:** nový izolovaný `diagnostics/safe_start_overlap.py` a `tests/test_safe_start_overlap.py`. Kontroluji přesně šest vstupních souborů ze čtyř rodin (SVAMP, MBPP+, 3 BFCL v4 kategorie, IFEval) na revizích z **nezměněného** `utils/eval/benchmarks.py`. SVAMP a MBPP+ ověřuji také proti známému SHA-256. BFCL/IFEval jsou připnuté Git commitem; zaznamenávám skutečný hash souboru. Ve všech případech extrahuji pouze texty zadání, nikoli gold answers. Přímý downloader oficiální evaluace ani jeho verifiery nespouštím.

**Ochrany:** před síťovým přístupem ověřím SHA-256 a ID našich **stávajících 12 otázek** proti původnímu `selection-report.json`; žádný automatický nový výběr. Chybějící zdroj, selhání hashe či neplatné schéma zruší audit bez pozitivního reportu. Finální ignorovaný `data/safe-start/overlap-audit.json` obsahuje jen evidenci, počty, hashe a indexy potenciálních shod. Nikdy nedeklaruje úplnou odolnost proti parafrázím ani `training_approved=true`.

**Ověření:** nových **18/18** unit testů prošlo **v izolovaném místním CPU prostředí**, se simulovanými síťovými zdroji; verifikoval jsem přesné kopie Python souborů na GitHubu. **Společná sada 79/79 a skutečné stažení všech šesti zdrojů v Kali ještě čekají**. V tomto kroku nebyl spuštěn model ani GPU.

**Dokumentace:** [SAFE-START-OVERLAP.md](SAFE-START-OVERLAP.md) / [English](../docs/SAFE-START-OVERLAP.en.md). Další postup: po pullu nejprve všechny testy; teprve poté `python -m diagnostics.safe_start_overlap --download`, vyhodnotit výstup a před jakýmkoli dalším experimentem si vyžádat nové schválení.


### 2026-10-10 — ✅ Kompletní Safe Start CPU suite 61/61 OK; eval korpus chybí

**Skutečný výstup z mého Kali/WSL2:** po synchronizaci větve `feat/reasoning-compression` jsem spustil společně `tests.test_offline_selector`, `tests.test_reasoning_probe`, `tests.test_safe_start_plan` a `tests.test_safe_start_data`. Terminál potvrdil **`Ran 61 tests in 0.600s`** a **`OK`**. Tím je doložená celá aktuální CPU testovací sada, nikoli jen oddělené běhy 45 + 16 testů.

Kontrola `test -f questions/questions.jsonl` oznámila **`Eval otázky chybí`**. Z předchozího skutečného reportu platí `overlap_audit_status=pending_local_eval_corpus`, `local_eval_audit_performed=false` a `overlap_audit_exhaustive=false`. **Nulový počet odmítnutých překryvů bez eval korpusu není důkaz absence kontaminace.**

**Uzavřená fáze:** úspěšná CPU validace schématu, načtení ověřeného GSM8K train souboru, výběr 12 kandidátů a příprava 36 *plánovaných* pokusů. **Neprovedeno a neschváleno:** stahování oficiálních evaluačních dat, spuštění oficiálního benchmarku, GPU inference, LoRA/trénování či měření tokenové úspory.

**Další volba:** nejprve schválit pouze kontrolu překryvu proti správným připnutým evaluačním otázkám; můj existující `utils/eval/benchmarks.py` při přímém spuštění stahuje další závislosti a sestaví celý benchmark, proto se nespouští automaticky. Výběr 12 příkladů zůstává `review_only`.

### 2026-10-10 — ✅ GSM8K Safe Start: potvrzen skutečný CPU výběr 12 úloh na Kali

**Skutečný výstup terminálu:** `Ran 16 tests in 0.512s`, `OK` pro `tests.test_safe_start_data`. `python -m diagnostics.safe_start_data --download` úspěšně zpracoval **7473 záznamů** z GSM8K `main/train`, zafixovaná revize `740312add88f781978c0658806c59bc2815b9866`; report uvedl `download_status=verified_cached` a kontrolní SHA-256 `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`.

**Vybrané identifikátory (v pořadí):** `gsm8k-train-06982, gsm8k-train-01136, gsm8k-train-06866, gsm8k-train-02829, gsm8k-train-01500, gsm8k-train-01015, gsm8k-train-01832, gsm8k-train-03268, gsm8k-train-06657, gsm8k-train-06089, gsm8k-train-02730, gsm8k-train-01217`. Výstup `selection-report.json` obsahuje rovněž SHA-256 každé otázky, ale skutečné znění otázek a gold answers ponechávám v lokálním ignorovaném `data/safe-start/questions.jsonl`.

**Ověřený dry run:** `python -m diagnostics.safe_start_plan --dry-run --questions data/safe-start/questions.jsonl` úspěšně validoval 12 otázek a naplánoval **36 pokusů** (`9001/9002/9003`; Qwen3-0.6B, thinking=true). **V tomto kroku se neprovedla žádná inference, GPU ani trénování**; výběr stále hlásí `review_only` a `training_approved=false`.

**Neuzavřená kontrola:** `overlap_audit_status=pending_local_eval_corpus`, `local_eval_audit_performed=false`, `overlap_audit_exhaustive=false`. Nulové počty vyřazených kandidátů **neznamenají ověřenou čistotu vůči oficiálním benchmarkům**. Bez dalšího odsouhlasení nestahuji evaluační data ani nespouštím GPU.

**Opravená závislost:** nejprve selhal import PyArrow kvůli NumPy 1.26.4 a novější nekompatibilní verzi. Po doporučené instalaci kompatibilní verze už skutečný CPU výběr fungoval. Do `requirements.txt` jsem proto připnul `pyarrow==16.1.0`. Celou kombinovanou sadu **61/61 na Kali ještě nemám doloženou**; doložené jsou dřívějších 45/45 a nynějších 16/16 jako dva samostatné běhy.

### 2026-10-10 — 🐇 Schváleno CPU stažení GSM8K train a výběr 12 úloh

**Moje rozhodnutí:** po úspěšném **45/45 testů za 0,045 s** na Kali a výstupu `safe_start_plan --dry-run` (`plan_only`, 12 otázek, 36 plánovaných pokusů, `gpu_used=false`) jsem schválil další krok: **pouze CPU stažení GSM8K main/train a deterministický výběr 12 kandidátů**. Neschválil jsem GPU sampling, LoRA, trénování ani použití zvolených otázek bez další revize.

**Implementoval jsem:** `diagnostics/safe_start_data.py` a `tests/test_safe_start_data.py` (16 nových jednotkových testů). Dataset je připnut k revizi `740312add88f781978c0658806c59bc2815b9866`; stahuji jen `main/train-00000-of-00001.parquet` s očekávaným SHA-256 `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`. Výběr používá zafixované řazení podle SHA-256, odmítá nečíselné výsledky, duplicity a zjevné překryvy s případným lokálním evaluačním souborem. Žádné oficiální benchmarky neupravuji. Artefakty pod `data/safe-start/` jsou `review_only`, nikdy automatická trénovací sada.

**Ověření:** 16/16 nových CPU testů a předchozích 15 testů plánovače (**31/31**) prošlo v izolovaném lokálním prostředí. Síťové stahování bylo při unit testech simulováno; **reálné stažení GSM8K v mém Kali a společná sada 61/61 zatím nejsou doložené**. GitHub obsah dvou nových Python souborů jsem ověřil proti lokálně testované verzi.

**Přesný postup:** [SAFE-START-DATA.md](SAFE-START-DATA.md) / [English](../docs/SAFE-START-DATA.en.md). První příkaz v Kali je společná CPU sada testů. Teprve po její zelené kontrole smím spustit `python -m diagnostics.safe_start_data --download`, zkontrolovat `selection-report.json` a potvrdit 12 skutečných identit úloh. Pokud nemám k dispozici lokální evaluační otázky, kontrola překryvu zůstane `pending_local_eval_corpus`; **nesmím tvrdit, že byla prokázána absence kontaminace**.

### 2026-10-10 — 🐇 Schválen RHAR Safe Start, CPU plán a testy

**Moje rozhodnutí:** schválil jsem první bezpečný malý pilot **12 matematických úloh × 3 generace**. Zatím jsem však povolil **pouze implementační plán, CPU validaci a jednotkové testy**, nikoli stažení dat, GPU inferenci nebo trénování.

**Implementováno:** `diagnostics/safe_start_plan.py` a `tests/test_safe_start_plan.py`. Plánovač připraví přesně 36 *plánovaných* pokusů se seedy 9001/9002/9003, připnutým Qwen3-0.6B, zapnutým thinking, samplingem 0.6/0.95/20 a limitem 512. Pro budoucí ručně předložený zdroj zatím nabízí pouze přísnou kontrolu 12 JSONL řádků GSM8K/train/math a pinned 40hex revize. Odmítá neočekávaná pole, chybné gold answers, duplicity, evaluační zdroje a jiná rozdělení. Nedělá žádné síťové požadavky ani modelové generování.

**Ověřeno:** izolovaně **15/15 nových CPU testů — OK**; `python -m diagnostics.safe_start_plan --dry-run` vrací `status=plan_only`, `planned_generations=36`, `gpu_used=false`, `dataset_downloaded=false`, `training_performed=false`. Ověření proběhlo v lokálním prostředí se shodnými konstantami původní diagnostiky, nikoli v úplném checkoutu repozitáře.

**Z předchozí fáze:** 30/30 CPU testů selektoru a diagnostiky potvrzeno na Kali. **Aktuální součet 45 testů zatím nemám ze svého Kali doložený** — čekám na `git pull` a kombinovaný testovací příkaz.

**Dokumentace:** [SAFE-START.md](SAFE-START.md) / [English](../docs/SAFE-START.en.md) obsahuje technický kontrakt, parametry, stop podmínky, hrubé náklady a explicitní oddělení plánování od experimentu. Žádná skutečná zdrojová úloha není stažena; kontrola názvu zdroje sama nedokáže vyloučit překryv s oficiální evaluací.

**Neprovedeno:** žádné nové modelové odpovědi, GPU, LoRA, změny vah, oficiální evaluace ani měřitelné tokenové úspory. **Další krok:** ověřit společných 45 CPU testů v Kali a potom zvlášť schválit konkrétní datové otázky a jejich původ.

### 2026-10-09 — ✅ RHAR v0.1: 30/30 CPU testů potvrzeno

**Skutečně ověřeno v mém Kali / WSL2:** po opravě starého formátu diagnostických záznamů jsem spustil společnou jednotkovou sadu selektoru a reasoning diagnostiky. Terminál skončil:

- `Ran 30 tests in 0.023s`
- `OK`

**Výsledek:** **30/30 testů prošlo**, žádný test nehlásil chybu ani selhání. Jde o **20 testů v `tests.test_offline_selector` a 10 testů v `tests.test_reasoning_probe`**. Čas **0,023 s** je čas reportovaný modulem `unittest` pro tuto CPU sadu, nikoli rychlost inference ani trénování.

**Navazující skutečně ověřený offline běh:** `runs/offline/20261009T214634155051Z/` na původním souboru `runs/diagnostics/20261009T210123Z/records.jsonl` správně hlásil `incorrect_answer: 1`, `correct_final_answers: 0` a `selected_for_review: 0`. SHA-256 vstupu `bf9360243279dd0a6636111c955492018521b00e18a390f3770ae36caab25de0`. Starší neúspěšný diagnostický výsledek zůstává zachován.

**Interpretace a hranice důkazu:** první **offline / CPU část RHAR v0.1** má nyní potvrzené regresní testy i kontrolu historického vstupu. **Netrénoval jsem Qwen, nezměnil modelové váhy, nemám zatím novou GPU inferenci, oficiální benchmark ani doloženou úsporu tokenů.** Správný finální výsledek také sám nedokazuje bezchybnost celého reasoning trace.

**Další krok, zatím neproveden:** rozhodnout o přesném návrhu sběru povolených trénovacích příkladů, jeho nákladech a validačních kontrolách. Nejdřív odsouhlasím konkrétní experiment, teprve pak spustím generování nebo trénování.

### 2026-10-09 — ✅ Ověření opraveného offline selektoru v Kali

**Skutečně provedeno:** po opravě kompatibility se starými diagnostickými záznamy jsem znovu spustil `python -m diagnostics.offline_selector runs/diagnostics/20261009T210123Z/records.jsonl` ve svém Kali / WSL2. Nepouštěl jsem žádnou novou inferenci ani trénování.

**Výsledek (doslovné hodnoty souhrnu):**

| Metrika | Hodnota |
| --- | ---: |
| `records` | **1** |
| `correct_final_answers` | **0** |
| `training_eligible_candidates` | **0** |
| `selected_for_review` | **0** |
| `reasons` | `{"incorrect_answer": 1}` |
| `no_training_performed` | `true` |
| `official_benchmark` | `false` |
| `review_only` | `true` |

**Identita a reprodukovatelnost:** zdrojový soubor `runs/diagnostics/20261009T210123Z/records.jsonl`, SHA-256 `bf9360243279dd0a6636111c955492018521b00e18a390f3770ae36caab25de0`; výstupní složka `runs/offline/20261009T214634155051Z/`. Stejný SHA-256 jako při předchozím běhu znamená, že hodnotím stejné vstupní bajty.

**Interpretace:** oproti prvnímu offline běhu, který chybně skončil `invalid_question_metadata: 1`, teď selektor pro známou úlohu `arithmetic_apples` správně rozlišil nesprávnou finální odpověď **42 místo očekávaných 43**. Žádný kandidát neprošel do trénovacího výběru; staré diagnostické záznamy navíc nemají požadovaná metadata pro trénování. Oprava tedy **funguje v tomto jednom reálném případu**, ale sama nedokazuje obecnou spolehlivost selektoru.

**Stav testování:** výpis potvrzuje **úspěšný offline CLI běh**, nikoli kompletní regresní sadu. Ve zdrojovém kódu je **20 testů selektoru + 10 testů reasoning diagnostiky**; výsledný běh `python -m unittest tests.test_offline_selector tests.test_reasoning_probe -v` z mého Kali **zatím nemám doložený**. Neoznačuji 30/30 za splněné.

**Historie:** starý výstup `runs/offline/20261009T214125471552Z/` ponechávám beze změny jako záznam původní chyby. Tento běh vytvořil vlastní nový výstup. Další krok: získat úplný výpis 30 jednotkových testů a teprve potom rozhodnout o navazujícím experimentu. **Žádné oficiální benchmarky, váhy ani GPU parametry jsem nezměnil.**

### 2026-10-09 — 🩹 První offline běh: kompatibilita staré diagnostiky

**Skutečně spuštěno na mém Kali:** `python -m diagnostics.offline_selector runs/diagnostics/20261009T210123Z/records.jsonl`. Běh vytvořil `runs/offline/20261009T214125471552Z/`; SHA-256 vstupu `bf9360243279dd0a6636111c955492018521b00e18a390f3770ae36caab25de0`.

**Doslovný souhrn:** `records=1`, `correct_final_answers=0`, `training_eligible_candidates=0`, `selected_for_review=0`, `reasons={"invalid_question_metadata":1}`, `no_training_performed=true`, `official_benchmark=false`, `review_only=true`.

**Co jsme našli:** původní `reasoning_probe.py` do záznamů ukládal `id/category/expected`, ale **neukládal `task` ani `kind`**. Offline selektor tuto informaci vyžadoval, takže řádek zamítl dříve, než dokázal vyhodnotit známou nesprávnou odpověď **42 místo 43**. Nulový počet vybraných kandidátů je správný, ale **důvod odmítnutí nebyl dost přesný**.

**Oprava ve vývojové větvi:** pouze pro šest známých ručně vytvořených diagnostických úloh odvozuji chybějící `kind` z původního seznamu `CASES`, a to jen při přesné shodě `id`, `category` a `expected` a při absenci pole `source`. U jiných dat nic nehádám. Staré diagnostické záznamy tím **nezískávají `source_revision`, `split=train` ani `prompt_hash`**, takže je nelze zařadit do trénovacího výběru.

**Nové regresní testy:** přidány testy skutečného starého schématu a jeho variant, logické/kódové otázky, nesouladu identity i pokusů s uvedeným zdrojem. **Počet definovaných testů nyní: 20 selektor + 10 reasoning probe = 30. Čerstvý testovací běh po opravě ještě čeká na ověření na Kali; nový offline souhrn zatím neexistuje.**

**Očekávání po opakování (nikoli již naměřený výsledek):** `records=1`, `correct_final_answers=0`, `selected_for_review=0`, `reasons={"incorrect_answer":1}`. Starý `runs/offline/20261009T214125471552Z/` zůstane jako historický důkaz a **nebude přepsán**.

### 2026-10-09 — 🧪 RHAR v0.1: offline correctness gate hotový

**Moje schválení:** odsouhlasil jsem první implementační krok RHAR v0.1: **výhradně offline** kontrolu už vytvořených `records.jsonl` a výběr kratších správných kandidátů, bez generování, trénování nebo čerpání GPU.

**Implementoval jsem:** `diagnostics/offline_selector.py` a `tests/test_offline_selector.py`. Algoritmus znovu ověřuje finální odpověď, formát, reasoning značky, ukončení, součet tokenů a původ dat. Vybere nanejvýš jednoho nejkratšího správného kandidáta z nejméně **dvou různých správných seedů stejné otázky**. Původní jednoduché diagnostické záznamy bez metadata `source / split / prompt_hash` zůstanou pouze pro analýzu. Zdroj podobný názvům oficiálních evaluací odmítá, ale **nemůže nezávisle prokázat původ libovolných dat**. Výstupy ukládá jako **`review_only`**, nikoli data k automatickému učení.

**Ověření:** 16/16 nových CPU testů selektoru prošlo; ve společném lokálním testu s rekonstruovanou současnou diagnostikou **26/26 prošlo**. Testování proběhlo v izolovaném prostředí bez LLM/GPU. **Čerstvý běh v mém Kali na větvi po pullu zatím nedokládám.** Žádný skutečný výsledek selektoru na historickém `records.jsonl` z mého počítače ještě nemám.

**Dokumentace:** [OFFLINE-SELECTOR.md](OFFLINE-SELECTOR.md) v CZ/EN obsahuje přesné příkazy, požadované metadata, schéma výstupu, hranice důvěry a omezení. Kód ani nastavení oficiální evaluace jsem neměnil; předchozí diagnostický skript zůstal zachovaný.

**Důležitá hranice:** správná finální odpověď **nezaručuje správné reasoning kroky**. Na RPS/RPD, skutečné LoRA trénování, nové GPU generace i výběr trénovací sady bude potřeba další schválení.

**Další krok:** po aktualizaci repa nejprve spustit `python -m unittest tests.test_offline_selector tests.test_reasoning_probe -v`. Potom můžu offline vyhodnotit starý Experiment 002. Protože obsahuje jednu nesprávnou odpověď, očekávám **0 výběrů**; výsledek však do deníku doplním až po skutečném spuštění.

### 2026-10-09 — 🧬 Schválení výzkumného směru RHAR v0.1

**Moje rozhodnutí:** schválil jsem **RHAR v0.1 — Correctness-Gated Reasoning Compression** jako první směr pro trénovací výzkum: chci se učit z **kratších správných reasoning traces** a později testovat, zda tuto schopnost lze přenést do vah původního Qwenu bez zhoršení přesnosti. Schválení není automatický souhlas s konkrétní loss funkcí, sběrem datasetu, délkou GPU pilotu ani trénováním.

**Sepsaná příprava:** [RHAR v0.1 — detailní protokol](RHAR-V01-PLAN.md) popisuje navržené povolené zdroje, 20–30 různých úloh, 2–3 generace na úlohu (zatím **pouze odhad**), correctness gate, záznam dat, oddělení train/val, LoRA jako jednu z možností, metriky a stop podmínky. **Nic z pilotu ani tréninku neproběhlo.**

**Technické nálezy:** původní `train.py` je demonstrační rollout a implicitně používá bf16 na CUDA, které moje Pascal GTX 1070 Ti nativně nepodporuje. Původní `prepare_data.py` přidává do trénovacích promptů ukázkové odpovědi `42` / `B`; tento možný zdroj zkreslení nechci zaměnit s opravou našeho nezávislého diagnostického promptu. Původní reward helper nemusí být stejně přísný jako oficiální evaluační grader.

**Omezení:** dle naměřené rychlosti může 40–90 generací řádově trvat 35–90 minut čisté inference. Výpočetní rozpočet **zatím neodsouhlasen**. Oficiální benchmarky, modelové váhy a diagnostický Python kód zůstaly beze změn; posledních 10 diagnostických testů stále čeká na potvrzený lokální běh.

**Následující návrh ke schválení:** začít **pouze offline sběrným schématem a filtrem správnosti s CPU unit testy** (bez generování, bez načítání Qwenu a bez změn vah). Později si samostatně schválím GPU pilot a LoRA.

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


### 2026-10-10 — 🐇 RHAR Pilot 001: tři skutečné generace na GSM8K

**Provedeno a doloženo lokálními výstupy:** po 241 zelených testech (`OK (skipped=2)`) jsem spustil schválený GPU pilot `--execute --pilot-3 --confirm-gpu-3` na jedné otázce `gsm8k-train-06982`, se třemi seedy, do `runs/rhar-pilot-001/`. CPU dry-run předtím ověřil kompletní vstupní plán 12 otázek / 36 pokusů; audit překryvu hlásil `potential_match_count=0`, ale zůstává `review_only`, `overlap_audit_exhaustive=false`, `training_approved=false`.

| Seed | Správná odpověď | Celkové tokeny | Reasoning tokeny | Dokončeno |
| --- | --- | ---: | ---: | --- |
| 9001 | Ne, generace useknutá | 512 | Neurčeno | Ne |
| 9002 | Ano | 433 | 425 | Ano |
| 9003 | Ano | 374 | 366 | Ano |

**Souhrn:** 3 generování, 2 správné a dokončené, 1 truncation na limitu 512; průměr 439,667 celkových tokenů a 76,854 s na generaci. U dokončených výstupů bylo průměrně 395,5 reasoning tokenů a 8 final tokenů.

**Moje zjištění:** mezi dvěma správnými řešeními stejné otázky je rozdíl **59 tokenů**, tedy **13,63 % vůči delšímu správnému běhu (433 tokenů)**. Jde o přirozenou variabilitu samplingů původního Qwenu, **nikoliv naměřenou úsporu způsobenou RHAR**. Jedna otázka a dvě správné odpovědi nestačí k hodnocení generalizace ani kvality trénovaného modelu.

**Co zatím není hotové:** úplný ruční audit reasoning trace 9003, kompatibilní převod polí z `safe_start_generate.py` (`generated_text`, `total_generated_tokens`, `reasoning_split_status`, `gold_answer`) pro `training_candidates.py` (`full_generated_text`, `total_tokens`, `split_status`, `prompt`), větší různorodý trénovací soubor, LoRA běh a baseline/candidate porovnání. Formát záznamů nesmím pouze domýšlet; je třeba ho otestovat proti skutečnému artefaktu. Žádné trénování ani oficiální benchmark neproběhlo.

**Další rozhodnutí:** nejdřív ověřit úplnost kandidáta 9003, bezpečně sjednotit datový formát a otestovat selektor. Až po dostatečném rozšíření povolených dat schválit konkrétní trénovací běh.


## 2026-10-10 — 🐇 RHAR Pilot 002 — tokenový limit a opakované ověřování

**Skutečně provedeno:** schválený GPU pilot na druhé otázce auditované sady GSM8K (1 otázka × 3 seedy, max_new_tokens=512). Výstup lokálně: `runs/rhar-pilot-002/records.jsonl`; zpráva selektoru `runs/rhar-pilot-002/training-candidates.json`. Jde o nezměněný základní model Qwen3-0.6B, bez LoRA, bez oficiální evaluace.

| Seed | Tokenů | Dokončeno | Split | Pozorování z konce trace |
| --- | ---: | --- | --- | --- |
| 9001 | 512 | Ne | `unclosed_think_block` | Vypočítá 14 kg, kontroluje výsledek opakovaně, nezavře thinking |
| 9002 | 512 | Ne | `unclosed_think_block` | Vypočítá 14 kg, ale při další kontrole začne pochybovat o správném násobení |
| 9003 | 512 | Ne | `generated_think_block` | Vypočítá 14 kg, uzavře `</think>`, zahájí `Final answer:`, ale odpověď nedokončí |

**Referenční aritmetika ze zobrazených úryvků:** 4 psi × 250 g/den × 14 dní = 14 000 g = **14 kg**. Tento výsledek je přítomen v průběhu všech tří reasoning traces, přestože podle přísného protokolu **0/3 dokončených správných odpovědí** a **3/3 truncation**. Nejde o úspěšné vyřešení úloh podle metriky evaluace. Seed 9003 měl 508 přiřazených reasoning tokenů a 4 final tokeny, ale finální odpověď skončila před číslem.

**Souhrn:** `responses=3`, `correct_responses=0`, `complete_terminations=0`, `valid_reasoning_splits=1`, `mean_total_generated_tokens=512`, `mean_generation_seconds=86.935`. Selektor: `selected_count=0`, `eligible_count=0`, `not_selected_longer_count=0`, `rejected_count=3`. Otisk původních záznamů: `45a19c23e8d5af28ce2af2a90df978de097e51e18c524f5ed93e22d686d115b6`. Žádné výsledky nezachraňovat dodatečným doplněním odpovědi.

**Pracovní hypotéza RHAR:** opakovaná slovní kontrola již správného jednoduchého výpočtu může vyčerpat limit generování, aniž by vznikla úplná finální odpověď. Pozorování z trojice běhů nepředstavuje důkaz obecné úspory tokenů ani kvantifikaci zbytečných kroků.

**Návrh Experimentu 003 — POUZE PLÁN:** porovnat na téže otázce se psy stejný pinned Qwen3-0.6B, stejné tři seedy a stejné sampling parametry; změnit pouze `max_new_tokens` z **512 na 768**. Zaznamenat u každé generace řádné ukončení, správnost finální odpovědi, reasoning/final tokeny a čas. Vyšší limit může prodloužit výstup; správnost není zaručena. Před pokusem připravit oddělený režim, CPU testy, čerstvý výstupní adresář a získat **samostatný výslovný souhlas s GPU**.

**Stav na konci zápisu:** Experiment 003 nebyl implementován ani spuštěn. Žádné nové GPU generování, trénink ani změna modelu. O dalším směru rozhodne porada.


## 2026-10-10 — 🧠 RHAR Stress Test 003: implementovaná CPU příprava

Po zeleném uživatelském běhu **258 testů, OK (skipped=2)** byla vytvořena samostatná diagnostika `diagnostics/stress_test_003.py` s testy `tests/test_stress_test_003.py` (zapojeno také do GitHub CI). Šest ručně připravených úloh: 2 vícekrokové matematické, 2 logické, 2 zavádějící. Jsou **výhradně diagnostické / holdout**, nesmí být zařazeny do LoRA trénovacích dat.

Experiment plánuje 6 úloh × 2 seedy (9001, 9003) × 2 limity (512, 1024) = **24 generování**, avšak **každá samostatná dávka obsahuje jen 4 generování na jedné úloze**. Měníme token budget, ne původní váhy. Přepínač `--dry-run --task-index 1` je CPU-only a bez vedlejších efektů; skutečný běh vyžaduje kombinaci `--execute --task-index N --confirm-gpu-4`, samostatné odsouhlasení uživatelem a nové umístění výstupu. Při existujícím adresáři nepřepisuje data. Inference načítá pouze lokálně cachované váhy.

Vyhodnocení: pouze dokončené výstupy lze označit za správné, vždy přes striktní `Final answer: <číslo>`; ukládáme přesný počet generovaných tokenů, stav thinking splitu, dobu běhu i celé traces. Párové srovnání 512 vs 1024 není deterministický replay prefixu a nemusí zcela izolovat vliv limitu na vysamplovaný průběh; interpretovat opatrně.

**Stav při zápisu:** implementace a testy commitnuté na `feat/reasoning-compression`; pro lokální ověření ještě spustit kompletní testy a CPU dry-run. **Žádné GPU, LoRA ani oficiální benchmark v této fázi.**


## 2026-10-10 — 🧠 RHAR Stress Test 003 / task 01 — podrobná analýza skutečného GPU běhu

**Výzkumný status: hotová diagnostika, nikoliv úspěšná evaluace nebo trénink.** Lokální artefakty: `runs/stress-003-task-01/records.jsonl`, `summary.json`, `config.json`. Zveřejněné výsledky pocházejí ze souhrnu a posledních **1 200 znaků** každé generace, nikoliv z kompletní ruční revize všech čtyř traces. Plné texty zůstávají v lokálních záznamech. Šest ručně připravených diagnostických úloh je holdout a nesmí být použito jako trénovací data.

### Testované podmínky

- Model: `Qwen/Qwen3-0.6B`, pinned revision `c1899de289a04d12100db370d81485cdf75e47ca`; původní nezměněné váhy, thinking zapnut.
- Úloha `rhar003-math-01`: 240 zařízení, přesně **3/8 rezervovaných**, z nezarezervovaných 20 % vadných, zbytek balený po šesti. Odpověď má být jediné číslo na řádku `Final answer:`.
- Sampling: temperature 0,6; top_p 0,95; top_k 20. Seedy 9001 a 9003, oba při `max_new_tokens=512` a `1024`. Dvojice limitů **nemění délku kontextového okna n_ctx**.
- Kontrolní výsledek předem: `240 × 3 / 8 = 90` rezervovaných; `240 − 90 = 150` dostupných; `150 × 0,2 = 30` vadných; `150 − 30 = 120` použitelných; `120 / 6 = 20` balení.

### Naměřený výsledek (strict grading)

| Seed | Limit | Generované tokeny | Ukončeno | Správná dokončená odpověď | Konec záznamu / diagnostické pozorování |
| --- | ---: | ---: | --- | --- | --- |
| 9001 | 512 | 512 | Ne | Ne | Uzavření thinking chybí; opakovaně používá chybný výsledek **28** |
| 9003 | 512 | 512 | Ne | Ne | Uzavření thinking chybí; počítá **28**, pak znovu kontroluje |
| 9001 | 1024 | 1024 | Ne | Ne | Thinking zůstává otevřený; dlouhé alternativní přepočítávání, na konci další zmatek |
| 9003 | 1024 | 1024 | Ne | Ne | Thinking zůstává otevřený; v zobrazené části **opraví 28 na správných 20**, ale pokračuje opakováním |

**Souhrn nástroje:** `status=completed`; `responses=4`; `correct_responses=0`; `complete_responses=0`; `training_performed=false`; `training_data_allowed=false`; `official_benchmark=false`. Celkem **3 072 generovaných tokenů**, z toho všechny běhy skončily na svém limitu. Všechny čtyři měly `reasoning_split_status=unclosed_think_block`; reasoning/final tokeny byly kvůli neuzavřenému thinking hlášeny jako `None`, **ne jako nula**.

### Analýza chyb — důležitý technický detail

Na počátku chybného postupu model spočítal `240 / 8 = 30` správně, ale chybně zaměnil tuto **jednu osminu** za celé **tři osminy**. Tím vznikla nesprávná větev: `240 − 30 = 210`, `20 % z 210 = 42`, `210 − 42 = 168`, `168 / 6 = 28`. Následné násobení a dělení už v této větvi mohou být interně aritmeticky správné — zdrojem chyby je interpretace zlomku.

U seedu **9003 při limitu 1024** ve zobrazeném závěru model výslovně rozpoznal, že 3/8 není 30, nýbrž `3 × 30 = 90`. Přepočítal `150 → 120 → 20`, pak však znovu otevřel kontrolu a generování bylo utnuto dříve, než předložil řádně ukončenou finální odpověď. **To neznamená correct=True.** U seedu **9001 při 1024** se v úryvku objevují i nesouvisející alternativy typu `210 / 6 = 35` bez odečtení vadných zařízení; v konci stále nemá stabilní dokončenou odpověď.

### Co je doložené a co zatím není

- **Doloženo:** 4/4 truncation, 0/4 dokončených správných odpovědí, přítomnost chyby v práci se zlomkem, opakované kontroly; v jednom delším běhu oprava na správných 20 uvnitř thinking.
- **Nedoloženo:** že vyšší limit zvyšuje finální správnost; že některou konkrétní kontrolní pasáž lze bezpečně odstranit; že úspora tokenů již nastala; že všechna interní řešení jsou chybně či správně od začátku; statistická generalizace ze čtyř běhů.
- **Metodické omezení:** výstupy při stejném seedu a dvou limitech jsou vzorkované generace, ne automaticky identické prefixy. Případný pozdější prefixový rozbor musí ověřit shodu skutečných token ID, nesmí ji předpokládat.

### Zpřesněná pracovní hypotéza RHAR

**Correctness-Preserving Adaptive Reasoning** je pracovní výzkumné označení, nikoliv prokázaný algoritmus: zachovat účelnou kontrolu, která opravuje chybné mezikroky, a omezovat teprve opakované ověřování, které nepřináší novou informaci. Učení modelu „skonči při první nalezené odpovědi“ by zde mohlo upevnit chybných **28**. O správném okamžiku zastavení musí rozhodovat správnost a kompletnost, ne pouhá existence čísla v thinking.

### Další navržený krok — zatím bez spuštění

1. CPU nástroj pro offline přehled **prvního výskytu 28 a 20**, sekvencí oprav, opakování a uzavření thinking; pracovat s plnými lokálními traces a uvádět nejistotu heuristik.
2. Manuálně ověřit souvislosti výpočtů; mechanický výskyt čísla 20 nesmí být automaticky označen jako správné řešení.
3. Po poradě rozhodnout mezi rozšířením diagnostického testu a přípravou širších **povolených trénovacích úloh**; diagnostických šest úloh držet mimo trénování.
4. Nové GPU generování nebo LoRA trénink až po CPU testech a **samostatném výslovném souhlasu**. Základní model nebyl změněn.

**Stav pro předání / poradu:** stress task 01 uzavřena jako negativní výsledek v přísné metrice; hypotéza aktualizována, další experiment ani trénování se nespouští.


## 2026-10-10 — ✅ RHAR Training 001: první skutečný LoRA GPU pilot

**Potvrzené uživatelským výstupem lokálního běhu** na GTX 1070 Ti: `python -m diagnostics.lora_pilot --candidates runs/rhar-pilot-001/training-candidates-v2.json --out runs/rhar-training-001 --max-length 1024 --max-steps 20 --approve-training` s offline HF proměnnými. Model Qwen3-0.6B, LoRA rank 8, **jeden** vybraný povolený trénovací kandidát. Trénink skončil `20/20`, doba **18,8301 s**, `train_steps_per_second=1.062`, průměrný `train_loss=0.08914567157626152`, loss krok 1 **0,2139**, krok 19 **0,0384**, krok 20 **0,0392**. Výstup hlásí `Pilot adapter saved: runs/rhar-training-001`. PEFT varovalo, že nenalezlo konfigurační soubor modelu pro kontrolu změn vocab; samo o sobě to nedokazuje chybu. Soubor `.safetensors` ještě nebyl nezávisle vylistován, načten ani vyhodnocen.

**Interpretace:** technický GPU LoRA fine-tuning byl reálně proveden. Klesající training loss na jednom vzorku **neprokazuje** úsporu reasoning tokenů, generalizaci ani splnění BottleCapAI kritérií. Žádné nové měření base vs adapter, `evaluate.py` / `compare.py`, jiné datové sady ani další GPU běhy se při tomto zápisu nespouštějí. Následuje offline ověření existence adaptéru, metadat a kompatibility; teprve po schválení izolované srovnávací evaluace.

**Doporučená CPU kontrola:** `ls -lh runs/rhar-training-001/adapter_model.safetensors runs/rhar-training-001/adapter_config.json runs/rhar-training-001/pilot_metadata.json` a `python -m json.tool runs/rhar-training-001/pilot_metadata.json`. Nezapisovat označení 100% vyřešeno, dokud oficiální hodnotící metriky nejsou doloženy.


## 2026-10-10 — RHAR Evaluation 001 připravena, GPU měření zatím NEPROBĚHLO

Nový modul `diagnostics/rhar_evaluation_001.py` a pět CPU testů `tests/test_rhar_evaluation_001.py`. Cíl: exploratorně porovnat nezměněný Qwen3-0.6B s LoRA `runs/rhar-training-001`, ve shodném promptu, seedu 9001, sampling temperature 0.6/top_p 0.95/top_k 20, `max_new_tokens=512`, thinking zapnut. Výchozí úloha je **holdout task-index 2** (řidič, 180 km při 60 km/h + 120 km při 40 km/h, správně 6 hodin), nikoliv první trénovací GSM8K vzorek. Obě varianty proběhnou sériově nad stejným modelem, nikoli se dvěma kopiemi VRAM. Výstup `records.jsonl`, `summary.json` a `plan.json`. Truncation znamená nesprávný výsledek; do celkových tokenů se započítává i thinking. Výsledek je pouze orientační **jeden párový vzorek**, není to oficiální skóre ani důkaz generalizace; za jediný běh nelze připsat zásluhu RHAR.

Bezpečné CPU plánování: `python -m diagnostics.rhar_evaluation_001 --dry-run --adapter runs/rhar-training-001 --task-index 2 --out runs/rhar-evaluation-001`. Volitelné GPU měření vyžaduje výslovný souhlas a CLI přepínače `--execute --approve-gpu-2`; nepouštět automaticky. Pro oficiální BottleCapAI porovnání nadále vyžadujeme jejich `evaluate.py` a `compare.py` na kompatibilním hardware. GTX 1070 Ti compute capability 6.1 nestačí pro podporované aktuální vLLM.


## 2026-10-10 — RHAR Evaluation 001: skutečné první srovnání baseline a LoRA; plán Training 002

**Zdroj důkazů:** uživatelem poskytnutý lokální výpis `runs/rhar-evaluation-001/summary.json` a koncové úseky obou `records.jsonl` traces (posledních 1 500 znaků každé). Celé generované traces zatím nebyly nezávisle přezkoumány. Test spuštěn v prostředí GTX 1070 Ti (Transformers/PyTorch), `diagnostics.rhar_evaluation_001`, `--execute --approve-gpu-2`, `--task-index 2`, adapter `runs/rhar-training-001`. `official_benchmark=false`.

**Párové nastavení:** nemodifikovaný Qwen3-0.6B vs Qwen3-0.6B + natrénovaný LoRA pilot; stejná diagnostická holdout úloha `rhar003-math-02`, stejný prompt, seed 9001, teplota 0,6 / top_p 0,95 / top_k 20, limit 512 generovaných tokenů, thinking zapnutý. Úloha: 180 km / 60 km/h + 120 km / 40 km/h; kontrolní výsledek **6 hodin**.

| Metrika | Baseline | LoRA |
| --- | ---: | ---: |
| Celkové vygenerované tokeny | 512 | 512 |
| Strict correct | false | false |
| Truncated | true | true |
| Split status | unclosed_think_block | unclosed_think_block |
| Výpočet správných 6 hodin v zobrazeném thinking | ano | ano |
| Uzavřená finální odpověď | ne | ne |

`token_difference_base_minus_adapter=0`, `token_reduction_pct=0.0`, `quality_preservation_demonstrated=false`, `generalization_demonstrated=false`. Koncové úryvky nejsou doslova stejné (`IDENTICKÝ TEXT: False`), ale **odlišný sampling text není sám o sobě kauzálním důkazem vlivu LoRA**. Obě varianty uvnitř thinking vypočítaly 3 + 3 = 6, opakovaly kontrolu přes průměrnou rychlost 300/6 = 50 km/h a narazily na limit před uzavřením a finální odpovědí. Tento test tedy **neprokázal úsporu tokenů ani dokončenou správnost**; 1 párový vzorek nemůže prokázat generalizaci. Zásadní je přestat zaměňovat správné mezivýsledky za `correct=True`.

**Training 001 je technický pilot:** 1 povolený GSM8K příklad, 20 LoRA kroků, rank 8, uložený a strukturově ověřený `adapter_model.safetensors` (112 tensorů); pokles trénovacího lossu není generalizační důkaz. Cíl Training 002: sestavit *více různorodých správných a kompletních* povolených trénovacích příkladů; zachovat thinking + uzavření + finální odpověď, označit původ a revision, odmítnout duplicity, chybné a zkrácené traces; nezahrnout SVAMP/BFCL/MBPP+/IFEval ani šest RHAR Stress Test 003 holdoutů. Kratší odpověď bez správnosti není úspěch. Důsledná kontrola leakage a oddělení evaluace.

**Následující milníky (zatím plán):** (1) pouze CPU inspekce dostupných povolených dat a schématu kandidátů; (2) návrh Training 002 datasetu a kontrol jeho kvality; (3) zelené unit testy / kontrola overlap; (4) samostatně schválený GPU Training 002; (5) vývojové párové ověření na větším počtu úloh; (6) oficiální `evaluate.py` na kompatibilním vLLM hardwaru, nebo transparentně uvést omezení v odevzdání. **Tento zápis nespouští trénování, stahování dat ani GPU.**


## 2026-10-10 — RHAR Dataset Builder 002 (CPU-only, bez generování)

Nový modul `diagnostics/dataset_builder_002.py` vytvoří plán z **existujících 12 již kontrolovaných GSM8K-train otázek** a jejich auditních metadat; nevyžaduje nové stahování. Volá `load_approved_inputs` a tedy ověřuje integritu lokálního výběru i předchozí orientační screening překryvů. Vytváří worklist s identifikátory, hashi promptů a třemi plánovanými seedy na otázku. **Neobsahuje v exportu znění otázek ani gold odpovědi, netvoří trénovací samples a netrénuje.** Odlišuje screening od úplného důkazu nulové kontaminace. Volitelné `--exclude-id gsm8k-train-06982` pro oddělení již použité trénovací otázky.

`python -m diagnostics.dataset_builder_002 --exclude-id gsm8k-train-06982 --out runs/rhar-dataset-002-worklist.json` (CPU only, s kontrolou neexistující výstupní cesty). Očekáváno 11 zbývajících otázek × 3 plánované generace = 33 **dosud neprovedených** generování, nikoli 33 kandidátů; žádný další GPU běh bez konkrétního schválení. Jakmile budou z povolených dat skutečné plné správné generace, půjdou přes `training_candidates.py` a `training_002_preflight.py`, s ručním posouzením kvality. Připraveno pět CPU unit testů.


## 2026-10-10 — Dataset 002: plán první malé dávky (jen CPU)

Přidán `diagnostics/dataset_batch_002.py` a šest CPU regresních testů. Vstupem je lokální `runs/rhar-dataset-002-worklist.json` (11 původně auditovaných GSM8K-train otázek, kromě již použitého pilotu). Výchozí první dávka obsahuje pouze **2 otázky × 3 seedy = 6 plánovaných generování**. Výběr přes indexy `--start 0 --size 2`, odmítání nesprávného původu, duplicit, přepisu výstupu a chybné struktury. Uložená dávka neobsahuje znění úloh ani správné odpovědi, pouze ID a hashe. **Je to plán, ne spuštěný GPU test, ne nový dataset ani autorizace trénování.**

Lokální CPU příkaz: `python -m diagnostics.dataset_batch_002 --worklist runs/rhar-dataset-002-worklist.json --size 2 --start 0 --out runs/rhar-dataset-002-batch-01.json`. Nové GPU generování vyžaduje zvláštní implementaci a zvláštní výslovné schválení po zelených testech. Benchmarky SVAMP, MBPP+, BFCL a IFEval nejsou součástí trénování.


## 2026-10-10 — PŘECHOD NA SKUTEČNÉ TRÉNOVÁNÍ: RHAR Teacher-SFT 002

Po zpětné vazbě uživatele: **prioritou není psaní dalších plánovačů, ale modelová intervence**. Přidán `diagnostics/rhar_teacher_train_002.py` — přímo trénovatelný LoRA SFT program na **skutečných GSM8K train referenčních řešeních** pro 12 dříve auditovaných otázek, typicky 11 s vyloučením již použitého pilotu `gsm8k-train-06982`. Použije pouze lokální ověřený `data/safe-start/raw/gsm8k-train.parquet` s pinned SHA-256 a existující overlap audit; žádná data z SVAMP/MBPP+/BFCL/IFEval. Vstupní `answer` rozdělí na výpočetní referenční zdůvodnění a `####` gold final; zruší interní anotace `<<...>>`, ale neupravuje smysl výpočtu. Tréninková completion obsahuje `<think>`, výpočet, `</think>`, `Final answer: číslo`, a EOS; při prefilled think markeru šablony se jeho duplicita odstraní. Na rozdíl od dřívějšího jednoho náhodného Qwen rollout se nyní přímo učí uzavření reasoningu a správný závěr ze zdrojových referenčních řešení. **Nejde o záruku zlepšení** a pořád málo vzorků pro robustní generalizaci.

CPU preflight příkaz (žádné GPU): `python -m diagnostics.rhar_teacher_train_002 --dry-run --exclude-id gsm8k-train-06982 --out runs/rhar-teacher-sft-002`. Pouze po samostatném výslovném souhlasu GPU: změnit `--dry-run` na `--approve-training`, přidat `--max-steps 60 --max-length 1024`. Bez automatického běhu, bez přepsání starších dat; úlohy s délkou nad limit budou vyřazeny a pokud zůstane méně než 8, trénink se nespustí. Po tréninku **nezávisle** porovnat na nenatrénovaných otázkách a neoznačovat žádná data za oficiální BottleCapAI benchmark.


---

## 🐇🛡️ 2026-10-10 — Milník: konec přípravné fáze, přechod k samotnému zlepšování Qwen3-0.6B

### Co jsme dosud skutečně udělali

- Prošli zadání BottleCapAI: zmenšit **celkový počet generovaných tokenů včetně thinking**, zachovat správnost a ponechat thinking zapnutý. Oficiální evaluace sleduje SVAMP, MBPP+, BFCL a IFEval; tyto benchmarky nepoužívat k trénování a neměnit oficiální `evaluate.py` / `compare.py`.
- Vytvořili RHAR diagnostiku, zápisy, kontrolu provenance GSM8K-train dat a ochrany proti záměně evaluačních a trénovacích příkladů. Připravili párové porovnání přes PyTorch/Transformers, protože lokální GTX 1070 Ti (8 GB, compute capability 6.1) nepodporuje běžnou moderní cestu přes vLLM.
- **Training 001: první opravdový LoRA trénink** Qwen3-0.6B úspěšně doběhl na GTX 1070 Ti: 1 správný GSM8K trénovací příklad, rank 8, 20 kroků; uložen `runs/rhar-training-001/adapter_model.safetensors`. To dokazuje funkčnost trénovacího postupu, **nikoli** zlepšení modelu.
- **RHAR Evaluation 001: první skutečné srovnání**, na oddělené matematické úloze (6 hodin), seed 9001, 512 tokenů: baseline i LoRA spotřebovaly 512 tokenů, obě generace byly uříznuté v neuzavřeném thinking bloku. Obě v textu spočítaly 6 hodin, ale nedaly hotovou finální odpověď; strict correct = false u obou. **Úspora = 0 %, zlepšení neprokázáno.** Rozdílný text generací sám o sobě nedokazuje efekt adaptéru.
- Pro Dataset 002 vznikl auditovaný GSM8K-train worklist: **11 otázek, 33 plánovaných generování, 0 nově získaných kandidátů**. Dávka 01 obsahuje otázky `gsm8k-train-01136` a `gsm8k-train-06866`, 6 plánovaných generování. To byly **plány, nikoli měření či trénink**. Lokální uživatel ohlásil 295 úspěšných CPU unit testů; testy ověřují software, nikoli dosažení cíle BottleCapAI.
- Následně vznikl **`diagnostics/rhar_teacher_train_002.py`**, první konkrétní přímý krok k dalšímu zlepšování modelu: používá pouze ověřenou trénovací část GSM8K a její referenční správná řešení, učí průchod od uvažování k `</think>`, `Final answer:` a EOS, LoRA SFT s explicitním schválením GPU. **Training 002 ještě není potvrzen jako proběhlý a jeho přínos dosud není změřený.** Výchozích nejvýše 11 různých řešení je jen omezený pilot, ne dostatečný důkaz generalizace.

### 🔁 Změna priorit — rozhodnutí týmu

Přiznáváme chybnou prioritizaci: nadměrně jsme řešili pomocnou infrastrukturu, plánovače, validátory a dokumentaci, přestože zadání vyžaduje především **funkční zlepšení vah/chování modelu a nezávislé změření výsledku**. Od tohoto milníku **nepřidávat další pomocné systémy bez konkrétního důkazu, že jsou nezbytné pro trénink, evaluaci nebo odevzdání**.

**Jediná hlavní výzkumná smyčka:** povolená trénovací data → skutečná úprava modelu (LoRA/jiná opodstatněná metoda) → párové měření baseline vs. candidate na oddělených úlohách → vyhodnocení *správnost + celkové tokeny + dokončenost* → další cílená změna. Trénovací loss, počet testů ani samotná délka reasoning nejsou metrikou úspěchu. Nespoléhat na promptové zkracování, vypnutí thinking ani trénink na evaluačních benchmarkových datech.

**Bezprostřední úkol:** zelené CPU ověření existujícího Training 002 skriptu, zkontrolovat dostupnost ověřeného lokálního GSM8K train Parquetu, teprve po samostatném schválení spustit první přímý teacher-SFT LoRA experiment na GTX 1070 Ti. Následně otestovat dokončené odpovědi a tokeny na více neviděných příkladech a rozhodnout podle čísel, zda metoda funguje. Pro oficiální BottleCapAI použít beze změn předepsaný runner na kompatibilním hardwaru; neoficiální lokální měření označovat pravdivě.

**Pravidlo:** 🛡️ „Bez zelené ani krok“ platí pro relevantní kontrolu funkčnosti, nikoli jako záminka k nekonečnému budování infrastruktury. **Odteď je hlavní výslednicí měřitelné zlepšení modelu.**


## 2026-10-10 — RHAR Training 003: skutečný větší LoRA experiment

Implementován `diagnostics/rhar_train_003.py` pro **1 000 GSM8K-train referenčních řešení + 100 oddělených GSM8K-train validačních řešení**, deterministický shuffle seed 42 a kontrolu (heuristického) překryvu vůči existujícím `questions/questions.jsonl` pouze podle promptů. Datový zdroj je **lokální pinned GSM8K main/train Parquet** s SHA-256; nezahrnovat oficiální evaluační gold odpovědi nebo evaluační příklady do tréninku. LoRA rank 8, learning rate 5e-5, batch 1, grad accumulation 4, eval + checkpoint po epoše, default jedna epocha. Thinking zachováno. SFT odpovědi vycházejí ze skutečných GSM8K referenčních racionalizací (nejde o nezávisle ověřené Qwen reasoning trajectories); experiment teprve ověří vliv na kvalitu. Trénink schvaluje `--approve-training` a neprovádí se automaticky.

CPU: `python -m diagnostics.rhar_train_003 --dry-run --out runs/rhar-training-003`. GPU (až po úspěšné kontrole): `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -m diagnostics.rhar_train_003 --approve-training --out runs/rhar-training-003 --train-size 1000 --val-size 100 --epochs 1 --max-length 1024`. Trénovací artefakt/val loss není automaticky úspora tokenů; po tréninku porovnat na oddělených úlohách se správností a celkovou délkou včetně thinking. `eval_overlap_exhaustively_ruled_out` nelze tvrdit: screening zůstává heuristický. Uloženo na vývojové větvi, lokální GPU test zatím neproběhl.



## Research originality review — 2026-10-10 (prior-art checkpoint)

**BottleCapAI wording:** “We're interested in your own ideas, not how well you can copy other's.” The four formal rules permit LoRA and fine-tuning on permitted non-evaluation data; they demand an unchanged evaluation and honest documentation. **Using a published baseline is allowed; claiming it is novel is not.** Do not train on SVAMP, MBPP+, BFCL or IFEval. 

**Current actual implementation:** RHAR Training 001 and 002, and planned Training 003, use ordinary LoRA supervised fine-tuning (SFT) on GSM8K responses or reference rationales, with a correct final answer and explicit thinking boundaries. This is an *established training baseline*, **NOT an invented RHAR compression algorithm**. RHAR modules RPS, RPD and TPC are hypotheses; there is no proven implementation. Existing Eval 002 observed 137 vs 512 tokens on one question, but the trained adapter answered 4.5 instead of 6 hours. Therefore it does **not** establish accuracy-preserving compression. Do not call the implementation novel, world-first, or an improvement on BottleCapAI metrics.

**Documented nearby research (citations and methods to check for overlap):**
- *Less is More Tokens: Efficient Math Reasoning via Difficulty-Aware Chain-of-Thought Distillation* (2025), https://arxiv.org/abs/2509.05226 : difficulty-proportional traces and SFT + preference optimization.
- *Making Small Language Models Efficient Reasoners: Intervention, Supervision, Reinforcement* (2025), https://arxiv.org/abs/2505.07961 : stopping-time and length-regularized RL.
- *Towards Structural Understanding of LLM Overthinking* (ACL 2026), https://deepmind.google/research/publications/203490/ : analysis of Qwen-family oververification/overexploration via thought progression graphs.
- *LEASH: Adaptive Length Penalty and Reward Shaping* (ACL 2026), https://aclanthology.org/2026.acl-long.129/ : adaptive length reward.
- *When Internalization Fails: Finding Better Targets for Reasoning Compression* (ACL Findings 2026), https://aclanthology.org/2026.findings-acl.734/ : alternatives for CoT shortening targets.
- *Keypoint-based Progressive Chain-of-Thought Distillation* (ICML 2024), https://proceedings.mlr.press/v235/feng24e.html : emphasis on reasoning keypoints.
- *AutoL2S: Auto Long-Short Reasoning* (2025), https://arxiv.org/abs/2505.22662 : adaptive short/long traces.

**Novelty gate:** Before presenting an RHAR mechanism as original, write an executable definition (inputs, outputs, learning signal, objective), cite the nearest prior method, state the actual difference and devise an ablation: plain SFT vs RHAR candidate on identical training data, base model and evaluation protocol; measure total tokens AND correctness, including task transfer. A renamed loss, another wrapper/validator or simple shortest-correct trace selection **does not satisfy novelty by itself**. Any originality assertion is provisional: one literature check cannot exclude unpublished/prior work. Continue Training 003 **only as a disclosed SFT control baseline**, not as the final novel algorithm. The official submission can transparently report negative results.


## 2026-10-10 — První RHAR-CEP pilot v kódu (bez GPU spuštění)

Po SFT 003 následovala ruční analýza šesti lokálních diagnostických úloh. SFT 003: **3/6 strict correct, 6/6 dokončené**, průměr 88,17 generovaných tokenů; původní Qwen na těchto šesti úlohách vždy dosáhl limitu 512 bez uzavřené odpovědi (cenzorovaný baseline; nelze z toho prokazovat zachovanou správnost). Chyby: skladová matematika (3/8 a 20 %), pořadí A,B→C→D (nesprávné počítání 4!×2), králíci (raw trace zatím nezískán).

Nový soubor `diagnostics/rhar_cep_pilot.py` je **první kandidátní intervence, ne prokázaně nová algoritmická metoda**. Experiment proti obyčejnému SFT 003: stejná deterministická train/validation data z připnutého GSM8K train parquet, LoRA rank8, learning rate 5e-5, epochy 1, seed 42. Mění se pouze tokenově vážená supervised cross-entropy (`boost=2.0`) pro lexikálně rozpoznaná čísla opsaná ze zadání, operátory a vybraná slova označující vztahy v referenčním řešení. Validační loss je nevažovaný. Tato ochrana je pouze **heuristická**, nepředstavuje ověřenou kauzální důležitost, může zhoršit generalizaci; případný úspěch zatím neověřen. Testy jsou CPU-only. GPU trénink neproběhl a zůstává na explicitním spuštění.

Příkazy (po zelené CPU validaci):
`python -m diagnostics.rhar_cep_pilot --dry-run --out runs/rhar-cep-pilot-001`
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -m diagnostics.rhar_cep_pilot --approve-training --train-size 1000 --val-size 100 --epochs 1 --boost 2.0 --out runs/rhar-cep-pilot-001`

Další rozhodnutí pouze podle párového měření správnosti a celkových tokenů proti SFT a base; žádné tvrzení o soutěžní úspěšnosti.


## 2026-10-10 — CEP Pilot 001: negativní kontrolní výsledek

**Stav:** dokončený GPU trénink a 6 lokálních párových diagnostických úloh; **nejde o oficiální BottleCapAI benchmark**. Toto je skutečně naměřený výsledek, nikoliv nová prokázaná metoda.

- **SFT 003:** 3/6 správně, všechny odpovědi dokončené; délky `[114, 54, 105, 139, 73, 44]` tokenů, průměr **88,17**.
- **CEP Pilot 001:** 2/6 správně, všechny odpovědi dokončené; délky `[103, 75, 83, 244, 73, 44]` tokenů, průměr **103,67**.
- **Rozdíl:** CEP oproti SFT ztratil jednu správnou úlohu (Task 4) a průměrně generoval o **15,5 tokenu / ~17,6 % více**. Na pouhých šesti známých diagnostických úlohách s jedním seedem jde jen o slabou evidenci; statistický závěr ani generalizace nejsou doloženy.
- **Původní model** ve všech šesti měřeních narazil na strop 512 tokenů a neuzavřel finální odpověď. Úspora vůči této cenzorované baseline se nesmí prezentovat jako prokázané zachování accuracy.
- **Task 4 — číslicový zámek:** úloha vyžaduje `X=Y+2`, `Z=2Y`, `X+Y+Z=14` a tři různé nenulové číslice. Správný kód je **536**. CEP ve vlastním reasoning výslovně vypsal správného kandidáta `X=5, Y=3, Z=6`, ale nakonec neprávem vybral `X=3, Y=1, Z=2` a uzavřel `Final answer: 312`. To porušuje součet `3+1+2=6`, nikoli 14. Model také chybně odmítl několik kandidátů kvůli „digits are not distinct“, ačkoli jejich číslice byly různé; problém byl jinde.
- **Pracovní interpretace:** jednoduchá lexikální 2× váha čísel a operátorů nezlepšila na tomto vzorku kvalitu rozhodnutí. **Nenazývat to ověřenou kauzální ochranou informací.** Alternativní příčiny, včetně náhodnosti inference a rozptylu malého vzorku, nejsou vyloučeny.

**Dohodnutý bezprostřední krok:** porovnat celý skutečně generovaný reasoning SFT 003 pro Task 4 s CEP 001. Soubor SFT je lokálně `runs/rhar-evaluation-004-task-4/records.jsonl`; v GitHubu není k dispozici. Dokud z něj nedostaneme výpis, **netvrdit, jak konkrétně SFT přišel ke správné odpovědi 536**. Zatím žádný další trénink.


### 2026-10-10 — Doplněn skutečný reasoning SFT 003, Task 4

Uživatel lokálně vytiskl `runs/rhar-evaluation-004-task-4/records.jsonl`: **SFT 003, 139 tokenů, strict correct**. Model přímo spojil vztahy `X=Y+2`, `Z=2Y` a `X+Y+Z=14`, dosadil `(Y+2)+3Y=14`, odvodil `Y=3`, `X=5`, `Z=6` a ukončil `Final answer: 536`. Naproti tomu **CEP 001, 244 tokenů, incorrect**, vyjmenovával kandidátní číslice, uvedl mimo jiné správnou trojici `X=5,Y=3,Z=6`, ale následně vybral `312` (součet 6 namísto 14). 

**Interpretace omezená důkazy:** v tomto *jednom páru* model SFT zachoval a vyřešil vazby symbolicky, kdežto CEP změnil strategii na enumeraci s chybným výběrem. Nelze prohlásit, že vážení tokenů přímo způsobilo přechod strategií; inference je stochastická (jediný seed) a šest diagnostických otázek je již prohlédnutých. Nezvyšovat boost naslepo. Další skutečně nezávislé vyhodnocení musí být na dosud neviděných povolených validačních úlohách; srovnat identické prompty/seeds/cap a vyhodnotit correctness i total tokens. CEP 001 není prokázaný přínos.


## 2026-10-10 — RHAR Validation 005 a izolovaná kontrola CEP 001

**Kontrolní lokální experiment (nikoli oficiální BottleCapAI benchmark):** Na 20 dalších oddělených úlohách GSM8K train byly porovnány dva natrénované adaptery při stejném seed 9001, samplingu a limitu 512 generovaných tokenů. Tyto úlohy nebyly mezi předchozími 1 000 trénovacími ani 100 loss-validačními příklady. Jde o jedinou generaci na otázku; neprokazuje generalizaci ani zachování kvality.

| Metrika | SFT 003 | CEP Pilot 001 |
| --- | ---: | ---: |
| Správné odpovědi | 9/20 (45 %) | 9/20 (45 %) |
| Dokončené odpovědi | 19/20 | 19/20 |
| Průměr tokenů | 114,85 | 115,80 |
| Součet tokenů | 2 297 | 2 316 |

**Závěr:** CEP 001 nepřinesl na této sadě zlepšení proti běžnému SFT; vygeneroval o 19 tokenů více celkem (+0,83 %). Na předchozích šesti již prohlédnutých diagnostických úlohách dosáhl SFT 3/6 a CEP 2/6. Data nepodporují účinnost jednoduchého lexikálního zvýhodnění čísel a operátorů, ale nevylučují širší hypotézu CEP. Z `eval_loss` nebo zkrácení vůči base, která narážela na 512tokenový strop, netvrdit úspěch v soutěžním zadání.

**Kontrola možné kontaminace adapterů při evaluaci:** V hromadném `diagnostics.rhar_validation_compare` se při přechodu SFT → CEP objevil PEFT `UserWarning: Already found a peft_config attribute in the model`. Kvůli tomu je třeba ověřit, že při hromadném přepínání zůstává skutečně aktivní pouze zamýšlený adapter. Oddělená kontrola v novém Python procesu:
`python -m diagnostics.rhar_evaluation_001 --execute --approve-gpu-2 --adapter runs/rhar-cep-pilot-001 --task-index 4 --out runs/rhar-cep-isolation-check-001`.
**Výsledek:** CEP znovu vytvořil **244 tokenů, incorrect, truncated=false**, přesně stejně jako jeho předchozí Task 4. To podporuje reprodukovatelnost chyby bez předchozího SFT adapteru; **neprokazuje** však správnou izolaci všech dvaceti hromadných měření.

**Příčina pozorovaného selhání v Task 4:** SFT 003 odvodil `(Y+2)+3Y=14` ⇒ `Y=3`, `X=5`, `Z=6` a správně uzavřel `536` (139 tokenů). CEP 001 při enumeraci uvedl správnou trojici `5,3,6`, ale vybral nesprávné `312` (244 tokenů); jeho kontrola podmínek byla nekonzistentní. Z jediné dvojice nelze prokázat, že váhování operátorů způsobilo odlišnou strategii.

**Další postup:** Nezvyšovat váhy naslepo ani nerozbíhat další pomocné experimenty. Nejdříve zkontrolovat a opravit čisté načtení/přepínání LoRA adapterů v porovnávacím skriptu. Následnou hypotézu zaměřit na uchování **celých ověřitelných vztahů a konzistenci odvození s finální odpovědí**, nikoli pouze na jednotlivé číselné tokeny; nové intervence posuzovat proti stejnému SFT a na dosud neprohlédnutých úlohách. Zatím nemáme doložený CEP algoritmus lepší než SFT ani oficiální skóre BottleCapAI.


## 2026-10-10 — Poslední plánovaný test dne: RHAR Evaluation 006 (větší čisté srovnání)

Připraveno, ale **GPU evaluace ještě nespustila žádná vzdálená akce**. Aktualizován `diagnostics/rhar_validation_compare.py`: pro SFT 003 a CEP 001 načítá **každý adapter na samostatném čistém backbone modelu** (bez opětovného použití PEFT-dekorovaného modelu) a vyžaduje `len(active.peft_config)==1`. Každá generace se zapisuje do `records.partial.jsonl`; při dokončení se vytvoří `records.jsonl` a souhrn. Průběžný soubor je bezpečnostní záznam, **automatické resume prozatím implementováno není**.

Nové CLI `--skip 20 --count 60` vybírá **60 dalších, dosud neprohlédnutých otázek** za dříve použitými 20 holdout otázkami a za 100 validačními / 1 000 trénovacími příklady v deterministickém splitu GSM8K train. Celkem plán **120 GPU generování**, seed 9001, cap 512, thinking on. Žádná soutěžní eval data netrénovat. Výsledky nejsou oficiální BottleCapAI benchmark, jde pouze o matematiku a jeden seed. Srovnávat přesnost, dokončení, tokeny i chyby. Hypotézu ani výsledek předem neoznačovat za úspěch.

Příkazy:
`python -m unittest tests.test_rhar_validation_compare -v`
`python -m diagnostics.rhar_validation_compare --dry-run --skip 20 --count 60 --out runs/rhar-validation-006`
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -m diagnostics.rhar_validation_compare --execute --approve-gpu --skip 20 --count 60 --sft runs/rhar-training-003 --cep runs/rhar-cep-pilot-001 --out runs/rhar-validation-006`

Nespouštět, pokud CPU kontrola není zelená; nevydávat budoucí záměr za provedený test.


## 2026-10-10 — Návrh CEP 002: Procedural XP a negativní zkušenost

Uživatel navrhl, aby RHAR-CEP po nezávislém ověření neukládal pouze správnou odpověď, ale zobecněný správný postup s podmínkami použití. Zkušenost („XP“) by po dalším trénování přecházela do vah Qwen3-0.6B; samotná inference ani dokončení úlohy váhy automaticky nemění. Příklad: zapamatovat obecný výpočet a pořadí procent místo čísla 20.

Druhá varianta: **negative procedural memory** — zaznamenat chybný postup včetně konkrétní příčiny a vstupních podmínek, aby další trénink učil model neplatné odvození nerozvíjet. Trestat bez vysvětlení celou odpověď nestačí: metoda může být správná pro jiné podmínky. Chybné řešení lze porovnat se správným na povolených trénovacích úlohách (kontrastivní učení, preference), ale nesmí se použít oficiální eval ani prohlédnutý holdout k trénování.

Třetí varianta: **multi-path selection / synthesis** — v trénovací fázi navrhnout více postupů, nezávisle je ověřit, vybrat až tři nejlepší podle correctness, nutných závislostí a délky a slučovat pouze kompatibilní a ověřené mezikroky. Výslednou krátkou správnou proceduru použít k distilaci do vah. Není bezpečné slepit části tří odpovědí bez ověření; tři generování při oficiální inferenci mohou zvýšit spotřebu tokenů a jejich použití by změnilo evaluační režim.

Hypotéza: zkušenosti ze správných i nesprávných *postupů* mohou zlepšit přesnost při menším počtu tokenů, ale jen když model prokáže přenos na nové úlohy. Pořadí: dokončit Evaluation 006 beze změny; poté návrh jednoho kontrolovaného CEP 002 experimentu. Nejde o implementaci, naměřený přínos ani prokázanou světovou originalitu.


## 2026-10-10 — RHAR Evaluation 006: dokončený lokální párový test (60 otázek)

**Zdroj:** uživatelem dodaný kompletní výstup `diagnostics.rhar_validation_compare --execute --approve-gpu --skip 20 --count 60` z místního stroje. Skript načítá každý LoRA adapter na samostatném čistém Qwen3-0.6B backbone. Dataset tvoří 60 dosud nepoužitých otázek z povolené části GSM8K train za předchozím 20otázkovým výběrem, seed 9001, max 512 tokenů, thinking zapnutý. **Nejde o oficiální BottleCapAI benchmark; jeden seed, pouze matematické otázky.**

| Metrika | SFT 003 | CEP Pilot 001 |
| --- | ---: | ---: |
| Strict correct | 19/60 (31,67 %) | 23/60 (38,33 %) |
| Complete | 59/60 | 59/60 |
| Průměr tokenů | 96,15 | 87,77 |
| Celkové vygenerované tokeny | 5 769 | 5 266 |

**Rozdíl CEP vs. SFT:** +4 správné odpovědi (+6,67 procentního bodu), -503 tokenů (o 8,72 % méně vzhledem k SFT). Párově CEP **opravil** otázky č. **8, 10, 12, 18, 19, 22, 35, 36**; **pokazil** původně správné otázky **1, 23, 29, 57**. Jedno generování od každého modelu narazilo na 512tokenový limit (SFT č. 47, CEP č. 34).

**Interpretace:** Pozitivní průběžný výsledek pro CEP 001 na tomto konkrétním vzorku; není prokázáno zachování přesnosti vůči originálnímu Qwenu, statisticky spolehlivý přínos algoritmu, generalizace do kódu/funkcí/instrukcí ani soutěžní skóre. Na dřívějším 20otázkovém testu byly oba modely 9/20 a CEP spotřeboval o 19 tokenů více; výsledky mezi výběry kolísají. `summary.json` výslovně hlásí `quality_preservation_demonstrated: false` a `generalization_demonstrated: false`.

**Pro příští výzkumný cyklus:** nedotýkat se již prohlédnutých 60 příkladů jako nového „nezávislého“ holdoutu ani je nepoužít k tréninku. CEP 002 je zatím návrh: ověřené přenositelné postupy („XP“), dokumentované příčiny chybných postupů a kontrolované skládání kompatibilních částí řešení do trénovacích vzorů; netvrdit, že je implementován nebo že zaručí zlepšení.


## 2026-10-11 — CEP-002 Data Intake 001 připraven (CPU, dosud nespouštěno na Kali)

Uživatel potvrdil funkční původní WSL Kali pracovní adresář, oba soubory `adapter_model.safetensors` SFT 003 / CEP Pilot 001 (po 4,4 MB), správný SHA-256 původního GSM8K train parquet `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d` a zachovaný souhrn Validation 006 (19/60 SFT vs 23/60 CEP; 5 769 vs 5 266 tokenů; nejde o oficiální benchmark). Neověřena kryptografická integrita samotných LoRA vah; prozatím máme pouze existenci souborů.

V izolované větvi `feat/cep002-cpu-mvp` jsou již zelené uživatelem spuštěné základní CEP-002 testy (22/22) a syntetická dávka (12/12 správných předem sestavených traces). Výstup všech rozšířených 34 testů v Kali uživatel zatím neposlal.

Nově vytvořen `diagnostics/cep002_data_intake.py`: explicitně SHA-256 kontrolované GSM8K train + povinná kontrola vůči dostupným oficiálním eval promptům; deterministický seed 42; izolace prvních 1 180 již použitých položek (1000/100/20/60); 12 dalších kandidátů označených REVIEW_REQUIRED a 60 budoucích rezervovaných holdout položek bez textu otázek v manifestu. Přidáno 10 unit testů a CZ/EN dokumentace. **Kód a nové testy zatím nebyly spuštěny v uživatelově prostředí**; další krok je zelené CPU testování a dry-run, bez GPU. Další dřívější jednotlivé piloty a 12 Safe Start otázek nemusí být plně zahrnuty do historického auditu; žádné automatické schvalování dat ani trénování.


## 2026-10-11 — První tři GSM8K kontrakty CEP-002: návrhy bez schválení

Uživatel poskytl první tři záznamy skutečného Data Intake 001 s ID `gsm8k-train-00664`, `gsm8k-train-06718` a `gsm8k-train-03644`. Ruční analýza zadání dala referenční správné odpovědi 12, 7 a 3840. Přidán `diagnostics/cep002_real_contract_drafts.py` a 11 CPU unit testů. Prototyp ověřuje shodu hashů otázek, provenance a přesné matematické relace na úrovni `Fraction`; záměrně **nevydává trénovací ani modelové příklady** a požaduje samostatný sémantický audit. Drafty mají `VPS=UNVERIFIED` a čekají na ruční review; recenzent ani automatická kontrola NESMÍ být předstíráni. Testy na Kali zatím nebyly spuštěny; dřívější zelených 44 CPU testů mělo uživatelský výstup `Ran 44 tests`, ale bez doloženého finálního `OK`. Žádný GPU běh, nové učení ani oficiální benchmark.


## 2026-10-11 — CEP-002 Human Semantic Review 001 (připraveno, běh čeká)

Uživatel spustil v Kali 55/55 CPU testů za 0,456 s s výsledkem `OK`. Nový `diagnostics.cep002_real_contract_drafts --execute` úspěšně vytvořil 3 matematicky konzistentní návrhy, všechny `review_required`, `locked_experiences: 0`, `semantic_contracts_independently_reviewed: 0`, bez GPU a tréninku.

Doplněn `diagnostics/cep002_review_packet.py` a 12 testů: strict identita vstupu a návrhu, manuální významové mapování veličin, vztahy, možné chyby a nezaškrtnutý checklist. Skript vytvoří `review-packet.md` bez trénovacích dat či XP zámku. Doplnění bylo vytvořeno v GitHub větvi `feat/cep002-cpu-mvp`; 12 nových testů ani revizní protokol dosud uživatel nespustil. Samotný draft ani jeho revizní protokol není nezávislé schválení sémantiky. Další krok: 67 CPU testů; jen po úspěchu příprava revizního dokumentu.


## 2026-10-11 — Oprava JSONL kompatibility revizních kontraktů

Při lokálním běhu `diagnostics.cep002_review_packet --dry-run` vznikl `ValueError: draft content or provenance changed: gsm8k-train-00664`. Analýza: `dataclasses.asdict(TaskContract)` zachovalo `rules` jako Python `tuple`, zatímco JSONL round-trip převádí sekvenci na `list`. Přímé `draft != create_draft(...)` vyhodnotilo typovou změnu jako manipulaci dat.

V izolované větvi `feat/cep002-cpu-mvp` upraven `diagnostics/cep002_real_contract_drafts.py`: kontrakt vrací explicitně JSON-kompatibilní seznam pravidel už při návrhu. Zachovává se porovnání identity a původu celého objektu bez vypnutí bezpečnostní kontroly. Dva nové regresní testy ověřují JSON serializaci a kompletní zápis/čtení kontraktů až k review packetu.

**Důležité:** Uživatel již vytvořený `contract-drafts.jsonl` nemusí generovat znovu — jeho pravidla jsou po JSONL uložena jako seznam. Oprava zpětně podporuje stávající obsah. Nové testy dosud uživatel v Kali nespustil; očekáváme 69 testů a revizní dokument pouze po zeleném běhu. Žádný trénink ani GPU výpočet.


## 2026-10-11 — CEP-002 revizní protokol zelený, předběžná kontrola sémantiky

Uživatel potvrdil: `Ran 69 tests in 0.271s — OK`; `diagnostics.cep002_review_packet --dry-run` vrací `plan_only`; `--execute` vrací `manual_review_pending` a soubor `runs/cep002-contract-drafts-001/review-packet.md` skutečně existuje. Všechny tři kontrakty mají `contract_semantic_approvals=0`, `xp_locks_created=0`, `training_records_exported=0`, `gpu_used=false`.

Asistent provedl pouze **předběžné vlastní posouzení významu zadání**, vyhodnoceno jako konzistentní 12, 7 a 3840; u šamponu je nutný předpoklad společné jednotky objemu, u sociálních sítí se sčítají počty na platformách. Záznam s omezeními v `CZ docs/CEP-002-SEMANTIC-REVIEW-001.md` a anglickém protějšku. Nejde o nezávislý podpis ani schválení pro trénink; původ a překryv dalšími piloty stále chybí.

V protokolu byly vidět doslovné escaped Markdown backticky `\``; opraveno v `diagnostics/cep002_review_packet.py` a přidán regresní test do `tests/test_cep002_review_packet.py`. Nový očekávaný počet testů je **70** (uživatelský běh 69 byl před tímto commitem). Nový hezky vykreslený packet musí být zapsán do **nové cesty** (např. `review-packet-v2.md`), původní soubor se záměrně nepřepisuje.


## 2026-10-11 — CEP-002 History Overlap 001: audit skutečných starších běhů připraven

Uživatel potvrdil **70/70 CPU testů OK** (0,250 s). Na původním WSL/Kali repozitáři ověřil existenci původních Safe Start otázek a reálných validačních záznamů 005/006; výpis `find` navíc objevil přibližně 25 `runs/**/records.jsonl` v pilotních, validačních, canary, stress a diagnostických bězích.

Přidán `diagnostics/cep002_history_overlap.py` a 18 regresních CPU testů `tests/test_cep002_history_overlap.py`; porovnání ID, SHA-256 a normalizované podoby pouze u aktuálně prohlížených 12 kandidátů, kontrola rezervovaných 60 holdout záznamů **pouze přes ID a SHA-256, bez přístupu k jejich původním otázkám či odpovědím**. Vstupní historické soubory čteny jen pro extrakci zdrojových referencí, bez exportu eval textů. Program kontroluje všechny původní `runs/**/records.jsonl` a Safe Start, odhaluje neznámé/ID-only záznamy v coverage reportu, nepřepisuje staré výsledky ani neschvaluje trénink.

Testy ani ostrý audit ještě na počítači uživatele neběžely, očekávaný součet je **88/88**. Po zelené a úspěšném dry-runu lze spustit read-only vstupní audit se zápisem nového souhrnu do `runs/cep002-history-audit-001`. Bez GPU. Nulový překryv není důkaz absence nepřímé/sémantické kontaminace.
