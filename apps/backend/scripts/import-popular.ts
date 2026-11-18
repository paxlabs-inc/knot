#!/usr/bin/env bun
/**
 * Mirror the most popular npm, crates.io, PyPI and Go packages into Knot Space.
 *
 * Usage:
 *   DATABASE_URL=... bun scripts/import-popular.ts [--ecosystems npm,crates,pypi,go] [--limit N] [--dry-run]
 *
 * Each package is published under the `mirror` user with the tags
 * `mirror`, `<ecosystem>` and a few upstream keywords. Upstream names that
 * do not fit Knot's name rules (dots, underscores, module paths) are normalised,
 * and the original name is kept at the front of the description.
 *
 * Files are written to <cwd>/uploads/<sha256>.tar.gz, exactly like the
 * /api/packages/upload endpoint, so run this from apps/backend on the
 * machine (or volume) that serves the registry.
 */
import { PrismaClient } from '@prisma/client';
import { createHash } from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { unzipSync } from 'fflate';
import * as tar from 'tar';
import { NPM, CRATES, PYPI, GO, type Ecosystem } from './popular-packages';

const prisma = new PrismaClient();
const MIRROR_USER = 'mirror';
const BASE_URL = process.env.KNOT_SPACE_URL || process.env.API_URL || 'http://localhost:3001';
const UA = 'knot-space-mirror (https://github.com/saravenpi/knot)';
const UPLOADS_DIR = path.join(process.cwd(), 'uploads');

const NAME_RE = /^[a-z0-9][a-z0-9-]*$/;
const VERSION_RE = /^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9-]+)?(\+[a-z0-9-]+)?$/;

interface Upstream {
  ecosystem: Ecosystem;
  upstreamName: string; // as known upstream
  name: string;          // normalised Knot name
  version: string;
  description: string;
  tags: string[];
  tarball: () => Promise<Uint8Array>; // gzip tarball bytes
}

// ---------- helpers ----------

function parseArgs() {
  const args = process.argv.slice(2);
  const get = (flag: string) => {
    const i = args.indexOf(flag);
    return i >= 0 ? args[i + 1] : undefined;
  };
  const ecosystems = (get('--ecosystems') || 'npm,crates,pypi,go').split(',') as Ecosystem[];
  const limit = parseInt(get('--limit') || '0') || Infinity;
  const dryRun = args.includes('--dry-run');
  return { ecosystems, limit, dryRun };
}

function normalizeName(raw: string): string {
  return raw.toLowerCase().replace(/^@/, '').replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').replace(/-{2,}/g, '-');
}

function normalizeTag(raw: string): string | null {
  const t = raw.toLowerCase().trim().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '');
  return t.length >= 1 && t.length <= 30 && /^[a-z0-9][a-z0-9-]*$/.test(t) ? t : null;
}

function buildTags(ecosystem: Ecosystem, keywords: string[] = []): string[] {
  const out = new Set<string>(['mirror', ecosystem]);
  for (const k of keywords) {
    if (out.size >= 10) break;
    const t = normalizeTag(k);
    if (t) out.add(t);
  }
  return [...out];
}

function describe(ecosystem: Ecosystem, upstreamName: string, desc: string | undefined): string {
  const label = { npm: 'npm', crates: 'crates.io', pypi: 'PyPI', go: 'Go' }[ecosystem];
  return `[${label}: ${upstreamName}] ${(desc || '').trim()}`.trim().slice(0, 1000);
}

async function fetchJson(url: string): Promise<any> {
  const res = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/json' } });
  if (!res.ok) throw new Error(`GET ${url} -> ${res.status}`);
  return res.json();
}

async function fetchBytes(url: string): Promise<Uint8Array> {
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`GET ${url} -> ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}

/** Convert a zip archive (Go module proxy format) into a gzip tarball. */
async function zipToTarGz(zip: Uint8Array): Promise<Uint8Array> {
  const files = unzipSync(zip);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'knot-mirror-'));
  try {
    for (const [name, data] of Object.entries(files)) {
      if (name.endsWith('/')) continue;
      const dest = path.join(tmp, name);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, data);
    }
    const out = path.join(tmp, 'out.tar.gz');
    const entries = fs.readdirSync(tmp);
    await tar.create({ gzip: true, cwd: tmp, file: out, portable: true }, entries);
    return new Uint8Array(fs.readFileSync(out));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ---------- ecosystem resolvers ----------

async function resolveNpm(name: string): Promise<Upstream> {
  const meta = await fetchJson(`https://registry.npmjs.org/${encodeURIComponent(name)}`);
  const version: string = meta['dist-tags']?.latest;
  const v = meta.versions?.[version];
  if (!v?.dist?.tarball) throw new Error('no tarball');
  return {
    ecosystem: 'npm',
    upstreamName: name,
    name: normalizeName(name),
    version,
    description: describe('npm', name, v.description || meta.description),
    tags: buildTags('npm', v.keywords || meta.keywords || []),
    tarball: () => fetchBytes(v.dist.tarball),
  };
}

