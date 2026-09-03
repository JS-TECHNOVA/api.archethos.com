/**
 * Dump the frontend's content modules to JSON so the backend seed can be built
 * from the real data rather than a hand transcription.
 *
 * Reads the UI repo, writes only into this scratchpad. Nothing in the UI is
 * modified.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DATA = "d:/NODE/archethos-nextjs/archethos/src/data";
const STAGE = join(HERE, "data");

mkdirSync(STAGE, { recursive: true });

const FILES = [
  "media.js",
  "company.js",
  "services.js",
  "projects.js",
  "gallery.js",
  "journal.js",
  "locations.js",
  "stats.js",
  "studio.js",
  "navigation.js",
];

// `@/data/x` -> `./x.mjs`, and drop the dev-only console warnings that reference
// process.env.
for (const name of FILES) {
  let src = readFileSync(join(DATA, name), "utf8");
  src = src.replace(/from\s+"@\/data\/(\w+)"/g, 'from "./$1.mjs"');
  writeFileSync(join(STAGE, name.replace(/\.js$/, ".mjs")), src, "utf8");
}

const out = {};
for (const name of FILES) {
  const mod = await import(
    pathToFileURL(join(STAGE, name.replace(/\.js$/, ".mjs"))).href
  );
  const key = name.replace(/\.js$/, "");
  out[key] = Object.fromEntries(
    Object.entries(mod).filter(
      ([, value]) => typeof value !== "function" && value !== undefined,
    ),
  );
}

writeFileSync(join(HERE, "site-data.json"), JSON.stringify(out, null, 2), "utf8");

for (const [file, mod] of Object.entries(out)) {
  const counts = Object.entries(mod)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.length : typeof v}`)
    .join(" ");
  console.log(`${file}: ${counts}`);
}
