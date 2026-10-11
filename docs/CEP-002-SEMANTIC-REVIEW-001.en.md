# 🧠 CEP-002 — preliminary semantic review 001

**Date:** 2026-10-11  
**Reviewer:** assistant, author of the draft proposals; **not an independent external review**  
**Status:** PRELIMINARY_CHECK / REVIEW_REQUIRED  
**Source:** locally pinned GSM8K `main/train`, revision `740312add88f781978c0658806c59bc2815b9866`  
**Inputs:** `runs/cep002-contract-drafts-001/review-packet.md`

## What was actually done

The user reported 69 passing CPU unit tests and successful `--dry-run` and `--execute` calls for review packet generation. All three draft contracts have exact arithmetic steps matching their gold answers. This report also explains their language-to-math interpretation; it **is not an independent external sign-off** and cannot authorize training.

## 1. `gsm8k-train-00664` — fish lifespan

- Source fact: hamsters live `2.5` years on average.
- “Dogs live 4 times as long”: `dog_years = 2.5 × 4 = 10`.
- “Fish can live 2 years longer than dogs”: `fish_years = 10 + 2 = 12`.
- Gold final `12` agrees.
- Pitfall: multiplying rather than adding the two extra years; `2.5 × (4+2) = 15` would be incorrect.
- **Preliminary assessment:** semantically and arithmetically consistent.

## 2. `gsm8k-train-06718` — shampoos

- Source quantities: `1/3` rose bottle, `1/4` jasmine bottle; daily use `1/12` bottle.
- Common denominator: `4/12 + 3/12 = 7/12`.
- Days: `(7/12)/(1/12) = 7`.
- Gold final `7` agrees.
- **Semantic assumption:** all bottles represent one standard volume unit, as implicitly intended by the problem. Differently sized bottles would make the problem underdetermined.
- Pitfall: adding denominators, or interpreting daily use as a fraction of *each* bottle.
- **Preliminary assessment:** correct under the equal-unit bottle assumption.

## 3. `gsm8k-train-03644` — social platforms

- Instagram `240` and Facebook `500` sum to `740`.
- Twitter = half the IG+FB sum = `370`.
- TikTok = three times Twitter = `1110`.
- YouTube = TikTok plus `510` = `1620`.
- Five-platform total = `240 + 500 + 370 + 1110 + 1620 = 3840`.
- Gold final `3840` agrees.
- **Semantic assumption:** sum platform follower counts, not deduplicated people across accounts.
- Pitfall: omit the original Instagram/Facebook counts or add the `510` difference twice.
- **Preliminary assessment:** semantically and arithmetically consistent for the per-platform total.

## Blocking gates before VPS/XP/training

- [ ] A genuinely independent reviewer checks the meaning and every proposed relation against the source wording.
- [ ] A documented historical-overlap audit also screens earlier pilot and Safe Start selections; heuristic screening against the 2,759 local evaluation prompts is not exhaustive.
- [ ] Explicitly record unit assumptions for bottles and the follower-count interpretation.
- [ ] Bind separate audit decisions to source question IDs/hashes, contract versions, and genuine reviewer identities.
- [ ] Only then decide whether any approved procedural training examples can be exported; no new model generations or training have occurred.

**Current contract status:** `VPS=UNVERIFIED`; `XP locks=0`; `approved_for_training=false`. These three viewed questions are not untouched holdout examples.
