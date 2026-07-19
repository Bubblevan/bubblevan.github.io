import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import os from "node:os";
import fs from "node:fs/promises";
import { spawnSync } from "node:child_process";

import {
  applyCachedPlanSkips,
  buildReferenceIndex,
  buildArchivePlan,
  buildCacheKey,
  buildDryRunReport,
  computeFileHash,
  collectFiles,
  createEmptyCacheStore,
  createArchivePlanForImage,
  executeArchivePlan,
  executeArchivePlans,
  formatConfigSummary,
  formatDryRunReport,
  formatExecutionSummary,
  formatPlanSummary,
  formatReferenceSummary,
  formatScanSummary,
  getSourceRelativeDirectory,
  inferYearFromMarkdownPath,
  loadCacheStore,
  normalizeCliConfig,
  parseMarkdownImageReferences,
  parseCliArgs,
  replaceMarkdownImageReference,
  resolveArchiveTargets,
  saveCacheStore,
  scanContentFiles,
  slugifyAlt,
} from "./daily-image-archiver.mjs";

const workspaceRoot = path.resolve("D:/MyLab/Hugo/bubblevan.github.io");

async function createTempWorkspace() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "daily-image-archiver-"));
  await fs.mkdir(path.join(root, "content", "daily", "2026", "jul"), {
    recursive: true,
  });
  await fs.mkdir(path.join(root, "content", "daily", "2025"), {
    recursive: true,
  });

  await fs.writeFile(
    path.join(root, "content", "daily", "2026", "jul", "2026-7-10.md"),
    "# sample\n\n![CUHK-welcome](image.png)\n",
    "utf8",
  );
  await fs.writeFile(
    path.join(root, "content", "daily", "2026", "jul", "image.png"),
    "png",
    "utf8",
  );
  await fs.writeFile(
    path.join(root, "content", "daily", "2025", "2025-12-31.md"),
    "# older\n",
    "utf8",
  );
  await fs.writeFile(
    path.join(root, "content", "daily", "authors.yml"),
    "authors: []\n",
    "utf8",
  );

  return root;
}

test("parseCliArgs parses dry-run, file, and year flags", () => {
  const actual = parseCliArgs([
    "--scope",
    "daily",
    "--dry-run",
    "--file",
    "content/daily/2026/jul/2026-7-10.md",
    "--year",
    "2026",
  ]);

  assert.deepEqual(actual, {
    scope: "daily",
    dryRun: true,
    file: "content/daily/2026/jul/2026-7-10.md",
    year: "2026",
    help: false,
  });
});

test("normalizeCliConfig resolves paths under content/daily", () => {
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: "content/daily/2026/jul/2026-7-10.md",
      year: "2026",
      help: false,
    },
    workspaceRoot,
  );

  assert.equal(config.mode, "dry-run");
  assert.equal(
    config.file,
    path.join(workspaceRoot, "content", "daily", "2026", "jul", "2026-7-10.md"),
  );
  assert.equal(config.year, 2026);
  assert.equal(config.contentRoot, path.join(workspaceRoot, "content", "daily"));
  assert.equal(config.staticRoot, path.join(workspaceRoot, "static", "daily"));
});

test("normalizeCliConfig rejects invalid year values", () => {
  assert.throws(
    () =>
      normalizeCliConfig(
        {
          dryRun: true,
          scope: "daily",
          file: null,
          year: "26",
          help: false,
        },
        workspaceRoot,
      ),
    /Invalid --year value/,
  );
});

test("normalizeCliConfig rejects files outside content/daily", () => {
  assert.throws(
    () =>
      normalizeCliConfig(
        {
          dryRun: false,
          scope: "daily",
          file: "content/blog/2026/example.md",
          year: null,
          help: false,
        },
        workspaceRoot,
      ),
    /must be inside content\/daily|must be inside content\\daily/,
  );
});

test("formatConfigSummary includes mode and scope details", () => {
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: "content/daily/2026/jul/2026-7-10.md",
      year: null,
      help: false,
    },
    workspaceRoot,
  );

  const summary = formatConfigSummary(config);
  assert.match(summary, /Mode: dry-run/);
  assert.match(summary, /Target Scope: daily/);
  assert.match(summary, /Scope: single-file/);
  assert.match(summary, /Supported Image Extensions:/);
});

