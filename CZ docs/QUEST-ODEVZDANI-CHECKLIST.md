# 📦 BottleCapAI — můj checklist odevzdání

**Stav:** plán; nic jsem neodeslal. **Podklad:** [původní zadání](../docs/UPSTREAM-README.md).

[🗺️ Roadmapa](QUEST-DOKONCENI-PLAN.md) · [🔬 Experiment](QUEST-EXPERIMENTALNI-PLAN.md)

## Povinné artefakty

- [ ] Kód a historie repozitáře jako Git bundle, vytvořený příkazem `git bundle create vystup.bundle --all`.
- [ ] Skutečný soubor `results.json` vygenerovaný oficiálním `evaluate.py`.
- [ ] Natrénovaný Qwen3-0.6B nebo LoRA adapter v souborech `.safetensors`.
- [ ] Stručné finální `IDEA.md`: motivace, metoda, experimenty, úspěchy, chyby, hardware a omezení.
- [ ] Konfigurace, zdroje a revize trénovacích dat, seedy, postup reprodukce.
- [ ] Případné další checkpointy ilustrující poměr mezi délkou a správností.

## Kontrola kvality

- [ ] Mám potvrzeno, že adapter skutečně mění chování modelu při aktivním thinking.
- [ ] Trénovací data neobsahují evaluační benchmarky SVAMP, MBPP+, BFCL ani IFEval.
- [ ] Stejně nastavený base a kandidát mají skutečně naměřené tokeny a správnost.
- [ ] Pokud provedu `compare.py`, jsou oba vstupní běhy porovnatelné.
- [ ] Testy jsou zelené; vysvětlím přeskočené a zdokumentuji případný neúplný benchmark.
- [ ] ZIP neobsahuje tajemství, přístupové klíče ani nežádoucí osobní údaje.
- [ ] Výsledky nejsou přikrášlené; negativní výsledky zůstávají uvedené.

## Předání

- [ ] Nejprve připravím ZIP s názvem podle požadavku BottleCapAI a velikostí nejvýše **500 MB**.
- [ ] Preferovaně použiju [oficiální formulář](https://bottlecapai.com/careers/thinkingcap-test-submission/).
- [ ] Pokud se ZIP nevejde, použiju povolený odkaz na Hugging Face nebo Google Drive a e-mail podle upstream zadání.
- [ ] **Bez mého výslovného souhlasu nic neodesílám ani nezveřejňuji.**

**Hotovo znamená:** reprodukovatelný upravený model + doložené výsledky + kompletní odevzdávací balíček. Ne pouze hypotéza nebo diagnostické skripty. 🐇


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
