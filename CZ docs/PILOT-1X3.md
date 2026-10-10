# 🐇 RHAR — malý pilot 1 otázka × 3 generování

**Stav:** implementovaný režim a CPU testy; GPU spuštění vyžaduje zvláštní souhlas. Nejde o trénování ani oficiální BottleCapAI evaluaci.

[📋 Plán questu](QUEST-DOKONCENI-PLAN.md) · [📔 DEV-NOTES](DEV-NOTES.md)

## Proč

Chci ověřit reálné chování generátoru a získat první srovnatelná uložená řešení bez spuštění celého plánu 12 × 3. Kompletní sada 12 otázek a její selekční i overlap audit musí i nadále projít před výběrem jedné otázky.

## Bezpečný dry-run v Kali

    cd ~/bottlecap-test
    git pull --ff-only origin feat/reasoning-compression
    source .venv/bin/activate
    python -m unittest discover -s tests -v
    python -m diagnostics.safe_start_generate --dry-run --pilot-3

Při úspěchu očekávám `question_count: 1`, `planned_generations: 3`, `full_audit_question_count: 12`, `model_generations_performed: 0` a `gpu_used: false`.

## Výslovná brána pro případné GPU spuštění

Příkaz s `--execute --pilot-3 --confirm-gpu-3` je dostupný až pro **samostatně odsouhlasený** pilot. Jeho přítomnost v CLI není mým souhlasem s GPU během.

Uchovám výstupy v novém `runs/` adresáři; nesmažu původní canary ani audit. Sada může přinést správné i nesprávné vzorky. Ani tři generování jedné otázky nejsou trénovací dataset nebo průkazný výsledek komprese.

## Co následuje

Po zelených testech a CPU dry-runu si schválím rozpočet generování, spustím případný GPU pilot, ověřím počet skutečných výstupů a teprve pak rozhodnu o rozšíření dat a o LoRA tréninku. Před použitím do trénování musím mít ověřenou integritu zdrojů, oddělení dat a správné mapování formátu do trénovacího selektoru.
