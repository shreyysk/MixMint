/* MixMint UX extras:
 *  1. Command palette: Ctrl/⌘+K or "/" → search releases, packs and DJs, jump anywhere (↑ ↓ Enter, Esc).
 *  2. Keyboard shortcuts: "?" shows them; g h / g r / g s / g l / g c / g d / g u go to pages.
 *  3. Cursor: on mouse devices a soft mint ring follows the pointer and grows over things you can click
 *     (the normal arrow stays, so nothing gets harder to use). Off with "c" or reduced motion.
 *  4. Phone keyboard: the bottom tab bar hides while typing and the focused field scrolls into view.
 *  5. Small touches: ripple on buttons, haptic tick on add-to-cart / buy (Android), copy-link feedback.
 */
(() => {
    const doc = document.documentElement;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
                    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
    const typing = (el) => el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
    const authed = !!document.querySelector('.mm-tabbar');
    const role = document.body.dataset.role || '';
    const esc = (s) => String(s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    // ── pages for the palette and "g" shortcuts ──
    const PAGES = [
        { k: 'h', title: 'Home', url: '/' },
        { k: 'r', title: 'All releases', url: '/releases/' },
        { k: 's', title: 'Sample packs', url: '/sample-packs/' },
        { title: 'Limited drops', url: '/drops/' },
        { title: 'Bundles', url: '/bundles/' },
        { title: 'DJs', url: '/djs/' },
        { k: 'c', title: 'Cart', url: '/cart/' },
        { k: 'l', title: 'My library', url: '/library/', auth: true },
        { k: 'd', title: 'Dashboard', url: role === 'dj' ? '/dashboard/dj/' : '/dashboard/', auth: true },
        { k: 'u', title: 'Upload music', url: '/upload/', dj: true },
        { title: 'Payouts', url: '/dashboard/dj/payouts/', dj: true },
        { title: 'Sell your music on MixMint', url: '/sell/' },
        { title: 'Recover a past download', url: '/recover/' },
        { title: 'Contact us', url: '/contact/' },
    ].filter((p) => (!p.auth || authed) && (!p.dj || role === 'dj'));

    // ─────────────────────────────── 1. command palette ───────────────────────────────
    let pal = null, input, list, items = [], sel = 0, timer = null, lastQ = '', opener = null;
    function build() {
        pal = document.createElement('div');
        pal.id = 'mm-palette';
        pal.setAttribute('role', 'dialog');
        pal.setAttribute('aria-modal', 'true');
        pal.setAttribute('aria-label', 'Search MixMint');
        pal.innerHTML = '<div class="mmp-box"><div class="mmp-head"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>' +
            '<input type="search" placeholder="Search tracks, packs, DJs or pages…" aria-label="Search" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="mmp-list">' +
            '<kbd>Esc</kbd></div><ul id="mmp-list" role="listbox"></ul>' +
            '<div class="mmp-foot"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>?</kbd> shortcuts</span></div></div>';
        document.body.appendChild(pal);
        input = pal.querySelector('input');
        list = pal.querySelector('ul');
        pal.addEventListener('mousedown', (e) => { if (e.target === pal) close(); });
        input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 140); render(); });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
            else if (e.key === 'Enter') { e.preventDefault(); go(items[sel]); }
            else if (e.key === 'Escape') { e.preventDefault(); close(); }
            else if (e.key === 'Tab') { e.preventDefault(); move(e.shiftKey ? -1 : 1); }
        });
        list.addEventListener('click', (e) => { const li = e.target.closest('li[data-i]'); if (li) go(items[+li.dataset.i]); });
        list.addEventListener('mousemove', (e) => { const li = e.target.closest('li[data-i]'); if (li && +li.dataset.i !== sel) { sel = +li.dataset.i; paint(); } });
    }
    function open(prefill) {
        if (!pal) build();
        opener = document.activeElement;
        pal.classList.add('open');
        document.body.classList.add('mmp-lock');
        input.value = prefill || '';
        render();
        requestAnimationFrame(() => input.focus());
    }
    function close() {
        if (!pal) return;
        pal.classList.remove('open');
        document.body.classList.remove('mmp-lock');
        if (opener && opener.focus) opener.focus();
    }
    let remote = [];
    async function search() {
        const q = input.value.trim();
        if (q.length < 2) { remote = []; lastQ = q; render(); return; }
        if (q === lastQ) return;
        lastQ = q;
        try {
            const r = await fetch('/search/quick/?q=' + encodeURIComponent(q), { headers: { Accept: 'application/json' } });
            if (r.ok && input.value.trim() === q) { remote = (await r.json()).results || []; render(); }
        } catch (e) {}
    }
    function render() {
        const q = input.value.trim().toLowerCase();
        const pages = PAGES.filter((p) => !q || p.title.toLowerCase().includes(q)).slice(0, q ? 4 : 8)
            .map((p) => ({ type: 'Page', title: p.title, url: p.url, sub: p.k ? 'g then ' + p.k : '' }));
        items = (q.length >= 2 ? remote : []).concat(pages);
        if (q.length >= 2) items.push({ type: 'Search', title: 'See all results for “' + input.value.trim() + '”', url: '/releases/?q=' + encodeURIComponent(input.value.trim()) });
        sel = Math.min(sel, Math.max(0, items.length - 1));
        list.innerHTML = items.length ? items.map((it, i) =>
            `<li role="option" data-i="${i}" id="mmp-${i}"><span class="mmp-ic">${it.img ? `<img src="${esc(it.img)}" alt="" loading="lazy">` : esc(it.type[0])}</span>` +
            `<span class="mmp-t"><b>${esc(it.title)}</b>${it.sub ? `<small>${esc(it.sub)}</small>` : ''}</span><span class="mmp-type">${esc(it.type)}</span></li>`).join('')
            : '<li class="mmp-empty">No matches yet. Try a DJ name, a genre or a song.</li>';
        paint();
    }
    function paint() {
        list.querySelectorAll('li[data-i]').forEach((li) => li.setAttribute('aria-selected', +li.dataset.i === sel ? 'true' : 'false'));
        const cur = list.querySelector(`#mmp-${sel}`);
        if (cur) { input.setAttribute('aria-activedescendant', cur.id); cur.scrollIntoView({ block: 'nearest' }); }
    }
    function move(d) { if (!items.length) return; sel = (sel + d + items.length) % items.length; paint(); }
    function go(it) { if (it && it.url) { close(); window.location.href = it.url; } }
    window.MMPalette = { open, close };
    document.querySelectorAll('[data-open-palette]').forEach((b) => b.addEventListener('click', (e) => { e.preventDefault(); open(); }));

    // ─────────────────────────────── 2. shortcuts ───────────────────────────────
    let help = null, gPending = 0;
    function toggleHelp() {
        if (!help) {
            help = document.createElement('div');
            help.id = 'mm-keys';
            help.setAttribute('role', 'dialog');
            help.setAttribute('aria-label', 'Keyboard shortcuts');
            const rows = [['Ctrl / ⌘ + K', 'Search everything'], ['/', 'Search'], ['?', 'This list'], ['c', 'Cursor effect on/off'], ['Esc', 'Close']]
                .concat(PAGES.filter((p) => p.k).map((p) => ['g then ' + p.k, p.title]));
            help.innerHTML = '<div class="mmk-box"><h2>Keyboard shortcuts</h2><dl>' + rows.map(([k, v]) => `<div><dt>${k.split(' ').map((x) => /^(then|\+)$/.test(x) ? x : `<kbd>${esc(x)}</kbd>`).join(' ')}</dt><dd>${esc(v)}</dd></div>`).join('') +
                '</dl><button type="button" class="btn-mm btn-ghost" data-close>Close</button></div>';
            help.addEventListener('click', (e) => { if (e.target === help || e.target.closest('[data-close]')) toggleHelp(); });
            document.body.appendChild(help);
        }
        help.classList.toggle('open');
        if (help.classList.contains('open')) help.querySelector('[data-close]').focus();
    }
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); pal && pal.classList.contains('open') ? close() : open(); return; }
        if (e.key === 'Escape' && help && help.classList.contains('open')) { toggleHelp(); return; }
        if (e.metaKey || e.ctrlKey || e.altKey || typing(e.target) || (pal && pal.classList.contains('open'))) return;
        if (e.key === '/') { e.preventDefault(); open(); return; }
        if (e.key === '?') { e.preventDefault(); toggleHelp(); return; }
        if (e.key === 'c' && fine) { cursorToggle(); return; }
        if (e.key === 'g') { gPending = Date.now(); return; }
        if (gPending && Date.now() - gPending < 1200) {
            const p = PAGES.find((x) => x.k === e.key.toLowerCase());
            gPending = 0;
            if (p) { e.preventDefault(); window.location.href = p.url; }
        }
    });

    // ─────────────────────────────── 3. cursor ───────────────────────────────
    let ring = null, dot = null, raf = 0, x = -100, y = -100, rx = -100, ry = -100;
    const CLICKABLE = 'a, button, [role=button], summary, label, select, input[type=checkbox], input[type=radio], .mm-card, [data-cursor]';
    function cursorOn() {
        if (ring || !fine || reduce) return;
        ring = document.createElement('div'); ring.id = 'mm-cursor-ring';
        dot = document.createElement('div'); dot.id = 'mm-cursor-dot';
        document.body.append(ring, dot);
        doc.classList.add('mm-cursor');
        const loop = () => {
            rx += (x - rx) * 0.2; ry += (y - ry) * 0.2;
            ring.style.transform = `translate3d(${rx}px, ${ry}px, 0) translate(-50%, -50%)`;
            raf = Math.abs(x - rx) + Math.abs(y - ry) > 0.3 ? requestAnimationFrame(loop) : 0;
        };
        document.addEventListener('pointermove', onMove, { passive: true });
        document.addEventListener('pointerdown', onDown, { passive: true });
        document.addEventListener('pointerup', onUp, { passive: true });
        document.addEventListener('mouseleave', onLeave);
        function onMove(e) {
            if (e.pointerType !== 'mouse') return;
            x = e.clientX; y = e.clientY;
            dot.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`;
            doc.classList.remove('mm-cursor-out');
            const t = e.target.closest && e.target.closest(CLICKABLE);
            ring.classList.toggle('hover', !!t);
            ring.classList.toggle('text', !t && typing(e.target));
            if (!raf) raf = requestAnimationFrame(loop);
        }
        function onDown() { ring && ring.classList.add('down'); }
        function onUp() { ring && ring.classList.remove('down'); }
        function onLeave() { doc.classList.add('mm-cursor-out'); }
        cursorOn.off = () => {
            document.removeEventListener('pointermove', onMove); document.removeEventListener('pointerdown', onDown);
            document.removeEventListener('pointerup', onUp); document.removeEventListener('mouseleave', onLeave);
            ring.remove(); dot.remove(); ring = dot = null; doc.classList.remove('mm-cursor');
        };
    }
    function cursorToggle() {
        if (ring) { cursorOn.off(); store.set('mm-cursor', 'off'); toast('Cursor effect off'); }
        else { store.set('mm-cursor', 'on'); cursorOn(); toast('Cursor effect on'); }
    }
    if (store.get('mm-cursor') !== 'off') cursorOn();

    // magnetic pull on the main buttons (mouse only)
    if (fine && !reduce) {
        document.querySelectorAll('.btn-mint, [data-magnetic]').forEach((b) => {
            b.addEventListener('pointermove', (e) => {
                if (e.pointerType !== 'mouse') return;
                const r = b.getBoundingClientRect();
                b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.12}px, ${(e.clientY - r.top - r.height / 2) * 0.2}px)`;
            });
            b.addEventListener('pointerleave', () => { b.style.transform = ''; });
        });
    }

    // ─────────────────────────────── 4. phone keyboard ───────────────────────────────
    const vv = window.visualViewport;
    if (vv && !fine) {
        const sync = () => {
            const open = window.innerHeight - vv.height > 150 && typing(document.activeElement);
            document.body.classList.toggle('kb-open', open);
            if (open) {
                const el = document.activeElement, r = el.getBoundingClientRect();
                if (r.bottom > vv.height - 12 || r.top < 60) el.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
            }
        };
        vv.addEventListener('resize', sync);
        document.addEventListener('focusin', () => setTimeout(sync, 250));
        document.addEventListener('focusout', () => setTimeout(sync, 100));
    }
    // "Enter" on a phone keyboard moves to the next field instead of submitting half-filled forms
    document.addEventListener('keydown', (e) => {
        const el = e.target;
        if (e.key !== 'Enter' || fine || el.tagName !== 'INPUT' || /^(submit|checkbox|radio|search)$/.test(el.type) || !el.form) return;
        const f = [...el.form.elements].filter((x) => !x.disabled && x.type !== 'hidden' && /^(INPUT|SELECT|TEXTAREA)$/.test(x.tagName) && x.offsetParent);
        const i = f.indexOf(el);
        if (i > -1 && i < f.length - 1) { e.preventDefault(); f[i + 1].focus(); }
    });

    // ─────────────────────────────── 5. small touches ───────────────────────────────
    function toast(msg) {
        if (window.MM && MM.toast) { MM.toast('info', msg); return; }
        let t = document.getElementById('mm-mini-toast');
        if (!t) { t = document.createElement('div'); t.id = 'mm-mini-toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
        t.textContent = msg; t.classList.add('show');
        clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 1600);
    }
    if (!reduce) {
        document.addEventListener('pointerdown', (e) => {
            const b = e.target.closest && e.target.closest('.btn-mm');
            if (!b || b.disabled) return;
            const r = b.getBoundingClientRect(), s = document.createElement('span');
            s.className = 'mm-ripple';
            s.style.left = (e.clientX - r.left) + 'px'; s.style.top = (e.clientY - r.top) + 'px';
            b.appendChild(s);
            setTimeout(() => s.remove(), 600);
        }, { passive: true });
    }
    document.addEventListener('click', (e) => {
        const b = e.target.closest && e.target.closest('[data-add-to-cart], [data-buy], .btn-mint');
        if (b && navigator.vibrate && !fine) { try { navigator.vibrate(8); } catch (err) {} }
        const c = e.target.closest && e.target.closest('[data-copy]');
        if (c) {
            e.preventDefault();
            const text = c.dataset.copy || window.location.href;
            (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => toast('Link copied')).catch(() => {});
        }
    });
})();