test("collectFiles recursively lists files", async () => {
  const tempRoot = await createTempWorkspace();
  const contentRoot = path.join(tempRoot, "content", "daily");

  const files = await collectFiles(contentRoot);
  const relative = files
    .map((filePath) => path.relative(contentRoot, filePath))
    .sort();

  assert.deepEqual(relative, [
    path.join("2025", "2025-12-31.md"),
    path.join("2026", "jul", "2026-7-10.md"),
    path.join("2026", "jul", "image.png"),
    "authors.yml",
  ]);
});

test("scanContentFiles filters by year and supported extensions", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );

  const result = await scanContentFiles(config);
  const markdownRelative = result.markdownFiles.map((filePath) =>
    path.relative(config.contentRoot, filePath),
  );
  const imageRelative = result.imageFiles.map((filePath) =>
    path.relative(config.contentRoot, filePath),
  );

  assert.deepEqual(markdownRelative, [path.join("2026", "jul", "2026-7-10.md")]);
  assert.deepEqual(imageRelative, [path.join("2026", "jul", "image.png")]);
});

test("scanContentFiles narrows scope for --file to same directory", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: "content/daily/2026/jul/2026-7-10.md",
      year: null,
      help: false,
    },
    tempRoot,
  );

  const result = await scanContentFiles(config);
  const markdownRelative = result.markdownFiles.map((filePath) =>
    path.relative(config.contentRoot, filePath),
  );
  const imageRelative = result.imageFiles.map((filePath) =>
    path.relative(config.contentRoot, filePath),
  );

  assert.deepEqual(markdownRelative, [path.join("2026", "jul", "2026-7-10.md")]);
  assert.deepEqual(imageRelative, [path.join("2026", "jul", "image.png")]);
});

test("formatScanSummary includes file counts", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const result = await scanContentFiles(config);

  const summary = formatScanSummary(result, config);
  assert.match(summary, /Scan Summary/);
  assert.match(summary, /Markdown Files: 1/);
  assert.match(summary, /Image Files: 1/);
});

test("parseMarkdownImageReferences extracts alt, src, and line hints", () => {
  const markdownPath = path.join(
    workspaceRoot,
    "content",
    "daily",
    "2026",
    "jul",
    "2026-7-10.md",
  );
  const content = "# sample\n\n![CUHK-welcome](image.png)\n";

  const references = parseMarkdownImageReferences(content, markdownPath);

  assert.equal(references.length, 1);
  assert.equal(references[0].alt, "CUHK-welcome");
  assert.equal(references[0].originalSrc, "image.png");
  assert.equal(references[0].lineHint, 3);
  assert.equal(
    references[0].absoluteImagePath,
    path.join(workspaceRoot, "content", "daily", "2026", "jul", "image.png"),
  );
});

test("buildReferenceIndex groups references by absolute image path", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);

  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);

  assert.equal(referenceIndex.entries.length, 1);
  assert.equal(referenceIndex.byImagePath.size, 1);

  const [entry] = referenceIndex.entries;
  assert.equal(entry.alt, "CUHK-welcome");
  assert.equal(entry.originalSrc, "image.png");
  assert.equal(
    referenceIndex.byImagePath.get(entry.absoluteImagePath)?.length,
    1,
  );
});

test("formatReferenceSummary includes reference counts", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);

  const summary = formatReferenceSummary(referenceIndex, config);
  assert.match(summary, /Reference Summary/);
  assert.match(summary, /Image References: 1/);
  assert.match(summary, /Unique Referenced Images: 1/);
  assert.match(summary, /CUHK-welcome/);
});

test("slugifyAlt normalizes simple ASCII labels", () => {
  assert.equal(slugifyAlt("CUHK-welcome"), "cuhk-welcome");
  assert.equal(slugifyAlt("Hello   World_2026"), "hello-world-2026");
});

test("inferYearFromMarkdownPath returns top-level year segment", () => {
  const markdownPath = path.join(
    workspaceRoot,
    "content",
    "daily",
    "2026",
    "jul",
    "2026-7-10.md",
  );

  assert.equal(
    inferYearFromMarkdownPath(markdownPath, path.join(workspaceRoot, "content", "daily")),
    "2026",
  );
});

