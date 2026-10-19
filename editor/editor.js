/* Browser UI for editor.py. Sync rules match editor.py and scripts/check-content.mjs. */

const SYNC_KEYS = new Set([
  "id", "href", "doi", "youtubeId", "year", "venue", "event", "date",
  "affiliationHref", "piHref", "orgUrl", "url",
]);
const LONG_KEYS = new Set([
  "lede", "dek", "description", "summary", "body", "detail", "caption", "cvNote",
  "footer", "paragraphs", "points", "activities", "projects", "approaches",
]);
const ENUMS = {
  kind: ["journal", "conference", "education", "employment", "teaching", "service"],
  role: ["first", "coauthor", "oral", "poster"],
};

const I18N = {
  en: {
    product: "Site editor",
    save: "Save",
    preview: "Preview",
    publish: "Publish",
    saved: "All changes saved",
    unsaved: "Unsaved changes",
    clean: "No unsaved changes",
    add: "Add",
    remove: "Remove",
    up: "Up",
    down: "Down",
    open: "Edit",
    close: "Close",
    untitled: "Untitled",
    synced: "Same in EN and KO",
    english: "English",
    korean: "한국어",
    removeConfirm: "Remove this entry from both languages?",
    saveFailed: "Could not save.",
    previewStarting: "Starting the preview…",
    publishing: "Publishing…",
    published: "Published. The live site updates in a minute or two.",
    attach: "Paste a YouTube URL",
    attachBtn: "Attach video",
    addVideo: "Add a video from a YouTube URL",
    addVideoBtn: "Add video",
    badUrl: "That is not a YouTube link.",
    replace: "Replace",
    photos: "Photos",
    cv: "CV files",
    current: "Open current file",
    optionalPillow: "Optional. Pillow rebuilds the portrait as JPEG, WebP, and AVIF.",
    publishTitle: "Publish to the live site?",
    publishHelp: "These files will be committed and pushed to the main branch. GitHub may ask you to sign in.",
    nothing: "Nothing to publish. Save a change first.",
    message: "Commit message",
    cancel: "Cancel",
    confirm: "Publish now",
    otherFiles: "Other changed files in this folder will be left uncommitted.",
    equal: "Equally contributed",
    corresponding: "Corresponding author",
    name: "Name",
  },
  ko: {
    product: "사이트 편집기",
    save: "저장",
    preview: "미리보기",
    publish: "게시",
    saved: "저장했습니다",
    unsaved: "저장하지 않은 변경",
    clean: "저장하지 않은 변경 없음",
    add: "추가",
    remove: "삭제",
    up: "위로",
    down: "아래로",
    open: "편집",
    close: "접기",
    untitled: "제목 없음",
    synced: "영어·한국어 동일",
    english: "English",
    korean: "한국어",
    removeConfirm: "두 언어에서 이 항목을 삭제할까요?",
    saveFailed: "저장하지 못했습니다.",
    previewStarting: "미리보기를 시작하는 중…",
    publishing: "게시하는 중…",
    published: "게시했습니다. 1–2분 뒤 실제 사이트에 반영됩니다.",
    attach: "유튜브 주소 붙여넣기",
    attachBtn: "영상 연결",
    addVideo: "유튜브 주소로 영상 추가",
    addVideoBtn: "영상 추가",
    badUrl: "유튜브 주소가 아닙니다.",
    replace: "교체",
    photos: "사진",
    cv: "CV 파일",
    current: "현재 파일 열기",
    optionalPillow: "선택 사항. Pillow가 프로필 사진을 JPEG, WebP, AVIF로 다시 만듭니다.",
    publishTitle: "실제 사이트에 게시할까요?",
    publishHelp: "아래 파일을 main 브랜치에 올리고 GitHub로 푸시합니다. GitHub 로그인 창이 뜰 수 있습니다.",
    nothing: "게시할 변경이 없습니다. 먼저 저장하세요.",
    message: "커밋 메시지",
    cancel: "취소",
    confirm: "지금 게시",
    otherFiles: "그 밖의 변경 파일은 커밋하지 않습니다.",
    equal: "공동 기여",
    corresponding: "교신 저자",
    name: "이름",
  },
};

