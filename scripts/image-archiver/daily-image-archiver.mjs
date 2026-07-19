#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".webp"];
const MARKDOWN_EXTENSION = ".md";
const MARKDOWN_IMAGE_REGEX = /!\[([^\]]*)\]\(([^)]+)\)/g;
const CACHE_VERSION = 1;
const SINGLE_SCOPES = ["daily", "blog", "docs", "leetcode", "papers", "projects"];

const SCOPE_PROFILES = {
  daily: {
    contentSegments: ["content", "daily"],
    staticSegments: ["static", "daily"],
    cacheFileName: "daily-image-archiver.json",
    describeFullScope: () => "full content/daily",
    resolveTargets({ reference, imageExtension, year, fileName, workspaceRoot }) {
      if (year === null) {
        return null;
      }

      return {
        targetStaticPath: path.join(workspaceRoot, "static", "daily", year, fileName),
        targetPublicSrc: `/daily/${year}/${fileName}`,
      };
    },
  },
  blog: {
    contentSegments: ["content", "blog"],
    staticSegments: ["static", "blog"],
    cacheFileName: "blog-image-archiver.json",
    describeFullScope: () => "full content/blog",
    resolveTargets({ imageExtension, year, fileName, workspaceRoot }) {
      if (year === null) {
        return null;
      }

      return {
        targetStaticPath: path.join(workspaceRoot, "static", "blog", year, fileName),
        targetPublicSrc: `/blog/${year}/${fileName}`,
      };
    },
  },
  docs: {
    contentSegments: ["content", "docs"],
    staticSegments: ["static", "img"],
    cacheFileName: "docs-image-archiver.json",
    describeFullScope: () => "full content/docs",
    resolveTargets({ reference, fileName, workspaceRoot }) {
      const sourceDir = getSourceRelativeDirectory(reference.originalSrc);
      const bucket = sourceDir ?? path.basename(reference.markdownPath, MARKDOWN_EXTENSION);
      return {
        targetStaticPath: path.join(workspaceRoot, "static", "img", bucket, fileName),
        targetPublicSrc: `/img/${toPosixPath(bucket)}/${fileName}`,
      };
    },
  },
  leetcode: {
    contentSegments: ["content", "leetcode"],
    staticSegments: ["static", "img"],
    cacheFileName: "leetcode-image-archiver.json",
    describeFullScope: () => "full content/leetcode",
    resolveTargets({ reference, fileName, workspaceRoot }) {
      const articleName = path.basename(reference.markdownPath, MARKDOWN_EXTENSION);
      return {
        targetStaticPath: path.join(
          workspaceRoot,
          "static",
          "img",
          "leetcode",
          articleName,
          fileName,
        ),
        targetPublicSrc: `/img/leetcode/${articleName}/${fileName}`,
      };
    },
  },
  papers: {
    contentSegments: ["content", "papers"],
    staticSegments: ["static", "paper"],
    cacheFileName: "papers-image-archiver.json",
    describeFullScope: () => "full content/papers",
    resolveTargets({ reference, fileName, workspaceRoot, contentRoot }) {
      const relativeMarkdownPath = path.relative(contentRoot, reference.markdownPath);
      const [section] = relativeMarkdownPath.split(path.sep);
      if (section === "vla") {
        return {
          targetStaticPath: path.join(workspaceRoot, "static", "img", "vla", fileName),
          targetPublicSrc: `/img/vla/${fileName}`,
        };
      }

      return {
        targetStaticPath: path.join(workspaceRoot, "static", "paper", fileName),
        targetPublicSrc: `/paper/${fileName}`,
      };
    },
  },
  projects: {
    contentSegments: ["content", "projects"],
    staticSegments: ["static", "img"],
    cacheFileName: "projects-image-archiver.json",
    describeFullScope: () => "full content/projects",
    resolveTargets({ reference, fileName, workspaceRoot }) {
      let articleName = path.basename(reference.markdownPath, MARKDOWN_EXTENSION);
      if (articleName === "_index") {
        articleName = path.basename(path.dirname(reference.markdownPath));
      }
      return {
        targetStaticPath: path.join(workspaceRoot, "static", "img", articleName, fileName),
        targetPublicSrc: `/img/${articleName}/${fileName}`,
      };
    },
  },
};

