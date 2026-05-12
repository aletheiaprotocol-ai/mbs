"""Command line interface for MBS."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

from .agent_tools import AgentToolError, call_agent_tool, handle_agent_tool_request, list_agent_tools
from .bench import mock_output, run_benchmark, run_benchmark_matrix
from .compare import compare_results, format_compare, write_compare_json
from .compiler import canonical_json, compile_schema, estimate_tokens, format_report, load_schema
from .cost import report_cost
from .demo import build_demo, format_demo, run_sample_benchmark, write_demo_artifacts
from .lang import compile_language_contract
from .models import load_model_registry, suite_models, suite_summary, validate_suite_coverage, write_model_ids
from .report import aggregate_results, markdown_report, trace_errors
from .retry_audit import audit_retry_attempts, format_retry_audit, write_retry_audit_json
from .trace import create_trace
from .triage import format_triage, triage_results, write_triage_json
from .validate import validate_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mbs", description="Minimal Behavioral Specification tools")
    sub = parser.add_subparsers(dest="command")

    p_compile = sub.add_parser("compile", help="Compile a schema into an MBS contract")
    p_compile.add_argument("schema")
    p_compile.add_argument("--format", choices=["natural", "progressive", "full", "strict"], default="full")
    p_compile.add_argument("--task", default="")
    p_compile.add_argument("--include-free", action="store_true")
    p_compile.add_argument("--json", action="store_true")
    p_compile.add_argument("--verbose", action="store_true")
    p_compile.add_argument("--input-language")
    p_compile.add_argument("--output-language")
    p_compile.add_argument("--contract-language")

    p_validate = sub.add_parser("validate", help="Validate output against a schema")
    p_validate.add_argument("--schema", required=True)
    p_validate.add_argument("--output", required=True, help="Output JSON file or inline JSON string")
    p_validate.add_argument("--json", action="store_true")

    p_check = sub.add_parser("check", help="Compile, run/mock, validate, trace, and report")
    p_check.add_argument("--schema", required=True)
    p_check.add_argument("--input", default="")
    p_check.add_argument("--output", help="Output JSON file or inline JSON string. If omitted, local mock output is used.")
    p_check.add_argument("--model", default="mock")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--trace-out")

    p_trace = sub.add_parser("trace", help="Create a trace from schema and output")
    p_trace.add_argument("--schema", required=True)
    p_trace.add_argument("--output", required=True)
    p_trace.add_argument("--input", default="")
    p_trace.add_argument("--model", default="unknown")
    p_trace.add_argument("--out")

    p_cost = sub.add_parser("cost", help="Report cost per valid output from result records")
    p_cost.add_argument("--results", help="JSON/JSONL records with status/tokens")
    p_cost.add_argument("--schema")
    p_cost.add_argument("--cases")
    p_cost.add_argument("--json", action="store_true")

    p_bench = sub.add_parser("bench", help="Run starter local benchmark")
    p_bench.add_argument("--schema")
    p_bench.add_argument("--cases")
    p_bench.add_argument("--config")
    p_bench.add_argument("--model", default="mock")
    p_bench.add_argument("--out")
    p_bench.add_argument("--json", action="store_true")

    p_demo = sub.add_parser("demo", help="Run the 30-second MBS prototype demo")
    p_demo.add_argument("--json", action="store_true")
    p_demo.add_argument(
        "--write-artifacts",
        action="store_true",
        help="Write the sample benchmark and one-page evidence brief",
    )

    p_test = sub.add_parser("test", help="Run structured-output regression tests")
    p_test.add_argument("--schemas", required=True)
    p_test.add_argument("--cases", required=True)
    p_test.add_argument("--models", default="")
    p_test.add_argument("--min-schema-valid-rate", type=float)
    p_test.add_argument("--out")
    p_test.add_argument("--json", action="store_true")

    p_lang = sub.add_parser("lang", help="Compile an MBS-Lang contract")
    p_lang.add_argument("schema")
    p_lang.add_argument("--input-language", required=True)
    p_lang.add_argument("--output-language", required=True)
    p_lang.add_argument("--contract-language", default="en")
    p_lang.add_argument("--json", action="store_true")

    p_report = sub.add_parser("report", help="Aggregate MBS benchmark result files")
    p_report.add_argument("--results", nargs="+", required=True, help="Result JSON files, directories, or glob patterns")
    p_report.add_argument("--out", help="Markdown report output path")
    p_report.add_argument("--exclude-infra", action="store_true", help="Exclude infrastructure-failed rows from the table")
    p_report.add_argument("--require-traces", action="store_true", help="Return nonzero if report rows lack trace evidence")
    p_report.add_argument("--summary-only", action="store_true", help="Print scorecards and failure summary without row table")
    p_report.add_argument("--json", action="store_true")

    p_compare = sub.add_parser("compare", help="Compare current MBS results against a baseline")
    p_compare.add_argument("--baseline", nargs="+", required=True, help="Baseline result JSON files or globs")
    p_compare.add_argument("--current", nargs="+", required=True, help="Current result JSON files or globs")
    p_compare.add_argument("--metric", action="append", help="Metric to compare. Can be repeated.")
    p_compare.add_argument(
        "--match-on",
        help="Comma-separated row identity fields. Default: schema,model,prompt_style,decoding_mode,language",
    )
    p_compare.add_argument("--max-drop", type=float, default=0.0)
    p_compare.add_argument("--out", help="JSON comparison output path")
    p_compare.add_argument("--json", action="store_true")

    p_retry_audit = sub.add_parser("retry-audit", help="Audit retry attempt selection inside result files")
    p_retry_audit.add_argument("--results", nargs="+", required=True, help="Retry result JSON files or globs")
    p_retry_audit.add_argument("--max-examples", type=int, default=20)
    p_retry_audit.add_argument("--out", help="JSON audit output path")
    p_retry_audit.add_argument("--json", action="store_true")

    p_models = sub.add_parser("models", help="Inspect or export broad benchmark model suites")
    p_models.add_argument("--registry", default="benchmarks/model_suites.json")
    p_models.add_argument("--suite", default="stage1_broad")
    p_models.add_argument("--out", help="Write model ids as newline-delimited text")
    p_models.add_argument("--min-models", type=int, default=1)
    p_models.add_argument("--min-families", type=int, default=1)
    p_models.add_argument("--min-size-bands", type=int, default=1)
    p_models.add_argument("--json", action="store_true")

    p_triage = sub.add_parser("triage", help="Triage remote MBS benchmark result files")
    p_triage.add_argument("--results", nargs="+", required=True)
    p_triage.add_argument("--expected-models")
    p_triage.add_argument("--min-schema-valid-rate", type=float, default=0.8)
    p_triage.add_argument("--min-valid-json-rate", type=float, default=0.9)
    p_triage.add_argument("--allow-missing-traces", action="store_true")
    p_triage.add_argument("--max-failure-examples", type=int, default=20)
    p_triage.add_argument("--max-issues", type=int, default=50, help="Maximum issue details to print; use -1 for all")
    p_triage.add_argument("--out")
    p_triage.add_argument("--json", action="store_true")

    p_agent_tools = sub.add_parser("agent-tools", help="Expose MBS as JSON-callable agent tools")
    p_agent_tools.add_argument("--list", action="store_true", help="List available MBS agent tools")
    p_agent_tools.add_argument("--call", help="Call a tool by name, for example mbs.check")
    p_agent_tools.add_argument("--args", default="{}", help="JSON object or path containing tool arguments")
    p_agent_tools.add_argument("--request", help="JSON object or path with {tool/name, arguments}")
    p_agent_tools.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "compile":
        return _cmd_compile(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "check":
        return _cmd_check(args)
    if args.command == "trace":
        return _cmd_trace(args)
    if args.command == "cost":
        return _cmd_cost(args)
    if args.command == "bench":
        return _cmd_bench(args)
    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "test":
        return _cmd_test(args)
    if args.command == "lang":
        return _cmd_lang(args)
    if args.command == "report":
        return _cmd_report(args)
    if args.command == "compare":
        return _cmd_compare(args)
    if args.command == "retry-audit":
        return _cmd_retry_audit(args)
    if args.command == "models":
        return _cmd_models(args)
    if args.command == "triage":
        return _cmd_triage(args)
    if args.command == "agent-tools":
        return _cmd_agent_tools(args)
    raise AssertionError(args.command)


def _cmd_compile(args: argparse.Namespace) -> int:
    schema = load_schema(args.schema)
    result = compile_schema(
        schema,
        format=args.format,
        task_context=args.task,
        include_free_enums=args.include_free,
        input_language=args.input_language,
        output_language=args.output_language,
        contract_language=args.contract_language,
    )
    if args.json:
        _print_json({k: v for k, v in result.items() if k != "full_prompt"})
    elif args.verbose:
        print(format_report(result))
    else:
        print(result["prompt"])
        print(f"\n# ~{result['token_estimate']} tokens ({result['savings_pct']}% savings vs verbose)")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    schema = load_schema(args.schema)
    output = _load_json_or_inline(args.output)
    result = validate_output(schema, output)
    if args.json:
        _print_json(result)
    else:
        _print_validation(result)
    return 0 if result["schema_valid"] else 2


def _cmd_check(args: argparse.Namespace) -> int:
    schema = load_schema(args.schema)
    contract = compile_schema(schema)
    output = _load_json_or_inline(args.output) if args.output else mock_output(schema, args.input)
    validation = validate_output(schema, output)
    output_tokens = estimate_tokens(canonical_json(validation.get("output")))
    trace = create_trace(schema, contract, validation, input_text=args.input, model=args.model, output_tokens=output_tokens)
    payload = {"output": validation["output"], "validation": validation, "trace": trace, "contract": contract}
    if args.trace_out:
        Path(args.trace_out).write_text(json.dumps(trace, indent=2), encoding="utf-8")
    if args.json:
        _print_json(payload)
    else:
        _print_check(payload)
    return 0 if validation["schema_valid"] else 2


def _cmd_trace(args: argparse.Namespace) -> int:
    schema = load_schema(args.schema)
    output = _load_json_or_inline(args.output)
    contract = compile_schema(schema)
    validation = validate_output(schema, output)
    output_tokens = estimate_tokens(canonical_json(validation.get("output")))
    trace = create_trace(schema, contract, validation, input_text=args.input, model=args.model, output_tokens=output_tokens)
    if args.out:
        Path(args.out).write_text(json.dumps(trace, indent=2), encoding="utf-8")
    _print_json(trace)
    return 0


def _cmd_cost(args: argparse.Namespace) -> int:
    if args.results:
        records = _load_records(args.results)
    elif args.schema and args.cases:
        records = run_benchmark(args.schema, args.cases)["rows"]
    else:
        raise SystemExit("mbs cost requires --results or --schema plus --cases")
    result = report_cost(records)
    if args.json:
        _print_json(result)
    else:
        print(f"Runs: {result['runs']}")
        print(f"Valid outputs: {result['valid_outputs']}")
        print(f"Failed outputs: {result['failed_outputs']}")
        print(f"Total tokens: {result['total_tokens']}")
        print(f"Cost per valid output: {result['cost_per_valid_output_tokens']} tokens")
    return 0


def _cmd_bench(args: argparse.Namespace) -> int:
    if args.config:
        config = _load_config(args.config)
        schema = config.get("schemas", config.get("schema"))
        if not schema:
            raise SystemExit("mbs bench config requires schema or schemas")
        cases = config["cases"]
        models = _config_list(config, "models", config.get("model", args.model))
        prompt_styles = _config_list(config, "prompt_styles", config.get("prompt_style", "full"))
        decoding_modes = _config_list(config, "decoding_modes", config.get("decoding_mode", "local_mock"))
        languages = _config_languages(config)
        result = run_benchmark_matrix(schema, cases, models, prompt_styles, decoding_modes, languages)
    else:
        if not args.schema or not args.cases:
            raise SystemExit("mbs bench requires --schema and --cases unless --config is provided")
        schema = args.schema
        cases = args.cases
        result = run_benchmark(schema, cases, model=args.model)
    if args.json:
        _print_json(result)
    else:
        _print_json(result["summary"])
    if args.out:
        _write_json(args.out, result)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    demo = build_demo()
    benchmark = run_sample_benchmark()
    artifacts = write_demo_artifacts() if args.write_artifacts else {}
    payload = {"demo": demo, "benchmark": benchmark, "artifacts": artifacts}
    if args.json:
        _print_json(payload)
    else:
        print(format_demo(demo))
        print("")
        print("Sample benchmark:")
        for row in benchmark["summary"]["by_strategy"]:
            print(
                f"- {row['strategy']}: "
                f"schema_valid={row['schema_valid_rate']} "
                f"semantic={row['semantic_correct_rate']} "
                f"avg_retries={row['avg_retry_count']} "
                f"cost_per_valid={row['cost_per_valid_output_tokens']} tokens"
            )
        if artifacts:
            print("")
            print("Wrote artifacts:")
            for label, path in artifacts.items():
                print(f"- {label}: {path}")
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    schema_dir = Path(args.schemas)
    model_config = _load_config(args.models) if args.models else {}
    models = _config_list(model_config, "models", model_config.get("model", "mock")) if model_config else ["mock"]
    rows: list[dict[str, Any]] = []
    for schema_file in sorted(schema_dir.glob("*.json")):
        candidate = _load_json_or_inline(str(schema_file))
        if not isinstance(candidate, dict) or "properties" not in candidate:
            continue
        for model in models:
            result = run_benchmark(schema_file, args.cases, model=model)
            rows.append({"schema": str(schema_file), "model": model, **result["summary"]})
    if args.json:
        _print_json(rows)
    else:
        for row in rows:
            print(
                f"{row['schema']} [{row['model']}]: "
                f"schema_valid_rate={row.get('schema_valid_rate')} "
                f"semantic={row.get('semantic_correct_rate')} "
                f"cost_per_valid={row.get('cost_per_valid_output_tokens')}"
            )
    if args.out:
        _write_json(args.out, rows)
    if args.min_schema_valid_rate is not None:
        failed = [row for row in rows if (row.get("schema_valid_rate") or 0) < args.min_schema_valid_rate]
        if failed:
            return 2
    return 0


def _cmd_lang(args: argparse.Namespace) -> int:
    schema = load_schema(args.schema)
    result = compile_language_contract(schema, args.input_language, args.output_language, args.contract_language)
    if args.json:
        _print_json(result)
    else:
        print(result["prompt"])
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    report = aggregate_results(args.results, exclude_infra=args.exclude_infra)
    errors = trace_errors(report) if args.require_traces else []
    markdown = markdown_report(report, summary_only=args.summary_only)
    if args.json:
        _print_json(report)
    else:
        print(markdown)
        for error in errors:
            print(f"Trace check failed: {error}")
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(markdown, encoding="utf-8")
    return 0 if report["rows"] and not errors else 2


def _cmd_compare(args: argparse.Namespace) -> int:
    key_fields = [item.strip() for item in args.match_on.split(",") if item.strip()] if args.match_on else None
    result = compare_results(args.baseline, args.current, metrics=args.metric, max_drop=args.max_drop, key_fields=key_fields)
    if args.json:
        _print_json(result)
    else:
        print(format_compare(result))
    if args.out:
        write_compare_json(args.out, result)
    return 0 if result["status"] == "PASS" else 2


def _cmd_retry_audit(args: argparse.Namespace) -> int:
    result = audit_retry_attempts(args.results, max_examples=max(args.max_examples, 0))
    if args.json:
        _print_json(result)
    else:
        print(format_retry_audit(result))
    if args.out:
        write_retry_audit_json(args.out, result)
    return 0 if result["status"] == "PASS" else 2


def _cmd_models(args: argparse.Namespace) -> int:
    registry = load_model_registry(args.registry)
    models = suite_models(registry, args.suite)
    summary = suite_summary(models)
    errors = validate_suite_coverage(
        models,
        min_models=args.min_models,
        min_families=args.min_families,
        min_size_bands=args.min_size_bands,
    )
    payload = {"suite": args.suite, "summary": summary, "coverage_errors": errors, "models": models}
    if args.out:
        write_model_ids(args.out, models)
    if args.json:
        _print_json(payload)
    else:
        print(f"Suite: {args.suite}")
        print(f"Models: {summary['models']}")
        print(f"Families: {summary['families']} ({', '.join(summary['family_names'])})")
        print(f"Size bands: {', '.join(summary['size_bands'])}")
        print(f"Access: {summary['access']}")
        if args.out:
            print(f"Wrote: {args.out}")
        if errors:
            print("Coverage errors:")
            for error in errors:
                print(f"- {error}")
    return 0 if not errors else 2


def _cmd_triage(args: argparse.Namespace) -> int:
    result = triage_results(
        args.results,
        expected_models=args.expected_models,
        min_schema_valid_rate=args.min_schema_valid_rate,
        min_valid_json_rate=args.min_valid_json_rate,
        require_traces=not args.allow_missing_traces,
        max_failure_examples=max(args.max_failure_examples, 0),
    )
    if args.json:
        _print_json(result)
    else:
        max_issues = None if args.max_issues < 0 else args.max_issues
        print(format_triage(result, max_issues=max_issues))
    if args.out:
        write_triage_json(args.out, result)
    return 0 if result["status"] == "PASS" else 2


def _cmd_agent_tools(args: argparse.Namespace) -> int:
    try:
        if args.list or (not args.call and not args.request):
            payload: Any = list_agent_tools()
        elif args.request:
            request = _load_config(args.request)
            payload = handle_agent_tool_request(request)
        elif args.call:
            arguments = _load_config(args.args)
            payload = {"tool": args.call, "result": call_agent_tool(args.call, arguments)}
        else:
            raise SystemExit("mbs agent-tools requires --list, --call, or --request")
    except AgentToolError as exc:
        raise SystemExit(str(exc)) from exc

    if args.json or args.call or args.request:
        _print_json(payload)
    else:
        for tool in payload:
            print(f"{tool['name']}: {tool['description']}")
    return 0


def _load_json_or_inline(value: str) -> Any:
    p = Path(value)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _load_config(value: str) -> dict[str, Any]:
    if not value:
        return {}
    p = Path(value)
    if p.exists():
        text = p.read_text(encoding="utf-8")
        suffix = p.suffix.lower()
    else:
        text = value
        suffix = ""
    stripped = text.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        text = stripped[1:-1]
    if suffix in {".yaml", ".yml"}:
        return _load_yaml_text(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _load_yaml_text(text)
    if not isinstance(data, dict):
        raise SystemExit("MBS config must be a JSON/YAML object")
    return data


def _load_yaml_text(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise SystemExit("MBS YAML config must be an object")
        return data
    except ModuleNotFoundError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_list:
            data[current_list].append(_parse_scalar(stripped[2:].strip()))
            continue
        if ":" not in stripped:
            raise SystemExit(f"Unsupported YAML config line: {raw_line}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value == "":
            data[key] = []
            current_list = key
        else:
            data[key] = _parse_scalar(raw_value)
            current_list = None
    return data


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _config_list(config: dict[str, Any], key: str, fallback: Any) -> list[Any]:
    value = config.get(key, fallback)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _config_languages(config: dict[str, Any]) -> list[str | dict[str, str] | None]:
    if "languages" in config:
        value = config["languages"]
        return value if isinstance(value, list) else [value]
    if any(k in config for k in ("input_language", "output_language", "contract_language")):
        return [
            {
                "input_language": config.get("input_language"),
                "output_language": config.get("output_language"),
                "contract_language": config.get("contract_language"),
            }
        ]
    return [None]


def _load_records(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _write_json(path: str, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _print_validation(result: dict[str, Any]) -> None:
    print(f"JSON valid: {result['json_valid']}")
    print(f"Schema valid: {result['schema_valid']}")
    print(f"Status: {result['status']}")
    for err in result["errors"]:
        print(f"- {err.get('type')} at {err.get('field')}: {err}")
    for warn in result["warnings"]:
        print(f"- warning {warn.get('type')} at {warn.get('field')}: {warn}")


def _print_check(payload: dict[str, Any]) -> None:
    validation = payload["validation"]
    trace = payload["trace"]
    contract = payload["contract"]
    print(f"JSON valid: {validation['json_valid']}")
    print(f"Schema valid: {validation['schema_valid']}")
    print(f"Status: {validation['status']}")
    print(f"MBS tokens: {contract['token_estimate']}")
    print(f"Verbose baseline: {contract['full_token_estimate']}")
    print(f"Savings: {contract['savings_pct']}%")
    print(f"Trace: {trace['trace_id']}")
    if validation["errors"]:
        print("Failure reasons:")
        for err in validation["errors"]:
            print(f"- {err.get('type')} at {err.get('field')}")


if __name__ == "__main__":
    raise SystemExit(main())