test("createArchivePlanForImage builds a process plan for single referenced image", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const imagePath = scanResult.imageFiles[0];
  const references = referenceIndex.byImagePath.get(imagePath);

  const plan = createArchivePlanForImage(imagePath, references, config);

  assert.equal(plan.status, "process");
  assert.equal(plan.targetFileName, "cuhk-welcome.png");
  assert.equal(plan.targetPublicSrc, "/daily/2026/cuhk-welcome.png");
  assert.equal(
    plan.targetStaticPath,
    path.join(tempRoot, "static", "daily", "2026", "cuhk-welcome.png"),
  );
});

test("createArchivePlanForImage falls back when alt slug is empty", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "daily-image-archiver-empty-alt-"));
  await fs.mkdir(path.join(tempRoot, "content", "daily", "2026", "jul"), {
    recursive: true,
  });
  await fs.writeFile(
    path.join(tempRoot, "content", "daily", "2026", "jul", "2026-7-10.md"),
    "# sample\n\n![](image.png)\n",
    "utf8",
  );
  await fs.writeFile(
    path.join(tempRoot, "content", "daily", "2026", "jul", "image.png"),
    "png",
    "utf8",
  );

  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const imagePath = scanResult.imageFiles[0];
  const references = referenceIndex.byImagePath.get(imagePath);

  const plan = createArchivePlanForImage(imagePath, references, config);
  assert.equal(plan.status, "process");
  assert.equal(plan.targetFileName, "2026-7-10-image-3.png");
});

test("getSourceRelativeDirectory extracts docs media bucket names", () => {
  assert.equal(
    getSourceRelativeDirectory("./media/大学生物学/figure1.png"),
    "大学生物学",
  );
  assert.equal(
    getSourceRelativeDirectory("media/新农科实践/overview.png"),
    "新农科实践",
  );
  assert.equal(getSourceRelativeDirectory("image.png"), null);
});

test("resolveArchiveTargets routes blog images into static/blog by year", () => {
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "blog",
      file: null,
      year: "2026",
      help: false,
    },
    workspaceRoot,
  );
  const reference = {
    alt: "InternDataN1",
    originalSrc: "interndatan1.png",
    markdownPath: path.join(
      workspaceRoot,
      "content",
      "blog",
      "2026",
      "2026-05-30-internvlan1-datasets.md",
    ),
    lineHint: 10,
  };

  const target = resolveArchiveTargets(reference, ".png", config);
  assert.equal(target.targetFileName, "interndatan1.png");
  assert.equal(target.targetPublicSrc, "/blog/2026/interndatan1.png");
  assert.equal(
    target.targetStaticPath,
    path.join(workspaceRoot, "static", "blog", "2026", "interndatan1.png"),
  );
});

test("resolveArchiveTargets routes docs media images into static/img buckets", () => {
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "docs",
      file: null,
      year: null,
      help: false,
    },
    workspaceRoot,
  );
  const reference = {
    alt: "",
    originalSrc: "./media/大学生物学/figure1.png",
    markdownPath: path.join(
      workspaceRoot,
      "content",
      "docs",
      "undergraduate",
      "通识杂项",
      "大学生物学.md",
    ),
    lineHint: 12,
  };

  const target = resolveArchiveTargets(reference, ".png", config);
  assert.equal(target.targetPublicSrc, "/img/大学生物学/大学生物学-image-12.png");
  assert.equal(
    target.targetStaticPath,
    path.join(workspaceRoot, "static", "img", "大学生物学", "大学生物学-image-12.png"),
  );
});

test("resolveArchiveTargets routes vla papers into static/img/vla", () => {
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "papers",
      file: null,
      year: null,
      help: false,
    },
    workspaceRoot,
  );
  const reference = {
    alt: "",
    originalSrc: "image.png",
    markdownPath: path.join(workspaceRoot, "content", "papers", "vla", "act.md"),
    lineHint: 9,
  };

  const target = resolveArchiveTargets(reference, ".png", config);
  assert.equal(target.targetPublicSrc, "/img/vla/act-image-9.png");
  assert.equal(
    target.targetStaticPath,
    path.join(workspaceRoot, "static", "img", "vla", "act-image-9.png"),
  );
});

test("resolveArchiveTargets routes projects images by article slug", () => {
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "projects",
      file: null,
      year: null,
      help: false,
    },
    workspaceRoot,
  );
  const reference = {
    alt: "项目概览",
    originalSrc: "image1.png",
    markdownPath: path.join(
      workspaceRoot,
      "content",
      "projects",
      "archaeological-reports",
      "_index.md",
    ),
    lineHint: 9,
  };

  const target = resolveArchiveTargets(reference, ".png", config);
  assert.equal(target.targetPublicSrc, "/img/archaeological-reports/archaeological-reports-image-9.png");
  assert.equal(
    target.targetStaticPath,
    path.join(
      workspaceRoot,
      "static",
      "img",
      "archaeological-reports",
      "archaeological-reports-image-9.png",
    ),
  );
});

