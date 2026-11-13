#!/usr/bin/env python3
"""
Regenerate features/BUTTONS.md -- the lookup table of every <button> in index.html.

    python3 features/extract_buttons.py

Line numbers in BUTTONS.md go stale the moment you edit index.html, so run this
after every cut. The hand-written verdict files (01-*.md .. 20-*.md,
duplicate-controls.md, clipboard-sprawl.md) are NOT touched -- those are yours.

What it finds, for each button:
  - the inline onclick handler, or
  - the addEventListener('click', ...) / .onclick = ... binding found elsewhere,
    including the `const btn = document.getElementById('x')` alias pattern
  - whether the button ships display:none
  - whether its only job is .click()ing another button (proxy)
  - which feature owns it, by the RULES table below

A button that comes out as `unclassified` is either new or genuinely homeless.
Add a rule for it, or delete it.
"""
import re, os, sys, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, 'index.html')

# feature slug -> regex matched against id + label + onclick + handlers + title.
# First match wins, so order matters: narrow prefixes before broad words.
RULES = [
 ('game-sources',      r'fetchChesscomGames|fetchLichessGames|openChesscomGameById|fetch-games-btn|fetch-lichess-btn|open-game-btn'),
 ('supabase-games',    r'\bsb[A-Z]\w*'),
 ('puzzles-transfer',  r'lnXfer'),
 ('supabase-lines',    r'\bln[A-Z]\w*'),
 ('puzzles-save',      r'\bpz[A-Z]\w*|PuzzleSaveModal'),
 ('print-cards',       r'\bpp[A-Z]\w*|ppLoadFile'),
 ('pgn-library',       r'\bplStep|plToggle|plExportJson|plJsonInput|plFolderInput'),
 ('sheets-drive',      r'gdrive|gnSignInBtn|gnRecentBtn'),
 ('what-went-wrong',   r'\bmm[A-Z]\w*'),
 ('mistake-hop',       r'\bmst[A-Z]\w*'),
 ('practice',          r'practice'),
 ('coach-ai',          r'coachPgn|ChessCoachChat|aiComment|setAiProvider|coachpgn-btn'),
 ('variations',        r'addVar2|AddVar2|oneLine|OneLine|insertPastedVariation|analyzeForVariation'
                       r'|addVariationToPgn|fillMissingVariations|playOut|playout|buildLichessPlayout'
                       r'|copyLichessFromPos|clearVariationResult|cycleVarBtn|clearVariationsBtn'
                       r'|exitVariationToBranch|insert-variation-btn|add-variation-btn'
                       r'|analyze-variation-btn|fill-variations-btn|fenLichess|insert-variation-input'),
 ('study-tool-report', r'Report|report|board2|fileSection|prevVariant|nextVariant|parseAnalysisReport'
                       r'|loadReportSection|loadHighlightedText|Preloaded|appendByOpening|editViewToggle'
                       r'|pasteIntoReport|loadClipboardPgn|updateReportWithPgn|getEvalForLoadedPgn'
                       r'|analyzeLoadedGame|copyEvalsForPaste|loadPgnFromHighlight|loadFenVariantFromHighlight'
                       r'|getEvalBtn'),
 ('fen-export',        r'fenQueue|copyExportedFen|exportFen|ExportFen|downloadBoardImages|loadFenBtn'
                       r'|fenColorToggle|submitLoadFenModal|analyzeFen|fenExportModal|loadFenModal'),
 ('text-view',         r'TextView|textView|viewTextBtn'),
 ('move-comment',      r'MoveComment|moveComment|insertPastedComment|toggleCoachBubbles|coachNoteBtn'
                       r'|addCommentBtn|insert-comment-input'),
 ('typed-move',        r'applyTypedMove|TypedMove|typedMove|applyCastle|showCastleMenu|castleBtn'
                       r'|startStockfishGame|startStockfishFromPosition|getTypedChess|board2Compact'
                       r'|copyTypedStatus'),
 ('core-board',        r'loadPgnToBoard|analyzeGame|copyPgnToClipboard|downloadPgn|toggleChessSound'
                       r'|toggleBoardBorder|openHintsModal|hintsModal|clearResults|flip_board2'
                       r'|board2PrevMove|board2NextMove|loadCurrentBtn|copyPgnBtn'
                       r'|toggleMoveTable|toggleAddVarBtn|toggleNavBtnsBtn|showOpeningToast'
                       r'|toggleChatBtn|loadAndAnalyze|lichessLinks|showOpening'),
]