const SECTIONS = [
  { id: "hero", paths: ["hero"], en: "Home", ko: "첫 화면" },
  { id: "files", paths: [], en: "Photos and CV", ko: "사진과 CV", files: true },
  { id: "about", paths: ["about", "media"], en: "About", ko: "소개" },
  { id: "research", paths: ["research"], en: "Research", ko: "연구" },
  { id: "labs", paths: ["lab", "pastLab"], en: "Labs", ko: "연구실" },
  {
    id: "publications",
    paths: ["publications"],
    en: "Publications",
    ko: "논문",
    hint: {
      en: "Titles, venues, links, DOIs, and authors stay the same in both languages. Add, remove, or reorder a paper here.",
      ko: "제목, 학술지, 링크, DOI, 저자는 두 언어가 같습니다. 여기서 논문을 추가·삭제·순서 변경하세요.",
    },
  },
  {
    id: "talks",
    paths: ["talks"],
    en: "Talks and videos",
    ko: "발표와 영상",
    hint: {
      en: "Talk titles, events, dates, and YouTube ids stay the same in both languages. Paste a full YouTube URL; only the id is saved.",
      ko: "발표 제목, 행사, 날짜, 유튜브 id는 두 언어가 같습니다. 유튜브 주소 전체를 붙여 넣으면 id만 저장됩니다.",
    },
  },
  { id: "awards", paths: ["awards"], en: "Awards", ko: "수상" },
  { id: "timeline", paths: ["timeline"], en: "Experience", ko: "경력" },
  { id: "skills", paths: ["skills"], en: "Skills", ko: "기술" },
  { id: "contact", paths: ["contact", "footer"], en: "Contact", ko: "연락" },
  {
    id: "interface",
    paths: ["meta", "nav", "ui"],
    en: "Button labels",
    ko: "버튼 문구",
    hint: {
      en: "Short labels for buttons and menus. You rarely need to change these.",
      ko: "버튼과 메뉴의 짧은 문구입니다. 자주 바꿀 필요는 없습니다.",
    },
  },
];

const state = { en: null, ko: null };
const openState = new Map();
let uiLang = "en";
let dirty = false;
let toastTimer = 0;

function t(key) {
  return I18N[uiLang][key] || I18N.en[key] || key;
}

function labelFor(key) {
  const text = String(key).replace(/([A-Z])/g, " $1").replace(/[_-]/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function isSynced(parts) {
  const key = parts[parts.length - 1];
  if (SYNC_KEYS.has(key)) return true;
  if (parts.length === 4 && parts[3] === "title") {
    if (parts[0] === "publications" && parts[1] === "items") return true;
    if (parts[0] === "talks" && parts[1] === "items") return true;
    if (parts[0] === "research" && parts[1] === "beamtimes") return true;
  }
  if (parts.length === 4 && parts[0] === "publications" && parts[1] === "items" && (parts[3] === "kind" || parts[3] === "role")) return true;
  if (parts.length === 4 && parts[0] === "talks" && parts[1] === "items" && parts[3] === "role") return true;
  if (parts.length === 4 && parts[0] === "timeline" && parts[1] === "items" && parts[3] === "kind") return true;
  return false;
}

function isAuthors(parts) {
  return parts.length === 4 && parts[0] === "publications" && parts[1] === "items" && parts[3] === "authors";
}

function isLong(key, parentKey, value) {
  if (LONG_KEYS.has(key) || LONG_KEYS.has(parentKey)) return true;
  return value.length > 96 || value.includes("\n");
}

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function markDirty() {
  dirty = true;
  paintState();
}

function paintState() {
  const node = document.getElementById("state");
  node.textContent = dirty ? t("unsaved") : t("clean");
  node.classList.toggle("dirty", dirty);
}

function toast(text) {
  const node = document.getElementById("toast");
  node.textContent = text;
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"), 3200);
}

function extractYoutubeId(text) {
  const raw = String(text || "").trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(raw)) return raw;
  try {
    const url = new URL(raw);
    let host = url.hostname.toLowerCase().replace(/^www\./, "");
    if (host.startsWith("m.")) host = host.slice(2);
    const parts = url.pathname.split("/").filter(Boolean);
    if (host === "youtu.be" && /^[A-Za-z0-9_-]{11}$/.test(parts[0] || "")) return parts[0];
    if (host === "youtube.com" || host === "music.youtube.com" || host === "youtube-nocookie.com") {
      const video = url.searchParams.get("v") || "";
      if (/^[A-Za-z0-9_-]{11}$/.test(video)) return video;
      for (const marker of ["embed", "shorts", "live", "v"]) {
        const index = parts.indexOf(marker);
        if (index >= 0 && /^[A-Za-z0-9_-]{11}$/.test(parts[index + 1] || "")) return parts[index + 1];
      }
    }
  } catch (_error) {
    return null;
  }
  return null;
}

function normalizeLocal(node) {
  if (Array.isArray(node)) {
    node.forEach(normalizeLocal);
    return;
  }
  if (!node || typeof node !== "object") return;
  if (node.equal === false) delete node.equal;
  if (node.corresponding === false) delete node.corresponding;
  for (const key of ["youtubeId", "doi", "orgUrl"]) {
    if (node[key] === "") delete node[key];
  }
  for (const value of Object.values(node)) normalizeLocal(value);
}

function emptyValue(value) {
  if (typeof value === "string") return "";
  if (typeof value === "boolean") return false;
  if (typeof value === "number") return 0;
  if (Array.isArray(value)) return [];
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, inner] of Object.entries(value)) out[key] = emptyValue(inner);
    return out;
  }
  return "";
}

