# 🖥️ Hardware — Rabbit Hollow Research

Stav konfigurace podle diagnostiky Windows PowerShell (8. října 2026).

| Komponenta | Detaily |
| --- | --- |
| **GPU** | NVIDIA GeForce GTX 1070 Ti, **8 GB VRAM** |
| **CPU** | Intel Core i5-3450 @ 3.10 GHz, **4 jádra / 4 vlákna** |
| **Základní deska** | ASUSTeK COMPUTER INC. **P8B75-M** |
| **RAM** | **16 GB** |
| **Vývojové prostředí** | Windows + PowerShell; WSL2/Kali dostupné |

## Omezení a rozhodnutí

GTX 1070 Ti je Pascal (compute capability 6.1). Standardní CUDA backend vLLM pro oficiální `evaluate.py` tuto generaci GPU nepodporuje, a proto zde **nebudeme vykazovat fiktivní benchmarky**.

- Lokálně: statická kontrola, pytest, unit testy, příprava trénovacích dat, krátké inferenční pokusy, pokud se runtime podaří rozchodit.
- Trénink: preferujeme LoRA na dostupné externí GPU, např. Google Colab T4 16 GB (fp16, nikoliv bf16).
- Oficiální finální evaluace: GPU s podporovaným vLLM, ideálně Ampere nebo novější.
- Srovnání: baseline a kandidát na stejném evaluačním nastavení; měřit přesnost i celkové tokeny, zachovat CI.

## Evidence výkonu

| Datum | Model / adaptér | Zařízení | Evaluace | Ušetřené tokeny | Změna přesnosti |
| --- | --- | --- | --- | --- | --- |
| — | Qwen3-0.6B | zatím neprovedeno | čeká | — | — |

Není zde žádný naměřený výsledek, dokud neproběhne skutečný run.
