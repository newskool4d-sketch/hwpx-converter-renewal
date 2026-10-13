// One request over stdin, one JSON envelope over stdout. No on-demand installs.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import tls from 'node:tls';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';

const LIMIT = 32 * 1024 * 1024;
const INPUT_LIMIT = 128 * 1024 * 1024;
const fail = (code, message) => Object.assign(new Error(message), { code });
const offline = () => { throw fail('LOCAL_ONLY', '외부 연결·모델 다운로드·보조 프로세스는 비활성 상태입니다.'); };
// Keep all document processing local, including package fallback paths.
globalThis.fetch = offline;
http.request = http.get = https.request = https.get = offline;
net.connect = net.createConnection = tls.connect = offline;
net.Socket.prototype.connect = offline;
for (const method of ['spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync', 'fork']) {
  childProcess[method] = offline;
}
syncBuiltinESMExports();
console.log = console.info = console.warn = console.error = () => {};

const OPTIONS = Object.freeze({ ocr: false, formulaOcr: false, layoutTables: 'keep',
  keepTrailingEmptyCols: true, keepEmptyParagraphs: true, removeHeaderFooter: false,
  dedupeRunningHeaders: false, inlineImages: false });
const API = {
  diagnose: [], parse: ['parse'], compare: ['parse', 'diffBlocks'],
  validate: ['validateHwpx'], fields: ['parse', 'extractFormSchema', 'extractClickHereFields'],
  fill: ['fillHwpx', 'fillWithUniqueGuard', 'validateHwpx', 'parse', 'diffBlocks'],
  patch: ['patchHwpx', 'validateHwpx', 'parse', 'diffBlocks'],
  render: ['renderDocument'], profile: ['hwpxToProfile'],
  lint: ['parse', 'lintGongmunText', 'lintMuncheText'],
};
let request = {};
let version;

function envelope(status, data, warnings = [], error = null) {
  return { id: request.id, action: request.action, version, ok: status === 'success',
    status, data, warnings, error };
}

function inputFile(value, limit = INPUT_LIMIT) {
  if (typeof value !== 'string' || !value.trim() || /^(?:https?|file|ftp):/i.test(value)) {
    throw fail('INVALID_PATH', '로컬 파일 경로를 지정하세요.');
  }
  const resolved = fs.realpathSync(value);
  const stat = fs.statSync(resolved);
  if (!stat.isFile()) throw fail('INVALID_PATH', '입력은 일반 파일이어야 합니다.');
  if (stat.size > limit) throw fail('INPUT_TOO_LARGE', '입력 파일 크기 제한을 초과했습니다.');
  const bytes = fs.readFileSync(resolved);
  const expected = request.args?.expected_fingerprints;
  if (expected !== undefined) {
    if (!expected || typeof expected !== 'object' || Array.isArray(expected)) {
      throw fail('INPUT_CHANGED', '미리보기 입력 정보가 올바르지 않습니다. 다시 미리보기 하세요.');
    }
    const canonical = name => process.platform === 'win32' ? path.resolve(name).toLowerCase() : path.resolve(name);
    const entry = Object.entries(expected).find(([name]) => canonical(name) === canonical(resolved));
    if (!entry || typeof entry[1] !== 'string' || !/^[a-f0-9]{64}$/i.test(entry[1]) || hash(bytes) !== entry[1].toLowerCase()) {
      throw fail('INPUT_CHANGED', '미리보기 후 입력 파일이 변경되었습니다. 다시 미리보기 하세요.');
    }
  }
  return { path: resolved, bytes };
}

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const arrayBuffer = bytes => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);

function ensureHwpx(file) {
  if (path.extname(file.path).toLowerCase() !== '.hwpx') {
    throw fail('HWPX_REQUIRED', '이 작업은 HWPX 파일만 지원합니다.');
  }
}

function outputPath(value, source, expectedExtension = '.hwpx') {
  if (typeof value !== 'string' || !value.trim() || /^(?:https?|file|ftp):/i.test(value)) {
    throw fail('OUTPUT_REQUIRED', '새 사본의 저장 경로가 필요합니다.');
  }
  const destination = path.resolve(value);
  const dir = fs.realpathSync(path.dirname(destination));
  const resolved = path.join(dir, path.basename(destination));
  if (resolved.toLowerCase() === source.toLowerCase()) {
    throw fail('SOURCE_OVERWRITE', '원본 문서를 덮어쓸 수 없습니다.');
  }
  if (path.extname(resolved).toLowerCase() !== expectedExtension) {
    throw fail('OUTPUT_FORMAT', `출력 확장자는 ${expectedExtension}여야 합니다.`);
  }
  if (fs.existsSync(resolved)) throw fail('OUTPUT_EXISTS', '기존 파일을 덮어쓸 수 없습니다. 새 이름을 지정하세요.');
  return resolved;
}

