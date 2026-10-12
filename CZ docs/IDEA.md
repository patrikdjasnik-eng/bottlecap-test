# 🐇 RHAR — jediná aktivní hypotéza a ověřovací plán

**Stav: výzkumná hypotéza; nikoliv prokázaný nový algoritmus. Aktualizace: 12. 10. 2026.**

[📔 Historie a surové výsledky](DEV-NOTES.md) · [📋 Soutěžní požadavky](QUEST-ODEVZDANI-CHECKLIST.md) · [🧠 CEP 002 — přesný jednoduchý návrh](CEP-002.md) · [🌍 IDEA (EN)](../IDEA.md)

## 📊 Aktuální kontrolní evidence — RHAR Validation 007 (12. 10. 2026)

**Lokální exploratorní test podle uživatelova terminálu, nikoli oficiální skóre:** 40 oddělených GSM8K-train otázek × base/SFT003/SFT004, 1 seed, cap 512, 120 dokončených generování jako experiment. **Base 6/40 správně, 19 860 tokenů, 32/40 uříznuto; SFT003 14/40, 4 885 tokenů; SFT004 17/40, 4 611 tokenů, 1/40 uříznuto.** SFT004 vs SFT003 +3 správné, −274 tokenů (~5,6 %), párově 6 oprav a 3 zhoršení. Původní model u 32/40 případů narazil na token cap; nejde o důkaz zachování přesnosti či generalizace. SFT004 je **běžná SFT kontrola, nikoli implementace CEP 002**. Lokální Validation 007 / Training 004 zdrojové skripty a artefakty v aktuálně prohlížené GitHub větvi chyběly; čísla jsou zdokumentována podle uživatelem dodaných logů. [Podrobný záznam a metodická omezení](RHAR-VALIDATION-007.md).

## 🎯 Zadání BottleCapAI, nikoliv naše vedlejší projekty

Vycházíme z `Qwen/Qwen3-0.6B`. Učíme **kratší skutečné generování tokenů včetně thinking** bez ztráty správnosti. Thinking zůstává zapnutý; nespoléháme na promptový trik. Finální hodnotící protokol `evaluate.py`/`compare.py` se nemění. **SVAMP, MBPP+, BFCL a IFEval jsou výhradně evaluace, nikdy trénink.**

## Jediná aktivní výzkumná hypotéza: RHAR-CEP

**RHAR-CEP — Causal Evidence Preservation**, pracovní označení:

> U malého reasoning modelu lze omezit zbytečné pokračování uvažování, pokud během učení upřednostníme zkrácené úplné postupy, které zachovávají **údaje ze zadání, nezbytné odvozovací kroky a správný závěr**, před pouhým zkracováním délky.

Jde o *testovatelný návrh*, nikoli tvrzení o světové originalitě nebo hotové implementaci.

**V čem by se hypotéza mohla lišit od běžné distilace:** nevybírat řešení jen podle správné poslední řádky a délky; odůvodnit zachování konkrétních závislostí vstup → výpočet → výsledek. Kandidátní trénovací signál bude odvozován od zásadních kroků. Mechanismus a jeho nezávislá verifikace **ještě nejsou implementovány ani ověřeny**. Nelze považovat pouhou heuristiku podobnosti nebo vymazání slov za důkaz kauzální důležitosti.

### Konkrétní chyba, kterou řešíme

Na úloze 180 km při 60 km/h + 120 km při 40 km/h je správně 6 hodin. LoRA 002 zvládla uzavřít thinking za 137 tokenů, ale bez opory v zadání změnila 180 km na 90 km a odpověděla 4,5 hodiny. Baseline skončila u limitu 512 tokenů s neuzavřeným thinking, přestože ve svém reasoning spočítala šest hodin.

**Naměřených 73,24 % kratší generování není splněné zadání**: chyba v odpovědi, jeden vzorek a baseline na stropu tokenů. Tenhle negativní výsledek je motivace pro zachování důkazních závislostí.

## Jeden výzkumný experiment se dvěma trénovanými kontrolami

1. **Kontrola — obyčejný SFT (Training 003):** stejné povolené trénovací otázky a stejné zdrojové reference. Existující `diagnostics/rhar_train_003.py` je běžný LoRA SFT experiment, **nikoliv RHAR algoritmus**.
2. **RHAR-CEP — kandidátní intervence:** na *stejných* příkladech explicitně zohlednit zachování ověřitelných odvozovacích kroků; porovnat se SFT při odpovídajícím trénovacím rozpočtu. Nejprve musí vzniknout konkrétní algoritmus; dokud neexistuje, netvrdit, že jsme CEP natrénovali.
3. **Oddělené srovnání:** původní Qwen vs. SFT vs. CEP na totožných nezahrnutých otázkách, samplingu a limitech; měřit **strict correctness, dokončenost, celkové generované tokeny** včetně thinking, chyby a rozptyl. Kratší špatná odpověď je neúspěch. Počet zelených unit testů a train loss nejsou soutěžní výsledky.

