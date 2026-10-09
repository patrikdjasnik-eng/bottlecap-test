# 🧠 BottleCapAI — ThinkingCap Test

**🇨🇿 Čeština** · [🇬🇧 English](../README.md)

[![Challenge](https://img.shields.io/badge/Challenge-BottleCapAI_ThinkingCap-7C3AED)](https://github.com/BottleCapAI/ThinkingCap-Test)
![Research status](https://img.shields.io/badge/Research-in_progress-yellow)
![Benchmark status](https://img.shields.io/badge/Full_benchmark-not_run-orange)
![GPU](https://img.shields.io/badge/GPU-GTX_1070_Ti_8GB-76B900?logo=nvidia&logoColor=white)
![CPU](https://img.shields.io/badge/CPU-Intel_i5--3450-0071C5?logo=intel&logoColor=white)
![Mainboard](https://img.shields.io/badge/Mainboard-ASUS_P8B75--M-232323)
![RAM](https://img.shields.io/badge/RAM-16_GB-475569)
![License](https://img.shields.io/badge/Upstream-Apache_2.0-2563EB)

> 🐇 Rabbit Hollow Research: učení kratšího reasoning procesu u **Qwen3-0.6B** bez znatelné ztráty přesnosti.

## 🎯 Zadání

Zvýšit efektivitu reasoning modelu **změnou jeho chování v modelu**, ne přepnutím na `enable_thinking=false` nebo pouhým promptem.

- **Výchozí model:** `Qwen/Qwen3-0.6B`.
- **Cíl:** snížit celkový počet generovaných tokenů (thinking + odpověď) při srovnatelné přesnosti.
- **Benchmarky:** SVAMP, MBPP+, BFCL, IFEval.
- **Pravidla:** žádný trénink na evaluačních datech, neměnit nastavení oficiální evaluace.
- **Aktuální stav:** struktura projektu připravena; žádný výsledek benchmarku ani zlepšení zatím netvrdíme.

## 🖥️ Vývojový počítač

| Součást | Konfigurace |
| --- | --- |
| GPU | **NVIDIA GeForce GTX 1070 Ti**, 8 GB VRAM |
| CPU | **Intel Core i5-3450**, 3,10 GHz, 4 jádra / 4 vlákna |
| Základní deska | **ASUS P8B75-M** |
| Operační paměť | **16 GB RAM** |

Podrobnosti, limity a plán práce s externí GPU: [HARDWARE.md](HARDWARE.md). GTX 1070 Ti může posloužit k lehkým lokálním pokusům, avšak oficiální vLLM evaluace vyžaduje novější GPU. Plný benchmark lokálně na této kartě nepředpokládáme.

## 🔬 Výzkumné soubory

- [IDEA.md](IDEA.md) — hypotéza, metoda, plán měření a protokol výsledků. [Anglicky](../IDEA.md).
- [DEV-NOTES.md](DEV-NOTES.md) — vývojový deník, postup a schvalování rozhodnutí. [Anglicky](../docs/DEV-NOTES.en.md).
- [UPSTREAM-README.md](UPSTREAM-README.md) — kompletní český překlad zadání. [Anglický originál](../docs/UPSTREAM-README.md).
- [HARDWARE.md](HARDWARE.md) — hardware a jeho omezení. [Anglicky](../docs/HARDWARE.en.md).
- `train.py`, `evaluate.py`, `compare.py` — oficiální nástroje BottleCapAI.

## ✅ Zásady experimentů

**Bez zelených testů ani krok.** Každý zásah musí mít opakovatelné ověření a měření proti stejné baseline. Výsledky zapisujeme včetně nepovedených experimentů a hardware, na kterém vznikly.

O důležitých technických rozhodnutích, nových experimentech a zásadních změnách se nejprve poradíme a vyžádáme souhlas vlastníka projektu. Pravidla a zápisy najdeš ve [vývojovém deníku](DEV-NOTES.md).

Zdrojové zadání: [BottleCapAI/ThinkingCap-Test](https://github.com/BottleCapAI/ThinkingCap-Test). Původní kód je distribuován s licencí Apache-2.0; viz [LICENSE](../LICENSE).
