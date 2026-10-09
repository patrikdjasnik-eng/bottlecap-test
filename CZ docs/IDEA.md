# IDEA.md — Adaptivní komprese reasoning procesu

## Motivace

Qwen3-0.6B dokáže vytvářet dlouhé řetězce uvažování i u jednoduchých úloh. Cíl: snížit *celkový počet generovaných tokenů* bez významné ztráty přesnosti, a to i na dosud neviděných benchmarcích.

## Hypotéza

**Destilace stručného reasoning procesu s filtrováním podle správnosti.** Z původního modelu získáme malý počet krátkých, ale *správných* postupů uvažování, a to pouze s využitím povolených trénovacích dat. Model doladíme pomocí malého adaptéru LoRA, přičemž zachováme explicitní uvažování a formát finální odpovědi. Cílem je méně nadbytečných kroků, nikoli jen zkracování pomocí promptu.

## Metoda (návrh)

1. Připravit trénovací a validační sady pomocí `utils/train/prepare_data.py`. Nikdy k trénování nepoužívat čtyři evaluační benchmarky.
2. Vygenerovat více kandidátních odpovědí z výchozího modelu Qwen3-0.6B se zapnutým uvažováním; zaznamenat počet vygenerovaných tokenů.
3. Pomocí správných odpovědí z trénovacích dat a `utils/train/rewards.py` odfiltrovat chybné výstupy. U každé otázky upřednostnit nejkratší *správný*, neprázdný postup uvažování.
4. Provést supervidované dolaďování (SFT) pomocí LoRA. Při výpočtu ztrátové funkce maskovat tokeny promptu. Začít na malé trénovací sadě a sledovat nadměrnou kompresi, uříznuté odpovědi a chyby ve formátu.
5. Ověřit výsledek na oddělené části trénovacích datasetů; potom vyhodnotit oficiálním, nezměněným `evaluate.py`.
6. Porovnat `runs/base` a `runs/mine` pomocí `compare.py`. Zapsat úsporu tokenů, změnu přesnosti, 95% intervaly spolehlivosti a konfiguraci běhu.

## Omezení

- Výchozí model: `Qwen/Qwen3-0.6B`.
- Finální model musí zůstat přibližně 0.6B veliký a skutečně provádět uvažování.
- Žádný trénink na SVAMP, MBPP+, BFCL ani IFEval.
- Neměnit prompty benchmarků, nastavení generování ani limit tokenů.
- Preferovat standardní cestu načítání Hugging Face + vLLM.
- Všechny výsledky musí být podloženy skutečnými běhy, nikoli odhady.

## Výsledky

Zatím nezměřeno.

## Hardware

Viz [HARDWARE.md](HARDWARE.md). Lokální sestava: GTX 1070 Ti (8 GB), Intel i5-3450, ASUS P8B75-M, 16 GB RAM.

## Co fungovalo / nefungovalo

Experimenty zatím čekají na provedení.
