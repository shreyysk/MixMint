/* Scroll reveal, progress bar, back-to-top (moved out of base.html so browsers cache it). */
(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Reveal on scroll (+ stagger children carrying data-reveal-child)
    const revealEls = document.querySelectorAll('[data-reveal]');
    if ('IntersectionObserver' in window && !reduceMotion) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((en) => {
                if (en.isIntersecting) {
                    const kids = en.target.querySelectorAll('[data-reveal-child]');
                    kids.forEach((k, i) => k.style.setProperty('--reveal-delay', (i * 70) + 'ms'));
                    en.target.classList.add('in');
                    io.unobserve(en.target);
                }
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
        revealEls.forEach((el) => io.observe(el));
    } else {
        revealEls.forEach((el) => el.classList.add('in'));
    }

    // 2. Scroll progress bar + back-to-top visibility
    const bar = document.getElementById('ux-scroll-progress');
    const toTop = document.getElementById('ux-to-top');
    let ticking = false;
    const onScroll = () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
            const h = document.documentElement;
            const max = h.scrollHeight - h.clientHeight;
            const p = max > 0 ? (h.scrollTop || document.body.scrollTop) / max : 0;
            if (bar) bar.style.setProperty('--scroll', p.toFixed(3));
            if (toTop) toTop.classList.toggle('show', (h.scrollTop || 0) > 600);
            ticking = false;
        });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    if (toTop) toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }));

    // 3. Animated counters ([data-count="1234"] counts up once visible)
    const counters = document.querySelectorAll('[data-count]');
    const runCounter = (el) => {
        if (el.classList.contains('counted')) return;
        el.classList.add('counted');
        const target = parseFloat(el.dataset.count || '0');
        if (reduceMotion || isNaN(target)) { el.textContent = el.dataset.count || ''; return; }
        const dur = 1100, t0 = performance.now();
        const step = (t) => {
            const k = Math.min((t - t0) / dur, 1);
            const eased = 1 - Math.pow(1 - k, 3);
            el.textContent = Math.round(target * eased).toLocaleString('en-IN');
            if (k < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    };
    if ('IntersectionObserver' in window) {
        const cio = new IntersectionObserver((es) => es.forEach((en) => {
            if (en.isIntersecting) { runCounter(en.target); cio.unobserve(en.target); }
        }), { threshold: 0.4 });
        counters.forEach((el) => cio.observe(el));
    }
})();

/* Page-change skeleton: if the next page hasn't arrived after a short moment, show a skeleton
   with the MixMint mark instead of a frozen screen. Hidden again when the page is shown (incl. back button). */
(() => {
    const pl = document.getElementById('mm-pageload');
    if (!pl) return;
    let timer = null;
    const show = () => { clearTimeout(timer); timer = setTimeout(() => pl.classList.add('show'), 220); };
    const hide = () => { clearTimeout(timer); pl.classList.remove('show'); };
    document.addEventListener('click', (e) => {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        const a = e.target.closest('a[href]');
        if (!a || a.target === '_blank' || a.hasAttribute('download') || a.dataset.noLoader !== undefined) return;
        const url = new URL(a.href, location.href);
        if (url.origin !== location.origin || url.pathname.startsWith('/api/v1/downloads') || url.pathname.includes('/download')) return;
        if (url.pathname === location.pathname && url.search === location.search) return; // same page / #anchor
        show();
    });
    document.addEventListener('submit', (e) => {
        const f = e.target;
        if (e.defaultPrevented || f.target === '_blank' || f.dataset.noLoader !== undefined || (f.method || 'get').toLowerCase() === 'dialog') return;
        setTimeout(() => { if (!e.defaultPrevented) show(); }, 0);
    });
    window.addEventListener('pageshow', hide);
    window.addEventListener('pagehide', () => clearTimeout(timer));
})();

/* Forms never lose what people typed.
   1) Before a form is sent, its fields are remembered for this tab (passwords, files and hidden fields excluded).
      If the same page comes back (an error, a refresh), empty fields are filled back in.
   2) Password rules and "passwords match" are checked before sending, so a typo never reloads the page. */