function blankItem(key, list) {
  const sample = list.find((item) => item && typeof item === "object");
  if (typeof list[0] === "string") return "";
  if (!sample) {
    if (key === "authors") return { name: "" };
    if (key === "links") return { label: "", href: "" };
    if (key === "videos") return { youtubeId: "", title: "", detail: "" };
    return "";
  }
  const keys = [];
  for (const item of list) {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      for (const name of Object.keys(item)) if (!keys.includes(name)) keys.push(name);
    }
  }
  const blank = {};
  for (const name of keys) {
    const example = list.map((item) => item && item[name]).find((value) => value !== undefined);
    if (name === "kind" || name === "role") blank[name] = example ?? "";
    else if (name === "id") blank[name] = `new-${Date.now().toString(36)}`;
    else blank[name] = emptyValue(example);
  }
  return blank;
}

function summary(item) {
  if (!item || typeof item !== "object") return String(item || "");
  return item.title || item.name || item.label || item.id || item.value || item.youtubeId || "";
}

function move(enList, koList, index, direction) {
  const next = index + direction;
  if (next < 0 || next >= enList.length) return;
  [enList[index], enList[next]] = [enList[next], enList[index]];
  [koList[index], koList[next]] = [koList[next], koList[index]];
  markDirty();
  render();
}

function removeAt(enList, koList, index) {
  if (!window.confirm(t("removeConfirm"))) return;
  enList.splice(index, 1);
  koList.splice(index, 1);
  markDirty();
  render();
}

