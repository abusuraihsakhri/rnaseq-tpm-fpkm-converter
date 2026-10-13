"""Reference calculations and regression tests for RNA-seq normalization."""
import csv
import math
import pytest
from rnaseq_norm import calculate_metrics, process_batch, main


def test_tpm_and_fpkm_reference():
    result = calculate_metrics([100, 200, 0], [1000, 2000, 500])
    assert result["tpm"] == pytest.approx([500_000, 500_000, 0])
    assert result["fpkm"] == pytest.approx([1e9 / 300 * .1, 1e9 / 300 * .1, 0])
    assert math.fsum(result["tpm"]) == pytest.approx(1_000_000)
    assert result["library_size"] == 300


def test_custom_library_size_changes_fpkm_not_tpm():
    default = calculate_metrics([5, 15], [1000, 3000])
    custom = calculate_metrics([5, 15], [1000, 3000], library_size=100)
    assert custom["tpm"] == pytest.approx(default["tpm"])
    assert custom["fpkm"] == pytest.approx([x / 5 for x in default["fpkm"]])


@pytest.mark.parametrize("counts,lengths,lib", [
    ([], [], None),
    ([0, 0], [100, 200], None),
    ([-1, 2], [100, 200], None),
    ([1, 2], [100, 0], None),
    ([1, float("nan")], [100, 200], None),
    ([1, 2], [100], None),
    ([1, 2], [100, 200], 2),
])
def test_rejects_invalid_values(counts, lengths, lib):
    with pytest.raises(ValueError):
        calculate_metrics(counts, lengths, lib)


def test_wide_csv_and_formula_escaping(tmp_path):
    src, dst = tmp_path / "in.csv", tmp_path / "out.csv"
    src.write_text("gene_id,length_bp,A,B\n=2+2,1000,5,10\nGeneB,2000,10,0\n", encoding="utf-8")
    assert process_batch(str(src), str(dst)) == 2
    with dst.open(newline="") as handle:
        output = list(csv.DictReader(handle))
    assert output[0]["gene_id"] == "'=2+2"
    assert float(output[0]["TPM_A"]) == pytest.approx(500_000)
    assert float(output[0]["TPM_B"]) == pytest.approx(1_000_000)
    assert float(output[1]["FPKM_B"]) == 0


def test_csv_rejects_corruption_and_duplicate_identifiers(tmp_path):
    src, dst = tmp_path / "in.csv", tmp_path / "out.csv"
    for contents in [
        "gene_id,length_bp,count\nA,100,2\nA,200,4\n",
        "gene_id,length_bp,count\nA,100,2,extra\n",
        "gene_id,length_bp,count\nA,100,-2\n",
        "gene_id,length_bp,count\nA,100,0\n",
        "gene_id,length_bp,count\n",
    ]:
        src.write_text(contents, encoding="utf-8")
        with pytest.raises(ValueError):
            process_batch(str(src), str(dst))


def test_same_input_output_rejected(tmp_path):
    src = tmp_path / "input.csv"
    src.write_text("gene_id,length_bp,count\nA,100,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        process_batch(str(src), str(src))


def test_cli_single(capsys):
    assert main(["single", "--counts", "100,200", "--lengths-bp", "1000,2000"]) == 0
    assert '"tpm": [' in capsys.readouterr().out
