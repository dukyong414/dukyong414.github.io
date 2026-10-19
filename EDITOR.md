# 사이트 편집기

코드나 JSON을 열지 않고 글, 사진, 이력서(CV)를 고치는 프로그램입니다. 영어와 한국어를 나란히 보여 줍니다.

## 1. Git 설치

1. <https://git-scm.com/download/win> 을 엽니다.
2. 설치 프로그램을 실행하고, 묻는 것은 기본값으로 넘어갑니다.
3. 설치가 끝나면 시작 메뉴에서 **Command Prompt** 또는 **PowerShell** 을 엽니다.
4. 아래를 입력하고 Enter 를 누릅니다.

```bat
git --version
```

`git version` 으로 시작하는 글이 보이면 된 것입니다.

## 2. Python 확인

이 컴퓨터에는 Python 3.11 이 있으면 됩니다.

```bat
python --version
```

`Python 3.11` 이상이 보여야 합니다. `Python was not found` 가 나오거나 Microsoft Store 가 열리면 <https://www.python.org/downloads/> 에서 Python 3.11 을 설치하고, 첫 화면의 **Add python.exe to PATH** 를 체크한 뒤 다시 확인합니다.

사진을 바꿀 때 JPEG 이외의 파일(PNG 등)을 쓰거나, 프로필 사진의 WebP·AVIF 를 다시 만들려면 Pillow 를 한 번만 설치합니다. 없어도 JPEG 교체는 됩니다.

```bat
pip install pillow
```

## 3. 사이트 폴더 받기

아래 명령을 한 줄씩 실행합니다. 이미 받아 둔 폴더가 있으면 그 폴더로 들어가 `git checkout main` 과 `git pull` 만 하면 됩니다.

```bat
cd %USERPROFILE%\Documents
git clone https://github.com/dukyong414/dukyong414.github.io.git
cd dukyong414.github.io
```

## 4. 편집기 실행

사이트 폴더 안에서:

```bat
python editor.py
```

브라우저가 열립니다. 주소는 `http://127.0.0.1:8765/` 처럼 이 컴퓨터 안에서만 열립니다. 검은 창은 끄지 마세요. 그 창이 편집기입니다. 끝나려면 그 창에서 `Ctrl+C` 를 누릅니다.

브라우저가 안 열리면 검은 창에 나온 주소를 브라우저 주소창에 붙여 넣습니다.

## 5. 고치기

왼쪽 메뉴에서 항목을 고릅니다.

- 영어와 한국어가 나란히 있습니다. 긴 글은 큰 입력칸입니다.
- **영어·한국어 동일** 표시가 있는 칸은 논문 제목, DOI, 날짜, 유튜브 id, 링크처럼 두 언어가 같아야 하는 값입니다. 한쪽을 고치면 다른 쪽도 같이 바뀝니다. 논문 제목은 원어 그대로 둡니다.
- 논문, 발표, 수상, 경력, 영상 목록은 **추가**, **위로**, **아래로**, **삭제** 가 있습니다. 순서를 바꾸거나 지울 때도 두 언어가 함께 움직입니다.
- 영상은 유튜브 주소 전체를 붙여 넣습니다. `https://www.youtube.com/watch?v=…` 또는 `https://youtu.be/…` 모두 됩니다. 저장되는 것은 11글자 id 뿐입니다.
- **사진과 CV** 에서 미리보기를 보고 **교체** 또는 **Delete / 삭제** 를 누릅니다. 프로필 사진처럼 페이지에 고정된 사진은 삭제되지 않습니다. 어디 쓰이는지 안내가 나오고, 바꾸려면 **교체** 를 씁니다. 글에만 들어 있는 사진은 확인 창에서 영어·한국어 항목을 함께 지울 수 있습니다. 삭제한 파일은 지워지지 않고 `.editor-backups/deleted-images/` 로 옮겨지며, 같은 화면의 **복원** 으로 되돌립니다. **사진 추가** 로 새 사진을 올릴 수 있습니다. 프로필 사진을 교체하면 사이트가 쓰는 JPEG, WebP, AVIF 를 다시 만듭니다. CV 의 PDF 와 Word 파일도 같은 화면에서 바꿉니다.

고친 뒤에는 오른쪽 위의 **저장** 을 누릅니다. `Ctrl+S` 도 같습니다. 이전 내용은 `.editor-backups` 폴더에 시간별로 남습니다. 이 폴더는 GitHub 에 올라가지 않습니다.

## 6. 미리보기

**미리보기** 는 이 컴퓨터에 Node.js 가 있을 때만 동작합니다. 없으면 버튼을 눌렀을 때 안내가 나옵니다. 그때는 저장한 뒤 **게시** 하면 됩니다. 게시가 GitHub 에 올라가면 1–2분 뒤 <https://dukyong414.github.io/> 가 바뀝니다.

