'use strict';

const EXAMPLE = 'gene_id,length_bp,count\nGeneA,1000,100\nGeneB,2000,200\nGeneC,500,50';
const MAX_BYTES = 10 * 1024 * 1024;

function parseCsv(text) {
  if (typeof text !== 'string' || !text.trim()) throw new Error('CSV is empty.');
  const input = text.replace(/^\uFEFF/, '');
  const rows = [];
  let row = [], field = '', quoted = false, quoteClosed = false;
  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    if (quoted) {
      if (c === '"' && input[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') { quoted = false; quoteClosed = true; }
      else field += c;
    } else if (c === ',' || c === '\n' || c === '\r') {
      row.push(field); field = ''; quoteClosed = false;
      if (c !== ',') {
        if (row.some(cell => cell.trim() !== '')) rows.push(row);
        row = [];
        if (c === '\r' && input[i + 1] === '\n') i++;
      }
    } else if (c === '"' && field === '' && !quoteClosed) quoted = true;
    else if (quoteClosed || c === '"') throw new Error('Invalid CSV quote near character ' + (i + 1) + '.');
    else field += c;
  }
  if (quoted) throw new Error('Unterminated quoted CSV field.');
  row.push(field);
  if (row.some(cell => cell.trim() !== '')) rows.push(row);
  return rows;
}

function numberValue(value, label, positive = false) {
  if (String(value).trim() === '') throw new Error(label + ' is empty.');
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || (positive && n <= 0))
    throw new Error(label + ' must be a finite ' + (positive ? 'positive' : 'nonnegative') + ' number.');
  return n;
}

function normalizeCsv(text, optionalLibrarySize = '') {
  const rows = parseCsv(text);
  if (rows.length < 2) throw new Error('CSV requires a header and at least one data row.');
  if (rows.length > 50001) throw new Error('Maximum 50,000 features per input.');
  const names = rows[0].map(c => c.trim());
  if (names.length < 3 || names[0] !== 'gene_id' || names[1] !== 'length_bp')
    throw new Error('Expected headers: gene_id,length_bp,count[,additional_sample...].');
  if (new Set(names).size !== names.length || names.some(n => !n))
    throw new Error('CSV headers must be unique and nonempty.');
  const samples = names.slice(2);
  if (optionalLibrarySize !== '' && samples.length !== 1)
    throw new Error('A custom library size is supported for a single sample only.');
  const genes = new Set();
  const data = rows.slice(1).map((cells, idx) => {
    const line = idx + 2;
    if (cells.length !== names.length) throw new Error('Row ' + line + ' has ' + cells.length + ' columns; expected ' + names.length + '.');
    const gene = cells[0].trim();
    if (!gene) throw new Error('Row ' + line + ': gene_id is empty.');
    if (genes.has(gene)) throw new Error('Duplicate gene_id: ' + gene + '.');
    genes.add(gene);
    return {gene, length: numberValue(cells[1], 'Row ' + line + ' length_bp', true), counts: cells.slice(2).map((c, k) => numberValue(c, 'Row ' + line + ' ' + samples[k]))};
  });
  const header = ['gene_id', 'length_bp'];
  samples.forEach(s => header.push('TPM_' + s, 'FPKM_' + s));
  const output = data.map(r => [r.gene, r.length]);
  const totals = [];
  for (let s = 0; s < samples.length; s++) {
    const observed = data.reduce((acc, r) => acc + r.counts[s], 0);
    const library = optionalLibrarySize === '' ? observed : numberValue(optionalLibrarySize, 'Library size', true);
    if (!Number.isFinite(observed) || observed <= 0 || !Number.isFinite(library) || library < observed)
      throw new Error('Sample ' + samples[s] + ' must contain positive counts not exceeding its library size.');
    const rates = data.map(r => r.counts[s] / r.length);
    const denominator = rates.reduce((acc, rate) => acc + rate, 0);
    if (!Number.isFinite(denominator) || denominator <= 0) throw new Error('Sample ' + samples[s] + ' has an invalid count/length total.');
    for (let i = 0; i < data.length; i++) {
      const tpm = 1e6 * rates[i] / denominator;
      const fpkm = 1e9 * rates[i] / library;
      if (!Number.isFinite(tpm) || !Number.isFinite(fpkm)) throw new Error('Nonfinite result for sample ' + samples[s] + '.');
      output[i].push(tpm, fpkm);
    }
    totals.push({sample: samples[s], library});
  }
  return {header, output, totals, featureCount: data.length};
}

