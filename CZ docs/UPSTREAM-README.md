# ThinkingCap Test

![logo](https://raw.githubusercontent.com/BottleCapAI/ThinkingCap-Test/main/img/logo.png)

Ahoj! Možná jsi už slyšel(a) o našich modelech [ThinkingCap](https://huggingface.co/bottlecapai/ThinkingCap-Qwen3.8-27B), které zkracují uvažování LLM. Teď hledáme lidi, kteří nám pomohou vytvořit to, co přijde dál.

Tohle je náš druhý otevřený test pro zájemce o práci ve [BottleCapAI](https://www.bottlecapai.com). Tentokrát je zaměřený na post-training (následné trénování modelů).

Zajímají tě LLM? Baví tě experimentovat s neuronovými sítěmi, implementovat různé nápady a zkoušet je? Chtěl(a) by ses tím živit? Pak jsi na správném místě!

## 📌 O BottleCapAI

V **BottleCapAI** děláme velké jazykové modely **radikálně efektivnějšími** — naším cílem je až **100× zlepšení** oproti současným přístupům. 🚀

### 👥 Zakladatelé
- Tomas Mikolov – tvůrce *word2vec*, průkopník neuronových jazykových modelů.
- Jaroslav Beck – spoluzakladatel *Beat Games* (*Beat Saber*, přes 10 milionů prodaných kopií, firmu koupila Meta).
- David Herel – tvůrce Thinking Tokens, spoluzakladatel startupu pro AI obchodování a finalista Amazon Alexa Prize.

### 🌍 Naše vize
Trénování a inference špičkových LLM dnes stojí **desítky milionů**. Naše nové algoritmy už tyto náklady snižují přibližně o **50 %**. Budujeme evropské centrum, které bude AI posouvat dopředu **algoritmy, ne hrubou výpočetní silou**.

📧 **hey(at)bottlecapai.com** · 🌐 [bottlecapai.com](https://www.bottlecapai.com)

---

## Cíl

Nauč **[Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B)** přemýšlet **stručněji**, aniž by ztratil přesnost.

Reasoning modely jsou dobré právě proto, že před odpovědí přemýšlejí, a ze stejného důvodu jsou drahé: každý token takového uvažování se musí vygenerovat. Qwen3-0.6B běžně spotřebuje stovky tokenů na otázky, které by mohl zodpovědět v několika desítkách. Tvým úkolem je naučit ho jít k věci.

**Cíl:** generovat **méně tokenů** (včetně uvažování) než původní Qwen3-0.6B a přitom zachovat **stejnou přesnost**.

---

## O co jde?

Zkrátit text je snadné. Uřízni uvažování, penalizuj každý token a výstupy budou krátké — a obvykle nesprávné. Těžké je odstranit nepotřebné uvažování, ale zachovat to, které je důležité.

Nehledáme kouzelnou větu, po které bude model přemýšlet méně. Chceme prozkoumat **algoritmické nápady, které lze škálovat**: postupy měnící způsob uvažování modelu, nikoli jen způsob formulace promptu. Prompt může být součástí metody, například při vytváření trénovacích dat, pokud se zkrácení nakonec projeví přímo v modelu.

Tento benchmark je určen pro:
- Lidi s omezeným hardwarem
- Lidi s vlastními nápady a zvídavostí

Můžeš zkoušet téměř cokoli, pokud model nakonec uvažuje stručněji (viz [Pravidla](#pravidla)). Například:
- Fine-tuning s vlastní účelovou funkcí
- Fine-tuning na datech podle vlastního výběru (ne na evaluačních benchmarcích; viz [Pravidla](#pravidla))
- Úpravu samotného modelu
- Něco, co ještě nikdo nezkusil!

**Nečekáme**, že budeš:
- Spoléhat se na prompt engineering
- Vypínat uvažování

Zajímají nás tvoje vlastní nápady, ne to, jak dobře umíš kopírovat jiné. Nápady by měly být obecné, fungovat v různých prostředích a neměly by být natvrdo přizpůsobené jedné velmi konkrétní situaci.

---

## Začínáme

Soubor [`train.py`](../train.py) načte model z Hugging Face a předá ti ho; všechno ostatní je na tobě.

```bash
git clone https://github.com/BottleCapAI/ThinkingCap-Test && cd ThinkingCap-Test
curl -LsSf https://astral.sh/uv/install.sh | sh    # skip if you already have uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

python utils/train/prepare_data.py    # writes data/train.jsonl, which train.py reads
python train.py
```

### Doporučené datasety

Trénovat můžeš na čemkoli, co dovolují [Pravidla](#pravidla). Pro snazší začátek navrhujeme tyto čtyři datasety: Qwen3-0.6B dokáže vyřešit podstatnou část úloh, ale ne všechny, takže je na čem se učit.

| Dataset | Oblast | Velikost trénovací sady |
| --- | --- | --- |
| [GSM8K](https://huggingface.co/datasets/openai/gsm8k) | Jednoduchá matematika | 7 473 |
| [Skywork-OR1](https://huggingface.co/datasets/Skywork/Skywork-OR1-RL-Data), lehká skupina | Matematika s prostorem pro zlepšení | ~28 tis. |
| [CommonsenseQA](https://huggingface.co/datasets/tau/commonsense_qa) | Odpovědi na otázky | 9 741 |
| [ARC Easy](https://huggingface.co/datasets/allenai/ai2_arc) | Odpovědi na otázky | 2 251 |

Složka [`utils/train/`](../utils/train/) obsahuje dva pomocné nástroje. Jejich použití není povinné, ale ušetří ti rutinní práci.

**[`utils/train/prepare_data.py`](../utils/train/prepare_data.py)** stáhne všechny čtyři datasety a převede je do jednoho formátu v `data/train.jsonl` a `data/val.jsonl` (200 oddělených validačních otázek z každého datasetu):

```bash
python utils/train/prepare_data.py
```

Každý záznam vypadá takto:

```json
{"prompt": [{"role": "user", "content": "<question> ... Put the final answer on the last line, like: Final answer: 42"}],
 "answer": "42", "task": "math", "source": "gsm8k"}
```

`prompt` je konverzace, kterou lze přímo předat chatovací šabloně tokenizéru. `answer` a `task` jsou hodnoty, které potřebuje hodnoticí funkce, a `source` určuje původní dataset (například pro vyvážení dat). Seznam chatových zpráv ve sloupci `prompt` a další sloupce očekává i většina trénovacích knihoven, takže tentýž soubor lze použít s různými metodami.

**[`utils/train/rewards.py`](../utils/train/rewards.py)** ověřuje správnost odpovědí. Předáš mu odpovědi modelu, správné odpovědi a typy úloh; za každou správnou odpověď vrátí 1.0 a za chybnou 0.0. Očekává, že odpověď končí řádkem `Final answer: <answer>`, jak požadují připravené prompty. Dodržuje rozhraní reward funkce knihovny TRL, takže by měl fungovat s většinou TRL trainerů.

[`train.py`](../train.py) ukazuje, jak to všechno zapadá dohromady: načte připravenou otázku, pomocí `rollout()` vygeneruje odpověď a vypíše její reward i délku v tokenech — dvě čísla, o která v tomto úkolu jde.

---

## Vyhodnocování benchmarků

Pro vyhodnocení tvého checkpointu jsme připravili čtyři benchmarky. Každý testuje jinou schopnost: matematiku (SVAMP), volání funkcí (BFCL), programování (MBPP+) a dodržování instrukcí (IFEval).

Celkem jde o **2 759 otázek**. Každá se zodpovídá 8krát, takže jeden plný běh vytvoří **22 072 odpovědí**. Menší počet vzorků lze použít pro rychlé testy, ale pouze 8 se počítá jako plné vyhodnocení.

| Benchmark | Počet otázek | Co úlohy vyžadují |
|---|---:|---|
| MBPP+ | 378 | Napsat Python funkci podle jednořádkového zadání a zachovat požadovaný název. |
| BFCL | 840 | Odpovědět na požadavek voláním nabízených funkcí. Tři podskupiny: |
| &nbsp;&nbsp;simple_python | 400 | K dispozici je jedna funkce a požadavek vyžaduje přesně jedno její volání. |
| &nbsp;&nbsp;multiple | 200 | K dispozici jsou dvě až čtyři funkce; vybrat správnou a vyplnit argumenty. |
| &nbsp;&nbsp;irrelevance | 240 | Žádná nabídnutá funkce se nehodí, a proto je správná odpověď bez volání funkce. |
| SVAMP | 1 000 | Slovní aritmetické úlohy na úrovni základní školy s jedinou číselnou odpovědí. |
| IFEval | 541 | Vytvořit odpověď splňující jednu až tři kontrolovatelné podmínky: 25 typů v 9 skupinách, například klíčová slova, délka, formátování, velikost písmen nebo jazyk. |
| **Celkem** | **2 759** | |

Průměr napříč benchmarky má pro každý ze čtyř benchmarků stejnou váhu; tři podskupiny BFCL se nejprve spojí v jeden benchmark. Změna přesnosti se průměruje aritmetickým průměrem, úspora tokenů geometrickým průměrem poměrů tokenů pro jednotlivé benchmarky.

### Spuštění baseline

Pokud máš repozitář naklonovaný a závislosti nainstalované (viz [Začínáme](#začínáme)), základní nezměněný Qwen3-0.6B vyhodnotíš dvěma příkazy:

```bash
python utils/eval/benchmarks.py        # download and freeze the questions
python evaluate.py --out runs/base     # the full baseline
```

První příkaz stáhne čtyři benchmarky v přesně určených revizích a uloží je do `questions/questions.jsonl`. Druhý vypíše jeden řádek pro každý benchmark (viz tabulka výše) a vytvoří `runs/base/`. V něm najdeš jednotlivé odpovědi v `records.jsonl` a soubor `results.json` se všemi informacemi potřebnými k interpretaci skóre. Baseline vyhodnoť jednou a výsledky si uchovej: všechny další běhy budeš s touto složkou porovnávat pomocí `compare.py`.

Před plným během ověř funkčnost pomocí `--smoke`. Tento režim zodpoví podmnožinu 30 otázek, vyhodnotí je stejným postupem jako skutečný běh, ale nevykazuje skóre; trvá přibližně minutu:

```bash
python evaluate.py --out runs/check --smoke
```

Uvede název každého benchmarku, jehož hodnoticí nástroj nefungoval. Odhalit to po minutě je levnější než po celém běhu.

### Vyhodnocení vlastního checkpointu

Checkpoint vyhodnoť na stejných otázkách jako baseline. Parametry závisí na způsobu trénování:

```bash
# a LoRA on top of the base model
python evaluate.py --out runs/mine --adapter ./my-lora

# your own weights, with or without an adapter of their own
python evaluate.py --out runs/mine --model ./my-qwen3
python evaluate.py --out runs/mine --model ./my-qwen3 --adapter ./my-lora
```

Potom jej porovnej s baseline. `compare.py` spáruje každou tvoji odpověď s odpovědí baseline na stejnou otázku a uvede úsporu tokenů i změnu přesnosti, vždy s intervalem spolehlivosti:

```bash
python compare.py runs/base runs/mine
```

Například takto může vypadat výstup pro LoRA adaptér (**ilustrační běh, nikoli cílové výsledky**):

```text
base       Qwen/Qwen3-0.6B
candidate  Qwen/Qwen3-0.6B + /home/.../adapter

bfcl_irrelevance  (240 prompts x 8 samples)
  tokens saved       +6.3%    CI [+2.3%, +10.0%]
  accuracy change   +0.00 pp  CI [-0.94 pp, +0.94 pp]

bfcl_multiple  (200 prompts x 8 samples)
  tokens saved       +8.5%    CI [+5.8%, +11.5%]
  accuracy change   +0.06 pp  CI [-1.50 pp, +1.69 pp]

bfcl_simple_python  (400 prompts x 8 samples)
  tokens saved       +6.9%    CI [+5.0%, +8.8%]
  accuracy change   +0.03 pp  CI [-0.78 pp, +0.84 pp]

ifeval  (541 prompts x 8 samples)
  tokens saved       +4.8%    CI [+1.8%, +7.7%]
  accuracy change   -0.46 pp  CI [-1.64 pp, +0.74 pp]

mbpp  (378 prompts x 8 samples)
  tokens saved       +7.8%    CI [+4.6%, +10.8%]
  accuracy change   -1.09 pp  CI [-2.45 pp, +0.40 pp]

svamp  (1000 prompts x 8 samples)
  tokens saved      +19.2%    CI [+17.4%, +20.9%]
  accuracy change   -0.14 pp  CI [-0.85 pp, +0.63 pp]

average over 4 benchmarks  (bfcl, ifeval, mbpp, svamp)
  equal weights; tokens saved is a geometric mean; BFCL subsets pooled as one
  tokens saved       +9.9%    CI [+8.6%, +11.1%]
  accuracy change   -0.42 pp  CI [-0.92 pp, +0.08 pp]
```

`accuracy change` znamená přesnost tvého modelu minus přesnost baseline v procentních bodech (pp), přičemž přesnost je podíl správných odpovědí v procentech. Odpovědi uříznuté limitem tokenů se počítají jako chybné. `tokens saved` představuje procentní pokles celkového počtu tokenů (uvažování i odpovědi) oproti baseline. Každá hodnota obsahuje **95% interval spolehlivosti**. Cílem je maximalizovat `tokens saved` a udržet `accuracy change` blízko nuly. Přesné definice jsou v [Poznámce k cílové metrice](#poznámka-k-cílové-metrice).

Poslední položka výstupu průměruje změnu přesnosti (aritmeticky) a úsporu tokenů (geometrický průměr poměrů tokenů) přes všechny benchmarky. Čtyři benchmarky mají stejnou váhu a tři podskupiny BFCL se považují za jediný benchmark.

### Menší rozsah vyhodnocení

Nemáš-li rychlou GPU, doporučujeme při vývoji neprovádět stále plnou evaluaci — menší počet benchmarků a vzorků zkrátí vývojovou smyčku. Pro konečná čísla se pokus vyhodnotit všechno. Pokud to není možné, práci přesto odešli a uveď, které části jsi nemohl(a) spustit; všechny přihlášky znovu vyhodnotíme sami. Ať už provádíš jakýkoli rozsah testů, základní model skóruj **přesně stejně** jako svůj checkpoint, jinak nemá srovnání smysl. Sleduj také intervaly spolehlivosti.

### Zdroje a licence

| Benchmark | Zdroj | Licence |
|---|---|---|
| MBPP+ | [EvalPlus MBPP+ release](https://github.com/evalplus/mbppplus_release), založeno na [MBPP](https://github.com/google-research/google-research/tree/master/mbpp) (Austin a kol., Google) | Apache-2.0 (MBPP+), CC-BY-4.0 (MBPP) |
| BFCL | [Gorilla](https://github.com/ShishirPatil/gorilla), Berkeley Function Calling Leaderboard v4 | Apache-2.0 |
| SVAMP | [arkilpatel/SVAMP](https://github.com/arkilpatel/SVAMP) | MIT |
| IFEval | [google-research](https://github.com/google-research/google-research), `instruction_following_eval` | Apache-2.0 |

Benchmarky patří jejich autorům. `utils/eval/benchmarks.py` je stahuje z výše uvedených zdrojů a dál je nešíří. Pokud zveřejníš výsledky, uveď původní benchmarky a dodrž jejich licenční podmínky.

---

## Pravidla

1. Začni s **Qwen3-0.6B**. Full fine-tuning, LoRA, menší architektonické úpravy[^1] a podobné postupy jsou povolené, pokud výsledkem zůstane přibližně 0.6B model, který před odpovědí uvažuje.
2. **Netrénuj** na evaluačních benchmarcích.
3. Měř pomocí dodané evaluace a neměň její nastavení (prompt, sampling, token cap). Menší počet benchmarků nebo fp16 na GPU bez bf16 je v pořádku, pokud má baseline stejnou konfiguraci.
4. Popiš svůj nápad v `IDEA.md` (motivaci, metodu a výsledky). Vítáme i negativní výsledky — napiš, co ses naučil(a)!

[^1]: Upravený model musí být možné načíst standardními verzemi Hugging Face Transformers a vLLM, protože `evaluate.py` jej používá v obou prostředích a nespouští vlastní modelový kód.

---

## Odevzdání

Pošli nám svoji práci. Nevadí, pokud při zkracování trochu klesla přesnost — chceme ji vidět i tak.

Přilož:

- svůj kód jako Git bundle: `git bundle create <first name>-<last name>.bundle --all`
- soubor `results.json` vytvořený pomocí `evaluate.py` ve složce zadané v `--out`
- natrénovaný model (nebo LoRA adaptér) ve formátu `.safetensors`, abychom jej mohli sami vyhodnotit
- krátký `IDEA.md` s popisem toho, co jsi zkoušel(a), proč, co fungovalo, co ne, a jaký hardware jsi použil(a)

Začne přesnost při výraznějším zkracování klesat? Pošli několik checkpointů z různých fází. Zajímá nás vztah mezi délkou a přesností; několik bodů na této křivce nám řekne víc než jeden jediný výsledek.

**Jak práci odeslat**

Pokud můžeš, použij [stránku pro odevzdání](https://bottlecapai.com/careers/thinkingcap-test-submission/): všechny výše uvedené věci vlož do jednoho souboru `.zip` o velikosti nejvýše 500 MB, pojmenovaného `<first name>-<last name>.zip`, a nahraj ho.

Pokud se obsah nevejde, nahraj jej na [Hugging Face](https://huggingface.co) nebo [Google Drive](https://drive.google.com) a pošli odkaz na hey(at)bottlecapai.com s předmětem `<first name>-<last name> <token reduction> <accuracy change>` (použij čísla svého nejlepšího checkpointu).

V tuto chvíli nás zajímají hlavně uchazeči ochotní přestěhovat se do Prahy. Pokud jsi mimořádně vhodný kandidát nebo kandidátka, rádi probereme možnosti podpory.

---

## Technické poznámky

Ačkoli je projekt navržen pro práci na **jedné GPU**, stojí za to pamatovat na několik věcí:

- **Paměť GPU a Google Colab:**

  Qwen3-0.6B je dost malý na generování i trénování na bezplatné [Google Colab](https://colab.research.google.com/) T4 (16 GB), pokud budeš rozumně hospodařit s pamětí. Hlavním problémem obvykle není samotný model (~1,2 GB ve fp16), ale **logity**: při slovníku s 151 936 tokeny vytvoří sekvence o délce 4 096 tokenů přibližně 2,3 GB logitů ve fp32 a naivně implementovaná ztrátová funkce drží během zpětného průchodu několik kopií. Pomoci může:

  - **Použít LoRA** místo full fine-tuningu. Gradienty a stav optimalizátoru se pak ukládají pouze pro malý adaptér, ne pro všech 600 milionů parametrů.
  - **Nedržet druhou kopii modelu.** Pokud vedle trénovaného modelu potřebuješ původní referenční model, vypni LoRA adaptér, místo abys znovu načítal(a) celý model.
  - **Zapnout gradient checkpointing** (`model.gradient_checkpointing_enable()`): výpočet bude pomalejší, ale aktivace už nebudou dominovat spotřebě paměti.
  - **Zlevnit výpočet ztráty.** Počítej ji pouze nad vygenerovanými tokeny, nikdy nad promptem, a použij blokovou nebo sloučenou cross-entropy (například [Liger Kernel](https://github.com/linkedin/Liger-Kernel)), aby se všechny logity nemusely najednou materializovat.
  - **Použít malé micro-batche** (klidně jednu sekvenci) a gradient accumulation pro dosažení větší efektivní dávky. Pomohou i kratší sekvence: poloviční délka znamená poloviční počet logitů.
  - **Pamatovat na přesnost T4:** T4 nepodporuje bf16, použij fp16 s váhami LoRA ve fp32 (mixed precision), případně fp32, pokud fp16 vede k hodnotám NaN.

  Na Colabu bývá větším omezením rychlost a doba relace než paměť: dlouhé generování na T4 je pomalé a bezplatné relace se odpojují, takže průběžně ukládej checkpointy.

- **Evaluace na T4:**

  vLLM se tam ve výchozím nastavení vůbec nespustí: z konfigurace modelu převezme bf16, které T4 neumí. Přidej `dtype="half"` do volání `LLM(...)` ve funkci `load_engine` a stejné nastavení použij i pro baseline. Plná evaluace na T4 trvá zhruba pět hodin. Pokud můžeš, pronajmi si na hodinu kartu architektury Ampere nebo novější — RTX 3090/4090, A5000, L4 nebo RTX PRO 6000 zvládnou bf16 bez změny a dokončí běh za méně než dvě hodiny.

- **Sampling:**

  Qwen v režimu uvažování doporučuje temperature 0.6, top-p 0.95 a top-k 20. Greedy decoding způsobuje, že se Qwen3 začne opakovat; výsledkem pak vypadá jako dlouhé uvažování, ale není to tak.

---

### Poznámka k cílové metrice

Každá otázka má 8 odpovědí, jak vyžaduje plná evaluace, a každá odpověď se hodnotí samostatně.

- **Přesnost (Accuracy)** v benchmarku je procento správných odpovědí. Odpověď uříznutá limitem tokenů se počítá jako špatná.
- **Průměrná přesnost (Averaged accuracy)** je průměr přesností čtyř benchmarků; tři podskupiny BFCL se počítají jako jeden benchmark.
- **Změna přesnosti (Accuracy change)** je tvoje průměrná přesnost minus průměrná přesnost baseline, vyjádřená v procentních bodech.
- **Úspora tokenů (Tokens saved)** v benchmarku je `1 - tokens_yours / tokens_baseline`, kde `tokens_yours` a `tokens_baseline` představují celkové počty vygenerovaných tokenů (včetně uvažování) přes všechny odpovědi v benchmarku, ať jsou správné, chybné nebo uříznuté.
- **Průměrná úspora tokenů (Average tokens saved)** je `1 - (r_1 × r_2 × r_3 × r_4)^(1/4)`, kde `r_i = tokens_yours / tokens_baseline` pro benchmark `i`; jde o geometrický průměr čtyř poměrů počtu tokenů.

Obě metriky obsahují **95% interval spolehlivosti**, vypočtený opakovaným vzorkováním celých otázek a párováním odpovědí tvého modelu s baseline otázku po otázce. Nesleduj jen samotný bodový odhad, ale i interval: pokud interval změny přesnosti zahrnuje nulu, nelze pomocí této evaluace změnu spolehlivě odlišit od žádné změny.