async function resolveCrate(name: string): Promise<Upstream> {
  const meta = await fetchJson(`https://crates.io/api/v1/crates/${name}`);
  const version: string = meta.crate.max_stable_version || meta.crate.max_version;
  return {
    ecosystem: 'crates',
    upstreamName: name,
    name: normalizeName(name),
    version,
    description: describe('crates', name, meta.crate.description),
    tags: buildTags('crates', [...(meta.crate.keywords || []), ...(meta.crate.categories || [])]),
    tarball: () => fetchBytes(`https://static.crates.io/crates/${name}/${name}-${version}.crate`),
  };
}

async function resolvePypi(name: string): Promise<Upstream> {
  const meta = await fetchJson(`https://pypi.org/pypi/${name}/json`);
  const version: string = meta.info.version;
  const sdist = (meta.urls as any[]).find((u) => u.packagetype === 'sdist' && u.filename.endsWith('.tar.gz'));
  if (!sdist) throw new Error('no .tar.gz sdist');
  return {
    ecosystem: 'pypi',
    upstreamName: name,
    name: normalizeName(name),
    version,
    description: describe('pypi', name, meta.info.summary),
    tags: buildTags('pypi', (meta.info.keywords || '').split(/[,\s]+/).filter(Boolean)),
    tarball: () => fetchBytes(sdist.url),
  };
}

function goShortName(module: string): string {
  const parts = module.replace(/\/v\d+$/, '').split('/');
  if (module.startsWith('golang.org/x/')) return `x-${parts[2]}`;
  if (module.startsWith('gopkg.in/')) return parts[1].replace(/\.v\d+$/, '');
  return parts[parts.length - 1];
}

async function resolveGo(entry: { module: string; description: string }): Promise<Upstream> {
  // Module proxy requires upper-case letters to be escaped as !x
  const escaped = entry.module.replace(/[A-Z]/g, (c) => `!${c.toLowerCase()}`);
  const info = await fetchJson(`https://proxy.golang.org/${escaped}/@latest`);
  const tag: string = info.Version; // e.g. v1.9.1
  const version = tag.replace(/^v/, '');
  return {
    ecosystem: 'go',
    upstreamName: entry.module,
    name: normalizeName(goShortName(entry.module)),
    version,
    description: describe('go', entry.module, entry.description),
    tags: buildTags('go', [entry.module.split('/')[0]]),
    tarball: async () => zipToTarGz(await fetchBytes(`https://proxy.golang.org/${escaped}/@v/${tag}.zip`)),
  };
}

// ---------- publishing ----------

async function ensureMirrorUser() {
  const existing = await prisma.user.findUnique({ where: { username: MIRROR_USER } });
  if (existing) return existing;
  // Unusable password: a random 64-byte value hashed, never shared.
  const bcrypt = await import('bcryptjs');
  const passwordHash = await bcrypt.hash(createHash('sha256').update(crypto.getRandomValues(new Uint8Array(64))).digest('hex'), 10);
  return prisma.user.create({
    data: { username: MIRROR_USER, email: 'mirror@knot.space', passwordHash },
  });
}

type Outcome = 'published' | 'exists' | 'conflict' | 'skipped' | 'failed';