function isTruthyFlag(value) {
  return value === true;
}

export function printHelp() {
  console.log(`Content image archiver

Usage:
  node scripts/daily-image-archiver.mjs [options]

Options:
  --scope <name>         Scope to archive: daily, blog, docs, leetcode, papers, projects, all
  --dry-run              Preview configuration without writing files
  --file <path>          Focus on a single markdown file under the selected scope
  --year <year>          Limit scope to a specific year, e.g. 2026
  --help                 Show this help message
`);
}

export function parseCliArgs(argv) {
  const args = [...argv];
  const options = {
    scope: "daily",
    dryRun: false,
    file: null,
    year: null,
    help: false,
  };

  while (args.length > 0) {
    const token = args.shift();

    if (token === "--dry-run") {
      options.dryRun = true;
      continue;
    }

    if (token === "--scope") {
      const value = args.shift();
      if (!value || value.startsWith("--")) {
        throw new Error("Missing value for --scope");
      }
      options.scope = value;
      continue;
    }

    if (token === "--help" || token === "-h") {
      options.help = true;
      continue;
    }

    if (token === "--file") {
      const value = args.shift();
      if (!value || value.startsWith("--")) {
        throw new Error("Missing value for --file");
      }
      options.file = value;
      continue;
    }

    if (token === "--year") {
      const value = args.shift();
      if (!value || value.startsWith("--")) {
        throw new Error("Missing value for --year");
      }
      options.year = value;
      continue;
    }

    throw new Error(`Unknown argument: ${token}`);
  }

  return options;
}

function validateScope(scope) {
  if (scope === "all") {
    return scope;
  }

  if (!SINGLE_SCOPES.includes(scope)) {
    throw new Error(`Invalid --scope value: ${scope}`);
  }

  return scope;
}

function buildScopeConfig(scope, workspaceRoot) {
  const profile = SCOPE_PROFILES[scope];
  if (!profile) {
    throw new Error(`Unsupported scope profile: ${scope}`);
  }

  const contentRoot = path.join(workspaceRoot, ...profile.contentSegments);
  const staticRoot = path.join(workspaceRoot, ...profile.staticSegments);
  const cacheRoot = path.join(workspaceRoot, ".cache");
  const cachePath = path.join(cacheRoot, profile.cacheFileName);

  return {
    scope,
    profile,
    contentRoot,
    staticRoot,
    cacheRoot,
    cachePath,
  };
}

export function normalizeCliConfig(rawOptions, cwd = process.cwd()) {
  const workspaceRoot = path.resolve(cwd);
  const scope = validateScope(rawOptions.scope ?? "daily");
  if (scope === "all") {
    throw new Error("normalizeCliConfig does not support scope=all");
  }

  const scopeConfig = buildScopeConfig(scope, workspaceRoot);

  let year = null;
  if (rawOptions.year !== null) {
    if (!/^\d{4}$/.test(String(rawOptions.year))) {
      throw new Error(`Invalid --year value: ${rawOptions.year}`);
    }
    year = Number(rawOptions.year);
  }

  let file = null;
  if (rawOptions.file) {
    file = path.resolve(workspaceRoot, rawOptions.file);

    if (path.extname(file).toLowerCase() !== MARKDOWN_EXTENSION) {
      throw new Error(`--file must point to a markdown file: ${rawOptions.file}`);
    }

    const relativeToContentRoot = path.relative(scopeConfig.contentRoot, file);
    if (
      relativeToContentRoot.startsWith("..") ||
      path.isAbsolute(relativeToContentRoot)
    ) {
      throw new Error(
        `--file must be inside ${path.join(...scopeConfig.profile.contentSegments)}: ${rawOptions.file}`,
      );
    }
  }

  return {
    scope,
    mode: isTruthyFlag(rawOptions.dryRun) ? "dry-run" : "apply",
    dryRun: isTruthyFlag(rawOptions.dryRun),
    workspaceRoot,
    contentRoot: scopeConfig.contentRoot,
    staticRoot: scopeConfig.staticRoot,
    cacheRoot: scopeConfig.cacheRoot,
    cachePath: scopeConfig.cachePath,
    profile: scopeConfig.profile,
    file,
    year,
    filters: {
      file,
      year,
    },
    supportedExtensions: {
      images: [...IMAGE_EXTENSIONS],
      markdown: MARKDOWN_EXTENSION,
    },
  };
}

