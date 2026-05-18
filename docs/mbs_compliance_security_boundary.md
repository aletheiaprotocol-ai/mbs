# MBS Compliance and Security Boundary

## Status

This is the formal project-local compliance and security boundary for MBS v0.1.1. It is not a SOC 2 report, penetration test, HIPAA attestation, GDPR legal opinion, or third-party audit.

## Product boundary

MBS is structured-output validation software. In its default local mode it:

- reads schemas, cases, and model outputs from local files;
- compiles behavioral contracts from JSON Schema-like inputs;
- validates structured outputs;
- writes traces, reports, gates, and evidence packs;
- optionally adapts externally collected provider outputs into MBS result records.

MBS does not operate a hosted service in this repository. It does not itself collect telemetry, phone home, or manage customer identities.

## Data classes

| Data class | Examples | Default handling | External sharing boundary |
| --- | --- | --- | --- |
| Demo/software fixture | bundled examples, deterministic sample benchmark | public/repository-safe | may be shared as software evidence only |
| CI evidence | local mock benchmark, CI gate output, evidence-pack CI artifacts | public/repository-safe after token scan | may be shared as CI regression evidence only |
| Provider/OSS/HPC evidence | real model outputs, provider run metadata, raw prompts/cases | restricted until reviewed | share only after artifact classification and sensitivity review |
| Customer/user data | real tickets, transactions, incidents, PHI/PII | not required by default | do not commit; sanitize or keep internal |
| Secrets | API keys, tokens, bearer strings, credentials | blocked | never share; rotate if exposed |

## Security controls currently implemented

- Controlled CLI and agent-tool errors for common bad file/path/JSON inputs.
- UTF-8/BOM-safe JSON reads in validated code paths.
- `.gitignore` coverage for virtualenvs, generated result directories, build output, and caches.
- High-confidence token regression scan in `tests/test_release_hygiene.py`.
- Release package content inspector in `scripts/assert_release_package.py`.
- Fresh wheel install proof in `scripts/assert_fresh_install.py`.
- Artifact classifier in `scripts/classify_release_artifacts.py`.
- CI package build, package-content check, and fresh-install check.

## Operator responsibilities

Before sharing evidence externally:

1. Run the release hygiene tests.
2. Build packages and run the package inspector.
3. Run the fresh-install proof.
4. Run artifact classification on the exact files/directories to be shared.
5. Manually review any artifact marked `review_required`.
6. Remove or redact sensitive raw inputs/outputs before external distribution.
7. Never include secrets in examples, configs, transcripts, evidence packs, or issue reports.

## Non-goals and explicit limits

- MBS does not guarantee that a model output is factually correct.
- MBS does not prevent prompt injection by itself; it validates output contracts and can expose invalid or policy-breaking outputs.
- MBS does not classify all possible PII types. The artifact classifier is a conservative release-review aid, not a DLP substitute.
- MBS does not provide compliance certification.
- Provider benchmark evidence is valid only for the listed schemas, cases, models, modes, and run settings.

## Minimum release commands

```bash
python -m pytest -q
python -m build
python scripts/assert_release_package.py --dist-dir dist
python scripts/assert_fresh_install.py --dist-dir dist
python scripts/classify_release_artifacts.py benchmarks/results/sample_benchmark.json benchmarks/results/sample_benchmark.md docs/mbs_evidence_brief.md --repo-root .
```

## Readiness interpretation

Passing these checks supports a stronger release-hygiene claim. It does not by itself support an Enterprise Production Ready claim. Enterprise Pilot readiness still requires the target pilot's exact workflows, provider evidence, data classification, security review, and deployment/support expectations.