NOISE = {'if','for','while','return','function','setTimeout','typeof','String','Number','alert'}


def extract(src):
    """Every <button> in src, as dicts. Handles multi-line open tags."""
    lines = src.split('\n')
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1

    def lineno(pos):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    out = []
    for m in re.finditer(r'<button\b', src):
        i, q = m.end(), None
        while i < len(src):                      # end of open tag, quote-aware
            c = src[i]
            if q:
                if c == q:
                    q = None
            elif c in '"\'':
                q = c
            elif c == '>':
                break
            i += 1
        tag = src[m.start():i + 1]
        close = src.find('</button>', i)
        inner = src[i + 1:close] if close != -1 else ''

        def attr(name):
            # quoted HTML attr, then unquoted JSX brace expression
            for pat in (name + r'\s*=\s*"([^"]*)"', name + r"\s*=\s*'([^']*)'",
                        name + r'\s*=\s*\{([^}]*)\}'):
                mm = re.search(pat, tag)
                if mm:
                    return mm.group(1)
            return ''

        # JSX uses onClick={...}; plain HTML uses onclick="..."
        onclick = attr('onclick') or attr('onClick')
        hs = [h for h in re.findall(r'\b([a-zA-Z_$][\w$]*)\s*\(', onclick) if h not in NOISE]
        n = lineno(m.start())
        raw = lines[n - 1]
        px = re.search(r"getElementById\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\.click\(\)", onclick)
        out.append(dict(
            line=n, id=attr('id'), title=attr('title')[:140], onclick=onclick[:160],
            label=re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', '', inner)).strip()[:70],
            handlers=hs[:4], hidden=('display: none' in raw or 'display:none' in raw),
            proxy_for=px.group(1) if px else None, jsx=False,
        ))

    # Buttons inside <script type="text/babel"> are React -- they are wired by
    # JSX onClick, so the addEventListener resolver will never find them.
    for m in re.finditer(r'<script[^>]*type\s*=\s*["\']text/babel["\'][^>]*>', src):
        a = lineno(m.end())
        end = src.find('</script>', m.end())
        b = lineno(end) if end != -1 else len(lines)
        for btn in out:
            if a <= btn['line'] <= b:
                btn['jsx'] = True
    return out, lines


# DOM/builtin methods that show up inside an onclick but are not the feature's
# handler -- e.g. onclick="document.getElementById('x').click()".
DOM_NOISE = {
    'getElementById', 'querySelector', 'querySelectorAll', 'click', 'focus', 'blur',
    'stopPropagation', 'preventDefault', 'writeText', 'readText', 'then', 'catch',
    'setItem', 'getItem', 'removeItem', 'replace', 'open', 'trim', 'toLowerCase',
    'toUpperCase', 'push', 'join', 'split', 'parse', 'stringify', 'gradient',
}

# Keywords the handler-name regex can capture when the listener is an inline
# closure: `addEventListener('click', function() {...})`. Not handler names.
ANON = {'function', 'async', 'await', 'new'}