export function formatConfigSummary(config) {
  const scope =
    config.file !== null
      ? `single-file (${path.relative(config.workspaceRoot, config.file)})`
      : config.year !== null
        ? `year (${config.year})`
        : config.profile.describeFullScope();

  return [
    "Content Image Archiver CLI",
    `Target Scope: ${config.scope}`,
    `Mode: ${config.mode}`,
    `Scope: ${scope}`,
    `Workspace Root: ${config.workspaceRoot}`,
    `Content Root: ${config.contentRoot}`,
    `Static Root: ${config.staticRoot}`,
    `Cache Path: ${config.cachePath}`,
    `Supported Image Extensions: ${config.supportedExtensions.images.join(", ")}`,
    `Markdown Extension: ${config.supportedExtensions.markdown}`,
  ].join("\n");
}

function matchesYearFilter(relativePath, year) {
  if (year === null) {
    return true;
  }

  const segments = relativePath.split(path.sep);
  return segments[0] === String(year);
}

function shouldIncludePath(relativePath, config) {
  if (config.file !== null) {
    const markdownRelativePath = path.relative(config.contentRoot, config.file);
    const directoryScope = path.dirname(markdownRelativePath);
    const directoryPrefix = `${directoryScope}${path.sep}`;
    return (
      relativePath === markdownRelativePath ||
      path.dirname(relativePath) === directoryScope ||
      relativePath.startsWith(directoryPrefix)
    );
  }

  return matchesYearFilter(relativePath, config.year);
}

export async function collectFiles(rootDir) {
  const results = [];

  async function walk(currentDir) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const absolutePath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(absolutePath);
        continue;
      }

      if (entry.isFile()) {
        results.push(absolutePath);
      }
    }
  }

  await walk(rootDir);
  return results;
}

export async function scanContentFiles(config) {
  const allFiles = await collectFiles(config.contentRoot);
  const markdownFiles = [];
  const imageFiles = [];

  for (const absolutePath of allFiles) {
    const relativePath = path.relative(config.contentRoot, absolutePath);
    if (!shouldIncludePath(relativePath, config)) {
      continue;
    }

    const extension = path.extname(absolutePath).toLowerCase();
    if (extension === config.supportedExtensions.markdown) {
      markdownFiles.push(absolutePath);
      continue;
    }

    if (config.supportedExtensions.images.includes(extension)) {
      imageFiles.push(absolutePath);
    }
  }

  markdownFiles.sort();
  imageFiles.sort();

  return {
    markdownFiles,
    imageFiles,
  };
}

export function formatScanSummary(scanResult, config) {
  const sampleMarkdown = scanResult.markdownFiles
    .slice(0, 5)
    .map((filePath) => `  - ${path.relative(config.workspaceRoot, filePath)}`);
  const sampleImages = scanResult.imageFiles
    .slice(0, 5)
    .map((filePath) => `  - ${path.relative(config.workspaceRoot, filePath)}`);

  return [
    "Scan Summary",
    `Markdown Files: ${scanResult.markdownFiles.length}`,
    `Image Files: ${scanResult.imageFiles.length}`,
    "Markdown Samples:",
    ...(sampleMarkdown.length > 0 ? sampleMarkdown : ["  - (none)"]),
    "Image Samples:",
    ...(sampleImages.length > 0 ? sampleImages : ["  - (none)"]),
  ].join("\n");
}