test("buildArchivePlan marks unreferenced images as skip", async () => {
  const tempRoot = await createTempWorkspace();
  await fs.writeFile(
    path.join(tempRoot, "content", "daily", "2026", "jul", "lonely.png"),
    "png",
    "utf8",
  );

  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);

  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
  const skipped = planResult.plans.find((plan) => plan.reason === "unreferenced-image");

  assert.equal(planResult.summary.total, 2);
  assert.equal(planResult.summary.process, 1);
  assert.equal(planResult.summary.skip, 1);
  assert.ok(skipped);
});

test("formatPlanSummary includes process and skip counts", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);

  const summary = formatPlanSummary(planResult, config);
  assert.match(summary, /Plan Summary/);
  assert.match(summary, /Process: 1/);
  assert.match(summary, /Skip: 0/);
  assert.match(summary, /cuhk-welcome\.png/);
});

test("buildDryRunReport aggregates counts and skip reasons", async () => {
  const tempRoot = await createTempWorkspace();
  await fs.writeFile(
    path.join(tempRoot, "content", "daily", "2026", "jul", "lonely.png"),
    "png",
    "utf8",
  );

  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);

  const report = buildDryRunReport(config, scanResult, referenceIndex, planResult);

  assert.equal(report.counts.imageFiles, 2);
  assert.equal(report.counts.processPlans, 1);
  assert.equal(report.counts.skipPlans, 1);
  assert.equal(report.skipReasonCounts["unreferenced-image"], 1);
});

test("formatDryRunReport includes process preview and skip reasons", async () => {
  const tempRoot = await createTempWorkspace();
  await fs.writeFile(
    path.join(tempRoot, "content", "daily", "2026", "jul", "lonely.png"),
    "png",
    "utf8",
  );

  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
  const report = buildDryRunReport(config, scanResult, referenceIndex, planResult);

  const formatted = formatDryRunReport(report, config);
  assert.match(formatted, /Dry Run Report/);
  assert.match(formatted, /Plans Ready To Process: 1/);
  assert.match(formatted, /Plans Skipped: 1/);
  assert.match(formatted, /public: \/daily\/2026\/cuhk-welcome\.png/);
  assert.match(formatted, /unreferenced-image: 1/);
});

test("createEmptyCacheStore returns current cache structure", () => {
  const cacheStore = createEmptyCacheStore();
  assert.equal(cacheStore.version, 1);
  assert.deepEqual(cacheStore.items, {});
});

test("saveCacheStore and loadCacheStore persist cache data", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "daily-image-archiver-cache-"));
  const cachePath = path.join(tempRoot, ".cache", "daily-image-archiver.json");
  const cacheStore = createEmptyCacheStore();
  cacheStore.items["content/daily/2026/jul/image.png"] = {
    sourceHash: "sha256:test",
    status: "done",
  };

  await saveCacheStore(cachePath, cacheStore);
  const loaded = await loadCacheStore(cachePath);

  assert.deepEqual(loaded, cacheStore);
});

test("replaceMarkdownImageReference rewrites the expected token on the hinted line", () => {
  const plan = {
    alt: "CUHK-welcome",
    originalSrc: "image.png",
    targetPublicSrc: "/daily/2026/cuhk-welcome.png",
    lineHint: 3,
  };

  const rewritten = replaceMarkdownImageReference(
    "# sample\n\n![CUHK-welcome](image.png)\n",
    plan,
  );

  assert.match(rewritten, /!\[CUHK-welcome\]\(\/daily\/2026\/cuhk-welcome\.png\)/);
});

test("executeArchivePlan copies image and rewrites markdown without deleting source", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: false,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
  const plan = planResult.plans.find((item) => item.status === "process");

  const result = await executeArchivePlan(plan);
  const updatedMarkdown = await fs.readFile(plan.markdownPath, "utf8");
  const copiedImage = await fs.readFile(plan.targetStaticPath, "utf8");

  assert.equal(result.status, "done");
  assert.match(updatedMarkdown, /!\[CUHK-welcome\]\(\/daily\/2026\/cuhk-welcome\.png\)/);
  assert.equal(copiedImage, "png");
  await assert.rejects(fs.readFile(plan.sourceImagePath, "utf8"));
});

