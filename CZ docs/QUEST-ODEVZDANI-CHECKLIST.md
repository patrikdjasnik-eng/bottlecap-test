# 📦 BottleCapAI — můj checklist odevzdání

**Stav:** plán; nic jsem neodeslal. **Podklad:** [původní zadání](../docs/UPSTREAM-README.md).

[🗺️ Roadmapa](QUEST-DOKONCENI-PLAN.md) · [🔬 Experiment](QUEST-EXPERIMENTALNI-PLAN.md)

## Povinné artefakty

- [ ] Kód a historie repozitáře jako Git bundle, vytvořený příkazem `git bundle create vystup.bundle --all`.
- [ ] Skutečný soubor `results.json` vygenerovaný oficiálním `evaluate.py`.
- [ ] Natrénovaný Qwen3-0.6B nebo LoRA adapter v souborech `.safetensors`.
- [ ] Stručné finální `IDEA.md`: motivace, metoda, experimenty, úspěchy, chyby, hardware a omezení.
- [ ] Konfigurace, zdroje a revize trénovacích dat, seedy, postup reprodukce.
- [ ] Případné další checkpointy ilustrující poměr mezi délkou a správností.

## Kontrola kvality

- [ ] Mám potvrzeno, že adapter skutečně mění chování modelu při aktivním thinking.
- [ ] Trénovací data neobsahují evaluační benchmarky SVAMP, MBPP+, BFCL ani IFEval.
- [ ] Stejně nastavený base a kandidát mají skutečně naměřené tokeny a správnost.
- [ ] Pokud provedu `compare.py`, jsou oba vstupní běhy porovnatelné.
- [ ] Testy jsou zelené; vysvětlím přeskočené a zdokumentuji případný neúplný benchmark.
- [ ] ZIP neobsahuje tajemství, přístupové klíče ani nežádoucí osobní údaje.
- [ ] Výsledky nejsou přikrášlené; negativní výsledky zůstávají uvedené.

## Předání

- [ ] Nejprve připravím ZIP s názvem podle požadavku BottleCapAI a velikostí nejvýše **500 MB**.
- [ ] Preferovaně použiju [oficiální formulář](https://bottlecapai.com/careers/thinkingcap-test-submission/).
- [ ] Pokud se ZIP nevejde, použiju povolený odkaz na Hugging Face nebo Google Drive a e-mail podle upstream zadání.
- [ ] **Bez mého výslovného souhlasu nic neodesílám ani nezveřejňuji.**

**Hotovo znamená:** reprodukovatelný upravený model + doložené výsledky + kompletní odevzdávací balíček. Ne pouze hypotéza nebo diagnostické skripty. 🐇
