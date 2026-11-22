"""Build the standalone reading page from story.md. Requires Pillow only."""
from pathlib import Path
from html import escape
from urllib.parse import unquote
from PIL import Image, ImageOps, ImageCms
import io
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs'
ASSETS = DEST / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
source = (ROOT / 'story.md').read_text(encoding='utf-8-sig')

def inline(text):
    # The story uses emphasis and strong emphasis; escape all literal HTML.
    tokens = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', text)
    return ''.join('<strong>' + escape(t[2:-2]) + '</strong>' if t.startswith('**') else
                   '<em>' + escape(t[1:-1]) + '</em>' if t.startswith('*') else escape(t)
                   for t in tokens)

images = {}
total_before = total_after = 0
for index, match in enumerate(re.finditer(r'^!\[([^\]]*)\]\(([^\n]+)\)$', source, re.M), 1):
    alt, url = match.groups()
    file = (ROOT / unquote(url)).resolve()
    if not file.is_relative_to(ROOT):
        raise ValueError('Image must be inside the repository')
    with Image.open(file) as original:
        im = ImageOps.exif_transpose(original)
        if im.info.get('icc_profile'):
            im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(im.info['icc_profile'])),
                                          ImageCms.createProfile('sRGB'), outputMode='RGB')
        else:
            im = im.convert('RGB')
        variants = []
        for width in sorted({min(w, im.width) for w in (640, 1000, 1600)}):
            height = round(im.height * width / im.width)
            name = f'scene-{index:02d}-{width}.webp'
            target = ASSETS / name
            im.resize((width, height), Image.Resampling.LANCZOS).save(target, 'WEBP', quality=82, method=6)
            with Image.open(target) as checked:
                checked.load()
                assert checked.size == (width, height)
            variants.append((name, width, height))
            total_after += target.stat().st_size
        total_before += file.stat().st_size
    name, width, height = variants[-1]
    srcset = ', '.join(f'assets/{name} {w}w' for name, w, _ in variants)
    images[url] = dict(alt=alt, name=name, width=width, height=height, srcset=srcset)

def image_markup(item, hero=False):
    sizes = '100vw' if hero else '(max-width: 1040px) calc(100vw - 32px), 1000px'
    attrs = 'fetchpriority="high"' if hero else 'loading="lazy"'
    return (f'<img src="assets/{item["name"]}" srcset="{item["srcset"]}" sizes="{sizes}" '
            f'width="{item["width"]}" height="{item["height"]}" alt="{escape("" if hero else item["alt"], quote=True)}" '
            f'decoding="async" {attrs}>')

blocks = re.split(r'\n\s*\n', source.strip())
chapters = []
body = []
paragraphs = []
title = None
for block in blocks:
    if block.startswith('# '):
        title = block[2:].replace('**', '').strip()
    elif block.startswith('### '):
        heading = block[4:].replace('**', '').strip()
        match = re.fullmatch(r'(\d+)\.\s+(.+)', heading)
        if not match:
            raise ValueError(f'Unexpected chapter heading: {heading}')
        number, name = match.groups()
        if chapters:
            body.append('</section>')
        chapters.append((number, name))
        body.append(f'<section class="chapter" id="chapter-{number}" aria-labelledby="heading-{number}">')
        body.append(f'<h2 id="heading-{number}"><span class="chapter-number">{number.zfill(2)}</span>{escape(name)}</h2>')
    elif block.startswith('!['):
        match = re.fullmatch(r'!\[([^\]]*)\]\(([^\n]+)\)', block)
        if not match:
            raise ValueError('Unsupported image Markdown')
        body.append('<figure class="scene">' + image_markup(images[match[2]]) + '</figure>')
    else:
        if re.match(r'^(#|```|<|\|)', block):
            raise ValueError(f'Unsupported Markdown block: {block[:50]}')
        paragraphs.append(block)
        css = 'dialogue' if block.startswith('—') else 'message' if block.startswith('*') and block.endswith('*') else ''
        body.append(f'<p class="{css}">{inline(block)}</p>')
body.append('</section>')
assert title and chapters and images
nav = '\n'.join(f'<a href="#chapter-{n}"><span>{n.zfill(2)}</span>{escape(name)}</a>' for n, name in chapters)
words = len(re.findall(r'\b[\w’]+\b', ' '.join(paragraphs)))
minutes = max(1, round(words / 180))
template = (ROOT / 'scripts' / 'page.html').read_text(encoding='utf-8')
values = dict(title=escape(title), chapters=str(len(chapters)), minutes=str(minutes),
              navigation=nav, body='\n'.join(body), hero=image_markup(next(iter(images.values())), hero=True))
for key, value in values.items():
    template = template.replace('{{' + key + '}}', value)
assert not re.search(r'\{\{\w+\}\}', template)
(DEST / 'index.html').write_text(template, encoding='utf-8')
(DEST / '.nojekyll').touch()
print(f'{len(chapters)} chapters, {len(paragraphs)} text blocks, {len(images)} illustrations.')
print(f'Original images: {total_before:,} bytes; all responsive WebP variants: {total_after:,} bytes.')
print(f'Built {DEST / "index.html"}')
