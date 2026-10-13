"""
Security and input validation tests for rnaseq-tpm-fpkm-converter.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from rnaseq_norm import calculate_metrics, process_batch, _validate_safe_path


class TestPathValidation:
    """Tests for path traversal protection."""

    def test_valid_path_accepted(self):
        p = _validate_safe_path("sample.csv")
        assert p is not None
        assert isinstance(p, Path)

    def test_path_traversal_blocked(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_safe_path("../../etc/passwd")

    def test_path_traversal_with_nested_dirs(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_safe_path("subdir/../../../etc/shadow")


class TestProcessBatchValidation:
    """Tests for process_batch error handling."""

    def test_missing_input_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_batch(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))

    def test_empty_csv_headers(self, tmp_path):
        csv_in = tmp_path / "empty.csv"
        csv_in.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty or has no headers"):
            process_batch(str(csv_in), str(tmp_path / "out.csv"))

    def test_valid_batch_processing(self, tmp_path):
        csv_in = tmp_path / "valid.csv"
        csv_in.write_text("Patient,v1,v2\nPat_001,15.0,3.0\n", encoding="utf-8")
        csv_out = tmp_path / "out.csv"
        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()
        content = csv_out.read_text(encoding="utf-8")
        assert "GeneA" in content
        assert "TPM_count" in content


class TestAuditSecurity:
    """Tests for audit trail security."""

    def test_audit_trail_requires_secret_key(self, monkeypatch):
        # Remove the env var if set
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        # Reset global audit to force re-initialization
        import agents.base as base
        original = base.GLOBAL_AUDIT
        base.GLOBAL_AUDIT = None

        try:
            from agents.base import AuditTrail
            with pytest.raises(RuntimeError, match="AUDIT_SECRET_KEY"):
                AuditTrail()
        finally:
            # Restore
            base.GLOBAL_AUDIT = original

    def test_audit_trail_with_secret_key(self, monkeypatch):
        monkeypatch.setenv("AUDIT_SECRET_KEY", "test-secret-key-for-testing-only")
        import agents.base as base
        original = base.GLOBAL_AUDIT
        base.GLOBAL_AUDIT = None

        try:
            from agents.base import AuditTrail
            trail = AuditTrail()
            assert trail is not None
        finally:
            base.GLOBAL_AUDIT = original


class TestEnrichmentSuite:
    """Tests for enrichment suite after duplicate removal."""

    def test_no_duplicate_results(self):
        from enrichment import RnaseqtpmfpkmconverterEnrichmentSuite
        suite = RnaseqtpmfpkmconverterEnrichmentSuite()
        results = suite.execute_all(primary_val=0.5, secondary_val=0.2)
        # Should have exactly 4 unique results (no duplicates)
        assert len(results) == 4
        expected_keys = {
            "BulkRnaseqDeconvolutionCibersortxCompatibilityEngine",
            "RationaleEngine",
            "ImplementationPlanEngine",
            "CrosssampleNormalizationAndBatchEffectCorrectionEngine",
        }
        assert set(results.keys()) == expected_keys

    def test_all_results_have_required_fields(self):
        from enrichment import RnaseqtpmfpkmconverterEnrichmentSuite
        suite = RnaseqtpmfpkmconverterEnrichmentSuite()
        results = suite.execute_all(primary_val=10.0, secondary_val=5.0)
        for key, result in results.items():
            assert hasattr(result, "status")
            assert hasattr(result, "score")
            assert hasattr(result, "alerts")
            assert hasattr(result, "recommendations")
