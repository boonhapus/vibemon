import type { VisualDNA, Point, Hsl } from '$lib/types';
import { seededRandom } from './seededRandom';

const BASE_RADIUS = 75;
const CX = 100;
const CY = 110;

// ── Hull Generation ──────────────────────────────────────────────

export function generateHullPoints(dna: VisualDNA, seed: number): Point[] {
	const rng = seededRandom(seed);
	const points: Point[] = [];

	for (let i = 0; i < dna.n_points; i++) {
		const baseAngle = (2 * Math.PI * i) / dna.n_points;
		const angleJitter = (rng() - 0.5) * (Math.PI / dna.n_points) * 0.6;
		const angle = baseAngle + angleJitter;
		const radius = BASE_RADIUS * (1 - dna.spikiness / 2 + rng() * dna.spikiness);
		points.push({
			x: CX + Math.cos(angle) * radius,
			y: CY + Math.sin(angle) * radius
		});
	}
	return points;
}

// ── Path Smoothing ───────────────────────────────────────────────

export function smoothClosedPath(pts: Point[]): string {
	const n = pts.length;
	const p = (i: number) => pts[((i % n) + n) % n];
	let path = `M ${p(0).x.toFixed(2)} ${p(0).y.toFixed(2)}`;

	for (let i = 0; i < n; i++) {
		const p0 = p(i - 1);
		const p1 = p(i);
		const p2 = p(i + 1);
		const p3 = p(i + 2);
		const cp1x = p1.x + (p2.x - p0.x) / 6;
		const cp1y = p1.y + (p2.y - p0.y) / 6;
		const cp2x = p2.x - (p3.x - p1.x) / 6;
		const cp2y = p2.y - (p3.y - p1.y) / 6;
		path += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
	}
	return path + ' Z';
}

// ── Limb Generation ──────────────────────────────────────────────

export interface LimbData {
	path: string;
	opacity: number;
	fill: string;
}

function getLowerLateralPoints(hullPoints: Point[]): Point[] {
	const sorted = [...hullPoints].sort((a, b) => b.y - a.y);
	const bottom40 = sorted.slice(0, Math.max(2, Math.ceil(hullPoints.length * 0.4)));
	return bottom40;
}

function extrudeStubby(anchor: Point, outwardAngle: number, rng: () => number): string {
	const len = BASE_RADIUS * 0.6;
	const cx = anchor.x + Math.cos(outwardAngle) * len * 0.6;
	const cy = anchor.y + Math.sin(outwardAngle) * len * 0.6;
	const r = len * 0.35 + rng() * len * 0.1;
	const pts: Point[] = [];
	const nPts = 6;
	for (let i = 0; i < nPts; i++) {
		const a = (2 * Math.PI * i) / nPts + rng() * 0.3;
		const rad = r * (0.85 + rng() * 0.3);
		pts.push({ x: cx + Math.cos(a) * rad, y: cy + Math.sin(a) * rad });
	}
	return smoothClosedPath(pts);
}

function extrudeElongated(anchor: Point, outwardAngle: number, rng: () => number): string {
	const len = BASE_RADIUS * 1.5;
	const tipX = anchor.x + Math.cos(outwardAngle) * len;
	const tipY = anchor.y + Math.sin(outwardAngle) * len;
	const perp = outwardAngle + Math.PI / 2;
	const w = 8 + rng() * 6;

	const p1x = anchor.x + Math.cos(perp) * w;
	const p1y = anchor.y + Math.sin(perp) * w;
	const p2x = anchor.x - Math.cos(perp) * w;
	const p2y = anchor.y - Math.sin(perp) * w;

	const cp1x = (anchor.x + tipX) / 2 + Math.cos(perp) * w * 0.7;
	const cp1y = (anchor.y + tipY) / 2 + Math.sin(perp) * w * 0.7;
	const cp2x = (anchor.x + tipX) / 2 - Math.cos(perp) * w * 0.7;
	const cp2y = (anchor.y + tipY) / 2 - Math.sin(perp) * w * 0.7;

	return `M ${p1x.toFixed(2)} ${p1y.toFixed(2)} Q ${cp1x.toFixed(2)} ${cp1y.toFixed(2)} ${tipX.toFixed(2)} ${tipY.toFixed(2)} Q ${cp2x.toFixed(2)} ${cp2y.toFixed(2)} ${p2x.toFixed(2)} ${p2y.toFixed(2)} Z`;
}

function extrudeWing(anchor: Point, outwardAngle: number, rng: () => number): string {
	const len = BASE_RADIUS * 1.2;
	const spread = 0.5 + rng() * 0.3;
	const a1 = outwardAngle - spread;
	const a2 = outwardAngle + spread;

	const tip1x = anchor.x + Math.cos(a1) * len;
	const tip1y = anchor.y + Math.sin(a1) * len;
	const tip2x = anchor.x + Math.cos(a2) * len;
	const tip2y = anchor.y + Math.sin(a2) * len;
	const midX = anchor.x + Math.cos(outwardAngle) * len * 0.6;
	const midY = anchor.y + Math.sin(outwardAngle) * len * 0.6;

	return `M ${anchor.x.toFixed(2)} ${anchor.y.toFixed(2)} Q ${midX.toFixed(2)} ${midY.toFixed(2)} ${tip1x.toFixed(2)} ${tip1y.toFixed(2)} L ${anchor.x.toFixed(2)} ${anchor.y.toFixed(2)} Q ${midX.toFixed(2)} ${midY.toFixed(2)} ${tip2x.toFixed(2)} ${tip2y.toFixed(2)} Z`;
}