function csvCell(value, preventFormula = false) {
  let text = String(value);
  if (preventFormula && /^[\s]*[=+\-@\t\r]/.test(text)) text = "'" + text;
  return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}
function exportCsv(result) {
  return [result.header.map(x => csvCell(x, true)).join(','), ...result.output.map(row => row.map((value, i) => csvCell(typeof value === 'number' ? Number(value.toPrecision(12)) : value, i === 0)).join(','))].join('\r\n') + '\r\n';
}

if (typeof module !== 'undefined' && module.exports) module.exports = {parseCsv, normalizeCsv, exportCsv};

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  let currentResult = null;
  $('csv-file').addEventListener('change', async () => {
    const file = $('csv-file').files[0];
    if (!file) return;
    if (file.size > MAX_BYTES) { $('error').textContent = 'File exceeds 10 MB.'; $('error').hidden = false; return; }
    try { $('csv-text').value = await file.text(); $('error').hidden = true; }
    catch { $('error').textContent = 'Could not read the selected CSV.'; $('error').hidden = false; }
  });
  $('calculate').addEventListener('click', () => {
    try {
      if (new Blob([$('csv-text').value]).size > MAX_BYTES) throw new Error('CSV exceeds 10 MB.');
      const result = normalizeCsv($('csv-text').value, $('library-size').value);
      currentResult = result;
      $('error').hidden = true;
      $('empty').hidden = true;
      $('summary').hidden = false;
      $('download').disabled = false;
      const stats = $('stats'); stats.replaceChildren();
      for (const [label, value] of [['Features', result.featureCount], ['Samples', result.totals.length], ...result.totals.map(t => [t.sample + ' · library', t.library.toLocaleString()])]) {
        const box = document.createElement('div'); box.className = 'stat';
        const strong = document.createElement('strong'); strong.textContent = String(value);
        const small = document.createElement('span'); small.textContent = label;
        box.append(strong, small); stats.append(box);
      }
      const head = $('results-table').querySelector('thead'); head.replaceChildren();
      const headerRow = document.createElement('tr');
      result.header.forEach(name => {const th = document.createElement('th'); th.textContent = name; headerRow.append(th);}); head.append(headerRow);
      const body = $('results-table').querySelector('tbody'); body.replaceChildren();
      for (const record of result.output.slice(0, 100)) {
        const tr = document.createElement('tr');
        record.forEach(value => {const td = document.createElement('td'); td.textContent = typeof value === 'number' ? value.toPrecision(6) : value; tr.append(td);}); body.append(tr);
      }
    } catch (err) {
      currentResult = null;
      $('download').disabled = true;
      $('summary').hidden = true;
      $('empty').hidden = false;
      $('error').textContent = err.message || 'Normalization failed.';
      $('error').hidden = false;
    }
  });
  $('reset').addEventListener('click', () => {
    $('csv-file').value = ''; $('csv-text').value = EXAMPLE; $('library-size').value = '';
    $('error').hidden = true; $('summary').hidden = true; $('empty').hidden = false;
    $('download').disabled = true; currentResult = null;
  });
  $('download').addEventListener('click', () => {
    if (!currentResult) return;
    const blob = new Blob([exportCsv(currentResult)], {type: 'text/csv;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'rnaseq_normalized.csv';
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}
