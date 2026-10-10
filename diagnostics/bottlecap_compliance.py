"""BottleCapAI submission/evaluation gate (CPU-only, no model imports).

Check official evaluation artifacts, pairable settings, adapter and IDEA.md.
This is a compliance preflight, NOT a claim of successful performance.
"""
import argparse
import json
from pathlib import Path

FORBIDDEN = ("svamp", "mbpp", "bfcl", "ifeval")


def inspect(base, candidate, adapter, idea, bundle=None):
    issues = []
    info = {"official_evaluation_results_present": False,
            "matching_evaluation_configuration": False,
            "adapter_safetensors_present": False, "idea_present": False,
            "bundle_present": False, "performance_proven": False}
    a, b = Path(base) / "results.json", Path(candidate) / "results.json"
    if not (a.is_file() and b.is_file()):
        issues.append("Both baseline and candidate official evaluate.py results.json are required")
    else:
        left, right = json.loads(a.read_text()), json.loads(b.read_text())
        info["official_evaluation_results_present"] = True
        # These invariants are mandatory for a meaningful paired comparison.
        for field in ("selection", "cohort_sha256", "samples", "seed"):
            if field not in left or field not in right or left[field] != right[field]:
                issues.append(f"Evaluation pairing mismatch or missing {field}")
        # Let compare.py do final rigorous pairing; do not guess complete schema.
        info["matching_evaluation_configuration"] = not issues
    safetensors = list(Path(adapter).glob("*.safetensors"))
    info["adapter_safetensors_present"] = bool(safetensors)
    if not safetensors:
        issues.append("Missing trained LoRA .safetensors")
    info["idea_present"] = Path(idea).is_file() and bool(Path(idea).read_text().strip())
    if not info["idea_present"]:
        issues.append("IDEA.md not completed")
    if bundle is not None:
        info["bundle_present"] = Path(bundle).is_file() and Path(bundle).stat().st_size > 0
        if not info["bundle_present"]:
            issues.append("Git bundle missing")
    else:
        issues.append("Git bundle path not provided")
    return {"status": "ready_for_manual_review" if not issues else "incomplete",
            "checks": info, "issues": issues,
            "requires_official_compare_py": True,
            "training_data_contamination_audit_required": True,
            "guarantees_accuracy_or_token_savings": False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--adapter",type=Path,required=True)
    p.add_argument("--idea",type=Path,default=Path("IDEA.md"))
    p.add_argument("--bundle",type=Path)
    a=p.parse_args(argv)
    print(json.dumps(inspect(a.base,a.candidate,a.adapter,a.idea,a.bundle),indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