test("executeArchivePlans reports skipped plans and successful process plans", async () => {
  const tempRoot = await createTempWorkspace();
  await fs.writeFile(
    path.join(tempRoot, "content", "daily", "2026", "jul", "lonely.png"),
    "png",
    "utf8",
  );

  const config = normalizeCliConfig(
    {
      dryRun: false,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
  const cacheStore = createEmptyCacheStore();

  const executionResult = await executeArchivePlans(planResult, {
    dryRun: false,
    config,
    cacheStore,
  });

  assert.equal(executionResult.summary.done, 1);
  assert.equal(executionResult.summary.skipped, 1);
  assert.equal(executionResult.summary.failed, 0);
  assert.equal(Object.keys(cacheStore.items).length, 1);
});

test("formatExecutionSummary includes done counts", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: false,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const planResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
  const executionResult = await executeArchivePlans(planResult, {
    dryRun: false,
    config,
    cacheStore: createEmptyCacheStore(),
  });

  const summary = formatExecutionSummary(executionResult, config);
  assert.match(summary, /Execution Summary/);
  assert.match(summary, /Done: 1/);
  assert.match(summary, /deleted only after copy \+ rewrite verification succeeds/);
});

test("computeFileHash returns stable sha256 hash", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "daily-image-archiver-hash-"));
  const filePath = path.join(tempRoot, "example.txt");
  await fs.writeFile(filePath, "hello", "utf8");

  const hash = await computeFileHash(filePath);
  assert.match(hash, /^sha256:/);
});

test("applyCachedPlanSkips marks matching plans as cached-match", async () => {
  const tempRoot = await createTempWorkspace();
  const config = normalizeCliConfig(
    {
      dryRun: true,
      scope: "daily",
      file: null,
      year: "2026",
      help: false,
    },
    tempRoot,
  );
  const scanResult = await scanContentFiles(config);
  const referenceIndex = await buildReferenceIndex(scanResult.markdownFiles);
  const initialPlanResult = buildArchivePlan(scanResult.imageFiles, referenceIndex, config);
  const processPlan = initialPlanResult.plans.find((plan) => plan.status === "process");

  await fs.mkdir(path.dirname(processPlan.targetStaticPath), { recursive: true });
  await fs.copyFile(processPlan.sourceImagePath, processPlan.targetStaticPath);
  const rewritten = replaceMarkdownImageReference(
    await fs.readFile(processPlan.markdownPath, "utf8"),
    processPlan,
  );
  await fs.writeFile(processPlan.markdownPath, rewritten, "utf8");

  const cacheStore = createEmptyCacheStore();
  cacheStore.items[buildCacheKey(processPlan.sourceImagePath, config.workspaceRoot)] = {
    sourceHash: await computeFileHash(processPlan.sourceImagePath),
    targetPublicSrc: processPlan.targetPublicSrc,
    status: "done",
  };

  const cachedPlanResult = await applyCachedPlanSkips(initialPlanResult, cacheStore, config);
  assert.equal(cachedPlanResult.summary.process, 0);
  assert.equal(cachedPlanResult.summary.skip, 1);
  assert.equal(cachedPlanResult.plans[0].reason, "cached-match");
});

test("CLI entrypoint prints scaffold summary", () => {
  const scriptPath = path.join(workspaceRoot, "scripts", "image-archiver", "daily-image-archiver.mjs");
  const result = spawnSync(
    process.execPath,
    [scriptPath, "--scope", "daily", "--dry-run", "--year", "2026"],
    {
      cwd: workspaceRoot,
      encoding: "utf8",
    },
  );

  assert.equal(result.status, 0);
  assert.match(result.stdout, /Content Image Archiver CLI/);
  assert.match(result.stdout, /Target Scope: daily/);
  assert.match(result.stdout, /Mode: dry-run/);
  assert.match(result.stdout, /Scope: year \(2026\)/);
  assert.match(result.stdout, /Scan Summary/);
  assert.match(result.stdout, /Image Files:/);
  assert.match(result.stdout, /Reference Summary/);
  assert.match(result.stdout, /Plan Summary/);
  assert.match(result.stdout, /Dry Run Report/);
});
