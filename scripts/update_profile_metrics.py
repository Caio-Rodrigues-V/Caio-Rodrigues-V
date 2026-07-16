import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

USERNAME = os.getenv("PROFILE_USERNAME", "Caio-Rodrigues-V")
README_PATH = os.getenv("README_PATH", "README.md")
TOKEN = os.getenv("GITHUB_TOKEN", "")
API = "https://api.github.com"
START = "<!-- LANG_METRICS_START -->"
END = "<!-- LANG_METRICS_END -->"

LANG_COLORS = {
    "Python": "3776AB",
    "Java": "F97316",
    "JavaScript": "F7DF1E",
    "TypeScript": "3178C6",
    "HTML": "E34F26",
    "CSS": "1572B6",
    "SQL": "336791",
    "Shell": "89E051",
    "Dockerfile": "2496ED",
}

LANG_CONTEXT = {
    "Python": "Automacoes, bots, APIs, IA aplicada e scripts operacionais",
    "Java": "Logica, backend, POO e base de programacao",
    "JavaScript": "Interfaces, paineis, interacoes web e integracoes",
    "TypeScript": "Interfaces tipadas, paineis e apps web",
    "HTML": "Estrutura de paginas, prototipos e telas",
    "CSS": "Layout, responsividade e acabamento visual",
    "SQL": "Consultas, dados operacionais, filtros e dashboards",
    "Shell": "Scripts, setup e rotinas de ambiente",
    "Dockerfile": "Ambientes, deploy e empacotamento",
}


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-metrics-updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.headers, __import__("json").loads(response.read().decode("utf-8"))


def paginated(url):
    results = []
    while url:
        headers, data = request_json(url)
        results.extend(data)
        link = headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1:part.find(">")]
        url = next_url
    return results


def language_totals():
    repos = paginated(f"{API}/users/{USERNAME}/repos?type=owner&per_page=100&sort=updated")
    totals = Counter()
    repo_count = 0
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        repo_count += 1
        try:
            _, languages = request_json(repo["languages_url"])
        except Exception as exc:
            print(f"Skipping {repo.get('name')}: {exc}", file=sys.stderr)
            continue
        for language, size in languages.items():
            totals[language] += int(size or 0)
    return totals, repo_count


def badge(label, percent, color):
    value = f"{percent:.1f}%"
    encoded = urllib.parse.quote(value, safe="")
    return f'<img src="https://img.shields.io/badge/{encoded}-{color}?style=flat-square&label=uso&labelColor=111827" alt="{label} {value}" />'


def render_metrics(totals, repo_count):
    total_bytes = sum(totals.values())
    if total_bytes <= 0:
        return "\nSem dados de linguagens encontrados ainda.\n"

    rows = []
    for language, size in totals.most_common(7):
        percent = (size / total_bytes) * 100
        color = LANG_COLORS.get(language, "6B7280")
        context = LANG_CONTEXT.get(language, "Projetos, estudos e evolucao pratica")
        rows.append(f"| {language} | {badge(language, percent, color)} | {context} |")

    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    lines = [
        "",
        "| Linguagem | Uso real nos repos | Onde aplico melhor |",
        "| --- | --- | --- |",
        *rows,
        "",
        f"<sub>Atualizado automaticamente em {updated}, analisando {repo_count} repositorios publicos.</sub>",
        "",
    ]
    return "\n".join(lines)


def update_readme(block):
    with open(README_PATH, "r", encoding="utf-8") as file:
        content = file.read()
    pattern = re.compile(f"{re.escape(START)}.*?{re.escape(END)}", re.DOTALL)
    replacement = f"{START}{block}{END}"
    new_content, count = pattern.subn(replacement, content)
    if count != 1:
        raise RuntimeError("Could not find language metrics markers in README.md")
    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8", newline="\n") as file:
            file.write(new_content)
        print("README metrics updated.")
    else:
        print("README metrics already up to date.")


def main():
    totals, repo_count = language_totals()
    update_readme(render_metrics(totals, repo_count))


if __name__ == "__main__":
    main()