**Rozhodovací pravidlo:** RHAR-CEP stojí za další vývoj jen pokud vůči běžnému SFT přinese na neviděných datech měřitelné zlepšení poměru tokenů a správnosti. Jinak hypotézu upravit nebo zamítnout; žádné další podprojekty.

## Originalita a nejbližší existující přístupy

- Keypoint-based Progressive Chain-of-Thought Distillation (ICML 2024): https://proceedings.mlr.press/v235/feng24e.html
- Less is More Tokens (2025): https://arxiv.org/abs/2509.05226
- LEASH — délková penalizace / reward shaping (2026): https://aclanthology.org/2026.acl-long.129/

**LoRA, SFT, GSM8K, kontrola správnosti, důležité kroky ani krátké traces nejsou naše vynálezy.** Náš potenciální přínos je konkrétní způsob určení a ochrany závislostí; jeho odlišnost od nejbližších metod a přínos musejí být prokázány srovnáním. Není možné garantovat, že obdobný mechanismus dosud nikdo nepublikoval.

## Dosavadní reálný stav (nezaměňovat s plánem)

| Milník | Výsledek |
| --- | --- |
| Training 001 | Skutečný LoRA adapter z 1 GSM8K příkladu, technický pilot |
| Training 002 | Skutečný LoRA adapter z 11 referenčních GSM8K řešení, 60 kroků |
| Eval 002 | 512 tokenů baseline / 137 tokenů adapter, ale **obě strict incorrect** (baseline uříznutá, adapter 4,5 místo 6) |
| Training 003 | Skript na větší běžný SFT s validací; **v tomto záznamu není doloženo dokončení GPU tréninku** |
| CEP | **Zatím hypotéza, ne implementovaná ani trénovaná metoda** |
| Oficiální BottleCapAI skóre | Zatím není |

Podrobnou historii testů, pomocných skriptů, limitů GTX 1070 Ti a negativních výsledků ponecháváme v [DEV-NOTES.md](DEV-NOTES.md) jako **archiv**, nikoliv aktivní roadmapu.

## Co teď vědomě neděláme

Žádné samostatné RPS/RPD/TPC/HRM moduly, honeynety, dashboardy, další sérii plánovačů ani „50 experimentů“. Historické názvy jsou *archivní nápady*, dokud se neprokáže jejich nezbytnost pro tuto jedinou hypotézu.

**Jediné další kroky:** ověřit kontrolní SFT → přesně navrhnout a implementovat malý CEP mechanismus → provést párové měření → podle výsledků pokračovat nebo směr zamítnout. Trénink/GPU vyžaduje výslovné spuštění; nic se nespouští automaticky.


## Kandidát CEP 002 — Procedural Experience Learning (návrh z 2026-10-10)

**Uživatelská hypotéza („CEP získává XP“):** Nezapamatovat si konkrétní odpověď ani ji jen vracet z cache. Po správném **nezávisle ověřeném** vyřešení trénovacího problému uložit **obecně použitelný postup**, jeho vstupy, závislosti a podmínky platnosti; při dalším učení jej zobecnit a přenést **do vah Qwen3-0.6B**, aby při nových úlohách obdobné struktury zvládl kratší a správné odvození.

Cyklus: **vyřešit → ověřit výsledek i dostupné mezikroky → abstrahovat přenositelný postup → ověřit na změněných příkladech → uložit zkušenost s původem → natrénovat LoRA → vyhodnotit na dosud neviděných úlohách**. Přirovnání k XP je motivační model, nikoli tvrzení o automatickém on-line učení bez tréninku.

Příklad: neukládat odpověď `20`, ale postup `floor(celkem * (1-rezervovaný_podíl) * (1-vadný_podíl) / velikost_balení)` spolu s předpokladem, že podíl vadných se počítá **až ze zbytku**. Jiný význam procent nebo jiné pořadí operací = postup nelze bez dalšího použít.

**Požadavky BottleCapAI:** Žádná databáze odpovědí při oficiální inferenci; přínos se musí projevit v naučených vahách, při zapnutém thinking. Zákaz učení z hodnoticích dat SVAMP, MBPP+, BFCL, IFEval a z již prohlédnutých validačních otázek, které bychom chtěli vykazovat jako nezávislý test. Kontrolovat přesnost, úplnost i celkové tokeny včetně reasoning. Správná finální odpověď sama o sobě nedokazuje správný postup. Hlídáme chybné zobecnění, uzavřenou smyčku vlastních chyb, zapomínání a náklady na ověřování.

