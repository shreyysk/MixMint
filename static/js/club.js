/* MixMint club layer: stage pointer glow + equalizer, rotating search hints, card tilt + light,
   shared-element page transition for release art, product-page record. Respects reduced motion. */
(function () {
    'use strict';
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var fine = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    // ── Stage: mesh follows the pointer, equalizer bars jump near it ──
    var stage = document.querySelector('[data-stage]');
    if (stage && !reduce) {
        var bars = Array.prototype.slice.call(stage.querySelectorAll('.mm-eq i'));
        var raf = 0, px = 0.5, py = 0.4;
        var paint = function () {
            raf = 0;
            stage.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
            stage.style.setProperty('--my', (py * 100).toFixed(1) + '%');
            var n = bars.length;
            for (var i = 0; i < n; i++) {
                var d = Math.abs(i / (n - 1) - px);
                var boost = Math.max(0, 1 - d * 5) * (0.4 + (1 - py) * 0.6);
                bars[i].style.setProperty('--boost', boost.toFixed(2));
            }
        };
        stage.addEventListener('pointermove', function (e) {
            var r = stage.getBoundingClientRect();
            px = (e.clientX - r.left) / r.width; py = (e.clientY - r.top) / r.height;
            if (!raf) raf = requestAnimationFrame(paint);
        }, { passive: true });
        stage.addEventListener('pointerleave', function () {
            bars.forEach(function (b) { b.style.removeProperty('--boost'); });
        });
        // Pause the heavy layers when the stage is off-screen
        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (es) {
                stage.classList.toggle('is-off', !es[0].isIntersecting);
            }).observe(stage);
        }
    }

    // ── Rotating search hints ──
    var q = document.querySelector('input[data-rotate]');
    if (q && !reduce) {
        var hints = q.getAttribute('data-rotate').split('|'), k = 0;
        setInterval(function () {
            if (document.activeElement === q || q.value) return;
            q.classList.add('swap');
            setTimeout(function () { k = (k + 1) % hints.length; q.placeholder = hints[k]; q.classList.remove('swap'); }, 260);
        }, 2800);
    }

    // ── Card tilt + moving light (mouse only) ──
    if (fine && !reduce) {
        document.addEventListener('pointermove', function (e) {
            var card = e.target.closest && e.target.closest('.mm-rcard');
            if (!card) return;
            var r = card.getBoundingClientRect();
            var x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
            card.classList.add('is-tilting');
            card.style.setProperty('--ry', ((x - 0.5) * 10).toFixed(2) + 'deg');
            card.style.setProperty('--rx', ((0.5 - y) * 10).toFixed(2) + 'deg');
            card.style.setProperty('--gx', (x * 100).toFixed(1) + '%');
            card.style.setProperty('--gy', (y * 100).toFixed(1) + '%');
        }, { passive: true });
        document.addEventListener('pointerout', function (e) {
            var card = e.target.closest && e.target.closest('.mm-rcard');
            if (card && !card.contains(e.relatedTarget)) {
                card.classList.remove('is-tilting');
                card.style.removeProperty('--rx'); card.style.removeProperty('--ry');
            }
        }, { passive: true });
    }

    // ── Shared-element transition: the clicked cover morphs into the product page artwork ──
    document.addEventListener('click', function (e) {
        var link = e.target.closest && e.target.closest('.mm-rcard a[href]');
        if (!link || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
        var img = link.closest('.mm-rcard').querySelector('.mm-rcard-art img');
        if (img) img.style.viewTransitionName = 'mm-art';
    });
    window.addEventListener('pageshow', function () {
        document.querySelectorAll('.mm-rcard-art img').forEach(function (i) { i.style.viewTransitionName = ''; });
    });

    // ── Product page: the record slides out of the sleeve once the art is on screen ──
    var art = document.querySelector('.mm-pdp-art');
    if (art) setTimeout(function () { art.classList.add('is-in'); }, reduce ? 0 : 450);

    // ── Shelves: mark as seen (draws the title underline) ──
    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (es) {
            es.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
        }, { threshold: 0.2 });
        document.querySelectorAll('.mm-shelf').forEach(function (s) { io.observe(s); });
    }
})();

/* Round 2: glass navbar on scroll, active nav link */
(function () {
    var root = document.documentElement, ticking = false;
    var onScroll = function () {
        if (ticking) return; ticking = true;
        requestAnimationFrame(function () { root.classList.toggle('is-scrolled', window.scrollY > 8); ticking = false; });
    };
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
    var here = location.pathname;
    document.querySelectorAll('nav.sticky a[href]').forEach(function (a) {
        var p = a.getAttribute('href');
        if (p && p !== '/' && p.charAt(0) === '/' && here.indexOf(p) === 0) { a.classList.add('is-active'); a.setAttribute('aria-current', 'page'); }
    });
})();
