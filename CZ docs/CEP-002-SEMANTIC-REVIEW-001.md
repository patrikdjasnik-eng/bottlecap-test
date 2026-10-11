# 🧠 CEP-002 — předběžná sémantická revize 001

**Datum:** 2026-10-11  
**Autor posouzení:** asistent, autor návrhů; **nejde o nezávislé externí hodnocení**  
**Stav:** PRELIMINARY_CHECK / REVIEW_REQUIRED  
**Zdroj:** lokálně připnutý GSM8K `main/train`, revize `740312add88f781978c0658806c59bc2815b9866`  
**Podklad:** `runs/cep002-contract-drafts-001/review-packet.md`

## Co skutečně proběhlo

Uživatel potvrdil 69 zelených CPU unit testů a úspěšné `--dry-run` i `--execute` revizního protokolu. Tři návrhy mají přesné matematické mezikroky a souhlasí s referenčními odpověďmi. Tento dokument navíc rozebírá sémantiku zadání nezávisle na číselném porovnání, ale stále **nepředstavuje externí nezávislou revizi** ani autorizační rozhodnutí.

## 1. `gsm8k-train-00664` — délka života ryby

- Výchozí množství: křečci žijí průměrně `2.5` roku.
- „Dogs live 4 times as long“: `dog_years = 2.5 × 4 = 10`.
- „Fish can live 2 years longer than dogs“: `fish_years = 10 + 2 = 12`.
- Referenční finále `12` souhlasí.
- Riziko: zaměnit přičtení dvou let za násobení; výpočet `2.5 × (4+2) = 15` by byl chybný.
- **Předběžný verdikt:** matematicky i jazykově konzistentní.

## 2. `gsm8k-train-06718` — šampony

- Výchozí množství: `1/3` lahve růžového, `1/4` lahve jasmínového šamponu; spotřeba `1/12` lahve denně.
- Převod do společného jmenovatele: `4/12 + 3/12 = 7/12`.
- Počet dní: `(7/12) / (1/12) = 7`.
- Referenční finále `7` souhlasí.
- **Podmínka významu:** obě uvedené „lahve“ představují stejnou referenční jednotku objemu, jak úloha implicitně předpokládá. Při různě velkých lahvích by zadání neudávalo dost údajů.
- Riziko: sčítat jmenovatele nebo zaměnit jednu dvanáctinu *z každé* lahve za jednu dvanáctinu celé standardní lahve.
- **Předběžný verdikt:** správné při předpokladu jednotné velikosti lahve.

## 3. `gsm8k-train-03644` — sociální sítě

- Instagram `240`, Facebook `500`: dohromady `740`.
- Twitter = polovina součtu IG+FB = `370`.
- TikTok = trojnásobek Twitteru = `1110`.
- YouTube = TikTok + `510` = `1620`.
- Součet pěti platforem = `240 + 500 + 370 + 1110 + 1620 = 3840`.
- Referenční finále `3840` souhlasí.
- **Podmínka významu:** počítáme součet sledování podle jednotlivých profilů, nikoliv počet unikátních osob, které mohou sledovat více profilů.
- Riziko: nezahrnout původní Instagram/Facebook nebo přičíst `510` ještě jednou.
- **Předběžný verdikt:** matematicky i jazykově konzistentní pro součet jednotlivých platforem.

## Blokující podmínky před VPS/XP/tréninkem

- [ ] Nezávislý recenzent ověří význam, všechna fakta a výpočty vůči původnímu zdroji (nikoli jen podle návrhu autora).
- [ ] Explicitně dokumentovaný audit historického překryvu zahrne další piloty a Safe Start; heuristické porovnání vůči 2 759 lokálním eval promptům není úplný průkaz bez překryvu.
- [ ] Sémantické předpoklady u zlomkových jednotek a sumace followerů budou zaznamenány.
- [ ] Samostatná auditní evidence sváže revizní rozhodnutí s ID a SHA-256 otázky, verzí kontraktu a identitou skutečného recenzenta.
- [ ] Poté a teprve potom lze rozhodnout, zda vzniknou schválené procedurální příklady; žádné modelové generace ani nové trénování zatím neproběhly.

**Aktuální stav kontraktů:** `VPS=UNVERIFIED`; `XP locks=0`; `approved_for_training=false`. Tři prohlédnuté příklady nesmějí být vydávány za nový neviděný holdout.