function saveExclusive(destination, bytes) {
  // Hard-link publication is atomic and fails if another writer claimed the name.
  const stage = path.join(path.dirname(destination), `.kordoc-${randomUUID()}.tmp`);
  try {
    const fd = fs.openSync(stage, 'wx', 0o600);
    try { fs.writeFileSync(fd, bytes); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    fs.linkSync(stage, destination);
  } finally {
    if (fs.existsSync(stage)) fs.unlinkSync(stage);
  }
}

function serializable(value) {
  if (value instanceof Uint8Array || value instanceof ArrayBuffer) {
    const bytes = Buffer.from(value instanceof ArrayBuffer ? value : arrayBuffer(value));
    return { byteLength: bytes.length, sha256: hash(bytes), omitted: 'binary' };
  }
  if (value instanceof Map) return Object.fromEntries([...value].map(([k, v]) => [k, serializable(v)]));
  if (Array.isArray(value)) return value.map(serializable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, serializable(v)]));
  return value;
}

async function parseFile(api, file) {
  // Buffer input deliberately omits filePath, disabling DRM/COM fallbacks.
  const parsed = await api.parse(file.bytes, OPTIONS);
  if (!parsed.success) throw fail(parsed.code || 'PARSE_ERROR', '문서 내용을 읽지 못했습니다. 암호·손상·지원 형식을 확인하세요.');
  return parsed;
}

// kordoc's public WarningCode values which indicate loss, incomplete recovery,
// or uncertain OCR content. Presentation-only page approximation is not loss.
const CONTENT_LOSS_WARNINGS = new Set(['SKIPPED_IMAGE', 'SKIPPED_OLE', 'TRUNCATED_TABLE',
  'UNSUPPORTED_ELEMENT', 'PARTIAL_PARSE', 'NEEDS_OCR', 'OCR_FAILED', 'OCR_LOW_CONF',
  'COM_EMPTY', 'MALFORMED_XML', 'BROKEN_ZIP_RECOVERY', 'LENIENT_CFB_RECOVERY', 'HIDDEN_TEXT_FILTERED']);
function partialWarnings(warnings = []) {
  return warnings.some(item => item && typeof item === 'object' && CONTENT_LOSS_WARNINGS.has(item.code));
}

function summary(parsed) {
  const numbers = [];
  const images = [];
  const merges = [];
  let paragraphs = 0;
  let tables = 0;
  const visit = (blocks, prefix = '') => (blocks || []).forEach((block, index) => {
    const address = `${prefix}${index}`;
    if (block.type === 'table' && block.table) {
      tables++;
      block.table.cells.forEach((row, r) => row.forEach((cell, c) => {
        if (cell.rowSpan > 1 || cell.colSpan > 1) merges.push({ block: address, row: r, col: c, rowSpan: cell.rowSpan, colSpan: cell.colSpan });
        if (cell.blocks?.length) visit(cell.blocks, `${address}/${r},${c}/`);
        else numbers.push(...((cell.text || '').match(/[-+]?\d[\d,]*(?:\.\d+)?/g) || []));
      }));
      visit(block.table.captionBlocks, `${address}/caption/`);
    } else if (block.type === 'image') {
      const image = block.imageData;
      images.push({ block: address, sha256: image?.data ? hash(image.data) : null,
        filename: image?.filename || null, text: block.text || '' });
    } else {
      paragraphs++;
      numbers.push(...((block.text || '').match(/[-+]?\d[\d,]*(?:\.\d+)?/g) || []));
    }
    visit(block.children, `${address}/child/`);
  });
  visit(parsed.blocks);
  return { fileType: parsed.fileType, pageCount: parsed.pageCount || parsed.metadata?.pageCount,
    blockCount: parsed.blocks.length, paragraphs, tables, imageCount: images.length,
    numbers, images, merges };
}

function multisetDifference(before, after) {
  const counts = new Map();
  for (const item of before) counts.set(item, (counts.get(item) || 0) + 1);
  for (const item of after) counts.set(item, (counts.get(item) || 0) - 1);
  return { removed: [...counts].filter(([, n]) => n > 0).map(([value, count]) => ({ value, count })),
    added: [...counts].filter(([, n]) => n < 0).map(([value, count]) => ({ value, count: -count })) };
}

