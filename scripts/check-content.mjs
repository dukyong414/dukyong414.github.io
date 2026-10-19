import { readFileSync } from "node:fs";

const en = JSON.parse(readFileSync(new URL("../src/data/en.json", import.meta.url), "utf8"));
const ko = JSON.parse(readFileSync(new URL("../src/data/ko.json", import.meta.url), "utf8"));
let failed = false;

function assert(condition, message) {
  if (!condition) {
    console.error("FAIL", message);
    failed = true;
  }
}

assert(en.lang === "en" && ko.lang === "ko", "lang codes");
assert(/[가-힣]/.test(JSON.stringify(ko)), "Korean hangul");
assert(!JSON.stringify(en).includes("YONHEE") && !JSON.stringify(ko).includes("YONHEE"), "no home address");
assert(!JSON.stringify(en).includes("kQS7nwHt0t0") && !JSON.stringify(ko).includes("kQS7nwHt0t0"), "no music video");
assert(!JSON.stringify(en).includes("kdy0414@"), "no outdated hanyang email");

const required = [
  "6eHbSF8AAAAJ",
  "0000-0002-5665-8317",
  "dukyong-kim-3729a3257",
  "github.com/dukyong414/SMAXI",
  "github.com/dukyong414",
  "fast-am.mech.northwestern.edu",
  "smlab.hanyang.ac.kr",
  "GvaxMWbJm4k",
  "sCgA6VVVTUc",
  "hc3nLJa31L8",
];
const blob = JSON.stringify(en) + JSON.stringify(ko);
for (const needle of required) assert(blob.includes(needle), `missing ${needle}`);

assert(en.publications.items.length === 9, "9 publications");
assert(ko.publications.items.length === 9, "9 ko publications");
en.publications.items.forEach((item, index) => {
  const other = ko.publications.items[index];
  assert(item.id === other.id, `pub id ${item.id}`);
  assert(item.title === other.title, `title translated? ${item.id}`);
  assert(item.href === other.href, `href ${item.id}`);
  assert(item.venue === other.venue, `venue ${item.id}`);
  assert(JSON.stringify(item.authors) === JSON.stringify(other.authors), `authors ${item.id}`);
});

assert(en.talks.items.length === 17 && ko.talks.items.length === 17, "17 talks");
en.talks.items.forEach((item, index) => {
  const other = ko.talks.items[index];
  assert(item.title === other.title && item.date === other.date && item.event === other.event, `talk ${item.id}`);
});

const aescape = en.talks.items.find((item) => item.id === "aescape-2026");
const aescapeKo = ko.talks.items.find((item) => item.id === "aescape-2026");
assert(aescape && aescapeKo, "aescape talk present");
assert(aescape.date === "09.11.2026" && aescape.youtubeId === "GvaxMWbJm4k", "aescape merged");
assert(aescapeKo.youtubeId === "GvaxMWbJm4k" && aescapeKo.date === aescape.date, "aescape ko");
assert(!JSON.stringify(en).includes("09.11.2027") && !JSON.stringify(ko).includes("09.11.2027"), "old aescape year gone");
assert(en.talks.videos.map((video) => video.youtubeId).join() === "sCgA6VVVTUc,hc3nLJa31L8", "smaxi videos");
assert(en.research.beamtimes.length === 7, "7 beamtimes");
en.research.beamtimes.forEach((item, index) => {
  assert(item.doi === ko.research.beamtimes[index].doi, `doi ${item.doi}`);
  assert(item.title === ko.research.beamtimes[index].title, `beam title ${index}`);
});

const names = en.publications.items.flatMap((item) => item.authors.map((author) => author.name));
assert(names.includes("Dukyong Kim"), "name present to bold");

if (failed) process.exit(1);
console.log("content ok");
