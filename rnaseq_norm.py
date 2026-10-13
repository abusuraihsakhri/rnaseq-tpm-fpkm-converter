#!/usr/bin/env python3
"""Dependency-free RNA-seq TPM and FPKM normalization for count matrices."""

import argparse
import csv
import json
import math
from pathlib import Path


def _validate_safe_path(filepath):
    """Reject relative traversal segments in file paths accepted by the CLI."""
    path = Path(filepath)
    if '..' in path.parts:
        raise ValueError(f'Path traversal detected: {filepath}')
    return path.resolve()


def _numeric(value, label, *, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label} must be numeric') from exc
    if not math.isfinite(number) or number < 0 or (positive and number <= 0):
        raise ValueError(f'{label} must be finite and {"positive" if positive else "nonnegative"}')
    return number


def calculate_metrics(counts, lengths_bp, library_size=None):
    """Return TPM and FPKM vectors for one sample.

    Counts represent reads (single-end) or fragments (paired-end); lengths are
    feature lengths in base pairs. By default, library size is the sum of the
    supplied counts. For a filtered table, supply the original library total.
    """
    counts = list(counts)
    lengths_bp = list(lengths_bp)
    if not counts or len(counts) != len(lengths_bp):
        raise ValueError('counts and lengths_bp must be equally sized, nonempty sequences')
    c = [_numeric(x, f'count[{i}]') for i, x in enumerate(counts)]
    lengths = [_numeric(x, f'length_bp[{i}]', positive=True) for i, x in enumerate(lengths_bp)]
    observed = math.fsum(c)
    total = observed if library_size is None else _numeric(library_size, 'library_size', positive=True)
    if observed <= 0 or not math.isfinite(observed) or total <= 0 or total < observed:
        raise ValueError('sample count total must be positive and cannot exceed library_size')
    rates = [count / length for count, length in zip(c, lengths)]
    rate_total = math.fsum(rates)
    if rate_total <= 0 or not math.isfinite(rate_total):
        raise ValueError('count/length denominator is zero or nonfinite')
    tpm = [(rate / rate_total) * 1_000_000 for rate in rates]
    fpkm = [(rate / total) * 1_000_000_000 for rate in rates]
    if not all(math.isfinite(value) for value in tpm + fpkm):
        raise ValueError('normalization result is nonfinite')
    return {'tpm': tpm, 'fpkm': fpkm, 'library_size': total}


def process_batch(input_csv, output_csv, library_size=None):
    """Normalize a wide CSV: gene_id,length_bp,count[,additional_sample...]."""
    source = _validate_safe_path(input_csv)
    target = _validate_safe_path(output_csv)
    if source == target:
        raise ValueError('input and output paths must differ')
    if not source.is_file():
        raise FileNotFoundError(f'Input file not found: {input_csv}')
    try:
        with source.open('r', encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, strict=True)
            columns = list(reader.fieldnames or [])
            if not columns:
                raise ValueError('CSV file is empty or has no headers')
            if len(columns) != len(set(columns)) or any(not name for name in columns):
                raise ValueError('CSV headers must be unique and nonempty')
            if columns[:2] != ['gene_id', 'length_bp'] or len(columns) < 3:
                raise ValueError('Expected headers: gene_id,length_bp,count[,additional_sample...]')
            samples = columns[2:]
            rows = list(reader)
    except (csv.Error, UnicodeError) as exc:
        raise ValueError(f'Invalid CSV format: {exc}') from exc
    if not rows:
        raise ValueError('CSV must contain at least one data row')
    ids, lengths = [], []
    matrix = {sample: [] for sample in samples}
    for line, row in enumerate(rows, 2):
        if None in row or any(row.get(field) is None for field in columns):
            raise ValueError(f'Row {line} has the wrong number of columns')
        gene = row['gene_id'].strip()
        if not gene:
            raise ValueError(f'Row {line}: gene_id cannot be empty')
        ids.append(gene)
        lengths.append(_numeric(row['length_bp'], f'Row {line} length_bp', positive=True))
        for sample in samples:
            matrix[sample].append(_numeric(row[sample], f'Row {line} {sample}'))
    if len(ids) != len(set(ids)):
        raise ValueError('gene_id entries must be unique')
    if library_size is not None and len(samples) != 1:
        raise ValueError('--library-size is supported only for one sample column')
    normalized = {sample: calculate_metrics(matrix[sample], lengths, library_size) for sample in samples}
    output_columns = ['gene_id', 'length_bp']
    for sample in samples:
        output_columns.extend((f'TPM_{sample}', f'FPKM_{sample}'))
    with target.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=output_columns)
        writer.writeheader()
        for i, gene in enumerate(ids):
            # Neutralize spreadsheet formulas in user-supplied identifiers.
            safe_id = "'" + gene if gene.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else gene
            record = {'gene_id': safe_id, 'length_bp': f'{lengths[i]:.12g}'}
            for sample in samples:
                record[f'TPM_{sample}'] = f'{normalized[sample]["tpm"][i]:.12g}'
                record[f'FPKM_{sample}'] = f'{normalized[sample]["fpkm"][i]:.12g}'
            writer.writerow(record)
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Normalize RNA-seq counts to TPM and FPKM')
    cmds = parser.add_subparsers(dest='command', required=True)
    single = cmds.add_parser('single', help='Normalize one sample with comma-separated vectors')
    single.add_argument('--counts', required=True, help='Counts, e.g. 10,20,30')
    single.add_argument('--lengths-bp', required=True, help='Feature lengths in bp, e.g. 1000,2000,1500')
    single.add_argument('--library-size', type=float, default=None)
    batch = cmds.add_parser('batch', help='Normalize a CSV count matrix')
    batch.add_argument('-i', '--input', required=True)
    batch.add_argument('-o', '--output', default='results.csv')
    batch.add_argument('--library-size', type=float, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == 'single':
            counts = args.counts.split(',')
            lengths = args.lengths_bp.split(',')
            print(json.dumps(calculate_metrics(counts, lengths, args.library_size), indent=2))
        else:
            n = process_batch(args.input, args.output, args.library_size)
            print(f'Normalized {n} features -> {args.output}')
    except (ValueError, FileNotFoundError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')
    return 0


if __name__ == '__main__':
    main()
