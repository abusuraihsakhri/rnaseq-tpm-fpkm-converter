# RNA-seq TPM / FPKM Converter

Normalize feature-level RNA-seq counts to transcripts per million (TPM) and fragments per kilobase per million mapped fragments (FPKM). A dependency-free Python normalization engine, standalone browser interface, and optional FastAPI endpoint use the same standard formulas.

## Use in the browser

The static application is in [web/](web/). Open `web/index.html` locally or use the published GitHub Pages application once deployment is enabled. Paste or upload CSV, select **Calculate TPM / FPKM**, review the results, and download the normalized matrix. Processing runs entirely in the browser. No remote APIs, accounts, cookies, telemetry, or upload are required.

### Input CSV

```csv
gene_id,length_bp,control,treated
GeneA,1000,100,60
GeneB,2000,200,120
GeneC,500,50,30
```

The first two headers must be `gene_id,length_bp`; subsequent columns are nonnegative read/fragment counts for one or more samples. Gene IDs must be unique; gene lengths must be finite and positive (base pairs). The web interface supports up to 10 MB and 50,000 features per file. Output includes `TPM_<sample>` and `FPKM_<sample>` for every sample.

TPM and FPKM for feature *i* are:

```text
TPM_i  = 1,000,000 × (count_i / length_bp_i) / Σ_j(count_j / length_bp_j)
FPKM_i = 1,000,000,000 × count_i / (length_bp_i × library_size)
```

By default, `library_size` is the total of the supplied feature counts in that sample. If the input contains only a subset of genes, specify the original library total to obtain FPKM values referenced to the complete library; TPM still sums to one million **across supplied features**. Use fragment counts and fragment-library totals for paired-end FPKM, or read counts and read-library totals for the numerically equivalent single-end RPKM calculation. Do not mix units. Gene length definitions and library-size conventions affect results.

**Limitations:** This is count/length scaling, not compositional/batch-effect correction or a differential-expression model. It does not perform CIBERSORTx deconvolution. Prefer raw counts with appropriate count-based models for differential expression.

## Python command line

Python 3.10+ is supported.

```bash
python rnaseq_norm.py single --counts 100,200,50 --lengths-bp 1000,2000,500
python rnaseq_norm.py batch -i sample.csv -o results.csv
# Single-sample filtered matrix with known complete library total:
python rnaseq_norm.py batch -i sample.csv -o results.csv --library-size 100000
```

Or install the package:

```bash
python -m pip install -e ".[web,test]"
rnaseq-converter batch -i sample.csv -o results.csv
pytest -q
node --test tests/browser.test.cjs
```

The Python normalization module itself uses only the standard library. Installed packaging also includes Pydantic for an **unrelated legacy audit subsystem**.

## Optional REST API and Docker

```bash
python cli.py serve --host 127.0.0.1 --port 8000
# or
uvicorn agents.api:app --host 127.0.0.1 --port 8000
```

Send JSON to `POST /api/normalize`:

```json
{"counts":[100,200],"lengths_bp":[1000,2000],"library_size":300}
```

It returns `tpm`, `fpkm`, and `library_size` arrays/values. `GET /health` checks server health; `GET /` serves the browser interface. The API receives submitted data on its host (unlike the independent browser-only calculation). Interactive API documentation is available at `/docs`.

A separate pre-existing **generic heuristic audit** API and CLI remain accessible through `python cli.py audit`, `/api/audit`, and related endpoints. Its thresholds are not scientifically validated RNA-seq QC or clinical rules. The `chat` command uses a deterministic mock responder, not live model inference. That audit subsystem requires a user-supplied `AUDIT_SECRET_KEY` for HMAC logging:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
docker compose up --build
```

Never commit a real `.env` or secret. The regex-based identifier guard is a precaution, **not comprehensive de-identification or a guarantee of regulatory compliance**.

## Development and deployment

- Python 3.10–3.12 and recent Chrome, Firefox, Edge, or Safari.
- Python tests: `pytest -q`. Browser checks: `node --test tests/browser.test.cjs`.
- GitHub Actions runs checks on changes to `master` and pull requests.
- Static site contents are in `web/`; the Pages workflow publishes those files when Pages is configured to use GitHub Actions.
- Docker builds the API as an unprivileged user. No browser Python runtime is required because the arithmetic runs natively in JavaScript.

## License

[MIT](LICENSE). Scientific interpretation and suitability of gene/transcript effective lengths remain the responsibility of the analyst.