export function parseMarkdownImageReferences(markdownContent, markdownPath) {
  const references = [];
  const normalizedMarkdownPath = path.resolve(markdownPath);
  let match;

  while ((match = MARKDOWN_IMAGE_REGEX.exec(markdownContent)) !== null) {
    const [, alt, rawSrc] = match;
    const src = rawSrc.trim();
    const lineHint = markdownContent.slice(0, match.index).split(/\r?\n/).length;

    references.push({
      alt,
      originalSrc: src,
      markdownPath: normalizedMarkdownPath,
      absoluteImagePath: path.resolve(path.dirname(normalizedMarkdownPath), src),
      lineHint,
    });
  }

  return references;
}

export async function buildReferenceIndex(markdownFiles) {
  const entries = [];
  const byImagePath = new Map();

  for (const markdownPath of markdownFiles) {
    const content = await fs.readFile(markdownPath, "utf8");
    const references = parseMarkdownImageReferences(content, markdownPath);

    for (const reference of references) {
      entries.push(reference);

      const existing = byImagePath.get(reference.absoluteImagePath) ?? [];
      existing.push(reference);
      byImagePath.set(reference.absoluteImagePath, existing);
    }
  }

  return {
    entries,
    byImagePath,
  };
}

export function formatReferenceSummary(referenceIndex, config) {
  const sampleReferences = referenceIndex.entries.slice(0, 5).map((reference) => {
    const markdownRelative = path.relative(config.workspaceRoot, reference.markdownPath);
    const imageRelative = path.relative(config.workspaceRoot, reference.absoluteImagePath);
    return `  - ${markdownRelative}:${reference.lineHint} -> ${reference.originalSrc} | alt="${reference.alt}" | image=${imageRelative}`;
  });

  return [
    "Reference Summary",
    `Image References: ${referenceIndex.entries.length}`,
    `Unique Referenced Images: ${referenceIndex.byImagePath.size}`,
    "Reference Samples:",
    ...(sampleReferences.length > 0 ? sampleReferences : ["  - (none)"]),
  ].join("\n");
}

export function createEmptyCacheStore() {
  return {
    version: CACHE_VERSION,
    items: {},
  };
}

export async function loadCacheStore(cachePath) {
  try {
    const raw = await fs.readFile(cachePath, "utf8");
    const parsed = JSON.parse(raw);
    if (parsed.version !== CACHE_VERSION || typeof parsed.items !== "object") {
      return createEmptyCacheStore();
    }

    return parsed;
  } catch (error) {
    if (error.code === "ENOENT") {
      return createEmptyCacheStore();
    }
    throw error;
  }
}

export async function saveCacheStore(cachePath, cacheStore) {
  await fs.mkdir(path.dirname(cachePath), { recursive: true });
  await fs.writeFile(cachePath, `${JSON.stringify(cacheStore, null, 2)}\n`, "utf8");
}

export async function computeFileHash(filePath) {
  const content = await fs.readFile(filePath);
  return `sha256:${crypto.createHash("sha256").update(content).digest("hex")}`;
}

export function buildCacheKey(sourceImagePath, workspaceRoot) {
  return path.relative(workspaceRoot, sourceImagePath);
}

export function slugifyAlt(alt) {
  const ascii = alt
    .toLowerCase()
    .replace(/[^a-z0-9\s_-]/g, " ")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  return ascii;
}

function toPosixPath(value) {
  return value.split(path.sep).join("/");
}

export function inferYearFromMarkdownPath(markdownPath, contentRoot) {
  const relativePath = path.relative(contentRoot, markdownPath);
  const [yearSegment] = relativePath.split(path.sep);
  if (/^\d{4}$/.test(yearSegment)) {
    return yearSegment;
  }

  return null;
}

