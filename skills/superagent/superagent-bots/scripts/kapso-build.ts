#!/usr/bin/env tsx
// Kapso Workflow Build Script
// Compiles all src/*.ts into workflows/<slug>/{workflow.ts, workflow.yaml, definition.json}
// Run with: npx tsx kapso-build.ts
//
// Pitfalls this script handles (see references/kapso-workflow-deployment.md for full context):
//   1. Appends `export default workflow` if missing (kapso push needs it)
//   2. Removes stale workflow.js left over from kapso pull
//   3. Writes metadata as YAML, not JSON
//   4. Skips source files that don't have a default workflow export

import * as fs from "fs";
import * as path from "path";
import YAML from "yaml";

const srcDir = path.join(process.cwd(), "src");
const workflowsDir = path.join(process.cwd(), "workflows");

if (!fs.existsSync(srcDir)) {
  console.error(`❌ Source dir not found: ${srcDir}`);
  process.exit(1);
}

const tsFiles = fs.readdirSync(srcDir).filter(f => f.endsWith(".ts"));
console.log(`📦 Building ${tsFiles.length} workflow(s)...\n`);

for (const file of tsFiles) {
  const tsFile = path.join(srcDir, file);

  // Dynamic import the source — must be ESM
  let mod: any;
  try {
    mod = await import(tsFile);
  } catch (e: any) {
    console.error(`❌ ${file}: import failed — ${e.message}`);
    continue;
  }

  const workflow = mod.default;
  if (!workflow || !workflow.toSourceFiles) {
    console.error(`❌ ${file}: no default export with toSourceFiles() — skip`);
    continue;
  }

  const { metadata, definitionJson } = workflow.toSourceFiles();
  const slug = metadata.slug;
  if (!slug) {
    console.error(`❌ ${file}: metadata.slug missing — skip`);
    continue;
  }

  const slugDir = path.join(workflowsDir, slug);
  fs.mkdirSync(slugDir, { recursive: true });

  // Remove stale workflow.js (from kapso pull --overwrite) so kapso push picks up .ts
  const jsFile = path.join(slugDir, "workflow.js");
  if (fs.existsSync(jsFile)) {
    fs.unlinkSync(jsFile);
  }

  // 1. Write workflow.ts (source with default export appended)
  let source = fs.readFileSync(tsFile, "utf-8");
  if (!source.includes("export default workflow")) {
    source = source.trimEnd() + "\n\nexport default workflow;\n";
  }
  fs.writeFileSync(path.join(slugDir, "workflow.ts"), source);

  // 2. Write workflow.yaml
  fs.writeFileSync(
    path.join(slugDir, "workflow.yaml"),
    YAML.stringify(metadata),
  );

  // 3. Write definition.json
  fs.writeFileSync(
    path.join(slugDir, "definition.json"),
    JSON.stringify(definitionJson, null, 2),
  );

  const nodes = (definitionJson as any).nodes?.length || 0;
  const edges = (definitionJson as any).edges?.length || 0;
  console.log(`   ✅ ${slug}: ${nodes} nodes, ${edges} edges`);
}

console.log(`\n✅ Layout ready. Run: kapso push workflow <slug>`);
