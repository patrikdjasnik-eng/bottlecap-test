# 🧪 RHAR v0.1 — Offline correctness gate a výběr kandidátů

[🇨🇿 Čeština](OFFLINE-SELECTOR.md) · [🇬🇧 English](../docs/OFFLINE-SELECTOR.en.md) · [Plán RHAR v0.1](RHAR-V01-PLAN.md)

**Stav:** implementoval jsem **offline revizi již existujících JSONL generací**. Skript nemá závislost na PyTorch ani na GPU. **Nespouští Qwen, nestahuje data, nemění váhy a nic netrénuje.** Výběr je určen k revizi, ne automaticky do training dat.

## Co přesně běží

`diagnostics/offline_selector.py` načte `records.jsonl`, znovu vyhodnotí odpověď podle reference (nespoléhá jen na původní pole `correct`) a ke každé generaci přiřadí důvod přijetí či odmítnutí. Kontroluje:

1. Známou úlohu a očekávanou odpověď; podporuje prozatím **číslo** (včetně desetinného) nebo **jednopísmennou volbu**. Neověřuje exekuci kódu, funkční volání ani obecná faktická tvrzení.
2. Jednoznačný poslední řádek `Final answer: ...`; chybné, vícenásobné či neparsovatelné výstupy odmítne.
3. Neuseknuté generování, rozpoznaný `<think>…</think>` blok (nebo korektně označený předvyplněný začátek) a konzistentní přepočet `reasoning_tokens + final_tokens == total_tokens`. Počty tokenů bere ze záznamu, **nepřepočítává je tokenizerem**.
4. Zjevné rozpory s původním příznakem správnosti, duplicitní seedy a srovnatelnost promptu/modelu a reference v rámci jedné otázky.
5. Oddělené trénovací metadata: `source`, `source_revision`, `split=train`, `model_revision`, `prompt_hash`, `thinking_enabled=true`, `seed`. **Bez těchto údajů je záznam jen pro analýzu.** Zdroj pojmenovaný SVAMP/MBPP/BFCL/IFEval či jejich běžnými variantami se explicitně odmítá pro trénovací výběr. Tento jednoduchý filtr **sám nedokazuje, že data žádný oficiální benchmark neobsahují** — před trénováním bude nutná skutečná kontrola původu a deduplikace.
6. Výběr pouze **jednoho nejkratšího správného kandidáta z alespoň dvou správných generací téže otázky s odlišnými seedy**. Pokud je správná jen jedna, nezískám falešný důkaz komprese.

**Pozor:** správný výsledek neznamená nutně správný každý mezikrok. **RPD ani RPS zatím nejsou implementovány**; vybrané stopy jsou pouze `review_only` a vyžadují další prověření.

## Spuštění v Kali / WSL2

Po stažení změn nejprve spustím CPU testy, bez načítání LLM:

~~~bash
cd ~/bottlecap-test
git pull --ff-only origin feat/reasoning-compression
source .venv/bin/activate
python -m unittest tests.test_offline_selector tests.test_reasoning_probe -v
~~~

Jestli testy projdou, lze **bez další inference** přečíst starý lokální Experiment 002:

~~~bash
python -m diagnostics.offline_selector runs/diagnostics/20261009T210123Z/records.jsonl
~~~

Volitelné parametry: `--out runs/offline/moje-kontrola` (musí jít o dosud neexistující složku), `--min-correct 2` (minimum je 2).

## Výstup: vždy nová složka `runs/offline/<UTC>/`

| Soubor | Obsah |
| --- | --- |
| `review_records.jsonl` | Záznam o každé odpovědi: `correct`, `training_eligible`, `selected`, `reason`, délka a seed |
| `selected_for_review.jsonl` | Maximálně jeden nejkratší správný kandidát na srovnatelnou otázku; **review_only**, nikoliv trénovací sada |
| `summary.json` | Počet záznamů, znovu zkontrolované správné odpovědi, důvody odmítnutí, SHA-256 vstupu, příznaky `no_training_performed=true` a `official_benchmark=false` |

Soubory zůstávají pod Git ignorovaným `runs/`. **Surový generovaný text může obsahovat citlivé údaje — nedávám ho bez kontroly do veřejného repa.** Existující výstupní složky se nepřepisují; chybné JSONL vstupy skončí s hlášením řádku ještě před zápisem výsledků.

Starý Experiment 002 má pouze jednu, navíc nesprávnou odpověď (`42` místo `43`). **Očekávané chování** je `selected_for_review = 0`. Není to nové naměřené číslo z Kali; takto by měl program starý záznam vyhodnotit.

## Testy, omezení a další rozhodnutí

- **Připraveno a lokálně ověřeno:** 16 nových CPU unit testů selektoru; společně s rekonstruovanou aktuální diagnostickou sadou **26/26 prošlo v izolovaném lokálním prostředí**. Ověření na mém Kali po `git pull` stále **čeká**, stejně jako případný GPU pilot.
- Regresní testy kontrolují mimo jiné chybnou odpověď `42`, halucinovanou správnost v poli `correct`, poškozené thinking značky, useknutý výstup, počty tokenů, zakázané zdroje, původ, duplicity, rozdílné prompty a zákaz přepisování souborů.
- Implementace **nevyhodnocuje poctivost každého kroku reasoning trace**, nepřipravuje bezpečný ML dataset a neumí potvrdit faktickou absenci kontaminace z benchmarků. Metadata v JSONL mohou být chybná nebo podvržená; před skutečným učením bude třeba je nezávisle ověřit.
- **Čeká na další samostatné rozhodnutí:** konečné trénovací zdroje, generovací pipeline, počet GPU běhů, rekonstrukční kontroly RPD, LoRA, úpravy vah a oficiální evaluace.

Na projektu otevřeně spolupracuji s **ChatGPT (OpenAI, GPT-6)** a vlastní lokální GGUF agentkou **Mášou**. Tento záznam píšu ze svého pohledu; Máše nepřisuzuji konkrétní běhy, které nemám doložené.