(() => {
    const KEY = 'mm-form-memory';
    const skip = (el) => !el.name || el.disabled || ['password', 'file', 'hidden', 'submit', 'button', 'reset'].includes(el.type)
        || el.name === 'csrfmiddlewaretoken' || el.closest('[data-no-memory]');
    const formId = (f) => (f.getAttribute('action') || location.pathname) + '#' + Array.from(document.forms).indexOf(f);

    // Check passwords before sending.
    document.addEventListener('submit', (e) => {
        const f = e.target;
        const pw = f.querySelector('input[type=password][name=password], input[type=password][name=new_password1], input[type=password][name=new_password]');
        const confirm = f.querySelector('input[name=confirm_password], input[name=new_password2], input[name=password2]');
        if (!pw || !confirm || f.dataset.noPwCheck !== undefined) return;
        let msg = '';
        const v = pw.value;
        if (v.length < 8) msg = 'Use at least 8 characters.';
        else if (!/[a-z]/.test(v) || !/[A-Z]/.test(v) || !/\d/.test(v) || !/[^A-Za-z0-9]/.test(v)) msg = 'Add an uppercase letter, a lowercase letter, a number and a symbol.';
        const target = msg ? pw : (confirm.value !== v ? confirm : null);
        if (!msg && target) msg = "The two passwords don't match.";
        if (msg) {
            e.preventDefault(); e.stopImmediatePropagation();
            target.setCustomValidity(msg); target.reportValidity();
            target.addEventListener('input', () => target.setCustomValidity(''), { once: true });
        }
    }, true);

    // Remember fields when a form is sent.
    document.addEventListener('submit', (e) => {
        const f = e.target;
        if (e.defaultPrevented || (f.method || 'get').toLowerCase() !== 'post' || f.dataset.noMemory !== undefined) return;
        const fields = {};
        Array.from(f.elements).forEach((el) => {
            if (skip(el)) return;
            if (el.type === 'checkbox' || el.type === 'radio') { if (el.checked) (fields[el.name] = fields[el.name] || []).push(el.value); }
            else fields[el.name] = el.value;
        });
        try { sessionStorage.setItem(KEY, JSON.stringify({ path: location.pathname, form: formId(f), t: Date.now(), fields })); } catch (_) {}
    });

    // Fill fields back in if this same page came back after sending.
    let saved = null;
    try { saved = JSON.parse(sessionStorage.getItem(KEY) || 'null'); sessionStorage.removeItem(KEY); } catch (_) {}
    if (!saved || saved.path !== location.pathname || Date.now() - saved.t > 15 * 60 * 1000) return;
    const restore = () => {
        const f = Array.from(document.forms).find((x) => formId(x) === saved.form);
        if (!f) return;
        Array.from(f.elements).forEach((el) => {
            if (skip(el) || !(el.name in saved.fields)) return;
            const val = saved.fields[el.name];
            if (el.type === 'checkbox' || el.type === 'radio') { if (Array.isArray(val) && !el.checked) el.checked = val.includes(el.value); }
            else if (!el.value) el.value = val;
            else return;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        });
    };
    // After Alpine has set its own initial values.
    if (window.Alpine) setTimeout(restore, 0); else document.addEventListener('alpine:initialized', () => setTimeout(restore, 0), { once: true });
    setTimeout(restore, 600);
})();

/* Ads load only when a slot is about to scroll into view (never blocks the page). */
(() => {
    const slots = document.querySelectorAll('[data-ad] ins.adsbygoogle');
    if (!slots.length) return;
    let loaded = false;
    const load = () => {
        if (loaded) return; loaded = true;
        const s = document.createElement('script');
        s.async = true; s.crossOrigin = 'anonymous';
        s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + encodeURIComponent(slots[0].dataset.adClient);
        document.head.appendChild(s);
    };
    const fill = (ins) => { load(); try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (_) {} };
    if (!('IntersectionObserver' in window)) { slots.forEach(fill); return; }
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { fill(e.target); io.unobserve(e.target); } }), { rootMargin: '300px 0px' });
    slots.forEach((s) => io.observe(s));
})();

/* Sliding rows: arrow buttons scroll one screen of cards; arrows switch off at the ends. */
(() => {
    document.querySelectorAll('[data-row]').forEach((row) => {
        const rail = row.querySelector('[data-rail]'), prev = row.querySelector('[data-row-prev]'), next = row.querySelector('[data-row-next]');
        if (!rail) return;
        const sync = () => {
            const max = rail.scrollWidth - rail.clientWidth - 2;
            if (prev) prev.disabled = rail.scrollLeft <= 2;
            if (next) next.disabled = rail.scrollLeft >= max;
            row.toggleAttribute('data-more-right', rail.scrollLeft < max);
            row.toggleAttribute('data-fits', max <= 0);
        };
        const go = (dir) => rail.scrollBy({ left: dir * rail.clientWidth * 0.9, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        prev && prev.addEventListener('click', () => go(-1));
        next && next.addEventListener('click', () => go(1));
        rail.addEventListener('scroll', () => requestAnimationFrame(sync), { passive: true });
        rail.addEventListener('keydown', (e) => { if (e.key === 'ArrowRight') { e.preventDefault(); go(1); } if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); } });
        window.addEventListener('resize', sync, { passive: true });
        sync();
    });
})();
