# 🐇 RHAR — jediná aktivní hypotéza a ověřovací plán

**Stav: výzkumná hypotéza; nikoliv prokázaný nový algoritmus. Aktualizace: 10. 10. 2026.**

[📔 Historie a surové výsledky](DEV-NOTES.md) · [📋 Soutěžní požadavky](QUEST-ODEVZDANI-CHECKLIST.md) · [🌍 IDEA (EN)](../IDEA.md)

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


## Hypotéza H-CEP-002: model získává „XP“ za ověřené přenositelné postupy (2026-10-10)

**Hypotéza:** Verifikace a zobecnění *postupů*, nikoliv memorování číselných odpovědí, může při následném učení vah Qwen3-0.6B podpořit přenos na neviděné úlohy a zkrátit zbytečný reasoning při stejné nebo lepší správnosti.

**Měřitelná predikce:** Proti standardnímu SFT 003 a CEP 001 na zcela novém, předem odděleném holdoutu musí kandidát CEP 002 vykázat příznivější párový poměr správnosti a **celkového** počtu generovaných tokenů; porovnat také úlohy se stejnou strukturou a změněnými údaji a úlohy se záměrně pozměněnou podmínkou, kde se uložený postup použít **nesmí**.

**Mechanismus k otestování:** z povolených trénovacích úloh vytvořit ověřenou zkušenost `{typ_problému, vstupy, vztahy, podmínky_použití, stručný_validovaný_postup, původ}`; použít k dalšímu LoRA tréninku, nikoli k doslovnému lookupu při oficiální inferenci. Výsledná inference nemá vyžadovat externí cache ani změnu oficiálního prompting/generation režimu.

**Alternativní vysvětlení:** případný zisk může být důsledkem kvalitnějších dat, většího trénovacího rozpočtu, náhody seedu nebo memorování vzorů, ne samotné „procedurální paměti“. Potřebujeme srovnatelný kontrolní trénink a nezávislá měření. Ukládání údajně správného postupu bez kontroly mezikroků může chyby upevnit.

**Stav důkazů:** Pouze formulovaný návrh, dosud žádné CEP 002 trénování ani evaluace. Průběžné hodnoty Evaluation 006 nejsou finální ani podkladem pro nový trénink. Neslibovat originality 1:1; related work existuje.
