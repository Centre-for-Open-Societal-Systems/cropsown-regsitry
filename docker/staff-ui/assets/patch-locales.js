#!/usr/bin/env node
/*
 * Add "om" (Afaan Oromoo) and "ti" (Tigrigna) to the list of supported Next.js locales.
 */
const fs = require("fs");
const path = require("path");

const ROOT = "/app/.next";

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (entry.name.endsWith(".js") || entry.name.endsWith(".json")) yield full;
  }
}

let patched = 0;
for (const file of walk(ROOT)) {
  const before = fs.readFileSync(file, "utf8");
  if (!before.includes('"en","es","fr","am","ar","hi"')) continue;
  const after = before.replaceAll('"en","es","fr","am","ar","hi"', '"en","es","fr","am","ar","hi","om","ti"');
  if (after !== before) {
    fs.writeFileSync(file, after);
    patched += 1;
    console.log("  patched locales in " + file.replace(ROOT + "/", ""));
  }
}

console.log(`Added om and ti locales in ${patched} bundle(s)`);
