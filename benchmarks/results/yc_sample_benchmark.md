# MBS YC Benchmark Sample

Deterministic local sample: 3 support-agent cases x 2 mock model adapters.
It compares a verbose prompt against an MBS contract with validation and one targeted retry.

| strategy | cases | models | schema-valid | semantic-correct | avg retries | cost / valid output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mbs_contract+retry | 6 | 2 | 1.000 | 1.000 | 0.333 | 121.833 |
| verbose_prompt | 6 | 2 | 0.500 | 0.500 | 0.000 | 385.0 |

Metrics: schema-valid means the output passed the schema validator; semantic-correct means required expected fields also matched the case label.
This is not the broad GPU benchmark; it is the smallest reproducible sample for a YC reviewer.