async function publish(pkg: Upstream, ownerId: string, dryRun: boolean): Promise<Outcome> {
  if (!NAME_RE.test(pkg.name) || pkg.name.length > 100) {
    console.log(`  skip ${pkg.upstreamName}: invalid name "${pkg.name}"`);
    return 'skipped';
  }
  // Two-part versions (PyPI: "3.20", "2026.6") are padded to x.y.0; anything else non-semver is skipped.
  if (/^\d+\.\d+$/.test(pkg.version)) pkg.version = `${pkg.version}.0`;
  if (!VERSION_RE.test(pkg.version) || pkg.version.length > 20) {
    console.log(`  skip ${pkg.upstreamName}: version "${pkg.version}" is not semver`);
    return 'skipped';
  }

  // Same name already taken by another ecosystem (or a real user)? Do not shadow it.
  const sameName = await prisma.package.findFirst({ where: { name: pkg.name }, include: { tags: true } });
  if (sameName) {
    const ecoTag = sameName.tags.find((t) => ['npm', 'crates', 'pypi', 'go'].includes(t.tag))?.tag;
    if (sameName.ownerId !== ownerId || ecoTag !== pkg.ecosystem) {
      console.log(`  conflict ${pkg.ecosystem}:${pkg.upstreamName}: "${pkg.name}" already belongs to ${ecoTag || 'a user'}`);
      return 'conflict';
    }
  }

  const exists = await prisma.package.findUnique({ where: { name_version: { name: pkg.name, version: pkg.version } } });
  if (exists) {
    console.log(`  exists ${pkg.name}@${pkg.version}`);
    return 'exists';
  }

  if (dryRun) {
    console.log(`  would publish ${pkg.name}@${pkg.version}  (${pkg.ecosystem}:${pkg.upstreamName})`);
    return 'published';
  }

  const bytes = await pkg.tarball();
  const checksum = createHash('sha256').update(bytes).digest('hex');
  const filename = `${checksum}.tar.gz`;
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
  fs.writeFileSync(path.join(UPLOADS_DIR, filename), bytes);

  await prisma.package.create({
    data: {
      name: pkg.name,
      version: pkg.version,
      description: pkg.description,
      ownerId,
      teamId: null,
      downloadUrl: `${BASE_URL}/uploads/${filename}`,
      filePath: `/uploads/${filename}`,
      fileSize: BigInt(bytes.length),
      checksumSha256: checksum,
      tags: { create: pkg.tags.map((tag) => ({ tag })) },
    },
  });
  console.log(`  published ${pkg.name}@${pkg.version}  (${(bytes.length / 1024).toFixed(0)} KB, ${pkg.ecosystem}:${pkg.upstreamName})`);
  return 'published';
}

// ---------- main ----------

async function main() {
  const { ecosystems, limit, dryRun } = parseArgs();
  const owner = await ensureMirrorUser();
  const totals: Record<Outcome, number> = { published: 0, exists: 0, conflict: 0, skipped: 0, failed: 0 };

  const work: Array<{ ecosystem: Ecosystem; label: string; resolve: () => Promise<Upstream> }> = [];
  if (ecosystems.includes('npm')) NPM.slice(0, limit).forEach((n) => work.push({ ecosystem: 'npm', label: n, resolve: () => resolveNpm(n) }));
  if (ecosystems.includes('crates')) CRATES.slice(0, limit).forEach((n) => work.push({ ecosystem: 'crates', label: n, resolve: () => resolveCrate(n) }));
  if (ecosystems.includes('pypi')) PYPI.slice(0, limit).forEach((n) => work.push({ ecosystem: 'pypi', label: n, resolve: () => resolvePypi(n) }));
  if (ecosystems.includes('go')) GO.slice(0, limit).forEach((e) => work.push({ ecosystem: 'go', label: e.module, resolve: () => resolveGo(e) }));

  console.log(`Importing ${work.length} packages (${ecosystems.join(', ')})${dryRun ? ' [dry run]' : ''} as user "${owner.username}"`);

  // Modest concurrency: upstream registries rate-limit aggressive clients (crates.io: 1 req/s guidance).
  const CONCURRENCY = 4;
  let next = 0;
  await Promise.all(
    Array.from({ length: CONCURRENCY }, async () => {
      while (next < work.length) {
        const item = work[next++];
        try {
          const pkg = await item.resolve();
          totals[await publish(pkg, owner.id, dryRun)]++;
        } catch (err) {
          totals.failed++;
          console.log(`  failed ${item.ecosystem}:${item.label}: ${err instanceof Error ? err.message : err}`);
        }
      }
    }),
  );

  console.log(`\nDone: ${totals.published} published, ${totals.exists} already present, ${totals.conflict} name conflicts, ${totals.skipped} skipped, ${totals.failed} failed`);
}

main()
  .then(async () => {
    await prisma.$disconnect();
    process.exit(0); // open fetch/keep-alive handles otherwise keep the process alive
  })
  .catch(async (err) => {
    console.error(err);
    await prisma.$disconnect();
    process.exit(1);
  });
