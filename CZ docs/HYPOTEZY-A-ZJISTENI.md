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