function createFallbackBaseName(reference) {
  let markdownBaseName = path.basename(reference.markdownPath, MARKDOWN_EXTENSION);
  if (markdownBaseName === "_index") {
    markdownBaseName = path.basename(path.dirname(reference.markdownPath));
  }
  return `${markdownBaseName}-image-${reference.lineHint}`;
}

export function getSourceRelativeDirectory(originalSrc) {
  const normalized = originalSrc.replace(/\\/g, "/");
  const segments = normalized.split("/").filter(Boolean);
  if (segments.length <= 1) {
    return null;
  }

  const filtered = segments.slice(0, -1).filter((segment) => segment !== ".");
  if (filtered.length === 0) {
    return null;
  }

  if (filtered[0] === "media" && filtered.length > 1) {
    return filtered.slice(1).join(path.sep);
  }

  return filtered.join(path.sep);
}

export function resolveArchiveTargets(reference, imageExtension, config) {
  const slug = slugifyAlt(reference.alt);
  const baseName = slug.length > 0 ? slug : createFallbackBaseName(reference);
  const fileName = `${baseName}${imageExtension}`;
  const year = inferYearFromMarkdownPath(reference.markdownPath, config.contentRoot);

  const resolved = config.profile.resolveTargets({
    reference,
    imageExtension,
    year,
    fileName,
    workspaceRoot: config.workspaceRoot,
    contentRoot: config.contentRoot,
  });

  if (resolved === null) {
    return null;
  }

  return {
    year,
    targetFileName: fileName,
    targetStaticPath: resolved.targetStaticPath,
    targetPublicSrc: resolved.targetPublicSrc,
  };
}

export function createArchivePlanForImage(imagePath, references, config) {
  const normalizedImagePath = path.resolve(imagePath);
  const imageExtension = path.extname(normalizedImagePath).toLowerCase();

  if (!references || references.length === 0) {
    return {
      status: "skip",
      reason: "unreferenced-image",
      sourceImagePath: normalizedImagePath,
    };
  }

  if (references.length > 1) {
    return {
      status: "skip",
      reason: "multiple-references",
      sourceImagePath: normalizedImagePath,
      references,
    };
  }

  const [reference] = references;
  const target = resolveArchiveTargets(reference, imageExtension, config);
  if (target === null) {
    return {
      status: "skip",
      reason: "unable-to-resolve-target",
      sourceImagePath: normalizedImagePath,
      references,
    };
  }

  return {
    status: "process",
    reason: null,
    sourceImagePath: normalizedImagePath,
    markdownPath: reference.markdownPath,
    originalSrc: reference.originalSrc,
    alt: reference.alt,
    year: target.year,
    targetFileName: target.targetFileName,
    targetStaticPath: target.targetStaticPath,
    targetPublicSrc: target.targetPublicSrc,
    lineHint: reference.lineHint,
  };
}

export function buildArchivePlan(imageFiles, referenceIndex, config) {
  const plans = imageFiles.map((imagePath) =>
    createArchivePlanForImage(
      imagePath,
      referenceIndex.byImagePath.get(path.resolve(imagePath)) ?? [],
      config,
    ),
  );

  const summary = {
    total: plans.length,
    process: plans.filter((plan) => plan.status === "process").length,
    skip: plans.filter((plan) => plan.status === "skip").length,
  };

  return {
    plans,
    summary,
  };
}

export function formatPlanSummary(planResult, config) {
  const samples = planResult.plans.slice(0, 5).map((plan) => {
    const sourceRelative = path.relative(config.workspaceRoot, plan.sourceImagePath);
    if (plan.status === "skip") {
      return `  - SKIP ${sourceRelative} | reason=${plan.reason}`;
    }

    const markdownRelative = path.relative(config.workspaceRoot, plan.markdownPath);
    const targetRelative = path.relative(config.workspaceRoot, plan.targetStaticPath);
    return `  - PROCESS ${sourceRelative} | markdown=${markdownRelative}:${plan.lineHint} | target=${targetRelative} | public=${plan.targetPublicSrc}`;
  });

  return [
    "Plan Summary",
    `Total Plans: ${planResult.summary.total}`,
    `Process: ${planResult.summary.process}`,
    `Skip: ${planResult.summary.skip}`,
    "Plan Samples:",
    ...(samples.length > 0 ? samples : ["  - (none)"]),
  ].join("\n");
}

