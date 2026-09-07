#!/usr/bin/env python3
"""Assemble the Stage 1 review page (HTML artifact) from the exported diagram SVGs.

    python3 tools/build-review-page.py [output.html]

Every diagram SVG in docs/uml/img is embedded as a base64 data URI; the page is a
self-contained review surface (index, per-diagram notes, zoom, comments left on the
artifact reach the author).
"""
import base64
import html
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMG = os.path.join(ROOT, "docs", "uml", "img")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "uml", "review.html")

SECTIONS = [
    ("Аналіз вимог", [
        ("01-use-case", "Діаграма прецедентів", "use case", "каскад: актор → корені → include/extend; усі UC1–UC15, параметри-листки (Ascending/Descending, All files / Only .cpp .png, назви стовпців, .cs as text / .jpg as image), обидва бонуси (drag-and-drop, drag out)"),
    ]),
    ("Високорівневе проєктування", [
        ("15-component", "Діаграма компонентів", "component", "три клієнт/серверні колонки, інтерфейси REST / S3 / SQL, залежності на @minidrive/shared, IPC між процесами Electron"),
        ("16-deployment", "Діаграма розгортання", "deployment", "три вузли-пристрої, Docker Compose у хмарі (caddy, api, web, postgres, minio) і локально, порти та протоколи на шляхах зв'язку"),
    ]),
    ("Деталізоване проєктування — класи", [
        ("02-class-domain", "Доменна модель", "class", "усі атрибути й операції з §3.1 специфікації, композиції (ромб біля цілого), FilePreview → TextPreview/ImagePreview, перелічення, легенда"),
        ("03-class-vopc-sort-filter", "VOPC — сортування та фільтрація (UC5+UC6)", "class · VOPC", "стереотипи «boundary»/«control»/«entity», актор торкається лише boundary, DriveViewModel як control, FileListUtils.sortByName / filterByType, FileDto як entity"),
        ("04-class-server", "Класи сервера (NestJS)", "class", "пакети-модулі Auth/Users/Files/Storage/Prisma, контролери → сервіси, DTO, сутності User / FileEntry"),
        ("05-class-clients", "Класи клієнтів та спільного пакета", "class", "packages/shared (FileListUtils, PreviewFactory, типи), apps/web, apps/desktop (Main / Preload / Renderer), залежності «use»"),
    ]),
    ("Деталізоване проєктування — поведінка", [
        ("06-activity-sync", "Активність: синхронізація (UC14)", "activity", "доріжки User / Renderer / Main / API, розгалуження «folder bound?», fork/join сканування та GET /files, цикл по SyncAction, правила плану у примітці"),
        ("07-activity-upload", "Активність: завантаження / оновлення файлу (UC9, UC10)", "activity", "кнопка або drag-and-drop → валідація 50 MB → JWT → upsert: перезапис (updatedAt, modifiedBy) або створення"),
        ("08-sequence-login", "Послідовність: реєстрація та вхід (UC1, UC2)", "sequence", "opt [new user], alt [valid]/[invalid], POST /auth/register та /auth/login, signJwt, SessionStore.set"),
        ("09-sequence-upload-preview", "Послідовність: завантаження та перегляд вмісту (UC9, UC8)", "sequence", "POST /files → upsert (alt exists/new) → putObject; клік по рядку → createPreview → GET /files/:id/content → PreviewPanel"),
        ("10-sequence-sync", "Послідовність: синхронізація (UC14)", "sequence", "scan + listFiles → computeSyncPlan → loop/alt upload/download/skip → SyncReport; opt FolderWatcher"),
        ("11-communication-sort-filter", "Комунікація: сортування та фільтрація (UC5, UC6)", "communication", "нумеровані повідомлення 1…4, ті самі об'єкти, що й у VOPC (SortControl, FilterControl, DriveViewModel, FileListUtils, FileTable)"),
        ("12-state-session", "Стани: сеанс клієнта", "state", "LoggedOut → Authenticating → LoggedIn {Browsing, Previewing, Uploading, Downloading, Deleting, Syncing}, вихід за logout / 401"),
        ("13-state-file", "Стани: життєвий цикл файлу під час синхронізації", "state", "LocalOnly / RemoteOnly / Synced / ModifiedLocally / ModifiedRemotely / Conflict / Uploading / Downloading; видалення не поширюються"),
        ("14-state-sync", "Стани: сеанс синхронізації (SyncEngine)", "state", "Idle → Scanning → Planning → Transferring → Completed | Failed, PickingFolder, Watching"),
    ]),
]

KIND_CLASS = {"use case": "k-uc", "component": "k-arch", "deployment": "k-arch", "class": "k-class", "class · VOPC": "k-class",
              "activity": "k-beh", "sequence": "k-beh", "communication": "k-beh", "state": "k-state"}


