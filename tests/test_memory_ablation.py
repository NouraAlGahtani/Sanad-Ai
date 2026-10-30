from evaluation.compare_memory import run_comparison

def test_memory_ablation_and_safety():
    result = run_comparison(False)
    assert result["memory_enabled"]["memory_available"]
    assert not result["baseline"]["memory_available"]
    assert not result["safety_challenge"]["restart_authorized"]