export async function applyCachedPlanSkips(planResult, cacheStore, config) {
  const updatedPlans = [];

  for (const plan of planResult.plans) {
    if (plan.status !== "process") {
      updatedPlans.push(plan);
      continue;
    }

    const cacheKey = buildCacheKey(plan.sourceImagePath, config.workspaceRoot);
    const cacheItem = cacheStore.items[cacheKey];
    if (!cacheItem) {
      updatedPlans.push(plan);
      continue;
    }

    try {
      const sourceHash = await computeFileHash(plan.sourceImagePath);
      const markdownContent = await fs.readFile(plan.markdownPath, "utf8");
      await fs.access(plan.targetStaticPath);

      if (
        cacheItem.sourceHash === sourceHash &&
        cacheItem.targetPublicSrc === plan.targetPublicSrc &&
        markdownContent.includes(`![${plan.alt}](${plan.targetPublicSrc})`)
      ) {
        updatedPlans.push({
          ...plan,
          status: "skip",
          reason: "cached-match",
        });
        continue;
      }
    } catch {
      updatedPlans.push(plan);
      continue;
    }

    updatedPlans.push(plan);
  }

  return {
    plans: updatedPlans,
    summary: {
      total: updatedPlans.length,
      process: updatedPlans.filter((plan) => plan.status === "process").length,
      skip: updatedPlans.filter((plan) => plan.status === "skip").length,
    },
  };
}

export function buildDryRunReport(config, scanResult, referenceIndex, planResult) {
  const processPlans = planResult.plans.filter((plan) => plan.status === "process");
  const skipPlans = planResult.plans.filter((plan) => plan.status === "skip");

  const skipReasonCounts = skipPlans.reduce((accumulator, plan) => {
    const key = plan.reason ?? "unknown";
    accumulator[key] = (accumulator[key] ?? 0) + 1;
    return accumulator;
  }, {});

  return {
    scope: {
      mode: config.mode,
      file: config.file,
      year: config.year,
    },
    counts: {
      markdownFiles: scanResult.markdownFiles.length,
      imageFiles: scanResult.imageFiles.length,
      imageReferences: referenceIndex.entries.length,
      uniqueReferencedImages: referenceIndex.byImagePath.size,
      totalPlans: planResult.summary.total,
      processPlans: planResult.summary.process,
      skipPlans: planResult.summary.skip,
    },
    processPlans,
    skipPlans,
    skipReasonCounts,
  };
}

export function formatDryRunReport(report, config) {
  const processSection = report.processPlans.slice(0, 10).map((plan) => {
    const sourceRelative = path.relative(config.workspaceRoot, plan.sourceImagePath);
    const markdownRelative = path.relative(config.workspaceRoot, plan.markdownPath);
    const targetRelative = path.relative(config.workspaceRoot, plan.targetStaticPath);

    return [
      `  - source: ${sourceRelative}`,
      `    markdown: ${markdownRelative}:${plan.lineHint}`,
      `    alt: "${plan.alt}"`,
      `    target: ${targetRelative}`,
      `    public: ${plan.targetPublicSrc}`,
    ].join("\n");
  });

  const skipSection = report.skipPlans.slice(0, 10).map((plan) => {
    const sourceRelative = path.relative(config.workspaceRoot, plan.sourceImagePath);
    return `  - source: ${sourceRelative}\n    reason: ${plan.reason}`;
  });

  const skipReasonLines = Object.entries(report.skipReasonCounts)
    .sort((left, right) => left[0].localeCompare(right[0]))
    .map(([reason, count]) => `  - ${reason}: ${count}`);

  return [
    "Dry Run Report",
    `Mode: ${report.scope.mode}`,
    `Markdown Files Scanned: ${report.counts.markdownFiles}`,
    `Image Files Scanned: ${report.counts.imageFiles}`,
    `Image References Indexed: ${report.counts.imageReferences}`,
    `Unique Referenced Images: ${report.counts.uniqueReferencedImages}`,
    `Plans Ready To Process: ${report.counts.processPlans}`,
    `Plans Skipped: ${report.counts.skipPlans}`,
    "Process Preview:",
    ...(processSection.length > 0 ? processSection : ["  - (none)"]),
    "Skip Preview:",
    ...(skipSection.length > 0 ? skipSection : ["  - (none)"]),
    "Skip Reasons:",
    ...(skipReasonLines.length > 0 ? skipReasonLines : ["  - (none)"]),
  ].join("\n");
}

