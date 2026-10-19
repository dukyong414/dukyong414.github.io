import { readFileSync } from "node:fs";

// Cross-language rules shared with editor.py. Counts are not frozen: the
// editor may add or remove papers, talks, and videos as long as English and
// Korean stay aligned.
const en = JSON.parse(readFileSync(new URL("../src/data/en.json", import.meta.url), "utf8"));
const ko = JSON.parse(readFileSync(new URL("../src/data/ko.json", import.meta.url), "utf8"));

const SYNC_KEYS = new Set([
  "id",
  "href",
  "doi",
  "youtubeId",
  "year",
  "venue",
  "event",
  "date",
  "affiliationHref",
  "piHref",
  "orgUrl",
  "url",
]);

const DENY = ["YONHEE", "kQS7nwHt0t0", "kdy0414@"];
const YOUTUBE = /^[A-Za-z0-9_-]{11}$/;
let failed = false;

function assert(condition, message) {
  if (!condition) {
    console.error("FAIL", message);
    failed = true;
  }
}

function stable(value) {
  return JSON.stringify(sortValue(value));
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = sortValue(value[key]);
    return out;
  }
  return value;
}

function titleSynced(parts) {
  if (parts.length !== 4 || parts[3] !== "title") return false;
  if (parts[0] === "publications" && parts[1] === "items") return true;
  if (parts[0] === "talks" && parts[1] === "items") return true;
  if (parts[0] === "research" && parts[1] === "beamtimes") return true;
  return false;
}

function enumSynced(parts) {
  if (parts.length !== 4) return false;
  if (parts[0] === "publications" && parts[1] === "items" && (parts[3] === "kind" || parts[3] === "role")) return true;
  if (parts[0] === "talks" && parts[1] === "items" && parts[3] === "role") return true;
  return parts[0] === "timeline" && parts[1] === "items" && parts[3] === "kind";
}

function authorsPath(parts) {
  return parts.length === 4 && parts[0] === "publications" && parts[1] === "items" && parts[3] === "authors";
}

function shape(a, b, path) {
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object") {
    assert(typeof a === typeof b, `${path} type`);
    return;
  }
  if (Array.isArray(a) || Array.isArray(b)) {
    assert(Array.isArray(a) && Array.isArray(b), `${path} array`);
    if (!Array.isArray(a) || !Array.isArray(b)) return;
    assert(a.length === b.length, `${path} length ${a.length} != ${b.length}`);
    const count = Math.min(a.length, b.length);
    for (let i = 0; i < count; i += 1) shape(a[i], b[i], `${path}[${i}]`);
    return;
  }
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  assert(stable(aKeys.slice().sort()) === stable(bKeys.slice().sort()), `${path} keys`);
  for (const key of aKeys) {
    if (Object.prototype.hasOwnProperty.call(b, key)) shape(a[key], b[key], `${path}.${key}`);
  }
}

function sync(a, b, parts) {
  if (!a || typeof a !== "object") return;
  if (Array.isArray(a)) {
    a.forEach((item, index) => {
      if (Array.isArray(b)) sync(item, b[index], parts.concat(String(index)));
    });
    return;
  }
  if (!b || typeof b !== "object" || Array.isArray(b)) return;
  for (const key of Object.keys(a)) {
    const child = parts.concat(key);
    if (!Object.prototype.hasOwnProperty.call(b, key)) continue;
    if (SYNC_KEYS.has(key) || titleSynced(child) || enumSynced(child) || authorsPath(child)) {
      assert(stable(a[key]) === stable(b[key]), `${child.join(".")} must match`);
    } else {
      sync(a[key], b[key], child);
    }
  }
}

function youtubeIds(node, path, found = []) {
  if (!node || typeof node !== "object") return found;
  if (Array.isArray(node)) {
    node.forEach((item, index) => youtubeIds(item, `${path}[${index}]`, found));
    return found;
  }
  if (typeof node.youtubeId === "string") found.push([`${path}.youtubeId`, node.youtubeId]);
  for (const [key, value] of Object.entries(node)) {
    if (key !== "youtubeId") youtubeIds(value, `${path}.${key}`, found);
  }
  return found;
}

assert(en.lang === "en" && ko.lang === "ko", "lang codes");
assert(en.home === "/" && ko.home === "/ko/", "home paths");
assert(/[가-힣]/.test(JSON.stringify(ko)), "Korean hangul");

const blob = JSON.stringify(en) + JSON.stringify(ko);
for (const needle of DENY) assert(!blob.includes(needle), `blocked text ${needle}`);

shape(en, ko, "$");
sync(en, ko, []);

for (const [path, id] of youtubeIds(en, "en", []).concat(youtubeIds(ko, "ko", []))) {
  assert(YOUTUBE.test(id), `${path} youtube id ${id}`);
}

const names = [];
for (const item of en.publications?.items ?? []) {
  for (const author of item.authors ?? []) names.push(author.name);
}
assert(names.includes("Dukyong Kim"), "name present to bold");

if (failed) process.exit(1);
console.log("content ok");