def data_uri(path: str, mime: str) -> str:
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode("ascii")


def main() -> None:
    cards, index, missing = [], [], []
    n = 0
    for section, items in SECTIONS:
        index.append(f'<li class="idx-sec">{html.escape(section)}</li>')
        cards.append(f'<h2 class="sec" id="s{len(cards)}">{html.escape(section)}</h2>')
        for out, title, kind, check in items:
            n += 1
            svg = os.path.join(IMG, out + ".svg")
            png = os.path.join(IMG, out + ".png")
            if os.path.exists(svg):
                src = data_uri(svg, "image/svg+xml")
            elif os.path.exists(png):
                src = data_uri(png, "image/png")
            else:
                missing.append(out)
                src = ""
            index.append(f'<li><a href="#{out}"><span class="num">{n:02d}</span>{html.escape(title)}</a></li>')
            fig = (f'<figure class="paper"><img src="{src}" alt="{html.escape(title)}" loading="lazy" data-zoom></figure>'
                   if src else '<div class="paper missing">Діаграму ще не згенеровано</div>')
            cards.append(f'''
<article class="dia" id="{out}">
  <header>
    <div class="eyebrow"><span class="num">Рис. {n}</span><span class="chip {KIND_CLASS.get(kind, "")}">{html.escape(kind)}</span></div>
    <h3>{html.escape(title)}</h3>
  </header>
  {fig}
  <dl class="meta">
    <dt>Що перевірити</dt><dd>{html.escape(check)}</dd>
    <dt>Файли</dt><dd><code>docs/uml/drawio/{out}.drawio</code> · <code>docs/uml/gen/{out.replace("-", "_")}.py</code> · <code>docs/uml/img/{out}.svg</code></dd>
  </dl>
</article>''')

    page = f'''<title>MiniDrive · UML етап 1</title>
<meta name="description" content="Огляд 16 UML-діаграм етапу 1 проєкту MiniDrive (варіант 4-6) для перевірки та коментарів">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg: #f4f5f8; --paper: #ffffff; --ink: #1c2230; --ink-2: #4a5468; --ink-3: #7b8497;
  --line: #d9dde6; --accent: #3d5a99; --accent-ink: #ffffff;
  --uc: #dae8fc; --uc-ink: #2c4a7d; --arch: #f5f5f5; --arch-ink: #444; --class: #d5e8d4; --class-ink: #2f5d2c;
  --beh: #fff2cc; --beh-ink: #6e5400; --state: #e1d5e7; --state-ink: #4d3a63;
  --sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif; --mono: "IBM Plex Mono", Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #14171d; --paper: #ffffff; --ink: #e8ebf2; --ink-2: #b4bccb; --ink-3: #7f889a; --line: #2c3240; --accent: #8fb0ee; --accent-ink: #14171d;
  --uc: #24344f; --uc-ink: #b9d0f5; --arch: #2a2e36; --arch-ink: #d5d9e0; --class: #23392a; --class-ink: #b7dcb4; --beh: #3e3517; --beh-ink: #f2dc8d; --state: #352a3e; --state-ink: #dccbe8;
}} }}
:root[data-theme="dark"] {{
  --bg: #14171d; --paper: #ffffff; --ink: #e8ebf2; --ink-2: #b4bccb; --ink-3: #7f889a; --line: #2c3240; --accent: #8fb0ee; --accent-ink: #14171d;
  --uc: #24344f; --uc-ink: #b9d0f5; --arch: #2a2e36; --arch-ink: #d5d9e0; --class: #23392a; --class-ink: #b7dcb4; --beh: #3e3517; --beh-ink: #f2dc8d; --state: #352a3e; --state-ink: #dccbe8;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.55 var(--sans); }}
a {{ color: var(--accent); }}
.wrap {{ display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 32px; max-width: 1400px; margin: 0 auto; padding: 32px 24px 80px; }}
@media (max-width: 900px) {{ .wrap {{ grid-template-columns: 1fr; }} nav.idx {{ position: static; }} }}
nav.idx {{ position: sticky; top: 24px; align-self: start; font-size: 13.5px; }}
nav.idx ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }}
nav.idx .idx-sec {{ margin-top: 14px; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); }}
nav.idx a {{ display: flex; gap: 10px; align-items: baseline; text-decoration: none; color: var(--ink-2); padding: 3px 6px; border-radius: 4px; }}
nav.idx a:hover, nav.idx a:focus-visible {{ background: var(--line); color: var(--ink); outline: none; }}
.num {{ font: 500 12px/1 var(--mono); color: var(--ink-3); min-width: 2.4em; font-variant-numeric: tabular-nums; }}
header.top h1 {{ font-size: 28px; font-weight: 600; margin: 0 0 6px; letter-spacing: -.01em; text-wrap: balance; }}
header.top p {{ margin: 0; color: var(--ink-2); max-width: 65ch; }}
.facts {{ display: flex; flex-wrap: wrap; gap: 8px 22px; margin: 16px 0 8px; font-size: 13.5px; color: var(--ink-2); }}
.facts b {{ color: var(--ink); font-weight: 500; }}
h2.sec {{ font-size: 13px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); margin: 44px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }}
article.dia {{ display: grid; gap: 12px; padding: 20px 0 28px; border-bottom: 1px solid var(--line); }}
article.dia header {{ display: grid; gap: 6px; }}
.eyebrow {{ display: flex; gap: 10px; align-items: center; }}
.eyebrow .num {{ font-size: 12px; color: var(--ink-3); }}
article.dia h3 {{ margin: 0; font-size: 20px; font-weight: 600; text-wrap: balance; }}
.chip {{ font: 500 11px/1 var(--mono); letter-spacing: .04em; padding: 5px 8px; border-radius: 999px; background: var(--arch); color: var(--arch-ink); }}
.chip.k-uc {{ background: var(--uc); color: var(--uc-ink); }} .chip.k-class {{ background: var(--class); color: var(--class-ink); }}
.chip.k-beh {{ background: var(--beh); color: var(--beh-ink); }} .chip.k-state {{ background: var(--state); color: var(--state-ink); }}
figure.paper {{ margin: 0; background: var(--paper); border: 1px solid var(--line); border-radius: 6px; padding: 12px; overflow-x: auto; }}
figure.paper img {{ display: block; max-width: 100%; height: auto; cursor: zoom-in; }}
.paper.missing {{ padding: 40px; text-align: center; color: var(--ink-3); background: var(--paper); border: 1px dashed var(--line); border-radius: 6px; }}
dl.meta {{ display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; font-size: 13.5px; }}
dl.meta dt {{ color: var(--ink-3); }} dl.meta dd {{ margin: 0; color: var(--ink-2); }}
code {{ font: 12.5px/1.4 var(--mono); background: var(--line); padding: 1px 5px; border-radius: 3px; color: var(--ink); }}
.zoom {{ position: fixed; inset: 0; background: rgba(10, 12, 18, .92); display: none; overflow: auto; padding: 24px; z-index: 10; cursor: zoom-out; }}
.zoom[open] {{ display: block; }}
.zoom img {{ display: block; margin: 0 auto; background: #fff; padding: 16px; border-radius: 6px; max-width: none; }}
.hint {{ font-size: 13px; color: var(--ink-3); }}
@media (prefers-reduced-motion: no-preference) {{ nav.idx a {{ transition: background .12s ease; }} }}
</style>
<div class="wrap">
  <nav class="idx" aria-label="Зміст">
    <ul>{''.join(index)}</ul>
  </nav>
  <main>
    <header class="top">
      <h1>MiniDrive — UML-специфікація, етап 1</h1>
      <p>Шістнадцять діаграм для системи типу 2 (клієнт віддаленої папки з файлами), варіант 4-6: перегляд <code>.cs</code> як тексту та <code>.jpg</code> як зображення; сортування за назвою; фільтр «усі» / лише <code>.cpp</code>, <code>.png</code>.</p>
      <div class="facts"><span>Діаграм: <b>{n}</b></span><span>Джерело: <b>draw.io</b> (редаговані файли у <code>docs/uml/drawio</code>)</span><span>Генератори: <code>docs/uml/gen</code></span></div>
      <p class="hint">Клік по діаграмі відкриває її в повний розмір. Коментарі, залишені на цій сторінці, потраплять до автора.</p>
    </header>
    {''.join(cards)}
  </main>
</div>
<div class="zoom" id="zoom" role="dialog" aria-label="Діаграма у повний розмір"><img alt=""></div>
<script>
(function () {{
  var z = document.getElementById('zoom'), zi = z.querySelector('img');
  document.querySelectorAll('img[data-zoom]').forEach(function (im) {{
    im.addEventListener('click', function () {{ zi.src = im.src; zi.alt = im.alt; z.setAttribute('open', ''); }});
  }});
  z.addEventListener('click', function () {{ z.removeAttribute('open'); zi.src = ''; }});
  document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape') {{ z.removeAttribute('open'); zi.src = ''; }} }});
}})();
</script>
'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    size = os.path.getsize(OUT)
    print(f"wrote {OUT} ({size / 1e6:.1f} MB); missing diagrams: {missing or 'none'}")


if __name__ == "__main__":
    main()
