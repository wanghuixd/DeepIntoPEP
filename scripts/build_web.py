#!/usr/bin/env python3
"""
Build a static web site that indexes PEP documents from docs/.

Output: web/index.html
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract optional YAML frontmatter. Returns (metadata, body)."""
    if not content.strip().startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    meta: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k == "tags":
                if v.startswith("["):
                    meta[k] = [
                        x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()
                    ]
                else:
                    meta[k] = [x.strip() for x in v.split(",") if x.strip()]
            else:
                meta[k] = v
    body = parts[2].lstrip("\n")
    return meta, body


def _extract_title(md: str) -> str:
    """Extract first # heading as title."""
    for line in md.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return "Untitled"


def _extract_pep_id(filename: str) -> str:
    """Extract PEP identifier from filename, e.g. pep426.md -> PEP 426."""
    m = re.match(r"^(pep\d+)\.md$", filename, re.I)
    if m:
        num = re.search(r"\d+", m.group(1))
        return f"PEP {num.group()}" if num else m.group(1).upper()
    return Path(filename).stem


def collect_peps(docs_dir: Path) -> list[dict]:
    """Collect all PEP markdown files and extract metadata."""
    peps: list[dict] = []
    for path in sorted(docs_dir.glob("*.md")):
        if path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        title = meta.get("title") or _extract_title(body or text)
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        content = body if meta else text
        pep_id = _extract_pep_id(path.name)
        if pep_id not in [t for t in tags if t.startswith("PEP")]:
            tags = [pep_id] + tags
        peps.append(
            {
                "id": path.stem,
                "title": title,
                "tags": tags,
                "body": content,
            }
        )
    return peps