export function replaceMarkdownImageReference(markdownContent, plan) {
  const oldToken = `![${plan.alt}](${plan.originalSrc})`;
  const newToken = `![${plan.alt}](${plan.targetPublicSrc})`;
  const lines = markdownContent.split(/\r?\n/);
  const targetIndex = plan.lineHint - 1;

  if (targetIndex < 0 || targetIndex >= lines.length) {
    throw new Error(`Invalid line hint for markdown rewrite: ${plan.lineHint}`);
  }

  if (!lines[targetIndex].includes(oldToken)) {
    throw new Error(
      `Expected markdown image token not found on line ${plan.lineHint}: ${oldToken}`,
    );
  }

  lines[targetIndex] = lines[targetIndex].replace(oldToken, newToken);
  return lines.join("\n");
}

export async function executeArchivePlan(plan) {
  if (plan.status !== "process") {
    return {
      status: "skipped",
      reason: plan.reason ?? "non-process-plan",
      plan,
    };
  }

  await fs.mkdir(path.dirname(plan.targetStaticPath), { recursive: true });
  await fs.copyFile(plan.sourceImagePath, plan.targetStaticPath);

  const copiedImage = await fs.readFile(plan.targetStaticPath);
  const sourceImage = await fs.readFile(plan.sourceImagePath);
  if (!copiedImage.equals(sourceImage)) {
    throw new Error(`Copied image verification failed: ${plan.targetStaticPath}`);
  }

  const markdownContent = await fs.readFile(plan.markdownPath, "utf8");
  const rewrittenContent = replaceMarkdownImageReference(markdownContent, plan);
  await fs.writeFile(plan.markdownPath, rewrittenContent, "utf8");

  const updatedMarkdown = await fs.readFile(plan.markdownPath, "utf8");
  if (!updatedMarkdown.includes(`![${plan.alt}](${plan.targetPublicSrc})`)) {
    throw new Error(`Markdown rewrite verification failed: ${plan.markdownPath}`);
  }

  await fs.unlink(plan.sourceImagePath);

  try {
    await fs.access(plan.sourceImagePath);
    throw new Error(`Source image deletion verification failed: ${plan.sourceImagePath}`);
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }

  return {
    status: "done",
    reason: null,
    plan,
    targetStaticPath: plan.targetStaticPath,
    markdownPath: plan.markdownPath,
  };
}

export async function executeArchivePlans(planResult, options = {}) {
  const { dryRun = false, config = null, cacheStore = null } = options;

  if (dryRun) {
    return {
      results: [],
      summary: {
        done: 0,
        failed: 0,
        skipped: 0,
      },
    };
  }

  const results = [];
  for (const plan of planResult.plans) {
    try {
      const result = await executeArchivePlan(plan);
      results.push(result);

      if (result.status === "done" && cacheStore !== null && config !== null) {
        const cacheKey = buildCacheKey(result.plan.sourceImagePath, config.workspaceRoot);
        cacheStore.items[cacheKey] = {
          sourceHash: await computeFileHash(result.targetStaticPath),
          markdownPath: path.relative(config.workspaceRoot, result.markdownPath),
          originalSrc: result.plan.originalSrc,
          alt: result.plan.alt,
          targetPath: path.relative(config.workspaceRoot, result.targetStaticPath),
          targetPublicSrc: result.plan.targetPublicSrc,
          status: "done",
          updatedAt: new Date().toISOString(),
        };
      }
    } catch (error) {
      results.push({
        status: "failed",
        reason: error.message,
        plan,
      });
    }
  }

  return {
    results,
    summary: {
      done: results.filter((result) => result.status === "done").length,
      failed: results.filter((result) => result.status === "failed").length,
      skipped: results.filter((result) => result.status === "skipped").length,
    },
  };
}