export function generateLimbs(
	hullPoints: Point[],
	dna: VisualDNA,
	seed: number
): LimbData[] {
	if (dna.limb_count === 0) return [];

	const rng = seededRandom(seed + 7777);
	const candidates = getLowerLateralPoints(hullPoints);
	const limbs: LimbData[] = [];

	const count = Math.min(dna.limb_count, candidates.length);

	const leftCandidates = candidates.filter((p) => p.x < CX).sort((a, b) => b.y - a.y);
	const rightCandidates = candidates.filter((p) => p.x >= CX).sort((a, b) => b.y - a.y);

	const anchors: Point[] = [];
	if (count >= 1 && leftCandidates.length > 0) anchors.push(leftCandidates[0]);
	if (count >= 2 && rightCandidates.length > 0) anchors.push(rightCandidates[0]);
	if (anchors.length < count) {
		for (const c of candidates) {
			if (anchors.length >= count) break;
			if (!anchors.includes(c)) anchors.push(c);
		}
	}

	for (const anchor of anchors) {
		const outAngle = Math.atan2(anchor.y - CY, anchor.x - CX);
		let path: string;
		let opacity = 1.0;

		switch (dna.limb_style) {
			case 'elongated':
				path = extrudeElongated(anchor, outAngle, rng);
				break;
			case 'wing':
				path = extrudeWing(anchor, outAngle, rng);
				opacity = 0.6;
				break;
			default:
				path = extrudeStubby(anchor, outAngle, rng);
				break;
		}
		limbs.push({ path, opacity, fill: 'var(--cs)' });
	}

	return limbs;
}

// ── Eye Generation ───────────────────────────────────────────────

export interface EyeData {
	shape: string;
	cx: number;
	cy: number;
	size: number;
}

function getEyeAnchor(hullPoints: Point[]): Point {
	const sorted = [...hullPoints].sort((a, b) => a.y - b.y);
	const top20 = sorted.slice(0, Math.max(2, Math.ceil(hullPoints.length * 0.2)));
	const cx = top20.reduce((s, p) => s + p.x, 0) / top20.length;
	const cy = top20.reduce((s, p) => s + p.y, 0) / top20.length;
	return { x: cx, y: cy };
}

export function generateEyes(
	hullPoints: Point[],
	dna: VisualDNA,
	seed: number
): EyeData[] {
	const rng = seededRandom(seed + 3333);
	const anchor = getEyeAnchor(hullPoints);
	const eyeR = dna.eye_size * BASE_RADIUS;
	const eyes: EyeData[] = [];
	const offset = eyeR * 2.5 + rng() * 4;

	if (dna.eye_count === 1) {
		eyes.push({ shape: dna.eye_shape, cx: anchor.x, cy: anchor.y, size: eyeR });
	} else {
		eyes.push({ shape: dna.eye_shape, cx: anchor.x - offset, cy: anchor.y, size: eyeR });
		eyes.push({ shape: dna.eye_shape, cx: anchor.x + offset, cy: anchor.y, size: eyeR });
	}
	return eyes;
}

export function eyeToSvg(eye: EyeData, uid: string, idx: number): string {
	const { shape, cx, cy, size } = eye;
	const id = `eye-${uid}-${idx}`;

	switch (shape) {
		case 'slit': {
			const rx = size * 0.35;
			const ry = size;
			return `<ellipse id="${id}" cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" rx="${rx.toFixed(2)}" ry="${ry.toFixed(2)}" fill="var(--ce)" />`;
		}
		case 'diamond': {
			const s = size;
			return `<polygon id="${id}" points="${cx.toFixed(2)},${(cy - s).toFixed(2)} ${(cx + s * 0.7).toFixed(2)},${cy.toFixed(2)} ${cx.toFixed(2)},${(cy + s).toFixed(2)} ${(cx - s * 0.7).toFixed(2)},${cy.toFixed(2)}" fill="var(--ce)" />`;
		}
		case 'compound': {
			const r = size * 0.4;
			const off = size * 0.5;
			return `<g id="${id}"><circle cx="${cx.toFixed(2)}" cy="${(cy - off * 0.4).toFixed(2)}" r="${r.toFixed(2)}" fill="var(--ce)" /><circle cx="${(cx - off * 0.5).toFixed(2)}" cy="${(cy + off * 0.3).toFixed(2)}" r="${(r * 0.8).toFixed(2)}" fill="var(--ce)" /><circle cx="${(cx + off * 0.5).toFixed(2)}" cy="${(cy + off * 0.3).toFixed(2)}" r="${(r * 0.8).toFixed(2)}" fill="var(--ce)" /></g>`;
		}
		default: {
			return `<circle id="${id}" cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" r="${size.toFixed(2)}" fill="var(--ce)" />`;
		}
	}
}

