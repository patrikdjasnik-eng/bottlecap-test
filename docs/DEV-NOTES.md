# 🔬 DEV-NOTES

## Stav — 9. 10. 2026

- [x] Založen samostatný repozitář a vývojová větev `feat/reasoning-compression`.
- [x] Převzaty oficiální Python skripty, testy a licence BottleCapAI.
- [x] Popsána skutečná PC konfigurace a limity GPU.
- [x] Připraven výzkumný plán `IDEA.md`.
- [x] Spuštěny lokální unit testy (Kali Linux / WSL2, Python 3.14.7): **87 testů OK, 2 přeskočeny** (EvalPlus a BFCL zatím nejsou stažené), běh 0,321 s.
- [ ] Zprovoznit izolovaný Python 3.11 a kompatibilní ML dependencies pro další fázi.
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