def resolve(btns, lines):
    """Fill in handlers for buttons wired by addEventListener instead of onclick."""
    alias = {}
    for l in lines:
        for m in re.finditer(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
                             r"document\.getElementById\(\s*['\"]([^'\"]+)['\"]", l):
            alias.setdefault(m.group(1), m.group(2))
    bind = {}
    for n, l in enumerate(lines, 1):
        for m in re.finditer(r"getElementById\(\s*['\"]([^'\"]+)['\"]\s*\)\s*"
                             r"\.addEventListener\(\s*['\"]click['\"]\s*,\s*([A-Za-z_$][\w$]*)?", l):
            nm = m.group(2)
            bind.setdefault(m.group(1), (n, '(inline fn)' if (not nm or nm in ANON) else nm))
        for m in re.finditer(r"\b([A-Za-z_$][\w$]*)\.addEventListener\(\s*['\"]click['\"]\s*,\s*"
                             r"([A-Za-z_$][\w$]*)?", l):
            eid = alias.get(m.group(1))
            if eid:
                nm = m.group(2)
                bind.setdefault(eid, (n, '(inline fn)' if (not nm or nm in ANON) else nm))
        for m in re.finditer(r"getElementById\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\.onclick\s*=\s*"
                             r"([A-Za-z_$][\w$]*)?", l):
            nm = m.group(2)
            bind.setdefault(m.group(1), (n, '(inline fn)' if (not nm or nm in ANON) else nm))
    for b in btns:
        if not b['handlers'] and b['id'] and b['id'] in bind:
            ln, fn = bind[b['id']]
            b['handlers'] = ['%s @%d' % (fn, ln)]
    return btns


def classify(btns, lines):
    for b in btns:
        blob = ' '.join([b['id'], b['label'], b['onclick'], ' '.join(b['handlers']),
                         b['proxy_for'] or '', b['title']])
        b['feature'] = next((s for s, rx in RULES if re.search(rx, blob)), None)
        b['guessed'] = False

    # A button with no identifying text of its own -- built inside a template
    # literal, or a JSX button whose handler is a closure. Inherit the feature
    # from the nearest owning code above it, and mark it a guess with "~".
    for b in btns:
        if b['feature']:
            continue
        # The <script type="text/babel"> block is the Coach Chat React
        # component, end to end. Do not walk out of it looking for a rule --
        # it reuses sbReportAccessCode, which would drag in supabase-games.
        if b['jsx']:
            b['feature'], b['guessed'] = 'coach-ai', True
            continue
        for n in range(b['line'] - 1, max(0, b['line'] - 400), -1):
            hit = next((s for s, rx in RULES if re.search(rx, lines[n - 1])), None)
            if hit:
                b['feature'], b['guessed'] = hit, True
                break
        else:
            b['feature'] = 'unclassified'
    return btns


# ---------------------------------------------------------------------------
# --trace : everything you must know before deleting one button
# ---------------------------------------------------------------------------

