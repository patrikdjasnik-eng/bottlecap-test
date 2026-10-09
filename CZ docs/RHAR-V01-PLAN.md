# 🧬 RHAR v0.1 — Correctness-Gated Reasoning Compression

**Stav: schválený výzkumný směr, podrobný implementační návrh; žádný pilot ani trénování zatím neproběhly.**  
**Datum:** 9. 10. 2026 · **Větev:** `feat/reasoning-compression`

[🇬🇧 English](../docs/RHAR-V01-PLAN.en.md) · [Můj vývojový deník](DEV-NOTES.md) · [IDEA.md](IDEA.md)

## 🎯 Cíl a můj důvod

Chci upravit samotný **Qwen3-0.6B**, aby generoval **méně celkových tokenů (reasoning + finální odpověď)** při co nejmenší ztrátě správnosti a schopností napříč úlohami. **Nevypnu thinking, nepoužiju prompt-only zkracování a netrénuji na oficiálních evaluačních úlohách.**

Schválil jsem **Correctness-Gated Reasoning Compression jako první trénovací výzkumný směr RHAR**, nikoliv přesný algoritmus, dataset, počet generování, GPU rozpočet nebo okamžité úpravy vah. Následující protokol je **návrh ke schválení před implementací**. První krok je ověřit, zda původní model vůbec vytváří správné, relativně krátké reasoning traces využitelné jako výukové příklady.

## 🧩 Návrh pipeline v0.1

1. **Baseline a zelené testy.** Na Kali ověřím současných **10 definovaných diagnostických testů**. Zopakuji opravený `reasoning_probe.py` pro jeden vzorek; původní Experiment 002 (325 tokenů / nesprávných 42 místo 43) nesmažu.
2. **Oddělená povolená data.** Pilot navrhuji z **20–30 různých zadání** pro aritmetiku a výběr odpovědi; jako možné zdroje slouží **GSM8K, CommonsenseQA, ARC Easy, Skywork-OR1** z původních helperů. Volbu zdrojů, jejich licence a konkrétní revize musím zafixovat **před spuštěním**. SVAMP, MBPP+, BFCL a IFEval slouží **výhradně evaluaci**.
3. **Více samplingů stejného zadání.** Pro každý trénovací příklad navrhuji **2–3 nezávislé generace**, se zapnutým thinking, zafixovaným seedem/sekvencí seedů, verzí modelu, revizí, samplingem, promptem a token limitem. Každé skutečné spuštění se uloží do samostatného lokálního `runs/`.
4. **Correctness gate.** Rozdělit reasoning/final/total tokeny a ověřit **přesnou správnost podle gold answer**, řádný konec generování, skutečně přítomný thinking blok a parsovatelnou odpověď. Chybnou, useknutou, prázdnou nebo nevyhodnotitelnou generaci **odmítnout s důvodem**, nikoli prohlásit za krátkou úspěšnou.
5. **Výběr kandidátů.** Pro stejné zadání porovnat **jen správné** kandidáty podle celkových tokenů. Zvolený kratší postup **automaticky nepovažuji za lepší**: nápad na kontrolu rekonstruovatelnosti (RPD) je zatím hypotéza, nesmím vydávat neprovedenou verifikaci za hotovou. Pokud neexistuje dost kvalitních správných variant, zastavím se u analýzy.
6. **Výukový artefakt a až poté LoRA.** Po schválení implementace vytvořit trénovací JSONL z vybraných příkladů se zachovanými reasoning značkami; případně **LoRA supervised fine-tuning**, loss **jen na tokeny generované odpovědi**, nikoli na prompt. **Nepřipravuji prozatím žádné skutečné váhy.**
7. **Ověření změny modelu.** Porovnat nezměněný Qwen a checkpoint **na nových oddělených validačních úlohách** při totožném promptu a sampling nastavení, s celkovou délkou včetně chybných výstupů. Teprve poté oficiální `evaluate.py` a `compare.py` na kompatibilní GPU.

## 📦 Plánovaný záznam dat

Jde o **schéma k návrhu**, nikoli o tvrzení, že soubory již existují.

| Kategorie | Navržená pole |
| --- | --- |
| Identita zadání | `question_id`, `source`, `source_revision`, `task`, `split`, `gold_answer` |
| Nastavení generování | `model`, `model_revision`, `seed`, `sampling`, `max_new_tokens`, `thinking_enabled`, `prompt_hash` |
| Syrový výsledek | `generated_text`, `final_text`, `reasoning_split_status`, `terminated`, `truncated` |
| Měření | `total_generated_tokens`, `reasoning_tokens`, `final_tokens`, `generation_seconds`, `peak_vram_gib` |
| Výběr | `correct`, `accepted`, `rejection_reason`, `candidate_rank`, `verifier_version` |

