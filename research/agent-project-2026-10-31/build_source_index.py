"""Index report URLs and check document consistency; no network requests."""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


root = Path(__file__).resolve().parent
frontier_path = root / "04-frontier-and-harness.md"
marker = "<!-- generated-source-references -->"
frontier = frontier_path.read_text(encoding="utf-8").split(marker)[0].rstrip()
refs = {}
for match in re.finditer(r"^\| (F\d{2}) \| (.*?) \|", frontier, re.MULTILINE):
    link = re.search(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", match[2])
    if link:
        refs[match[1]] = (link[1], link[2])
definitions = "\n".join(f"[{key}]: {url}" for key, (_, url) in refs.items())
frontier_path.write_text(f"{frontier}\n\n{marker}\n{definitions}\n", encoding="utf-8")

sources = {}
local_links = []
replacement_characters = []
row_counts = {}
evidence_counts = {"A": 0, "B": 0}
link_pattern = re.compile(r"\[([^\]\n]*)\]\(([^\s)]+)\)")
for path in sorted(root.glob("*.md")):
    content = path.read_text(encoding="utf-8")
    if "\ufffd" in content:
        replacement_characters.append(path.name)
    for prefix in ("CN", "G", "O", "F"):
        ids = re.findall(rf"^\| ({prefix}\d{{2}}) \|", content, re.MULTILINE)
        if ids:
            row_counts[f"{path.name}:{prefix}"] = len(set(ids))
    if path.name.startswith(("01-", "02-")):
        for line in content.splitlines():
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) > 5 and re.fullmatch(r"CN\d{2}", cells[1]):
                evidence_counts[cells[5]] += 1
            elif len(cells) > 4 and re.fullmatch(r"G\d{2}", cells[1]):
                evidence = "B" if cells[1] in {"G31", "G32"} else cells[4][0]
                evidence_counts[evidence] += 1
    for line_no, line in enumerate(content.splitlines(), start=1):
        for match in link_pattern.finditer(line):
            title, url = match.groups()
            if url.startswith(("https://", "http://")):
                item = sources.setdefault(url, {"url": url, "domain": urlsplit(url).netloc,
                                                "titles": [], "occurrences": []})
                if title not in item["titles"]:
                    item["titles"].append(title)
                item["occurrences"].append({"file": path.name, "line": line_no})
            elif not url.startswith("#"):
                local_links.append((path.name, line_no, unquote(url.split("#")[0])))

index = {
    "access_date": "2026-10-31",
    "note": "URL inventory extracted from reports; may include leads, inaccessible pages and historical sources. Evidence grades remain in the reports. No automated live URL validation.",
    "unique_urls": len(sources),
    "sources": sorted(sources.values(), key=lambda entry: (entry["domain"], entry["url"])),
}
(root / "sources.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
missing_local = [item for item in local_links if not (root / item[2]).exists()
                 and item[2] != "audit.json"]
short_refs = set(re.findall(r"\[(F\d{2})\](?![:(])", frontier))
audit = {
    "access_date": "2026-10-31",
    "row_counts": row_counts,
    "jd_evidence_counts": evidence_counts,
    "frontier_reference_definitions": len(refs),
    "unresolved_frontier_references": sorted(short_refs - refs.keys()),
    "missing_local_links": missing_local,
    "unicode_replacement_character_files": replacement_characters,
    "unique_url_count": len(sources),
    "external_url_status_checked": False,
    "agent_project_implemented_or_benchmarked": False,
}
(root / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, ensure_ascii=False, indent=2))
if missing_local or replacement_characters or short_refs - refs.keys():
    raise SystemExit("Document consistency check failed")