def strip_code(s):
    """Blank out string/template/comment contents so brace counting is honest."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in '"\'`':
            q, i = c, i + 1
            while i < n:
                if s[i] == '\\':
                    i += 2
                    continue
                if s[i] == q:
                    i += 1
                    break
                i += 1
            out.append('""')
            continue
        if c == '/' and i + 1 < n and s[i + 1] == '/':
            break
        if c == '/' and i + 1 < n and s[i + 1] == '*':
            j = s.find('*/', i + 2)
            i = n if j == -1 else j + 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def block_extent(lines, start, max_lines=600):
    """From 1-indexed `start`, return the last line of the brace-balanced block.

    Rough -- it counts braces outside strings and comments. Good enough for a
    report you read before deleting, not good enough to delete from blindly.
    """
    depth, seen, end = 0, False, start
    for n in range(start, min(len(lines), start + max_lines) + 1):
        code = strip_code(lines[n - 1])
        for ch in code:
            if ch == '{':
                depth += 1
                seen = True
            elif ch == '}':
                depth -= 1
        end = n
        if seen and depth <= 0:
            return n
    return end


def find_defs(lines, name):
    """Where a handler is defined. Returns [(line, kind, last_line)]."""
    pats = [
        (r'\bfunction\s+' + re.escape(name) + r'\s*\(', 'function'),
        (r'\b(?:const|let|var)\s+' + re.escape(name) + r'\s*=\s*(?:async\s*)?(?:function|\()', 'const fn'),
        (r'\bwindow\.' + re.escape(name) + r'\s*=\s*(?:async\s*)?(?:function|\()', 'window fn'),
    ]
    out = []
    for n, l in enumerate(lines, 1):
        code = strip_code(l)
        for rx, kind in pats:
            if re.search(rx, code):
                out.append((n, kind, block_extent(lines, n)))
                break
    return out


def trace(btns, lines, needle):
    """Print the blast radius of one button. Returns 0, or 1 if not found."""
    hits = [b for b in btns if b['id'] == needle]
    if not hits:
        nl = needle.lower()
        hits = [b for b in btns if nl in html.unescape(b['label']).lower()]
    if not hits:
        print(f"no button matches {needle!r} by id or label.")
        print("Look it up in features/BUTTONS.md, or rerun with no arguments to rebuild it.")
        return 1
    if len(hits) > 1:
        print(f"{len(hits)} buttons match {needle!r} -- tracing each.\n")

    for b in hits:
        safe, warn = [], []
        print("=" * 72)
        label = html.unescape(b['label']) or '(no label)'
        tags = []
        if b['hidden']:
            tags.append('display:none')
        if b['jsx']:
            tags.append('jsx')
        print(f"{b['id'] or '(no id)'}  \"{label}\"  [{b['feature']}]"
              + (f"  ({', '.join(tags)})" if tags else ""))
        print("=" * 72)
        print(f"  element        index.html:{b['line']}")
        safe.append(str(b['line']))

        # A display:none button is only dead if nothing ever reveals it.
        if b['hidden'] and b['id']:
            shown = [n for n, l in enumerate(lines, 1)
                     if b['id'] in l and re.search(r"display\s*=\s*['\"](?!none)", l)]
            # also catch alias vars pointing at this id
            for n, l in enumerate(lines, 1):
                m = re.search(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
                              r"document\.getElementById\(\s*['\"]" + re.escape(b['id']) + r"['\"]", l)
                if m:
                    var = m.group(1)
                    shown += [k for k, ll in enumerate(lines, 1)
                              if re.search(r'\b' + re.escape(var) + r'\b', ll)
                              and re.search(r"display\s*=\s*['\"](?!none)", ll)]
            if shown:
                warn.append(f"hidden, but REVEALED by JS at {sorted(set(shown))} -- it is in use, not dead")
            else:
                print("  reveal         never -- no display assignment makes it visible")

        if b['proxy_for']:
            print(f"  proxies to     #{b['proxy_for']}  (this button only .click()s that one)")

        # Where is this element fetched by id? Each site is either the click
        # binding (safe to delete with the button) or a read from somewhere
        # else (the updateReportBtn trap -- it goes null and throws).
        reads, alias_binds = [], []
        if b['id']:
            idrx = r"getElementById\(\s*['\"]" + re.escape(b['id']) + r"['\"]"
            reads = [n for n, l in enumerate(lines, 1) if re.search(idrx, l)]
            for n in reads:
                m = re.search(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*document\." + idrx,
                              lines[n - 1])
                if not m:
                    continue
                var = m.group(1)
                # Alias names like `btn` recur all over the file, so only count
                # an addEventListener inside this declaration's own block.
                stop = min(block_extent(lines, n), n + 60)
                for k in range(n, stop + 1):
                    if re.search(r'\b' + re.escape(var) + r'\.addEventListener\(\s*[\'"]click',
                                 lines[k - 1]):
                        alias_binds.append((n, k))
                        break
            for n, l in enumerate(lines, 1):
                if re.search(idrx, l) and ('.addEventListener' in l or '.onclick' in l):
                    print(f"  binding        index.html:{n}  (direct)")
            for decl, bind in alias_binds:
                end = block_extent(lines, decl)
                # a `// Load Current -- ...` style comment above the block is
                # part of the dead code; pull it in so it does not get orphaned
                top = decl
                while top > 1 and lines[top - 2].strip().startswith('//'):
                    top -= 1
                print(f"  binding        index.html:{bind}  (alias declared {decl})")
                print(f"  block          index.html:{top}-{end}   <-- "
                      + ("comment + " if top < decl else "") + "const + if + addEventListener")
                safe.append(f"{top}-{end}")

        # named handlers: are they shared?
        if b['proxy_for'] and all(h.split(' @')[0].strip() in DOM_NOISE for h in b['handlers']):
            print("  handler        none of its own -- it just forwards the click")
            print(f"                 trace the real one:  --trace {b['proxy_for']}")
            b = dict(b, handlers=[])
        for h in b['handlers']:
            name = h.split(' @')[0].strip()
            if name in DOM_NOISE:
                continue
            if not name or name == '(inline fn)' or not re.match(r'^[A-Za-z_$][\w$]*$', name):
                print(f"  handler        {h}   (anonymous closure -- nothing else can call it)")
                continue
            defs = find_defs(lines, name)
            dtxt = ', '.join(f"{d}-{e} ({k})" for d, k, e in defs) or 'not found'
            print(f"  handler        {name}  defined at {dtxt}")
            calls = [n for n, l in enumerate(lines, 1)
                     if re.search(r'\b' + re.escape(name) + r'\s*\(', strip_code(l))
                     and n != b['line'] and not any(d == n for d, _, _ in defs)]
            if calls:
                warn.append(f"handler {name}() has {len(calls)} other call site(s): "
                            f"{calls[:12]}{' ...' if len(calls) > 12 else ''} -- KEEP THE FUNCTION")
            else:
                print(f"                 no other callers -- the function can go too")
                for d, k, e in defs:
                    safe.append(f"{d}-{e}")
            exports = [n for n, l in enumerate(lines, 1)
                       if re.search(r'\bwindow\.' + re.escape(name) + r'\s*=', l)]
            print(f"  window export  {exports if exports else 'none'}")

        # The updateReportBtn trap: an id read that is NOT the click binding.
        # After the element goes, that read returns null and the next property
        # access throws. Name the enclosing function so you know what breaks.
        bound_decls = {d for d, _ in alias_binds}
        if b['id']:
            direct = r"getElementById\(\s*['\"]" + re.escape(b['id']) + r"['\"]"
            bound_decls |= {n for n in reads
                            if re.search(direct, lines[n - 1])
                            and ('.addEventListener' in lines[n - 1]
                                 or '.onclick' in lines[n - 1])}
        for n in reads:
            if n in bound_decls:
                continue
            owner, span = None, None
            for d, l in enumerate(lines, 1):
                if d > n:
                    break
                m = re.search(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', strip_code(l))
                if m and block_extent(lines, d) >= n:
                    owner, span = m.group(1), (d, block_extent(lines, d))
            where = f" inside {owner}() [{span[0]}-{span[1]}]" if owner else ""
            end = block_extent(lines, n)
            warn.append(f"element read by id at index.html:{n}{where} -- NOT the click binding. "
                        f"After the delete this is null and throws. Remove or guard "
                        f"index.html:{n}-{end}.")

        keys = set()
        for n in range(b['line'], min(b['line'] + 3, len(lines))):
            keys |= set(re.findall(r"localStorage\.\w+\(\s*['\"]([^'\"]+)['\"]", lines[n - 1]))
        print(f"  localStorage   {sorted(keys) if keys else 'none at the element; check the handler body'}")

        for w in warn:
            print(f"\n  !! {w}")
        print(f"\n  CANDIDATE LINES TO DELETE: {', '.join(safe)}")
        if warn:
            print("  ^ read the warnings above first -- this list is not safe as-is.")
        print("\n  After deleting, run:  node --check  on the inline scripts "
              "(`extract_buttons.py --check`),\n  then rerun this script with no arguments "
              "to refresh BUTTONS.md and the feature tables.\n")
    return 0


def check_scripts():
    """node --check every inline <script> (skips src= and text/babel)."""
    import subprocess, tempfile
    src = open(INDEX, encoding='utf-8', errors='replace').read()
    blocks = []
    for m in re.finditer(r'<script([^>]*)>(.*?)</script>', src, re.S):
        attrs, body = m.group(1), m.group(2)
        if 'src=' in attrs or 'text/babel' in attrs:
            continue
        blocks.append((src[:m.start(2)].count('\n') + 1, body))
    print(f"{len(blocks)} inline script blocks")
    bad = 0
    for line, body in blocks:
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
            f.write(body)
            path = f.name
        r = subprocess.run(['node', '--check', path], capture_output=True, text=True)
        os.unlink(path)
        if r.returncode:
            bad += 1
            print(f"  FAIL  block at index.html:{line}")
            print('        ' + '\n        '.join(r.stderr.strip().split('\n')[:6]))
        else:
            print(f"  ok    block at index.html:{line}  ({body.count(chr(10)) + 1} lines)")
    return 1 if bad else 0


USAGE = """features/extract_buttons.py -- button inventory for index.html

  (no args)            rebuild features/BUTTONS.md from index.html
  --trace <id|label>   everything you must know before deleting that button
  --check              node --check every inline <script> block
  --help

