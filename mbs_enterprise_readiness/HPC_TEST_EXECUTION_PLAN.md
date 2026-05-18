# HPC Test Execution Plan

## Goal

Use large compute intelligently to create durable enterprise evidence without wasting grants.

## Execution phases

### Phase 0 — Local smoke

- Validate schemas and cases locally.
- Run tiny/small models or provider sample runs.
- Confirm parsers, trace writers, reports, and gates.
- Stop if there are software bugs.

### Phase 1 — OSS endpoint smoke

- vLLM/Ollama/LM Studio OpenAI-compatible smoke runs.
- 10-25 cases per schema.
- text and JSON-compatible modes.

### Phase 2 — Medium matrix

- 5-8 families.
- tiny/small/medium models.
- at least 3 hard schemas.
- no retry and one retry.

### Phase 3 — Large/HPC matrix

- large and 70B+ models where feasible.
- quantized and non-quantized variants where feasible.
- selected hard schemas only.
- failure-specific retry and semantic retry.

### Phase 4 — Closed-provider matrix

- Azure/OpenAI/Anthropic/Gemini/Cohere where available.
- Compare provider-native structured modes to MBS contract modes.

### Phase 5 — Regression suite

- Convert best hard cases and known failures into recurring CI/regression packs.

## Job manifest requirements

Each HPC run must record:
- job ID;
- cluster/partition/GPU type;
- model path;
- model hash or revision;
- quantization;
- endpoint server version;
- prompt/contract version;
- schema/case version;
- seed;
- command;
- start/end time;
- infra failure status.

## Stop conditions

- Parser/trace bug found.
- Schema/case design issue invalidates results.
- Endpoint misconfiguration causes infra failures.
- Cost exceeds planned budget.
- Duplicate failures already explained by smaller runs.

## Promotion conditions

- Results are reproducible from command logs.
- All artifacts are present.
- Infra/model/software/design failures are separated.
- Scorecard updated.