**Stav:** Jde o směr pro případný CEP 002, nikoliv hotový modul, nový prokázaný algoritmus nebo naměřené zlepšení. Příbuzné principy self-trainingu, distilace a opětovného využití postupů již existují. Dokončit Evaluation 006 beze změn.

 
### 🧠 CEP 002 — REC: Retroactive Experience Correction (zpětná oprava zkušeností)

**Nově přijatá výzkumná hypotéza, nikoliv implementovaná funkce.** Když se model v pozdější trénovací úloze (např. 10) naučí nezávisle ověřený postup, který je v rozporu s jeho dřívějším řešením (např. otázky 3), REC má umožnit označit starší záznam k opětovnému přezkumu. Samotný Qwen si ale mezi samostatnými běhy nepamatuje všechna řešení, sám nepozná chybu a při inferenci si automaticky nemění váhy. REC je pracovní název, nikoliv tvrzení o nové vědecké metodě.

**Navržený algoritmus jen pro přípravu trénovacích dat:**

1. **Provenience a verzování.** U povolených trénovacích úloh zaznamenat ID/hash, zdroj a split, původní reasoning/final, předpoklady, ověřovací status a historii. Udržovat **nejvýše tři skutečně existující nezávisle ověřené postupy** pro danou strukturu; pokud jsou jen dva, třetí nevymýšlet. Můžeme též vybrat tři obecné strategie napříč daty.
2. **Spouštěč opravy.** Pozdější ověřený krok, protipříklad nebo nalezený rozpor vytvoří návrh na zpětnou kontrolu. Podobnost zadání sama o sobě není důkazem chyby. Okamžitý návrat i kontrola na konci dávky zůstávají variantami k rozhodnutí podle ceny.
3. **Nezávislý verifier.** Znovu ověřit celé původní zadání, finální číslo i kontrolovatelné mezikroky deterministicky (aritmetika, rovnice, omezení, testy). LLM-judge smí navrhnout podezření, ale není konečnou autoritou; bez důkazu stav neověřeno.
4. **Nemazat minulost.** Originální generaci uchovat neměnnou, navrhnout novou verzi s přesnou příčinou chyby, důkazem a podmínkami platnosti. Rozlišit **XP+** (ověřené správné), **XP−** (ověřené selhání za konkrétních podmínek) a **REC** (historie opravy); náhodně správný final s chybným postupem není pozitivní trénovací trace.
5. **Přenos a trénování.** Správný postup zobecnit, otestovat na dalších povolených trénovacích variantách s jinými čísly i omezeními a **teprve po samostatném souhlasu** využít pro LoRA. Výsledný model otestovat na úplně novém holdoutu; měřit správnost, dokončení, total tokens (thinking + final), falešné opravy a výpočetní náklady REC.

**Soulad s původním BottleCapAI zadáním:** REC funguje **offline před trénováním / při přípravě dat**, ne během oficiálního evaluate.py. Odevzdaný Qwen3-0.6B nebo LoRA musí zůstat načitatelný standardními Transformers i vLLM bez vlastního runtime orchestrátoru či externí paměti; thinking zůstává zapnutý, oficiální prompty, sampling i limity se nemění. Neučit se z SVAMP, MBPP+, BFCL a IFEval. **60 již prohlédnutých otázek Evaluation 006 není nový nezávislý holdout**; pokud je někdy použijeme pro trénink, musíme je z nezávislých validačních nároků vyřadit. Vhodnější je stavět REC na jiných povolených trénovacích úlohách.

**Verified Lock (CEP 002 v0.3):** model smí navrhnout podezření na starou chybu, ale nesmí sám rozhodnout, že dříve nezávisle ověřený postup je neplatný. VPS uzamkne pouze kompletní, kontrolovatelný postup s důvěryhodným zadáním, ověřenými mezikroky a final; REC pak může pouze žádat nové ověření původních podmínek. Falešnou opravu zamítnout a počítat; při konfliktu kontraktů/verifierů vyhlásit LOCK_DISPUTED, zabránit automatickému zahrnutí do nového tréninku a vyžádat audit. Původní záznam vždy zachovat. Zámek **není důkaz neomylnosti verifieru**. Celý jednoduchý návrh: [RHAR-CEP 002 v0.3](CEP-002.md).

**Stav:** pouze dokumentace a testovatelná hypotéza. Žádná implementace REC/Verified Lock, nové GPU spuštění, trénování CEP 002 ani prokázaná úspora. Implementace, data a rozpočet čekají na zvláštní schválení.