Culling one button:
  1. python3 features/extract_buttons.py --trace loadCurrentBtn
  2. read the warnings; delete only what you have accounted for
  3. python3 features/extract_buttons.py --check
  4. python3 features/extract_buttons.py          # refresh BUTTONS.md
  5. record it under "## Culled" in the owning features/NN-*.md, one commit
"""


def main():
    args = sys.argv[1:]
    if args and args[0] in ('-h', '--help'):
        print(USAGE)
        return 0

    src = open(INDEX, encoding='utf-8', errors='replace').read()
    btns, lines = extract(src)
    classify(resolve(btns, lines), lines)

    if args and args[0] == '--check':
        return check_scripts()
    if args and args[0] == '--trace':
        if len(args) < 2:
            print("--trace needs a button id or a piece of its label.\n")
            print(USAGE)
            return 2
        return trace(btns, lines, args[1])
    if args:
        print(f"unknown option {args[0]!r}\n")
        print(USAGE)
        return 2

    files = {f[3:-3]: f for f in sorted(os.listdir(HERE)) if re.match(r'\d\d-.*\.md$', f)}
    esc = lambda s: html.unescape(s or '').replace('|', '\\|').replace('\n', ' ').strip()

    with open(os.path.join(HERE, 'BUTTONS.md'), 'w') as f:
        f.write("# Every button in index.html\n\n")
        f.write(f"{len(btns)} buttons, generated by `features/extract_buttons.py`. Sorted by line.\n")
        f.write("`feature` links to the file that owns it and carries the keep/cut verdict.\n\n")
        f.write("Line numbers go stale as soon as you edit `index.html` -- rerun the script.\n\n")
        f.write("`(hidden)` ships `display:none`. `(jsx)` lives in the React block and is wired by\n")
        f.write("JSX `onClick`. A `~` before the feature means it was inherited from the surrounding\n")
        f.write("code rather than read off the button, so check it before acting on it.\n\n")
        f.write("| line | id | label | handler | feature |\n|---:|---|---|---|---|\n")
        for b in sorted(btns, key=lambda x: x['line']):
            h = ', '.join(b['handlers']) or '—'
            if b['proxy_for']:
                h = f"proxy → #{b['proxy_for']}"
            flag = ' **(hidden)**' if b['hidden'] else ''
            flag += ' *(jsx)*' if b['jsx'] else ''
            fn = files.get(b['feature'])
            tilde = '~' if b['guessed'] else ''
            feat = f"{tilde}[{b['feature']}]({fn})" if fn else f"**{tilde}{b['feature']}**"
            f.write(f"| {b['line']} | `{b['id'] or '—'}` | {esc(b['label']) or '—'}{flag} | "
                    f"`{esc(h)}` | {feat} |\n")

    c = collections.Counter(b['feature'] for b in btns)
    print(f"{len(btns)} buttons -> features/BUTTONS.md")
    for k, v in c.most_common():
        print(f"  {v:4d}  {k}")
    # JSX buttons are expected to have no addEventListener binding.
    unres = [b for b in btns if not b['handlers'] and not b['proxy_for'] and not b['jsx']]
    if unres:
        print(f"\n{len(unres)} with no click binding found (dead, or bound in a way "
              f"the script does not see):")
        for b in unres:
            print(f"  index.html:{b['line']}  id={b['id'] or '-'}  {b['label'][:40]!r}")
    guessed = [b for b in btns if b['guessed']]
    if guessed:
        print(f"\n{len(guessed)} feature assignments inherited from surrounding code (marked ~).")
    if c['unclassified']:
        print(f"\n{c['unclassified']} unclassified -- add a RULES entry or delete the button.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