function contentText(block) {
  // Compare content, not renderer positions or regenerated internal object IDs.
  return [block.type, block.text || '', block.table?.caption || '',
    block.table?.cells.map(row => row.map(cell => [cell.text, (cell.blocks || []).map(contentText)])),
    (block.children || []).map(contentText)];
}

function exactCellDiffs(before, after) {
  return Array.from({ length: Math.max(before.rows, after.rows) }, (_, row) =>
    Array.from({ length: Math.max(before.cols, after.cols) }, (_, col) => {
      const a = before.cells[row]?.[col]?.text, b = after.cells[row]?.[col]?.text;
      return { type: a === b ? 'unchanged' : a === undefined ? 'added' : b === undefined ? 'removed' : 'modified',
        before: a, after: b };
    }));
}

function compareParsed(api, before, after) {
  const a = summary(before), b = summary(after);
  const result = api.diffBlocks(before.blocks, after.blocks);
  let beforeIndex = 0, afterIndex = 0;
  for (const diff of result.diffs) {
    // kordoc aligns by similarity and treats >= .99 as unchanged. Keep that
    // alignment, but never hide a one-character edit inside a long paragraph/cell.
    if (diff.type === 'unchanged' && JSON.stringify(contentText(diff.before)) !== JSON.stringify(contentText(diff.after))) {
      diff.type = 'modified';
      diff.exactContentChanged = true;
      delete diff.similarity;
      result.stats.unchanged--;
      result.stats.modified++;
    }
    if (diff.type === 'modified' && diff.before?.table && diff.after?.table) {
      diff.cellDiffs = exactCellDiffs(diff.before.table, diff.after.table);
    }
    // Zero-based original/result block positions, including unchanged entries.
    diff.beforeIndex = diff.before ? beforeIndex++ : null;
    diff.afterIndex = diff.after ? afterIndex++ : null;
    if (diff.cellDiffs) diff.cellChanges = diff.cellDiffs.flatMap((row, r) => row.flatMap((cell, c) =>
      cell.type === 'unchanged' ? [] : [{ row: r, col: c, ...cell }]));
  }
  return { ...result, before: a, after: b, integrity: {
    numbers: multisetDifference(a.numbers, b.numbers),
    numberOrderChanged: JSON.stringify(a.numbers) !== JSON.stringify(b.numbers),
    imageCountChanged: a.imageCount !== b.imageCount,
    imagesChanged: JSON.stringify(a.images) !== JSON.stringify(b.images),
    mergesChanged: JSON.stringify(a.merges) !== JSON.stringify(b.merges),
    note: '관찰된 차이입니다. 의도한 변경과 의도하지 않은 손실은 검토자가 판단해야 합니다.',
  } };
}

