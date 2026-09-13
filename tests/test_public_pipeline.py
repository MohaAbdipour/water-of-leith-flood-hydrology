from scripts.run_public_pipeline import ANALYSIS_SCRIPTS, DOWNLOAD_SCRIPTS


def test_public_pipeline_excludes_restricted_validation():
    scripts = DOWNLOAD_SCRIPTS + ANALYSIS_SCRIPTS
    assert "scripts/validate_against_nrfa.py" not in scripts
    assert scripts.index("scripts/run_analysis.py") < scripts.index("scripts/run_diagnostics.py")
    assert scripts.index("scripts/run_rainfall_runoff_analysis.py") < scripts.index("scripts/run_event_classification.py")
