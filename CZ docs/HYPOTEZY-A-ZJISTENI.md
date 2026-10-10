# 🧠 RHAR — Moje hypotézy a zjištění

![Stav](https://img.shields.io/badge/stav-v%C3%BDzkum-yellow)
![Model](https://img.shields.io/badge/model-Qwen3--0.6B-7C3AED)
![GPU](https://img.shields.io/badge/GPU-GTX_1070_Ti-76B900)
![Výsledek](https://img.shields.io/badge/prok%C3%A1zan%C3%A1_%C3%BAspora-0-orange)

> 🐇 Rabbit Hollow Research · 10. října 2026  
> Můj osobní přehled toho, co jsem skutečně změřil, co si zatím myslím a co musím teprve ověřit. Nezaměňuji hypotézu za výsledek.

[📔 Vývojový deník](DEV-NOTES.md) · [🔬 Experiment 002](experiments/002-reasoning-baseline.md) · [🧬 Plán RHAR](RHAR-V01-PLAN.md)

## 🎯 Proč RHAR dělám

Mým cílem není vytvořit dalšího chatbota. Zkoumám, zda dokážu u malého reasoning modelu `Qwen/Qwen3-0.6B` snížit počet **skutečně generovaných tokenů** (reasoning + finální odpověď), a přitom zachovat srovnatelnou správnost.

Nechci jen vypnout thinking nebo napsat prompt „přemýšlej stručněji“. Chci postupně vyzkoumat změnu chování modelu a nakonec ji poctivě ověřit proti nezměněné baseline. Zatím ale **nemám upravený ani natrénovaný RHAR model**.

## 🧭 Rychlá orientace

| Otázka | Moje současná odpověď |
| --- | --- |
| Funguje mi model na lokální GPU? | Ano, jedna kontrolní inference skutečně doběhla |
| Dokáže odpovědět správně? | Ano, na jedné konkrétní matematické úloze |
| Přemýšlí někdy déle, než by se zdálo nutné? | V mém vzorku se po dosažení správné odpovědi opakovaně kontroloval |
| Umím vyhledat explicitně opakované výpočty? | Ano, částečně pomocí offline heuristik |
| Zjistil jsem přesný počet ušetřitelných tokenů? | Ne |
| Umím dokázat, že předčasné ukončení nepoškodí přesnost? | Ne |
| Provedl jsem LoRA/trénování nebo oficiální benchmark? | Ne |

## 🧪 Co jsem opravdu provedl

### 1. Ověřil jsem svůj hardware a prostředí

Na Kali/WSL2 jsem ověřil NVIDIA GTX 1070 Ti s 8 GB VRAM, PyTorch `2.6.0+cu118`, funkční CUDA, compute capability `6.1` a skutečný FP16 výpočet. V cache jsem našel modelovou revizi `c1899de289a04d12100db370d81485cdf75e47ca`.

V poslední doložené plné lokální sadě mi doběhlo **213 testů, 0 selhání a 2 přeskočené testy**. Zelené unit testy potvrzují chování mého kódu pro testované případy, nikoli vědeckou platnost celé hypotézy.

### 2. Spustil jsem GPU Canary 002

Moje úloha: pět krabic po dvanácti jablkách, prodáno sedmnáct. Správně má zůstat **43**.

| Metrika | Skutečný výsledek |
| --- | ---: |
| Správnost | 1/1 správně |
| Celkové generované tokeny | 423 |
| Reasoning tokeny | 415 |
| Finální tokeny | 8 |
| Podíl reasoningu | 98,11 % |
| Čas inference | 82,552 s |
| Rychlost | 5,124 tokenu/s |
| Peak PyTorch alokace | 1,185 GiB |
| Useknutá generace | Ne |

Výstup jsem uložil do `runs/canary-002/20261010T102914Z/`. Historický Experiment 002 měl chybnou odpověď 42, 325 tokenů a 51,3 s. Tyto dva jednotlivé vzorky **nepoužívám jako důkaz zlepšení ani zhoršení**, protože nemám potvrzené plně srovnatelné podmínky.

### 3. Prošel jsem pět offline experimentů

| Experiment | Co jsem zjistil |
| --- | --- |
| RHAR 003 | 265 slov uvažování, 5 odstavců a 3 opakované čtyřslovné sekvence |
| RHAR 004 | Identifikoval jsem kontrolní fráze a textové kroky; segmentace původně vytvořila 27 kroků, po opravě 33 |
| RHAR 005 | Zaznamenal jsem 6 rozpoznaných matematických operací a 2 jejich opakování |
| RHAR 006 | U všech 6 rozpoznaných operací se shodoval vypočtený a tvrzený výsledek; checkpoint jsem našel po 646 znacích, dalších 616 znaků následovalo |
| RHAR 007 | Zpětný tokenizer vytvořil 423 tokenů; kandidátní checkpoint ležel na hranici po 200 tokenových jednotkách a dalších 223 jich následovalo |

Tyto výsledky se týkají **jednoho konkrétního běhu**, nikoliv obecné statistiky přesnosti Qwenu.

## 💡 Moje hlavní hypotézy

### H1 — Opakované ověřování může spotřebovávat významnou část reasoning rozpočtu

V mém vzorku model už napsal `43 apples remaining`, ale poté se opakovaně vracel k násobení a odečítání. Dvakrát jsem rozpoznal tutéž operaci pod různým zápisem:

- `5 times 10` a `10*5`
- `5 times 2` a `2*5`

**Co už vím:** k opakovaným výpočtům v tomto vzorku opravdu došlo.

**Co zatím nevím:** zda byly tyto kontroly zbytečné a zda by se bez nich zachovala správnost na jiných zadáních.

### H2 — Pouhá detekce opakovaných slov nestačí

Ve vzorku mám jen tři opakované čtyřslovné sekvence, ale text obsahuje opakované matematické úkony a potvrzování výsledku. Proto potřebuji rozpoznávat operace a významové vztahy, ne jen shodné řetězce.

**Omezení:** můj parser stále nerozpozná všechny přirozenojazyčné formulace. Neoznačený výpočet nemusí znamenat nový výpočet.

### H3 — Kandidátní checkpoint může být výchozím bodem pro budoucí test komprese

Ve RHAR 006 jsem našel první formulaci správné odpovědi u znakového offsetu 646, po níž následovalo dalších 616 znaků reasoningu. Ve RHAR 007 se po zpětné tokenizaci hranice objevila na indexu 200 z celkových 423 tokenů.

**Pozor:** 223 zpětně tokenizovaných tokenů za checkpointem **není 223 ušetřených tokenů**. Je to pouze popis části uloženého výstupu. Skutečný proces generování mohl po předčasném zastavení fungovat jinak.

### H4 — Přesná tokenová evidence je předpokladem kvalitnějšího měření

Z původního experimentu mám text a naměřené celkové počty, ale ne původní vygenerovaná tokenová ID. Zpětná tokenizace dala stejný počet tokenů, což je užitečná kontrola, ale nepotvrzuje identickou sekvenci.

Proto chci u budoucích experimentů ukládat tokenová ID, revizi tokenizeru, hashe a validační metadata.

### H5 — O kompresi má smysl rozhodovat jen se zachováním správnosti

Můj cíl není generovat nejkratší odpověď za každou cenu. Chci měřit **správnost + celkový počet generovaných tokenů** při totožném nastavení baseline a kandidáta, na oddělených validačních úlohách.

Zatím nemám data, která by prokázala úspěch této hypotézy nebo konkrétní trénovací metody.

## 😳 Co mi zatím připadá opravdu zajímavé

Nejvíc mě překvapilo, že malý model u jednoduchého příkladu dospěl ke správné odpovědi a přesto dál prováděl výpočty, kontroloval zadání a opakoval závěr. Zároveň jsem zjistil, že `5 times 10` a `10*5` musím porovnávat jako matematické operace, ne jako text.

To je **zajímavý pozorovaný jev a dobrá výzkumná otázka**, nikoliv objev nového mechanismu AI. Zatím jsem nevyvinul nové trénování, neprokázal úsporu a nepřekonal cizí výsledky.

## 🐛 Chyby, které mě naučily nejvíc

| Problém | Jak jsem ho vyřešil | Poučení |
| --- | --- | --- |
| Regex vracel `None` místo `True/False` u výpočtu | Upravil jsem hranici čísla, aby nevadila tečka za výsledkem | Textové parsování snadno zkreslí metriky |
| Rozdělení textu vracelo 2 místo 3 kroků v testu | Povolil jsem větu začínající číslicí | Počet kroků závisí na segmentaci |
| Hledání rovnic s `=` přehlíželo slovní výpočty | Zavedl jsem normalizaci matematických zápisů | Lexikální shoda není totéž jako shoda operace |
| Textový checkpoint jsem mohl zaměnit za úsporu | Přidal jsem explicitní `measured_token_savings=null` a `early_stop_safety_verified=false` | Musím odlišovat pozorování od důkazu |
| Nemám originální generovaná tokenová ID | RHAR 007 konzervativně hlásí `retokenized_boundary_only` | Stejná délka tokenizace ještě nezaručuje totožné tokeny |
| Testovací sada měla 3 selhání | Zastavil jsem postup, opravil parser a znovu spustil celou sadu | Bez zelených testů nepokračuji |

## 📚 Co jsem se při tom naučil o AI

Naučil jsem se v praxi rozlišovat inferenci, reasoning, finální odpověď, tokenizaci, sampling, CUDA a FP16. Začal jsem chápat, proč potřebuji fixovat seed, modelovou revizi a podmínky experimentu a proč nemohu vydávat jedno správné řešení za přesnost celého modelu.

Především jsem se naučil, že **výzkum AI není jen psaní Python skriptů**. Je to i navrhování ověřitelných hypotéz, hledání slabin vlastního měření a poctivé přiznání výsledků, které zatím nemám.

## 🗺️ Kde právě jsem a kam chci dojít

- [x] Ověřil jsem CUDA, FP16 a lokální Qwen3-0.6B.
- [x] Získal jsem jeden správný GPU canary výstup.
- [x] Dokončil jsem offline analýzy RHAR 003–007.
- [x] Opravil jsem tři regresní chyby a ověřil 213 lokálních testů (2 přeskočené).
- [ ] **RHAR 008:** navrhnout ukládání originálních tokenových ID v nových experimentech; zatím neschváleno jako implementace.
- [ ] Získat více nezávislých úloh a opakování.
- [ ] Ověřit kandidátní checkpointy proti skutečným tokenovým datům.
- [ ] Navrhnout a schválit konkrétní metodu změny modelového chování.
- [ ] Případně natrénovat LoRA adaptér.
- [ ] Porovnat se stejnou baseline na neviděné validaci a následně oficiální evaluaci.

## 🛡️ Co rozhodně netvrdím

Netvrdím, že RHAR už zrychluje Qwen, že umím bezpečně vymazat 223 tokenů, že má metoda zaručeně zachová přesnost ani že jsem objevil novou architekturu AI.

**Momentálně mám výzkumnou pipeline, první ověřené pozorování a konkrétní hypotézu. Nemám prokázanou kompresi.**

Moje pracovní pravidlo zůstává: **Bez zelených testů ani krok. Výsledky musí být skutečně změřené.** 🐇🛡️


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
