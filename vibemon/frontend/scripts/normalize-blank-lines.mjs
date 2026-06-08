#!/usr/bin/env node
/**
 * Collapse excessive blank lines (common agent artifact) then hand off to Prettier.
 * Usage: node scripts/normalize-blank-lines.mjs [paths...]
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(root, '..');

const HIGH_BLANK_RATIO = 0.28;

function blankRatio(text) {
	const lines = text.split('\n');
	if (lines.length === 0) return 0;
	const blank = lines.filter((line) => !line.trim()).length;
	return blank / lines.length;
}

function collapseBlankLines(text) {
	return text
		.split('\n')
		.filter((line, index, lines) => {
			if (line.trim()) return true;
			const prev = lines[index - 1];
			const next = lines[index + 1];
			if (!prev?.trim() || !next?.trim()) return true;
			return false;
		})
		.join('\n');
}

function normalizeScriptOrStyle(block) {
	if (blankRatio(block) < HIGH_BLANK_RATIO) return block;
	return collapseBlankLines(block);
}

function normalizeSvelte(source) {
	return source
		.replace(
			/(<script[^>]*>)([\s\S]*?)(<\/script>)/g,
			(_match, open, body, close) => open + normalizeScriptOrStyle(body) + close
		)
		.replace(
			/(<style[^>]*>)([\s\S]*?)(<\/style>)/g,
			(_match, open, body, close) => open + normalizeScriptOrStyle(body) + close
		);
}

function walkSvelteFiles(entry) {
	const resolved = path.resolve(process.cwd(), entry);
	if (!fs.existsSync(resolved)) return [];
	const stat = fs.statSync(resolved);
	if (stat.isFile()) return resolved.endsWith('.svelte') ? [resolved] : [];
	const files = [];
	for (const name of fs.readdirSync(resolved)) {
		files.push(...walkSvelteFiles(path.join(resolved, name)));
	}
	return files;
}

function collectPaths(args) {
	if (args.length > 0) return args.flatMap((entry) => walkSvelteFiles(entry));
	return walkSvelteFiles(path.join(frontendRoot, 'src'));
}

const targets = collectPaths(process.argv.slice(2));
const changed = [];

for (const file of targets) {
	if (!fs.existsSync(file)) continue;
	const before = fs.readFileSync(file, 'utf8');
	const after = normalizeSvelte(before);
	if (after !== before) {
		fs.writeFileSync(file, after);
		changed.push(path.relative(frontendRoot, file));
	}
}

if (changed.length > 0) {
	execSync(`pnpm exec prettier --write ${changed.map((f) => JSON.stringify(f)).join(' ')}`, {
		cwd: frontendRoot,
		stdio: 'inherit'
	});
}

console.log(changed.length ? `Normalized ${changed.length} file(s).` : 'No high-blank-ratio Svelte files found.');