## 7. 게시

1. **게시** 를 누릅니다.
2. 바뀐 파일 목록을 확인합니다.
3. **지금 게시** 를 누릅니다.

Git 이 이 폴더의 `main` 브랜치에 커밋하고 GitHub 로 푸시합니다. 처음이면 GitHub 로그인 창이 뜰 수 있습니다. 로그인을 끝내면 다시 **게시** 를 누릅니다.

사이트가 몇 분이 지나도 안 바뀌면 GitHub 저장소의 **Settings → Pages → Source** 가 **GitHub Actions** 인지 확인합니다.

### 자주 나오는 안내

- Git 이 없다는 문구: 1단계를 다시 합니다.
- 복제본이 아니라는 문구: 3단계의 `git clone` 으로 받은 폴더에서 `python editor.py` 를 실행합니다.
- main 이 아니라는 문구: 사이트 폴더에서 `git checkout main` 을 실행한 뒤 편집기를 다시 엽니다.
- 이름을 알려 달라는 문구: 한 번만 실행합니다.

```bat
git config --global user.name "Dukyong Kim"
git config --global user.email "본인@이메일"
```

---

# Site editor

A small program for changing the words, photos, and CV without opening JSON or code. English and Korean are shown side by side.

## 1. Install Git

1. Open <https://git-scm.com/download/win>.
2. Run the installer and keep the default options.
3. Open **Command Prompt** or **PowerShell** from the Start menu.
4. Run:

```bat
git --version
```

You should see a line that starts with `git version`.

## 2. Check Python

Python 3.11 or newer is enough.

```bat
python --version
```

If Windows says Python was not found, or the Microsoft Store opens, install Python 3.11 from <https://www.python.org/downloads/> and check **Add python.exe to PATH** on the first screen.

Pillow is optional. Install it once if you want to drop in a PNG (or another format) and have the portrait rebuilt as JPEG, WebP, and AVIF. Replacing a photo with a JPEG works without it.

```bat
pip install pillow
```

## 3. Clone the site

Run these one at a time. If you already have the folder, open it and run `git checkout main` and `git pull` instead.

```bat
cd %USERPROFILE%\Documents
git clone https://github.com/dukyong414/dukyong414.github.io.git
cd dukyong414.github.io
```

## 4. Start the editor

Inside the site folder:

```bat
python editor.py
```

A browser opens to an address like `http://127.0.0.1:8765/`. That address works only on this computer. Leave the black window open; it is the editor. Press `Ctrl+C` in that window when you are finished.

If the browser does not open, copy the address from the black window into the address bar.

## 5. Edit

Pick a section in the left menu.

- English and Korean sit side by side. Long text uses a large box.
- A field marked **Same in EN and KO** is a value that must match: paper titles, DOIs, dates, YouTube ids, and links. Editing one side updates the other. Leave paper and talk titles in their original language.
- Publications, talks, awards, experience, and videos have **Add**, **Up**, **Down**, and **Remove**. Reordering or deleting moves both languages together.
- For a video, paste the whole YouTube URL (`https://www.youtube.com/watch?v=…` or `https://youtu.be/…`). Only the 11-character id is stored.
- **Photos and CV** shows a thumbnail, **Replace**, and **Delete / 삭제**. A photo that is built into the page, such as the portrait, cannot be deleted: the dialog lists where it is used and tells you to replace it. A photo that appears only in the text can be deleted together with those English and Korean entries. Deleted files are moved to `.editor-backups/deleted-images/`, not erased, and **Restore** on the same screen puts them back. **Add photo** uploads a new image. Replacing the portrait regenerates the JPEG, WebP, and AVIF files the site serves. The CV PDF and Word file are replaced on the same screen.

Click **Save** (or press `Ctrl+S`). The previous files are copied into `.editor-backups`, one folder per save. That folder is not pushed to GitHub.

## 6. Preview

**Preview** runs only when Node.js is installed. If it is not, the button explains that. Save and then **Publish** instead. A minute or two after the push, <https://dukyong414.github.io/> updates.

## 7. Publish

1. Click **Publish**.
2. Read the list of changed files.
3. Click **Publish now**.

Git commits on the `main` branch of this folder and pushes to GitHub. The first time, a GitHub sign-in window may appear. Finish signing in, then click **Publish** again.

If the live site does not change after a few minutes, set the GitHub repository **Settings → Pages → Source** to **GitHub Actions**.

### Messages you might see

- Git is not installed: repeat step 1.
- This folder is not a git clone: run `python editor.py` inside the folder from `git clone` in step 3.
- Not on main: in the site folder run `git checkout main`, then start the editor again.
- Git needs your name: run this once.

```bat
git config --global user.name "Dukyong Kim"
git config --global user.email "you@example.com"
```
