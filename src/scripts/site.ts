const root = document.documentElement;

const themeBtn = document.querySelector<HTMLButtonElement>("[data-theme-toggle]");

function syncThemeButton() {
  if (!themeBtn) return;
  const dark = root.dataset.theme === "dark";
  themeBtn.setAttribute("aria-pressed", dark ? "true" : "false");
  const label = dark ? themeBtn.dataset.labelLight : themeBtn.dataset.labelDark;
  if (label) themeBtn.setAttribute("aria-label", label);
}

themeBtn?.addEventListener("click", () => {
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("theme", next);
  syncThemeButton();
});
syncThemeButton();

const scheme = window.matchMedia("(prefers-color-scheme: dark)");
scheme.addEventListener("change", (event) => {
  if (localStorage.getItem("theme")) return;
  root.dataset.theme = event.matches ? "dark" : "light";
  syncThemeButton();
});

document.querySelectorAll<HTMLAnchorElement>("[data-set-lang]").forEach((link) => {
  link.addEventListener("click", () => {
    const lang = link.dataset.setLang;
    if (lang) localStorage.setItem("lang", lang);
  });
});

document.querySelectorAll<HTMLElement>("[data-filter-group]").forEach((group) => {
  const targetSel = group.dataset.filterGroup;
  if (!targetSel) return;
  const target = document.querySelector(targetSel);
  if (!target) return;
  const buttons = group.querySelectorAll<HTMLButtonElement>("[data-filter]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const filter = button.dataset.filter ?? "all";
      buttons.forEach((item) => {
        item.setAttribute("aria-pressed", item === button ? "true" : "false");
      });
      target.querySelectorAll<HTMLElement>("[data-kind]").forEach((item) => {
        const kind = item.dataset.kind ?? "";
        const show =
          filter === "all" ||
          kind === filter ||
          (filter === "presenting" && kind !== "coauthor");
        item.hidden = !show;
      });
    });
  });
});

document.querySelectorAll<HTMLButtonElement>("[data-youtube]").forEach((button) => {
  button.addEventListener("click", () => {
    const id = button.dataset.youtube;
    const title = button.dataset.title ?? "YouTube video";
    if (!id) return;
    const frame = button.parentElement;
    if (!frame) return;
    const iframe = document.createElement("iframe");
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1`;
    iframe.title = title;
    iframe.allow =
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    frame.replaceChildren(iframe);
  });
});

const navLinks = [...document.querySelectorAll<HTMLAnchorElement>('nav a[href^="#"]')];
const sections = navLinks
  .map((link) => document.querySelector<HTMLElement>(link.getAttribute("href") ?? ""))
  .filter((section): section is HTMLElement => Boolean(section));

if (sections.length && "IntersectionObserver" in window) {
  const spy = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      navLinks.forEach((link) => link.removeAttribute("aria-current"));
      const active = navLinks.find((link) => link.getAttribute("href") === `#${visible.target.id}`);
      active?.setAttribute("aria-current", "true");
    },
    { rootMargin: "-45% 0px -48% 0px", threshold: [0, 0.2, 0.6] },
  );
  sections.forEach((section) => spy.observe(section));
}

const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
if (!motion.matches && "IntersectionObserver" in window) {
  const reveal = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        reveal.unobserve(entry.target);
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -8% 0px" },
  );
  document.querySelectorAll(".reveal").forEach((el) => reveal.observe(el));
  window.setTimeout(() => {
    document.querySelectorAll(".reveal:not(.is-in)").forEach((el) => el.classList.add("is-in"));
  }, 1600);
} else {
  document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-in"));
}