function safeSvg(svg) {
  // Preview output cannot load remote resources or run embedded code.
  return svg.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, '')
    .replace(/<foreignObject\b[^>]*>[\s\S]*?<\/foreignObject\s*>/gi, '')
    .replace(/\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*')/gi, '')
    .replace(/(\s(?:xlink:)?href\s*=\s*)(["'])(?!#|data:image\/)[\s\S]*?\2/gi, '$1""')
    .replace(/url\(\s*["']?(?!#|data:image\/)[^)]+\)/gi, 'none');
}

async function run(api) {
  const action = request.action;
  const args = request.args || {};
  if (!(action in API)) throw fail('UNSUPPORTED_ACTION', '지원하지 않는 문서 작업입니다.');
  if (API[action].some(name => typeof api[name] !== 'function')) throw fail('UNSUPPORTED_API', '설치한 kordoc 버전이 이 작업 API를 지원하지 않습니다.');
  if (action === 'diagnose') return envelope('success', { version, nodeVersion: process.version,
    localOnly: true, ocr: false, capabilities: Object.fromEntries(Object.entries(API).map(([name, exports]) =>
      [name, exports.every(key => typeof api[key] === 'function')])) });
  if (action === 'compare') {
    const before = await parseFile(api, inputFile(args.before));
    const after = await parseFile(api, inputFile(args.after));
    const warnings = [...(before.warnings || []), ...(after.warnings || [])];
    return envelope(partialWarnings(warnings) ? 'partial' : 'success', compareParsed(api, before, after), warnings);
  }
  const file = inputFile(args.path);
  if (action === 'validate') {
    ensureHwpx(file);
    const data = await api.validateHwpx(file.bytes);
    return envelope(data.ok ? 'success' : 'error', data, [], data.ok ? null : { code: 'INVALID_HWPX', message: 'HWPX 구조 검사에서 문제가 발견됐습니다.' });
  }
  if (action === 'profile') {
    ensureHwpx(file);
    return envelope('success', await api.hwpxToProfile(file.bytes));
  }
  if (action === 'render') {
    const page = args.page ?? 1;
    if (!Number.isInteger(page) || page < 1) throw fail('INVALID_PAGE', '페이지 번호는 1 이상의 정수여야 합니다.');
    const rendered = await api.renderDocument(file.bytes, { format: 'svg', pages: [page], reflow: true, maxImageBytes: 16 * 1024 * 1024 });
    const asset = rendered.assets.find(asset => asset.page === page) || rendered.assets[0];
    if (!asset) throw fail('PAGE_NOT_FOUND', '요청한 페이지를 렌더링하지 못했습니다.');
    const warnings = [...(rendered.scene.warnings || []), '검토용 렌더입니다. 실제 한컴 화면·인쇄 검증을 대신하지 않습니다.'];
    return envelope('success', { svg: safeSvg(String(asset.data)), page, pageCount: rendered.scene.pageCount || rendered.scene.pages?.length,
      width: asset.width, height: asset.height, scene: rendered.scene }, warnings);
  }
  if (action === 'fill' || action === 'patch') {
    ensureHwpx(file);
    const dryRun = args.dry_run !== false;
    const destination = dryRun ? null : outputPath(args.output, file.path);
    const beforeHash = hash(file.bytes);
    const before = await parseFile(api, file);
    let result, bytes, partial = partialWarnings(before.warnings);
    let warnings = [...(before.warnings || [])];
    if (action === 'fill') {
      const values = JSON.parse(inputFile(args.values_file, 1024 * 1024).bytes.toString('utf8').replace(/^\uFEFF/, ''));
      if (!values || Array.isArray(values) || typeof values !== 'object' || !Object.keys(values).length) throw fail('INVALID_VALUES', '채울 값은 라벨과 값이 있는 JSON 객체여야 합니다.');
      const validValue = value => typeof value === 'string' || (Array.isArray(value) && value.every(v => typeof v === 'string'));
      for (const [key, value] of Object.entries(values)) {
        if (!key.trim() || !(validValue(value) || (value && typeof value === 'object' && validValue(value.value) && (value.format === undefined || typeof value.format === 'string')))) {
          throw fail('INVALID_VALUES', '양식 값은 문자열·문자열 배열·{value,format}만 지원합니다.');
        }
      }
      result = await api.fillWithUniqueGuard(values, (vals, blocked) => api.fillHwpx(arrayBuffer(file.bytes), vals, blocked));
      bytes = Buffer.from(result.buffer);
      partial ||= Boolean(result.rejected?.length || result.unmatched?.length || result.warnings?.length);
      warnings.push(...(result.warnings || []));
    } else {
      // Markdown line endings are syntax separators, not document text. Windows
      // CRLF otherwise produces a false residual diff in kordoc's table verifier.
      const markdown = inputFile(args.markdown_file, 8 * 1024 * 1024).bytes.toString('utf8').replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
      // Patches are text/cell edits. New external images are outside this contract.
      if (/!\[[^\]]*\]\(\s*(?:https?:|\/\/)|<(?:img|image)\b[^>]*(?:src|href)\s*=\s*["']?\s*(?:https?:|\/\/)/i.test(markdown)) throw fail('LOCAL_ONLY', '외부 이미지가 있는 수정 원고는 지원하지 않습니다.');
      result = await api.patchHwpx(file.bytes, markdown, { verify: true });
      if (!result.success || !result.data) throw fail('PATCH_FAILED', '지원하는 변경을 적용하지 못했습니다.');
      bytes = Buffer.from(result.data);
      const residual = result.verification?.stats;
      partial ||= Boolean(result.skipped?.length || !residual || residual.added || residual.removed || residual.modified);
    }
    const validation = await api.validateHwpx(bytes);
    if (!validation.ok) return envelope('error', { dryRun, output: null, validation }, warnings, { code: 'INVALID_RESULT', message: '수정본 구조 검증에 실패하여 저장하지 않았습니다.' });
    const after = await parseFile(api, { bytes });
    if (hash(fs.readFileSync(file.path)) !== beforeHash) throw fail('SOURCE_CHANGED', '처리 중 원본이 변경되어 사본 저장을 중단했습니다.');
    if (partialWarnings(after.warnings)) partial = true;
    const details = { ...result };
    delete details.buffer;
    delete details.data;
    // Do not duplicate filled private values in operation reports.
    if (details.filled) details.filled = details.filled.map(({ value, ...field }) => ({ ...field, valueLength: String(value ?? '').length }));
    const data = { ...details, dryRun, output: null, sourceSha256: beforeHash,
      resultSha256: hash(bytes), byteLength: bytes.length, validation,
      changes: compareParsed(api, before, after) };
    if (partial && !dryRun) {
      warnings.push('일부 변경이 적용되지 않아 사본을 저장하지 않았습니다. 미적용 내용을 확인하고 수정 원고·값을 조정하세요.');
    } else if (!dryRun) {
      if (Buffer.byteLength(JSON.stringify(serializable({ data, warnings }))) > LIMIT - 4096) {
        throw fail('OUTPUT_TOO_LARGE', '결과 크기 제한(32 MiB)을 초과하여 사본을 저장하지 않았습니다.');
      }
      saveExclusive(destination, bytes);
      data.output = destination;
    }
    return envelope(partial ? 'partial' : 'success', data, [...warnings, ...(after.warnings || [])]);
  }
  const parsed = await parseFile(api, file);
  const warnings = parsed.warnings || [];
  const status = partialWarnings(warnings) ? 'partial' : 'success';
  if (action === 'parse') return envelope(status, { ...parsed, summary: summary(parsed) }, warnings);
  if (action === 'fields') {
    const fields = api.extractFormSchema(parsed.blocks);
    const clickHere = parsed.fileType === 'hwpx' ? await api.extractClickHereFields(arrayBuffer(file.bytes)) : [];
    return envelope(status, { ...fields, clickHere }, warnings);
  }
  if (action === 'lint') return envelope(status, { gongmun: api.lintGongmunText(parsed.markdown),
    munche: api.lintMuncheText(parsed.markdown) }, warnings);
}

try {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > 1024 * 1024) throw fail('INPUT_TOO_LARGE', '요청 크기 제한을 초과했습니다.');
    chunks.push(chunk);
  }
  request = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  if (Number(process.versions.node.split('.')[0]) < 20) throw fail('NODE_VERSION', 'Node 20 이상이 필요합니다.');
  const packageDir = path.resolve(process.argv[2]);
  const pkg = JSON.parse(fs.readFileSync(path.join(packageDir, 'package.json'), 'utf8'));
  if (pkg.name !== 'kordoc') throw fail('INVALID_PACKAGE', 'kordoc 패키지 경로가 올바르지 않습니다.');
  version = pkg.version;
  const api = await import(pathToFileURL(path.join(packageDir, 'dist', 'index.js')).href);
  const result = JSON.stringify(serializable(await run(api)));
  if (Buffer.byteLength(result) > LIMIT) throw fail('OUTPUT_TOO_LARGE', '결과 크기 제한(32 MiB)을 초과했습니다.');
  process.stdout.write(result);
} catch (error) {
  const known = new Set(['LOCAL_ONLY', 'INVALID_PATH', 'INPUT_CHANGED', 'INPUT_TOO_LARGE', 'HWPX_REQUIRED', 'OUTPUT_REQUIRED', 'SOURCE_OVERWRITE', 'OUTPUT_FORMAT', 'OUTPUT_EXISTS', 'UNSUPPORTED_ACTION', 'UNSUPPORTED_API', 'INVALID_PAGE', 'PAGE_NOT_FOUND', 'INVALID_VALUES', 'PATCH_FAILED', 'SOURCE_CHANGED', 'NODE_VERSION', 'INVALID_PACKAGE', 'OUTPUT_TOO_LARGE']);
  const code = typeof error.code === 'string' ? error.code : 'BRIDGE_ERROR';
  const message = known.has(code) ? error.message : ({ ENOENT: '입력 파일 또는 설치 구성 파일을 찾지 못했습니다.',
    EEXIST: '기존 파일을 덮어쓸 수 없습니다.', EACCES: '파일 접근 권한이 없습니다.',
    EPERM: '파일 작업 권한이 없습니다.' }[code] || '문서 처리를 완료하지 못했습니다. 입력 형식과 설치 상태를 확인하세요.');
  process.stdout.write(JSON.stringify(envelope('error', null, [], { code, message })));
}
