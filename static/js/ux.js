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
