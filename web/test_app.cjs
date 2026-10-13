'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {parseCsv, normalizeCsv, exportCsv} = require('./app.js');

test('TPM is one million, FPKM uses library-size units', () => {
  const result = normalizeCsv('gene_id,length_bp,count\nA,1000,100\nB,2000,200\n');
  assert.deepEqual(result.output.map(x => x[2]), [500000,500000]);
  assert.ok(Math.abs(result.output[0][3] - 1e9 * .1 / 300) < 1e-6);
  assert.equal(result.featureCount,2);
});
test('custom library size changes FPKM not TPM', () => {
  const data = 'gene_id,length_bp,count\nA,1000,100\nB,2000,200\n';
  const original = normalizeCsv(data), filtered = normalizeCsv(data,'600');
  assert.equal(filtered.output[0][2],original.output[0][2]);
  assert.equal(filtered.output[0][3],original.output[0][3]/2);
});
test('multi-sample columns and quoted gene names', () => {
  const result = normalizeCsv('gene_id,length_bp,s1,s2\n"A,1",1000,10,0\nB,2000,0,5');
  assert.equal(result.output[0][0],'A,1');
  assert.equal(result.output[0][2],1000000);
  assert.equal(result.output[1][4],1000000);
  assert.ok(exportCsv(result).includes('"A,1"'));
});
test('CSV formula injection is neutralized in download', () => {
  const out = exportCsv(normalizeCsv('gene_id,length_bp,count\n=1+1,1000,10'));
  assert.ok(out.includes("'=1+1"));
});
test('invalid and malformed inputs fail without fabricated results', () => {
  const invalid = [
    'gene_id,length_bp,count\nA,0,10',
    'gene_id,length_bp,count\nA,1000,-1',
    'gene_id,length_bp,count\nA,1000,0',
    'gene_id,length_bp,count\nA,1000,2,3',
    'gene_id,length_bp,count\nA,1000,2\nA,2000,3',
    'gene_id,length_bp,count\nA,1000,NaN',
    'gene_id,length_bp,count\nA,1000,1\nB,1000,',
    'gene_id,length_bp,count\n"A,1000,1'
  ];
  invalid.forEach(x=>assert.throws(()=>normalizeCsv(x)));
});
test('quoted CRLF CSV parses correctly', () => {
  assert.deepEqual(parseCsv('gene_id,length_bp,count\r\n"A""B",1000,10\r\n')[1],[ 'A"B','1000','10']);
});