function actionButton(text, onClick, className) {
  const button = el("button", className || "btn tiny");
  button.type = "button";
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function setText(owner, key, value, mirror) {
  let next = value;
  if (key === "youtubeId") {
    const extracted = extractYoutubeId(value);
    if (extracted) next = extracted;
  }
  owner[key] = next;
  if (mirror) mirror[key] = next;
  markDirty();
  return next;
}

function controlFor(owner, key, parentKey, onValue) {
  const current = owner[key] ?? "";
  if (typeof current === "boolean" || key === "equal" || key === "corresponding") {
    const label = el("label", "check");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(owner[key]);
    input.addEventListener("change", () => onValue(input.checked));
    label.append(input, document.createTextNode(key === "corresponding" ? t("corresponding") : t("equal")));
    return label;
  }
  if (ENUMS[key] && ENUMS[key].includes(String(current))) {
    const select = document.createElement("select");
    for (const option of ENUMS[key]) {
      const node = document.createElement("option");
      node.value = option;
      node.textContent = option;
      if (option === current) node.selected = true;
      select.append(node);
    }
    select.addEventListener("change", () => onValue(select.value));
    return select;
  }
  const long = isLong(key, parentKey, String(current));
  const input = document.createElement(long ? "textarea" : "input");
  if (!long) input.type = "text";
  input.value = current;
  input.addEventListener("input", () => {
    const written = onValue(input.value);
    if (written !== input.value) input.value = written;
  });
  return input;
}

function renderSynced(enParent, koParent, key) {
  const wrap = el("div", "field");
  const label = el("div", "label");
  label.textContent = labelFor(key);
  const badge = el("span", "badge");
  badge.textContent = t("synced");
  label.append(badge);
  wrap.append(label);
  wrap.append(controlFor(enParent, key, "", (value) => setText(enParent, key, value, koParent)));
  return wrap;
}

function renderPair(enParent, koParent, key) {
  const wrap = el("div", "field");
  const label = el("div", "label");
  label.textContent = labelFor(key);
  wrap.append(label);
  const cols = el("div", "cols");
  for (const [lang, owner] of [[t("english"), enParent], [t("korean"), koParent]]) {
    const col = el("div", "col");
    const span = document.createElement("span");
    span.textContent = lang;
    col.append(span);
    col.append(controlFor(owner, key, "", (value) => setText(owner, key, value)));
    cols.append(col);
  }
  wrap.append(cols);
  return wrap;
}

function renderAuthors(enItem, koItem) {
  const wrap = el("div", "list");
  const label = el("div", "label");
  label.textContent = "Authors";
  const badge = el("span", "badge");
  badge.textContent = t("synced");
  label.append(badge);
  wrap.append(label);
  const mirror = () => {
    koItem.authors = structuredClone(enItem.authors);
    markDirty();
  };
  enItem.authors.forEach((author, index) => {
    const row = el("div", "item");
    const head = el("div", "item-head");
    const name = document.createElement("input");
    name.type = "text";
    name.value = author.name || "";
    name.placeholder = t("name");
    name.addEventListener("input", () => {
      author.name = name.value;
      mirror();
    });
    head.append(name);
    head.append(actionButton(t("up"), () => move(enItem.authors, koItem.authors, index, -1)));
    head.append(actionButton(t("down"), () => move(enItem.authors, koItem.authors, index, 1)));
    head.append(actionButton(t("remove"), () => removeAt(enItem.authors, koItem.authors, index), "btn tiny danger"));
    row.append(head);
    const checks = el("div", "row-actions");
    for (const flag of ["equal", "corresponding"]) {
      const box = el("label", "check");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = Boolean(author[flag]);
      input.addEventListener("change", () => {
        if (input.checked) author[flag] = true;
        else delete author[flag];
        mirror();
      });
      box.append(input, document.createTextNode(flag === "equal" ? t("equal") : t("corresponding")));
      checks.append(box);
    }
    row.append(checks);
    wrap.append(row);
  });
  wrap.append(actionButton(t("add"), () => {
    enItem.authors.push({ name: "" });
    mirror();
    render();
  }));
  return wrap;
}

function renderNode(enVal, koVal, parts, key, enParent, koParent) {
  if (isAuthors(parts)) return renderAuthors(enParent, koParent);
  if (isSynced(parts) && (typeof enVal !== "object" || enVal === null)) {
    return renderSynced(enParent, koParent, key);
  }
  if (Array.isArray(enVal) && Array.isArray(koVal)) return renderList(enVal, koVal, parts, key);
  if (enVal && typeof enVal === "object" && koVal && typeof koVal === "object") {
    const box = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = labelFor(key);
    box.append(legend);
    renderObject(enVal, koVal, parts, box);
    return box;
  }
  if (enParent && koParent && key) return renderPair(enParent, koParent, key);
  const note = el("p", "hint");
  note.textContent = String(enVal ?? "");
  return note;
}

function renderObject(enObj, koObj, parts, mount) {
  for (const key of Object.keys(enObj)) {
    if (key === "lang" || key === "home") continue;
    if (!Object.prototype.hasOwnProperty.call(koObj, key)) continue;
    mount.append(renderNode(enObj[key], koObj[key], parts.concat(key), key, enObj, koObj));
  }
}

function renderList(enList, koList, parts, key) {
  const wrap = el("div", "list");
  const label = el("div", "label");
  label.textContent = labelFor(key);
  wrap.append(label);
  if (parts.join(".") === "talks.videos") wrap.append(videoAdder(enList, koList));
  const objects = enList.some((item) => item && typeof item === "object");
  const collapse = objects && enList.length >= 4 && Object.keys(enList.find((item) => item && typeof item === "object") || {}).length >= 4;
  enList.forEach((item, index) => {
    const path = `${parts.join(".")}.${index}`;
    if (typeof item === "string" || typeof koList[index] === "string") {
      const row = el("div", "string-row");
      for (const [lang, list] of [[t("english"), enList], [t("korean"), koList]]) {
        const col = el("div", "col");
        const span = document.createElement("span");
        span.textContent = lang;
        col.append(span, controlFor(list, String(index), key, (value) => {
          list[index] = value;
          markDirty();
          return value;
        }));
        row.append(col);
      }
      const actions = el("div", "row-actions");
      actions.append(actionButton(t("up"), () => move(enList, koList, index, -1)));
      actions.append(actionButton(t("down"), () => move(enList, koList, index, 1)));
      actions.append(actionButton(t("remove"), () => removeAt(enList, koList, index), "btn tiny danger"));
      row.append(actions);
      wrap.append(row);
      return;
    }
    const card = el("article", collapse && !isOpen(path) ? "item closed" : "item");
    const head = el("div", "item-head");
    const title = document.createElement("strong");
    title.textContent = summary(item) || t("untitled");
    head.append(title);
    if (collapse) {
      head.append(actionButton(isOpen(path) ? t("close") : t("open"), () => {
        openState.set(path, !isOpen(path));
        render();
      }));
    }
    head.append(actionButton(t("up"), () => move(enList, koList, index, -1)));
    head.append(actionButton(t("down"), () => move(enList, koList, index, 1)));
    head.append(actionButton(t("remove"), () => removeAt(enList, koList, index), "btn tiny danger"));
    card.append(head);
    const body = el("div", "item-body");
    if (parts[0] === "talks" && parts[1] === "items" && !Object.prototype.hasOwnProperty.call(item, "youtubeId")) {
      body.append(attachVideo(item, koList[index]));
    }
    renderObject(item, koList[index], parts.concat(String(index)), body);
    card.append(body);
    wrap.append(card);
  });
  wrap.append(actionButton(t("add"), () => {
    const blank = blankItem(key, enList);
    enList.push(blank);
    koList.push(structuredClone(blank));
    markDirty();
    render();
  }));
  return wrap;
}

function isOpen(path) {
  if (!openState.has(path)) openState.set(path, path.endsWith(".0"));
  return openState.get(path);
}

function videoAdder(enList, koList) {
  const row = el("div", "adder");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "https://www.youtube.com/watch?v=…";
  row.append(input);
  row.append(actionButton(t("addVideoBtn"), () => {
    const id = extractYoutubeId(input.value);
    if (!id) {
      toast(t("badUrl"));
      return;
    }
    const item = { youtubeId: id, title: "", detail: "" };
    enList.push(structuredClone(item));
    koList.push(structuredClone(item));
    input.value = "";
    markDirty();
    render();
  }));
  const hint = el("p", "hint");
  hint.textContent = t("addVideo");
  const wrap = el("div");
  wrap.append(hint, row);
  return wrap;
}

function attachVideo(enItem, koItem) {
  const row = el("div", "adder");
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = t("attach");
  row.append(input);
  row.append(actionButton(t("attachBtn"), () => {
    const id = extractYoutubeId(input.value);
    if (!id) {
      toast(t("badUrl"));
      return;
    }
    enItem.youtubeId = id;
    koItem.youtubeId = id;
    markDirty();
    render();
  }));
  return row;
}

function renderFiles(mount) {
  const section = el("section", "section");
  section.id = "sec-files";
  const heading = document.createElement("h2");
  heading.textContent = uiLang === "ko" ? "사진과 CV" : "Photos and CV";
  section.append(heading);
  const hint = el("p", "hint");
  hint.textContent = uiLang === "ko"
    ? "프로필 사진은 JPEG, WebP, AVIF 세 가지로 저장됩니다. 다른 사진은 JPEG 한 장입니다."
    : "The portrait is stored as JPEG, WebP, and AVIF. Each other photo is a single JPEG.";
  section.append(hint);
  fetch("/api/status").then((response) => response.json()).then((info) => {
    if (!info.pillow) {
      const note = el("p", "note");
      note.textContent = `${t("optionalPillow")} ${info.pillowHint[uiLang]}`;
      section.insertBefore(note, section.querySelector(".grid") || null);
    }
  }).catch(() => {});
  const grid = el("div", "grid");
  section.append(grid);
  const cvTitle = document.createElement("h3");
  cvTitle.textContent = t("cv");
  section.append(cvTitle);
  const cvBox = el("div");
  section.append(cvBox);
  mount.append(section);
  fetch("/api/files").then((response) => response.json()).then((data) => {
    for (const image of data.images) {
      const card = el("figure", "shot");
      const img = document.createElement("img");
      img.alt = image.label[uiLang] || image.label.en;
      img.src = `/media/images/${encodeURIComponent(image.thumb)}?v=${image.mtime}`;
      const caption = document.createElement("figcaption");
      caption.textContent = image.label[uiLang] || image.label.en;
      const files = document.createElement("p");
      files.textContent = image.files.join(", ");
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.className = "file-input";
      input.addEventListener("change", () => {
        const file = input.files && input.files[0];
        if (!file) return;
        replaceFile(`/api/replace-image?id=${encodeURIComponent(image.id)}`, file, () => {
          img.src = `/media/images/${encodeURIComponent(image.thumb)}?v=${Date.now()}`;
        });
      });
      const button = el("button", "btn");
      button.type = "button";
      button.textContent = t("replace");
      button.addEventListener("click", () => input.click());
      card.append(img, caption, files, button, input);
      grid.append(card);
    }
    for (const cv of data.cvs) {
      const row = el("div", "cv-row");
      const link = document.createElement("a");
      link.href = `/media/cv/${encodeURIComponent(cv.name)}?v=${cv.mtime}`;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = `${cv.name} · ${t("current")}`;
      const input = document.createElement("input");
      input.type = "file";
      input.className = "file-input";
      input.accept = cv.kind === "pdf" ? "application/pdf,.pdf" : ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      input.addEventListener("change", () => {
        const file = input.files && input.files[0];
        if (file) replaceFile(`/api/replace-cv?kind=${cv.kind}`, file);
      });
      const button = el("button", "btn");
      button.type = "button";
      button.textContent = t("replace");
      button.addEventListener("click", () => input.click());
      row.append(link, button, input);
      cvBox.append(row);
    }
  }).catch(() => {
    const note = el("p", "hint");
    note.textContent = "Could not load images.";
    grid.append(note);
  });
}

function replaceFile(url, file, after) {
  fetch(url, { method: "POST", body: file }).then((response) => response.json()).then((data) => {
    if (!data.ok) {
      toast(data.error ? data.error[uiLang] : t("saveFailed"));
      return;
    }
    const note = (data.notes || []).map((item) => item[uiLang]).filter(Boolean).join(" ");
    toast(note || t("saved"));
    if (after) after();
  }).catch(() => toast(t("saveFailed")));
}

function render() {
  const y = window.scrollY;
  const main = document.getElementById("main");
  const nav = document.getElementById("nav");
  main.replaceChildren();
  nav.replaceChildren();
  document.getElementById("product").textContent = t("product");
  document.getElementById("save").textContent = t("save");
  document.getElementById("preview").textContent = t("preview");
  document.getElementById("publish").textContent = t("publish");
  document.getElementById("lang-en").setAttribute("aria-pressed", uiLang === "en" ? "true" : "false");
  document.getElementById("lang-ko").setAttribute("aria-pressed", uiLang === "ko" ? "true" : "false");
  document.documentElement.lang = uiLang === "ko" ? "ko" : "en";
  paintState();
  for (const section of SECTIONS) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = section[uiLang];
    button.addEventListener("click", () => {
      document.getElementById(`sec-${section.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", `#${section.id}`);
    });
    if (location.hash === `#${section.id}`) button.setAttribute("aria-current", "true");
    nav.append(button);
    if (section.files) {
      renderFiles(main);
      continue;
    }
    const block = el("section", "section");
    block.id = `sec-${section.id}`;
    const heading = document.createElement("h2");
    heading.textContent = section[uiLang];
    block.append(heading);
    if (section.hint) {
      const hint = el("p", "hint");
      hint.textContent = section.hint[uiLang];
      block.append(hint);
    }
    for (const path of section.paths) {
      const enVal = state.en[path];
      const koVal = state.ko[path];
      if (typeof enVal === "string") {
        block.append(renderPair(state.en, state.ko, path));
      } else {
        const group = el("div");
        if (section.paths.length > 1) {
          const sub = document.createElement("h3");
          sub.textContent = labelFor(path);
          group.append(sub);
        }
        renderObject(enVal, koVal, [path], group);
        block.append(group);
      }
    }
    main.append(block);
  }
  window.scrollTo(0, y);
}

async function load() {
  const response = await fetch("/api/content");
  const data = await response.json();
  state.en = data.en;
  state.ko = data.ko;
  dirty = false;
  render();
  if (location.hash) {
    document.getElementById(`sec-${location.hash.slice(1)}`)?.scrollIntoView();
  }
}

async function save() {
  normalizeLocal(state.en);
  normalizeLocal(state.ko);
  const response = await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ en: state.en, ko: state.ko }),
  });
  const data = await response.json();
  if (!data.ok) {
    const lines = (data.errors || [data.error]).filter(Boolean).map((item) => item[uiLang] || item.en || String(item));
    const box = el("div", "errors");
    box.textContent = lines.join(" ");
    document.getElementById("main").prepend(box);
    toast(t("saveFailed"));
    return false;
  }
  dirty = false;
  render();
  toast(t("saved"));
  return true;
}

