# 🐇 RHAR Safe Start — implementační plán a CPU testy

**Stav 10. 10. 2026:** první přípravná fáze schválena a CPU plánovač implementován. **Neproběhla žádná nová inference, stahování trénovacích dat ani trénování.** Nepředstírám dosaženou tokenovou úsporu.

[🇬🇧 English](../docs/SAFE-START.en.md) · [RHAR v0.1](RHAR-V01-PLAN.md) · [Vývojový deník](DEV-NOTES.md)

## 🎯 Co jsem schválil

Začnu malým matematickým pilotem: **12 různých úloh × 3 generace = 36 odpovědí**, se zapnutým thinking. Záměrem je zjistit, zda původní Qwen vytváří u stejných otázek různě dlouhé, ale **správné** reasoning traces. **36 je plánovaný počet, nikoli provedený benchmark.** Neslibuji, že vznikne 12 použitelných trénovacích vzorků.

## 🧩 Pevná konfigurace návrhu

| Nastavení | Předem navržená hodnota |
| --- | --- |
| Model | `Qwen/Qwen3-0.6B` |
| Revize modelu | `c1899de289a04d12100db370d81485cdf75e47ca` |
| Úlohy | 12 různých aritmetických otázek |
| Generace na úlohu | 3 se seedy `9001`, `9002`, `9003` |
| Thinking | `True` |
| Sampling | temperature `0.6`, top_p `0.95`, top_k `20` |
| Limit | `max_new_tokens=512`; useknuté odpovědi vyřadím |
| Možný budoucí zdroj | **GSM8K / train**, přesná revize musí být schválena a zafixována |
| Formát výsledku | pouze neutrální instrukce pro závěrečný řádek `Final answer:`, bez příkladu `42` |
| Oficiální evaluace | SVAMP, MBPP+, BFCL, IFEval zůstávají nedotčené |

Seedy označují **naplánované nezávislé samplingy**, nikoli garanci statistické nezávislosti či skutečně provedené inference. Zatím jen připravuji konfiguraci; generování bude potřebovat samostatný výslovný souhlas.

## 🧱 Fáze implementace a kontrolní brány

**A — Hotovo: offline plánovač.** Vytvořil jsem `diagnostics/safe_start_plan.py` a `tests/test_safe_start_plan.py`. Plánovač používá jen standardní knihovnu a konstanty ze stávající `reasoning_probe.py`. Jediný povolený režim CLI je `--dry-run`. Nenačítá GPU, Transformers ani datasetový klient, nic nezapisuje do souborů.

**B — Zatím neschváleno: připravit skutečných 12 otázek.** Jako návrh jsem v validátoru zafixoval **GSM8K train / math**. Skutečná data nesmím automaticky stahovat. Budu potřebovat schválit konkrétní revizi datasetu, výběr 12 otázek, licenci, kontrolu duplicity oproti ostatním datům i oficiálním benchmarkům a konzistentní train/validation hranici. Kontrola řetězce `source=gsm8k` **sama nezaručuje reálný původ dat ani nulový překryv s evaluací**.

**C — Zatím neschváleno: 36 GPU generací.** Až na další pokyn připravím samostatný generátor s checkpointy, pevnou konfigurací a záznamem úplných výstupů. Nechám původní Qwen uvažovat, zaznamenám reasoning/final/total tokeny, seedy, formát, latenci i chyby. Odhad 30–60 minut čisté inference z našich minulých běhů je **hrubý a nejistý**, bez nároku na schválení výpočetního rozpočtu.

**D — Zatím neschváleno: correctness-gated výběr.** Na výstupy použiji dosavadní `offline_selector.py`, ale teprve po prokázání autentického původu dat a kompatibility generovaných polí. Ten neověřuje matematické mezikroky v reasoning trace: nejkratší správná finální odpověď není automaticky důkazní postup. Výsledky budou pouze `review_only`.

**E — Samostatné budoucí rozhodnutí: LoRA a evaluace.** Příprava dat není trénování. Úpravu vah, validační sadu a oficiální porovnání provedu teprve po dalším schválení a na vhodném hardwaru.

## 🛡️ Kontrakt lokálních vstupních dat

Až budou data schválena, jediný lokální JSONL soubor musí mít **přesně 12 řádků**. Každý řádek bude JSON objekt s přesně těmito poli:

| Pole | Význam |
| --- | --- |
| `question_id` | Jednoznačný identifikátor úlohy |
| `question` | Neprázdná textová matematická otázka |
| `gold_answer` | Číselná správná odpověď, jako řetězec |
| `source` | Pouze `gsm8k` v tomto návrhu |
| `source_revision` | Přesně 40 hexadecimálních znaků konkrétního datového commitu |
| `split` | Pouze `train` |
| `task` | Pouze `math` |

Žádná skutečná otázka ani její gold answer není v repozitáři přidána. Validátor odmítá jiné zdroje, neznámá pole, různé revize, jiné splity, nečíselné odpovědi, chybějící úlohy a přesné duplicity. **Neodhalí všechny parafráze či kontaminaci — tu musím zvlášť auditovat.**

## 🧪 Jak ověřím CPU přípravu

V Kali po `git pull`:

```bash
cd ~/bottlecap-test
source .venv/bin/activate
python -m unittest tests.test_safe_start_plan -v
python -m unittest tests.test_offline_selector tests.test_reasoning_probe tests.test_safe_start_plan -v
python -m diagnostics.safe_start_plan --dry-run
```

Volitelně **po pozdějším schválení a ruční přípravě dat**:

```bash
python -m diagnostics.safe_start_plan --dry-run --questions data/safe-start/questions.jsonl
```

Tento příkaz **neprovádí generování**. Zvaliduje JSONL v paměti, spočítá plán **36 pokusů** a pouze vytiskne souhrn. Neobsahuje otázky ani správné výsledky ve výstupním manifestu, ale metadata ze vstupního souboru **neověřuje vůči skutečnému serveru datasetu**.

## ✅ Skutečné ověření a hranice

- V izolovaném lokálním Python prostředí prošlo **15/15 nových CPU testů** a také `python -m diagnostics.safe_start_plan --dry-run`. Pro použití existuje jen minimální lokální kopie konstant původní `reasoning_probe.py`, nikoli potvrzení celé GitHub větve.
- Předchozí **30/30** testů offline selektoru a reasoning diagnostiky potvrdil můj Kali běh v předcházejícím kroku. **Současnou společnou sadu 45 testů musí Kali po `git pull` teprve ověřit.**
- Nikdo zatím nevygeneroval 36 odpovědí, nepřipravil autorizovanou dvanáctku dat, netrénoval LoRA ani nezměřil snížení tokenů. **Plánování není výsledný RHAR algoritmus.**

Na projektu pracuji s pomocí **ChatGPT (OpenAI, GPT-6)** a vlastní lokální GGUF AI agentkou **Mášou**. Tento text a rozhodnutí píšu ze svého vývojářského pohledu; Máše nepřisuzuji nedoložené běhy.

**Další hranice souhlasu:** po zelené sadě 45/45 navrhnu přesný výběr dat, jejich revizi a postup deduplikace. **GPU zůstane vypnutá, dokud výslovně neschválím další experiment.**
