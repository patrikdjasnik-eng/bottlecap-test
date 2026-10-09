# 🔬 DEV-NOTES — Vývojový deník

[🇨🇿 Česky](DEV-NOTES.md) · [🇬🇧 English](DEV-NOTES.en.md)

## Pravidla spolupráce

- **O důležitých technických rozhodnutích, nových experimentech a zásadních nápadech rozhoduje vlastník projektu.** Asistent předem vysvětlí možnosti, výhody, rizika a vyžádá si souhlas.
- Bez předchozího souhlasu neměnit směr výzkumu, model, trénovací strategii, benchmarkové podmínky, strukturu projektu ani neprovádět zásadní změny v repozitáři.
- Běžné, výslovně zadané úpravy dokumentace a technické opravy v odsouhlaseném rozsahu lze provádět, s jasným zápisem do deníku.
- Rozlišovat **provedeno / ověřeno / navrženo / čeká na schválení / chyba**. Nikdy nepředstírat úspěch testů nebo naměřené výsledky.
- Zápisy uvádějí datum, změny, důvod, ověření a další krok. Zásadní rozhodnutí mají explicitní stav schválení.
- **Bez zelených testů ani krok** při změnách kódu; pro dokumentační změny ověřit strukturu a odkazy.

## Deník

### 2026-10-09 — CUDA výpočet ověřen na lokální GPU

**Stav:** ověřeno uživatelem v Kali Linux / WSL2.

**Provedeno:** v aktivovaném `.venv` (Python 3.11) byl spuštěn jednoduchý PyTorch CUDA test s `torch.ones(256, device="cuda")` a součtem `(tensor * 2).sum()`.

**Výsledek:** PyTorch `2.6.0+cu118`, CUDA runtime `11.8`, `torch.cuda.is_available(): True`, GPU `NVIDIA GeForce GTX 1070 Ti`, compute capability `(6, 1)`, výsledek GPU výpočtu `512.0`.

**Upozornění:** při importu se objevilo `Failed to initialize NumPy: No module named 'numpy'`; tento warning test CUDA nezastavil.

**Co to neprokazuje:** model Qwen3-0.6B nebyl spuštěn ani trénován, oficiální benchmark nebyl proveden.

**Další návrh (čeká na schválení):** doinstalovat kompatibilní NumPy, znovu ověřit běh a poté projednat první inferenční pokus s Qwen3-0.6B.


### 2026-10-09 — Pravidla spolupráce a jazykové klony

**Stav:** pravidla potvrzena vlastníkem projektu; dokumentace se doplňuje na vývojové větvi.

**Provedeno:** zaznamenáno, že DEV-NOTES je vývojový deník, nikoli jen seznam úkolů. Doplněna pravidla schvalování významných kroků. Zahájeny české a anglické jazykové protějšky dokumentace.

**Ověření:** předchozí uživatelský běh jednotkových testů 87 OK, 2 přeskočené; pro novou dokumentaci nebylo provedeno nové trénování ani spuštění benchmarku.

**Čeká na schválení:** konkrétní algoritmus komprese reasoning procesu, způsob trénování, první GPU experiment a případné změny v kódu.

## Přehled dosavadního stavu

## Stav — 9. 10. 2026

- [x] Založen samostatný repozitář a vývojová větev `feat/reasoning-compression`.
- [x] Převzaty oficiální Python skripty, testy a licence BottleCapAI.
- [x] Popsána skutečná PC konfigurace a limity GPU.
- [x] Připraven výzkumný plán `IDEA.md`.
- [x] Spuštěny lokální unit testy (Kali Linux / WSL2, Python 3.14.7): **87 testů OK, 2 přeskočeny** (EvalPlus a BFCL zatím nejsou stažené), běh 0,321 s.
- [x] Zprovozněn izolovaný Python **3.11.17** v `.venv` na Kali Linux / WSL2; ověřil uživatel 9. 10. 2026.
- [x] `nvidia-smi` ve WSL2 detekuje **NVIDIA GeForce GTX 1070 Ti (8192 MiB)**, driver 582.78, nvidia-smi 580.178.01; v okamžiku kontroly 882 MiB obsazeno. Zobrazené `CUDA Version: 13.0` udává schopnost driveru, nikoli funkčnost PyTorch.
- [ ] Ověřit CUDA výpočty v **PyTorch 2.6.0 + cu118** na GPU (zatím netestováno); při problémech nezaměňovat detekci GPU za funkční kernel.
- [ ] Doinstalovat knihovny Transformers/Accelerate až po zeleném PyTorch CUDA testu.
- [ ] Prověřit bubblewrap sandbox před evaluací MBPP+ (varování: dostupný jen slabší fallback s resource limity).
- [ ] Připravit tréninková data mimo eval benchmarky.
- [ ] Provést baseline smoke test a uložit run artefakty.
- [ ] Vygenerovat správné, krátké reasoning traces.
- [ ] Trénovat LoRA adaptér a provést validaci.
- [ ] Porovnat plnou evaluaci baseline vs kandidát na podporované GPU.
- [ ] Sepsat reprodukovatelný závěrečný report včetně negativních výsledků.

## Poznámky

Benchmarky v projektu dávají úlohám osm samplů na otázku při plném běhu. Plná sada obsahuje 2 759 zadání. Nezaměňovat syntetické metriky s oficiální evaluací.

Po vývoji na feature větvi otevřít PR do `main` až po validaci.
