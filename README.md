# Dukyong Kim

Personal academic site for Dukyong Kim, Ph.D. student in mechanical engineering at Northwestern University (Fast-AM Laboratory, Professor Tao Sun). English and Korean. Static files, so it can be hosted later without a server.

The site is published at <https://dukyong414.github.io/>.

To change the words, photos, or CV without editing code, use the local editor. Step-by-step instructions in Korean and English are in [EDITOR.md](EDITOR.md).

```bash
python editor.py
```

## Preview

Requires Node.js 22.22 or newer.

```bash
npm install
npm run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). Korean is at [http://127.0.0.1:43123/ko/](http://127.0.0.1:43123/ko/).

```bash
npm run check   # confirm the two languages still match
npm run build   # writes the static site to dist/
npm run preview # serves dist/ on the same port
```

## Edit the words

The editor in [EDITOR.md](EDITOR.md) writes these files for you. If you edit them by hand, all visible copy lives in two files:

- `src/data/en.json` — English
- `src/data/ko.json` — Korean

Keep these aligned when you add a paper, talk, or link:

- publication and talk **titles**, venues, dates, author lists, and URLs (titles stay in the original language in both files)
- YouTube ids
- DOIs

Then run `npm run check`. It fails if a title or link drifted between the languages.

Images are in `public/images/`. The downloadable CV is `public/cv/Dukyong-Kim-CV.pdf` and `public/cv/Dukyong-Kim-CV.docx`.

The language toggle remembers a choice in the browser. The theme toggle follows the system setting until someone picks light or dark, then remembers that choice.

Paths are root-absolute (`/`, `/ko/`), which fits a user site or a custom domain. For a GitHub *project* site, set `base` in `astro.config.mjs` before building.