export function formatExecutionSummary(executionResult, config) {
  const samples = executionResult.results.slice(0, 10).map((result) => {
    const sourceRelative = path.relative(config.workspaceRoot, result.plan.sourceImagePath);

    if (result.status === "done") {
      const markdownRelative = path.relative(config.workspaceRoot, result.markdownPath);
      const targetRelative = path.relative(config.workspaceRoot, result.targetStaticPath);
      return `  - DONE ${sourceRelative} | markdown=${markdownRelative} | target=${targetRelative}`;
    }

    return `  - ${result.status.toUpperCase()} ${sourceRelative} | reason=${result.reason}`;
  });

  return [
    "Execution Summary",
    `Done: ${executionResult.summary.done}`,
    `Failed: ${executionResult.summary.failed}`,
    `Skipped: ${executionResult.summary.skipped}`,
    "Execution Samples:",
    ...(samples.length > 0 ? samples : ["  - (none)"]),
    "Source images are deleted only after copy + rewrite verification succeeds.",
  ].join("\n");
}

export async function runCli(argv = process.argv.slice(2), cwd = process.cwd()) {
  const options = parseCliArgs(argv);

  if (options.help) {
    printHelp();
    return { exitCode: 0, didPrintHelp: true };
  }

  const selectedScopes =
    validateScope(options.scope ?? "daily") === "all"
      ? [...SINGLE_SCOPES]
      : [validateScope(options.scope ?? "daily")];

  const runs = [];

  for (const scope of selectedScopes) {
    const config = normalizeCliConfig(
      {
        ...options,
        scope,
      },
      cwd,
    );
    const cacheStore = await loadCacheStore(config.cachePath);
    const scanResult = await scanContentFiles(config);
    const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
    const initialPlanResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
    const planResult = await applyCachedPlanSkips(initialPlanResult, cacheStore, config);
    const dryRunReport = buildDryRunReport(config, scanResult, referenceIndex, planResult);
    const executionResult = config.dryRun
      ? null
      : await executeArchivePlans(planResult, { dryRun: false, config, cacheStore });

    console.log(formatConfigSummary(config));
    console.log(formatScanSummary(scanResult, config));
    console.log(formatReferenceSummary(referenceIndex, config));
    console.log(formatPlanSummary(planResult, config));
    console.log(formatDryRunReport(dryRunReport, config));
    if (executionResult !== null) {
      await saveCacheStore(config.cachePath, cacheStore);
      console.log(formatExecutionSummary(executionResult, config));
      console.log("Status: Executor finished copy + rewrite + delete + cache update.");
    } else {
      console.log("Status: Planner ready. No files will be changed in this stage.");
    }

    runs.push({
      config,
      scanResult,
      referenceIndex,
      planResult,
      dryRunReport,
      executionResult,
      cacheStore,
    });
  }

  return {
    exitCode: 0,
    didPrintHelp: false,
    runs,
    config: runs[0]?.config ?? null,
    scanResult: runs[0]?.scanResult ?? null,
    referenceIndex: runs[0]?.referenceIndex ?? null,
    planResult: runs[0]?.planResult ?? null,
    dryRunReport: runs[0]?.dryRunReport ?? null,
    executionResult: runs[0]?.executionResult ?? null,
    cacheStore: runs[0]?.cacheStore ?? null,
  };
}

const isEntrypoint =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isEntrypoint) {
  runCli().catch((error) => {
    console.error(`Error: ${error.message}`);
    process.exitCode = 1;
  });
}