// ── Pupil ────────────────────────────────────────────────────────

export function pupilToSvg(eye: EyeData, uid: string, idx: number): string {
	const { shape, cx, cy, size } = eye;
	const pr = size * 0.35;

	if (shape === 'compound') return '';
	if (shape === 'slit') {
		return `<ellipse cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" rx="${(pr * 0.3).toFixed(2)}" ry="${(pr * 1.1).toFixed(2)}" fill="#111" />`;
	}
	return `<circle cx="${cx.toFixed(2)}" cy="${cy.toFixed(2)}" r="${pr.toFixed(2)}" fill="#111" />`;
}

// ── Mouth Generation ─────────────────────────────────────────────

function getMouthAnchor(hullPoints: Point[]): Point {
	const sorted = [...hullPoints].sort((a, b) => b.y - a.y);
	const bottom = sorted.slice(0, Math.max(2, Math.ceil(hullPoints.length * 0.15)));
	const cx = bottom.reduce((s, p) => s + p.x, 0) / bottom.length;
	const cy = bottom.reduce((s, p) => s + p.y, 0) / bottom.length;
	return { x: cx, y: cy - 6 };
}

export function generateMouth(hullPoints: Point[], dna: VisualDNA): string | null {
	if (dna.mouth_style === 'none') return null;

	const anchor = getMouthAnchor(hullPoints);
	const w = 12;
	const h = 5;

	switch (dna.mouth_style) {
		case 'line':
			return `<path d="M ${(anchor.x - w).toFixed(2)} ${anchor.y.toFixed(2)} Q ${anchor.x.toFixed(2)} ${(anchor.y + h).toFixed(2)} ${(anchor.x + w).toFixed(2)} ${anchor.y.toFixed(2)}" fill="none" stroke="var(--cs)" stroke-width="1.5" stroke-linecap="round" />`;

		case 'open': {
			const ry = 6;
			return `<ellipse cx="${anchor.x.toFixed(2)}" cy="${anchor.y.toFixed(2)}" rx="${w.toFixed(2)}" ry="${ry.toFixed(2)}" fill="#1a1020" stroke="var(--cs)" stroke-width="1" />`;
		}

		case 'fanged': {
			const ry = 7;
			const fangH = 5;
			const fangW = 3;
			const lx = anchor.x - w * 0.5;
			const rx = anchor.x + w * 0.5;
			return `<ellipse cx="${anchor.x.toFixed(2)}" cy="${anchor.y.toFixed(2)}" rx="${w.toFixed(2)}" ry="${ry.toFixed(2)}" fill="#1a1020" stroke="var(--cs)" stroke-width="1" />` +
				`<polygon points="${lx.toFixed(2)},${(anchor.y - ry * 0.3).toFixed(2)} ${(lx - fangW).toFixed(2)},${(anchor.y + fangH).toFixed(2)} ${(lx + fangW).toFixed(2)},${(anchor.y + fangH).toFixed(2)}" fill="white" />` +
				`<polygon points="${rx.toFixed(2)},${(anchor.y - ry * 0.3).toFixed(2)} ${(rx - fangW).toFixed(2)},${(anchor.y + fangH).toFixed(2)} ${(rx + fangW).toFixed(2)},${(anchor.y + fangH).toFixed(2)}" fill="white" />`;
		}

		default:
			return null;
	}
}

// ── Texture Generation ───────────────────────────────────────────

export function generateTexturePattern(dna: VisualDNA, uid: string): string | null {
	const id = `texture-${uid}`;
	const opacity = 0.2;

	switch (dna.texture_pattern) {
		case 'dots':
			return `<pattern id="${id}" x="0" y="0" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.5" fill="var(--cs)" opacity="${opacity}" /><circle cx="9" cy="9" r="1.5" fill="var(--cs)" opacity="${opacity}" /></pattern>`;

		case 'stripes':
			return `<pattern id="${id}" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="var(--cs)" stroke-width="2" opacity="${opacity}" /></pattern>`;

		case 'scales':
			return `<pattern id="${id}" x="0" y="0" width="14" height="10" patternUnits="userSpaceOnUse"><path d="M 0 10 Q 7 0 14 10" fill="none" stroke="var(--cs)" stroke-width="1.2" opacity="${opacity}" /></pattern>`;

		case 'cracks': {
			const o = opacity + 0.05;
			return `<pattern id="${id}" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M 2 2 L 10 8 L 8 16 M 10 8 L 18 6 M 10 8 L 14 18" fill="none" stroke="var(--cs)" stroke-width="1" opacity="${o}" /></pattern>`;
		}

		default:
			return null;
	}
}

// ── HSL Helper ───────────────────────────────────────────────────

export function hsl(c: Hsl): string {
	return `hsl(${c[0].toFixed(1)}, ${(c[1] * 100).toFixed(1)}%, ${(c[2] * 100).toFixed(1)}%)`;
}
