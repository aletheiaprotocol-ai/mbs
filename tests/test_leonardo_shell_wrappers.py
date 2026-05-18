from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_submitter_exposes_job_label_prompt_style_and_offline_mode():
    submitter = (REPO_ROOT / "scripts" / "submit_leonardo_mbs_matrix.sh").read_text(encoding="utf-8")

    assert 'JOB_LABEL="${JOB_LABEL:-$SUITE}"' in submitter
    assert 'PROMPT_STYLE="${PROMPT_STYLE:-nested}"' in submitter
    assert "HF_HUB_OFFLINE=1" in submitter
    assert "TRANSFORMERS_OFFLINE=1" in submitter
    assert "HF_DATASETS_OFFLINE=1" in submitter
    assert "ALETHEIA_LOCAL_FILES_ONLY=1" in submitter
    assert "--local-files-only" in submitter
    assert "--prompt-style ${PROMPT_STYLE}" in submitter


def test_70b_compact_single_wrapper_uses_fresh_single_model_quantized_job():
    wrapper = (REPO_ROOT / "scripts" / "submit_leonardo_70b_compact_single.sh").read_text(encoding="utf-8")

    assert "JOB_LABEL=\"compact_70b_single_01\"" in wrapper
    assert "PROMPT_STYLE=\"compact\"" in wrapper
    assert "MODELS=\"NousResearch/Meta-Llama-3.1-70B-Instruct\"" in wrapper
    assert "QUANT_ARGS=\"--load-in-4bit\"" in wrapper
    assert "exec bash ./submit_leonardo_mbs_matrix.sh large" in wrapper
    assert "TIME_LIMIT=\"00:30:00\"" in wrapper