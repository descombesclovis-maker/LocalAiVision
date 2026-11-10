"""Model-free contract tests for the bounded V2-S ComfyUI probe."""

from tools.benchmark_wan_t2v_attention import PROMPT, workflow


def test_probe_is_tiny_and_keeps_french_prompt_and_fixed_schedule():
    wf = workflow("pytorch attention", 1, "test")
    assert wf["5"]["inputs"]["text"] == PROMPT
    assert wf["7"]["inputs"]["width"] == 256
    assert wf["7"]["inputs"]["height"] == 256
    assert wf["7"]["inputs"]["length"] == 5
    assert wf["9"]["inputs"]["steps"] == 1
    assert wf["9"]["inputs"]["seed"] == 20261110


def test_probe_int8_uses_comfy_core_attention_patch_only_when_selected():
    baseline = workflow("pytorch attention", 1, "same")
    int8 = workflow("Comfy Kitchen attention", 1, "same")
    assert "12" not in baseline
    assert int8["12"]["class_type"] == "ModelAttentionBackend"
    assert int8["12"]["inputs"]["attention"] == "Comfy Kitchen attention"
    assert int8["4"]["inputs"]["model"] == ["12", 0]
    for node_id in ("1", "2", "3", "5", "6", "7", "9", "8", "20", "21"):
        assert baseline[node_id] == int8[node_id]