def build_html(peps: list[dict], output_path: Path) -> None:
    """Generate the static HTML with embedded data."""
    data_json = json.dumps(peps, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DeepIntoPep - PEP 提案索引</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {{
      --bg: #fafaf9;
      --bg-sidebar: #f5f5f4;
      --border: #e7e5e4;
      --text: #1c1917;
      --text-muted: #57534e;
      --accent: #44403c;
      --tag-bg: #e7e5e4;
      --code-bg: #f5f5f4;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; height: 100%; }}

    body {{
      font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", serif;
      font-size: 16px;
      line-height: 1.75;
      color: var(--text);
      background: var(--bg);
    }}

    .layout {{
      display: flex;
      height: 100%;
      min-height: 100vh;
    }}

    .sidebar {{
      width: 280px;
      min-width: 280px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border);
      overflow-y: auto;
      padding: 1.5rem 0;
    }}

    .sidebar-title {{
      font-weight: 600;
      font-size: 0.95rem;
      color: var(--text-muted);
      padding: 0 1.25rem 0.75rem;
      letter-spacing: 0.02em;
    }}

    .nav-item {{
      display: block;
      padding: 0.5rem 1.25rem;
      color: var(--text);
      text-decoration: none;
      font-size: 0.9rem;
      border-left: 3px solid transparent;
      transition: background 0.15s, border-color 0.15s;
    }}

    .nav-item:hover {{
      background: rgba(0,0,0,0.04);
    }}

    .nav-item.active {{
      background: rgba(0,0,0,0.06);
      border-left-color: var(--accent);
      font-weight: 500;
    }}

    .main {{
      flex: 1;
      overflow-y: auto;
      padding: 2.5rem 3rem 4rem;
      max-width: 720px;
      margin: 0 auto;
    }}

    .doc-title {{
      font-size: 1.75rem;
      font-weight: 700;
      margin: 0 0 0.5rem;
      line-height: 1.35;
    }}

    .doc-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-bottom: 1.75rem;
    }}

    .doc-tag {{
      font-family: "JetBrains Mono", "SF Mono", monospace;
      font-size: 0.75rem;
      padding: 0.2rem 0.5rem;
      background: var(--tag-bg);
      border-radius: 4px;
      color: var(--text-muted);
    }}

    .doc-body {{
      font-size: 1rem;
    }}

    .doc-body h1 {{ font-size: 1.5rem; margin: 2rem 0 0.75rem; font-weight: 600; }}
    .doc-body h2 {{ font-size: 1.25rem; margin: 1.75rem 0 0.6rem; font-weight: 600; }}
    .doc-body h3 {{ font-size: 1.1rem; margin: 1.5rem 0 0.5rem; font-weight: 600; }}
    .doc-body p {{ margin: 0 0 1rem; }}
    .doc-body ul, .doc-body ol {{ margin: 0 0 1rem; padding-left: 1.5rem; }}
    .doc-body li {{ margin-bottom: 0.35rem; }}
    .doc-body blockquote {{
      margin: 1rem 0;
      padding: 0.5rem 0 0.5rem 1rem;
      border-left: 4px solid var(--border);
      color: var(--text-muted);
    }}
    .doc-body table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
      font-size: 0.9rem;
    }}
    .doc-body th, .doc-body td {{
      border: 1px solid var(--border);
      padding: 0.5rem 0.75rem;
      text-align: left;
    }}
    .doc-body th {{ background: var(--bg-sidebar); font-weight: 600; }}
    .doc-body code {{
      font-family: "JetBrains Mono", "SF Mono", monospace;
      font-size: 0.88em;
      background: var(--code-bg);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
    }}
    .doc-body pre {{
      background: var(--code-bg);
      padding: 1rem;
      border-radius: 6px;
      overflow-x: auto;
      margin: 1rem 0;
      font-size: 0.88rem;
    }}
    .doc-body pre code {{
      background: none;
      padding: 0;
    }}
    .doc-body a {{ color: var(--accent); text-decoration: none; }}
    .doc-body a:hover {{ text-decoration: underline; }}

    .empty-state {{
      color: var(--text-muted);
      font-size: 0.95rem;
      padding: 2rem 0;
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-title">PEP 提案索引</div>
      <nav id="nav"></nav>
    </aside>
    <main class="main">
      <article id="content">
        <div class="empty-state">选择左侧文档查看内容</div>
      </article>
    </main>
  </div>

  <script>
    const PEP_DATA = {data_json};

    const nav = document.getElementById('nav');
    const content = document.getElementById('content');

    marked.setOptions({{
      gfm: true,
      breaks: true,
    }});

    function renderDoc(pep) {{
      content.innerHTML = `
        <h1 class="doc-title">${{pep.title}}</h1>
        <div class="doc-tags">
          ${{pep.tags.map(t => `<span class="doc-tag">${{t}}</span>`).join('')}}
        </div>
        <div class="doc-body">${{marked.parse(pep.body)}}</div>
      `;
    }}

    function initNav() {{
      nav.innerHTML = PEP_DATA.map(pep => `
        <a href="#${{pep.id}}" class="nav-item" data-id="${{pep.id}}">${{pep.title}}</a>
      `).join('');

      nav.querySelectorAll('.nav-item').forEach(el => {{
        el.addEventListener('click', (e) => {{
          e.preventDefault();
          const id = el.dataset.id;
          location.hash = id;
          selectDoc(id);
        }});
      }});
    }}

    function selectDoc(id) {{
      const pep = PEP_DATA.find(p => p.id === id);
      if (pep) {{
        nav.querySelectorAll('.nav-item').forEach(n => {{
          n.classList.toggle('active', n.dataset.id === id);
        }});
        renderDoc(pep);
      }}
    }}

    if (PEP_DATA.length > 0) {{
      initNav();
      const hashId = location.hash.slice(1);
      const initial = hashId ? PEP_DATA.find(p => p.id === hashId) : null;
      if (initial) {{
        selectDoc(initial.id);
      }} else {{
        selectDoc(PEP_DATA[0].id);
      }}
      window.addEventListener('hashchange', () => {{
        const id = location.hash.slice(1);
        if (id) selectDoc(id);
      }});
    }}
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PEP index web site")
    parser.add_argument(
        "--docs",
        type=Path,
        default=_repo_root() / "docs",
        help="Directory containing PEP markdown files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_repo_root() / "web" / "index.html",
        help="Output HTML path",
    )
    args = parser.parse_args()
    peps = collect_peps(args.docs)
    build_html(peps, args.output)
    print(f"Built {len(peps)} PEP(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