Trénovací a validační otázky oddělím **podle identity otázky před generováním**, nikoli náhodným rozdělením jednotlivých odpovědí na jednu otázku. Ošetřím duplicity či velmi podobné úlohy mezi splity, aby nedocházelo k úniku řešení.

`utils/train/rewards.py` používá pro doporučené trénovací sady vlastní hodnocení, které je místy **benevolentnější než oficiální evaluace**; příklady proto pro výběr nemohu přijímat bez validace formátu. Výchozí `utils/train/prepare_data.py` obsahuje v trénovacích instrukcích doslovné příklady `Final answer: 42` / `Final answer: B`. Tento **možný matoucí vliv** je nutné zvlášť rozhodnout a otestovat; odlišné trénovací prompty nejsou oprávněním měnit **oficiální** evaluační prompty.

## 🖥️ Odhad pilotu a limity

Na GTX 1070 Ti jsme naměřili přibližně **51–61 sekund** pro jednu krátkou inference. **40–90 generování** by tak mohlo řádově znamenat **35–90 minut čisté generace**, bez načítání modelu, různě dlouhých odpovědí a případných zpomalení. **Je to hrubý odhad, nikoliv rezervovaný GPU rozpočet ani již vykonaný běh.** Než ho spustím, zvolím konečný počet úloh a generování.

`train.py` z původního repa je jen ukázkový rollout, **ne hotový RHAR trainer**. Navíc na CUDA implicitně volí `bfloat16`; Pascal GTX 1070 Ti nemá nativní bf16 podporu. Pokud schválím LoRA pilot, bude třeba ověřit šetrnou `float16` konfiguraci, batch size 1, gradient checkpointing a správnou práci s pamětí, ne slíbit, že se na 8 GB určitě vejde.

## 🧪 Navržená metodika ověření

| Kontrola | Co chci prokázat |
| --- | --- |
| Unit testy | Prázdný/malformed thinking, chybné číslo, ukončení, duplicity, správný split, nepropuštění neúspěšných řešení |
| Dry run | Schéma dat a sestavení výběru bez GPU ani stahování modelu |
| Sampling pilot | Počet generací, poměr správných, kolik bylo kratších správných, poměr reasoning/final |
| Jednoduchá baseline | Výběr nejkratší správné odpovědi bez tvrzení o vědecké originalitě |
| Trénování | Zda LoRA vůbec běží bez OOM/NaN a dá standardní adapter `.safetensors` |
| Neviděná validace | Společně sledovat **přesnost + celkové tokeny**, ne jen délku odpovědi |
| Budoucí RHAR ablace | Teprve potom zvlášť změřit přínos RPS, RPD, TPC a kandidátní HRM |
| Oficiální závěr | Neměněné SVAMP / MBPP+ / BFCL / IFEval; párové CI přes `compare.py` |

**Stop pravidla:** červený unit test; chybějící/unikající gold answer; nesprávné či neukončené generace; nedostatek správných kandidátů; OOM/NaN; viditelný propad přesnosti; nesrovnatelné prompty nebo sampling. **Jeden dobře vypadající výsledek není důkaz úspěchu.**

## 🤝 AI spolupráce a transparentnost

Na RHAR spolupracuji s **ChatGPT (OpenAI, GPT-6)** a vlastní **GGUF AI agentkou Mášou**. ChatGPT pomáhá s návrhy, analýzou, kódem a dokumentací. Máša je součást mého vývojového prostředí; **bez doloženého běhu jí nepřisuzuji konkrétní výsledky tohoto experimentu**. Výběr směru i finální schvalování zůstávají na mně.

## 🧪 Realizovaná offline fáze

První schválený implementační krok **již mám v repu**: `diagnostics/offline_selector.py` a **16 nových CPU testů**. Pracuje pouze se starými JSONL generacemi, nevyvolává model ani trénování. Podrobný popis je v [OFFLINE-SELECTOR.md](OFFLINE-SELECTOR.md). **Výstup `selected_for_review.jsonl` není schválený training dataset.** Zatím čekám na první čerstvý běh testů ve vlastním Kali a offline analýzu historického Experimentu 002.

## ✅ Aktuální hranice schválení

**Schváleno:** výzkumný směr v0.1 a sepsání jeho implementačního návrhu.  
**Dosud neschváleno jako konkrétní akce:** výběr a stahování dat, kód nové GPU generovací pipeline, počet GPU generování, LoRA trénování, úpravy vah a oficiální evaluace. **Offline filtr a jeho CPU testy už jsou implementované.**  
**Zatím neprovedeno:** pilot, trénování, porovnání checkpointu, naměřená úspora, zelené testy po poslední diagnostické opravě.

**Další rozhodnutí:** zda mám připravit **nejdřív bezpečnou offline implementaci výběru kandidátů + jednotkové testy bez generování nebo trénování**. To je první omezená fáze, kterou mohu ověřit bez spotřeby GPU.
