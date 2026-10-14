"""Check public Markdown links, anchors, SVG safety, and README command parity.

Static checks only; not a Markdown/Mermaid renderer or behavior evaluator.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def anchors(content):
    result, seen = set(), {}
    content = re.sub(r'```.*?```', '', content, flags=re.S)
    for title in re.findall(r'^#{1,6}\s+(.+)$', content, re.M):
        base = re.sub(r'[^\w\-\s]', '', title.lower()).replace(' ', '-')
        n = seen.get(base, 0)
        result.add(base if not n else f'{base}-{n}')
        seen[base] = n + 1
    result.update(re.findall(r'<a\s+id="([^"]+)"', content))
    return result


def main():
    docs = sorted([*ROOT.glob('*.md'), *ROOT.glob('docs/*.md')])
    errors, checked = [], 0
    for file in docs:
        content = file.read_text(encoding='utf-8-sig')
        if len(re.findall(r'^```', content, re.M)) % 2:
            errors.append(f'Unbalanced fences: {file.name}')
        for target in re.findall(r'\]\(([^)]+)\)', content):
            if re.match(r'[a-z]+:', target):
                continue
            local, _, fragment = unquote(target).partition('#')
            dest = (file.parent / local).resolve() if local else file
            checked += 1
            if not dest.exists():
                errors.append(f'Missing target: {file.name}: {target}')
            elif fragment and dest.suffix == '.md':
                if fragment not in anchors(dest.read_text(encoding='utf-8-sig')):
                    errors.append(f'Missing anchor: {file.name}: {target}')
        if re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/(?:Users|home)/', content):
            errors.append(f'Local absolute path: {file.name}')
    svgs = sorted(ROOT.glob('assets/**/*.svg'))
    for file in svgs:
        tree = ET.parse(file)
        root = tree.getroot()
        if 'viewBox' not in root.attrib:
            errors.append(f'Missing viewBox: {file.name}')
        names = {e.tag.split('}')[-1] for e in root.iter()}
        if not {'title', 'desc'} <= names:
            errors.append(f'Missing accessible description: {file.name}')
        if names & {'script', 'foreignObject', 'image'}:
            errors.append(f'Active or embedded content: {file.name}')
        for e in root.iter():
            if any(k.startswith('on') or k.endswith('href') for k in e.attrib):
                errors.append(f'Unexpected event or linked content: {file.name}')
    en = (ROOT / 'README.md').read_text(encoding='utf-8-sig')
    cn = (ROOT / 'README_CN.md').read_text(encoding='utf-8-sig')
    for lang in ('powershell', 'bash', 'sh'):
        pattern = rf'```{lang}\n(.*?)```'
        if re.findall(pattern, en, re.S) != re.findall(pattern, cn, re.S):
            errors.append(f'Bilingual command mismatch: {lang}')
    for token in ('204', 'NOT_RUN', 'Quality First', 'Balanced', 'Adaptive', 'Custom'):
        if token not in en or token not in cn:
            errors.append(f'Missing bilingual invariant: {token}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(docs)} documents, {checked} local links/anchors, {len(svgs)} SVGs, bilingual commands')


if __name__ == '__main__':
    main()