async function preview() {
  toast(t("previewStarting"));
  const response = await fetch("/api/preview", { method: "POST" });
  const data = await response.json();
  if (!data.ok) {
    window.alert(data.error[uiLang]);
    return;
  }
  window.open(data.url, "site-preview");
}

function publishable(line) {
  const path = line.slice(3).trim();
  return (
    path === "src/data/en.json" ||
    path === "src/data/ko.json" ||
    path === "src/components/Page.astro" ||
    path.startsWith("public/images/") ||
    path.startsWith("public/cv/") ||
    path === "public/images" ||
    path === "public/cv"
  );
}

async function publish() {
  if (dirty) {
    const ok = await save();
    if (!ok) return;
  }
  const response = await fetch("/api/changes");
  const data = await response.json();
  if (!data.ok && data.error) {
    window.alert(data.error[uiLang]);
    return;
  }
  if (data.error) {
    window.alert(data.error[uiLang]);
    return;
  }
  const files = (data.files || []).filter(publishable);
  const others = (data.files || []).filter((line) => !publishable(line));
  const back = document.getElementById("modal");
  const modal = el("div", "modal");
  modal.setAttribute("role", "dialog");
  const heading = document.createElement("h2");
  heading.textContent = t("publishTitle");
  const help = el("p", "hint");
  help.textContent = files.length ? t("publishHelp") : t("nothing");
  modal.append(heading, help);
  if (files.length) {
    const list = document.createElement("ul");
    for (const line of files) {
      const item = document.createElement("li");
      item.textContent = line.trim();
      list.append(item);
    }
    modal.append(list);
    if (others.length) {
      const extra = el("p", "hint");
      extra.textContent = t("otherFiles");
      modal.append(extra);
    }
    const label = el("label", "field");
    label.textContent = t("message");
    const input = document.createElement("input");
    input.type = "text";
    input.value = "Update site content";
    label.append(input);
    modal.append(label);
  }
  const actions = el("div", "actions");
  actions.append(actionButton(t("cancel"), () => {
    back.hidden = true;
    back.replaceChildren();
  }));
  if (files.length) {
    const go = actionButton(t("confirm"), async () => {
      go.disabled = true;
      toast(t("publishing"));
      const result = await fetch("/api/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true, message: modal.querySelector("input").value }),
      });
      const payload = await result.json();
      back.hidden = true;
      back.replaceChildren();
      if (!payload.ok) {
        window.alert(payload.error[uiLang]);
        return;
      }
      toast(t("published"));
    }, "btn primary");
    actions.append(go);
  }
  modal.append(actions);
  back.replaceChildren(modal);
  back.hidden = false;
}

function boot() {
  const params = new URLSearchParams(location.search);
  if (params.get("lang") === "ko" || (!params.get("lang") && navigator.language.toLowerCase().startsWith("ko"))) {
    uiLang = "ko";
  }
  document.getElementById("lang-en").addEventListener("click", () => {
    uiLang = "en";
    render();
  });
  document.getElementById("lang-ko").addEventListener("click", () => {
    uiLang = "ko";
    render();
  });
  document.getElementById("save").addEventListener("click", () => save());
  document.getElementById("preview").addEventListener("click", () => preview());
  document.getElementById("publish").addEventListener("click", () => publish());
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      save();
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });
  load().catch(() => {
    document.getElementById("main").textContent = "Could not load the site content.";
  });
}

if (typeof document !== "undefined") boot();
