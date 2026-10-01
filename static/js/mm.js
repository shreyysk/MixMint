/*
 * MixMint front-end helpers (loaded on every page).
 *
 *   MM.toast(type, text)            -> shows a toast (success | error | warning | info)
 *   MM.api(url, {method, body})     -> fetch with CSRF + JSON; throws Error(message) on failure
 *   MM.checkout(url, body, opts)    -> starts a payment for PhonePe (redirect) or Razorpay (modal)
 *   MM.busy(button, label)          -> puts a button into a loading state; returns a restore() fn
 *   MM.deviceHash()                 -> stable per-browser fingerprint used for download tokens
 */
(function () {
    "use strict";

    function cookie(name) {
        var m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
        return m ? decodeURIComponent(m[1]) : "";
    }

    function csrf() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return cookie("csrftoken") || (meta && meta.content) || "";
    }

    function toast(type, text) {
        window.dispatchEvent(new CustomEvent("show-toast", { detail: { type: type || "info", text: text } }));
    }

    function loginRedirect() {
        var next = window.location.pathname + window.location.search;
        window.location.href = "/login/?next=" + encodeURIComponent(next);
    }

    async function api(url, opts) {
        opts = opts || {};
        var method = (opts.method || (opts.body !== undefined ? "POST" : "GET")).toUpperCase();
        var headers = { Accept: "application/json" };
        if (method !== "GET") {
            headers["Content-Type"] = "application/json";
            headers["X-CSRFToken"] = csrf();
        }
        Object.assign(headers, opts.headers || {});
        var res;
        try {
            res = await fetch(url, {
                method: method,
                headers: headers,
                credentials: "same-origin",
                body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
            });
        } catch (e) {
            throw new Error("Network error — check your connection and try again.");
        }
        var data = {};
        try {
            data = await res.json();
        } catch (e) {
            /* non-JSON response */
        }
        var toLogin = res.redirected && /\/login\//.test(res.url);  // @login_required bounced us
        if (res.status === 401 || toLogin || (res.status === 403 && data.detail && /credentials/i.test(data.detail))) {
            if (opts.redirectOnAuth !== false) loginRedirect();
            var authErr = new Error(data.error || "Please log in to continue.");
            authErr.status = 401;
            throw authErr;
        }
        if (!res.ok) {
            var err = new Error(data.error || data.detail || "Something went wrong (" + res.status + ").");
            err.status = res.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    function busy(button, label) {
        if (!button) return function () {};
        var original = button.innerHTML;
        var wasDisabled = button.disabled;
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
        button.classList.add("is-busy");
        if (label) {
            button.innerHTML = '<span class="mm-spinner" aria-hidden="true"></span><span>' + label + "</span>";
        }
        return function restore() {
            button.innerHTML = original;
            button.disabled = wasDisabled;
            button.removeAttribute("aria-busy");
            button.classList.remove("is-busy");
        };
    }

    /*
     * Upload a file straight to R2: ask MixMint for a signed URL, then PUT the file.
     * kind: "audio" | "album" | "cover". Resolves to {key, public_url}.
     */
    async function upload(kind, file, onProgress) {
        var target = await api("/upload/url/", { body: { kind: kind, filename: file.name, size: file.size } });
        await new Promise(function (resolve, reject) {
            var x = new XMLHttpRequest();
            x.open("PUT", target.url);
            Object.keys(target.headers || {}).forEach(function (k) { x.setRequestHeader(k, target.headers[k]); });
            x.upload.onprogress = function (ev) {
                if (ev.lengthComputable && onProgress) onProgress(Math.max(2, Math.round((ev.loaded / ev.total) * 100)));
            };
            x.onload = function () {
                if (x.status >= 200 && x.status < 300) resolve();
                else reject(new Error("Upload failed (" + x.status + "). Please try again."));
            };
            x.onerror = function () { reject(new Error("Upload was blocked or the connection dropped. Please try again.")); };
            x.send(file);
        });
        return target;
    }

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            if (document.querySelector('script[src="' + src + '"]')) return resolve();
            var s = document.createElement("script");
            s.src = src;
            s.async = true;
            s.onload = resolve;
            s.onerror = function () {
                reject(new Error("Could not load the payment window. Disable ad-blockers and retry."));
            };
            document.head.appendChild(s);
        });
    }

    function showOverlay(state, title, text) {
        var el = document.getElementById("mm-pay-overlay");
        if (!el) return;
        el.dataset.state = state;
        el.querySelector("[data-title]").textContent = title;
        el.querySelector("[data-text]").textContent = text || "";
        el.hidden = false;
        el.querySelector("[data-focus]").focus();
    }

    function hideOverlay() {
        var el = document.getElementById("mm-pay-overlay");
        if (el) el.hidden = true;
    }

    /*
     * Start a payment. `url` is any MixMint endpoint that returns the checkout
     * payload from apps.payments.views._gateway_payload.
     */
    async function checkout(url, body, opts) {
        opts = opts || {};
        var restore = busy(opts.button, opts.busyLabel || "Starting secure payment…");
        var canGuest = !!document.getElementById("mm-guest");
        try {
            var data;
            try {
                data = await api(url, { body: body || {}, redirectOnAuth: !canGuest });
            } catch (authErr) {
                if (authErr.status !== 401 || !canGuest) throw authErr;
                restore();
                if (!(await guest())) return;
                restore = busy(opts.button, opts.busyLabel || "Starting secure payment…");
                data = await api(url, { body: body || {} });
            }
            if (data.checkout === "redirect" && data.redirect_url) {
                showOverlay("pending", "Redirecting to PhonePe…", "Don't close this tab.");
                window.location.href = data.redirect_url;
                return;
            }
            if (data.checkout !== "razorpay") throw new Error(data.error || "Payment could not be started.");

            await loadScript("https://checkout.razorpay.com/v1/checkout.js");
            await new Promise(function (resolve, reject) {
                var rzp = new window.Razorpay({
                    key: data.key,
                    amount: data.amount,
                    currency: data.currency || "INR",
                    name: "MixMint",
                    description: data.description || "Secure purchase",
                    order_id: data.order_id,
                    prefill: data.prefill || {},
                    theme: { color: "#00FFB3" },
                    modal: {
                        ondismiss: function () {
                            reject(Object.assign(new Error("Payment cancelled."), { cancelled: true }));
                        },
                    },
                    handler: async function (resp) {
                        showOverlay("pending", "Confirming payment…", "This takes a few seconds.");
                        try {
                            var confirmed = await api(data.confirm_url || "/api/v1/payments/razorpay/confirm/", {
                                body: resp,
                            });
                            resolve(confirmed);
                        } catch (e) {
                            reject(e);
                        }
                    },
                });
                rzp.on("payment.failed", function (resp) {
                    var reason = (resp && resp.error && resp.error.description) || "Payment failed.";
                    reject(new Error(reason));
                });
                rzp.open();
            }).then(function (confirmed) {
                showOverlay("success", "Payment confirmed", "Taking you to your library…");
                var target = opts.successUrl || confirmed.redirect_url || "/library/?payment=success";
                setTimeout(function () {
                    window.location.href = target;
                }, 1200);
            });
        } catch (e) {
            hideOverlay();
            restore();
            if (e.cancelled) {
                toast("info", "Payment cancelled — nothing was charged.");
            } else if (e.status !== 401 && !opts.onError) {
                toast("error", e.message);
            }
            if (opts.onError) opts.onError(e);
        }
    }

    // Guest checkout: ask for an email, make the account, carry on paying. Resolves true when signed in.
    function guest() {
        var dlg = document.getElementById("mm-guest");
        if (!dlg) { loginRedirect(); return Promise.resolve(false); }
        var form = dlg.querySelector("form"), msg = dlg.querySelector("[data-msg]"), email = form.querySelector("input[type=email]");
        var send = dlg.querySelector("[data-send-link]");
        msg.textContent = ""; send.hidden = true;
        dlg.showModal ? dlg.showModal() : dlg.setAttribute("open", "");
        setTimeout(function () { email.focus(); }, 30);
        return new Promise(function (resolve) {
            function done(ok) { form.onsubmit = null; dlg.onclose = null; if (dlg.open) dlg.close(); resolve(ok); }
            dlg.onclose = function () { resolve(false); };
            form.onsubmit = async function (e) {
                e.preventDefault();
                var btn = form.querySelector("[type=submit]"), r = busy(btn, "One moment…");
                try {
                    await api("/checkout/guest/", { body: { email: email.value }, redirectOnAuth: false });
                    r(); done(true);
                } catch (err) {
                    r(); msg.textContent = err.message;
                    send.hidden = !(err.data && err.data.exists);
                }
            };
            send.onclick = async function () {
                var fd = new FormData(); fd.append("email", email.value); fd.append("csrfmiddlewaretoken", csrf());
                try { await fetch("/recover/", { method: "POST", body: fd, credentials: "same-origin" }); } catch (x) { }
                msg.textContent = "Check your inbox: we sent a sign-in link to " + email.value + ". Open it on this device, then tap Buy again.";
                send.hidden = true;
            };
        });
    }

    async function deviceHash() {
        var key = "mm_device_hash_v1";
        try {
            var saved = localStorage.getItem(key);
            if (saved) return saved;
        } catch (e) {
            /* storage blocked */
        }
        var raw = [
            navigator.userAgent,
            navigator.language,
            screen.width + "x" + screen.height,
            Intl.DateTimeFormat().resolvedOptions().timeZone || "",
            Math.random().toString(36).slice(2),
        ].join("|");
        var digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw));
        var hex = Array.from(new Uint8Array(digest))
            .map(function (b) {
                return b.toString(16).padStart(2, "0");
            })
            .join("");
        try {
            localStorage.setItem(key, hex);
        } catch (e) {
            /* ignore */
        }
        return hex;
    }

    function showLater(button, n) {
        var box = document.getElementById("mm-later") || document.createElement("div");
        box.id = "mm-later";
        box.className = "mm-later";
        box.setAttribute("role", "status");
        var html = "<p class='mm-later-title'>We're getting this file ready for you</p>" +
            "<p>It's an older release, so it takes a few minutes to bring back. You don't need to wait here: " +
            "we'll send the download link to <b>" + esc(n.email || "your email") + "</b>" +
            (n.telegram_linked ? " and to your <b>Telegram</b>" : "") + " as soon as it's ready.</p>";
        if (n.telegram_link) {
            html += "<a class='btn-mm btn-ghost mm-later-tg' target='_blank' rel='noopener' href='" + esc(n.telegram_link) +
                "'>Also send it to my Telegram</a>";
        }
        box.innerHTML = html;
        if (button && button.parentNode && !box.parentNode) button.parentNode.insertBefore(box, button.nextSibling);
        else if (!box.parentNode) toast("info", "We'll email you the download link as soon as it's ready.");
    }

    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; });
    }

    async function download(tokenUrl, opts) {
        opts = opts || {};
        var restore = busy(opts.button, "Preparing secure link…");
        try {
            var hash = await deviceHash();
            var data, started = Date.now();
            // 202 = an older file is coming back from the Telegram vault. Wait a little; if it's
            // taking long, tell the buyer we'll email (and Telegram) them the link, and stop waiting.
            for (;;) {
                data = await api(tokenUrl, { body: { device_hash: hash }, headers: { "X-Device-Hash": hash } });
                if (!data.preparing) break;
                if (opts.button) opts.button.textContent = "Getting your file ready… " + Math.round((Date.now() - started) / 1000) + "s";
                if (Date.now() - started > 25 * 1000) {
                    restore();
                    showLater(opts.button, data.notify || {});
                    return;
                }
                await new Promise(function (r) { setTimeout(r, (data.retry_after || 5) * 1000); });
            }
            if (data.warning) toast("warning", data.warning);
            window.location.href = data.page_url || data.download_url;
        } catch (e) {
            restore();
            if (e.status === 402 && e.data && e.data.redownload_available) {
                toast("warning", "Re-download available for ₹" + e.data.redownload_price + ".");
                if (opts.onRedownload) opts.onRedownload(e.data);
            } else if (e.status !== 401) {
                toast("error", e.message);
            }
        }
    }

    // Links in "your download is ready" messages end with ?download=1: start it right away.
    document.addEventListener("DOMContentLoaded", function () {
        if (new URLSearchParams(location.search).get("download") !== "1") return;
        var btn = document.getElementById("download-btn");
        if (btn) setTimeout(function () { btn.click(); }, 400);
    });

    window.MM = {
        api: api,
        busy: busy,
        upload: upload,
        preview: preview,
        guest: guest,
        checkout: checkout,
        csrf: csrf,
        deviceHash: deviceHash,
        download: download,
        showLater: showLater,
        toast: toast,
        loginRedirect: loginRedirect,
    };

    // <div x-data="mmImage('cover_url', 'https://…current.jpg')"> — pick an image, it uploads to R2 and
    // fills the hidden input named `field` with its public URL.
    document.addEventListener("alpine:init", function () {
        window.Alpine.data("mmImage", function (field, current) {
            return {
                field: field, url: current || "", busy: false, pct: 0, err: "",
                async pick(e) {
                    var f = e.target.files[0];
                    if (!f) return;
                    if (!/^image\/(jpeg|png|webp)$/.test(f.type)) { this.err = "Choose a JPG, PNG or WebP image."; return; }
                    this.err = ""; this.busy = true; this.pct = 0;
                    var form = e.target.form, submit = form && form.querySelector("[type=submit]");
                    if (submit) submit.disabled = true;
                    try {
                        var t = await upload("cover", f, (p) => { this.pct = p; });
                        this.url = t.public_url;
                    } catch (x) { this.err = x.message; }
                    this.busy = false;
                    if (submit) submit.disabled = false;
                    e.target.value = "";
                },
                clear() { this.url = ""; },
            };
        });

        // Help desk: ask a question (guests give an email), see my questions + replies, answer back.
        window.Alpine.data("mmHelp", function (loggedIn) {
            return {
                loggedIn: !!loggedIn, tab: "ask", category: "other", message: "", email: "", name: "", website: "",
                sending: false, sent: "", error: "", tickets: [], loadingMine: false, openId: null, replyText: "",
                async send() {
                    this.error = ""; this.sending = true;
                    try {
                        var r = await api("/api/v1/platform/support/ticket/", { body: {
                            message: this.message, category: this.category, email: this.email, name: this.name, website: this.website,
                        }, redirectOnAuth: false });
                        this.sent = r.message; this.message = "";
                        if (this.loggedIn) this.loadMine();
                    } catch (e) { this.error = e.message; }
                    this.sending = false;
                },
                async loadMine() {
                    if (!this.loggedIn) return;
                    this.loadingMine = true;
                    try { this.tickets = await api("/api/v1/platform/support/tickets/", { redirectOnAuth: false }); } catch (e) { this.tickets = []; }
                    this.loadingMine = false;
                },
                async reply(t) {
                    if (!this.replyText.trim()) return;
                    try {
                        var updated = await api("/api/v1/platform/support/tickets/" + t.id + "/reply/", { body: { message: this.replyText } });
                        Object.assign(t, updated); this.replyText = "";
                    } catch (e) { toast("error", e.message); }
                },
                when(iso) { try { return new Date(iso).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch (e) { return ""; } },
                label(s) { return { open: "Waiting for us", answered: "Answered", closed: "Closed", resolved: "Closed" }[s] || s; },
            };
        });
    });

    // ── Preview: the DJ's own YouTube / Instagram clip in a pop-up (MixMint never streams the file) ──
    function preview(btn) {
        var dlg = document.getElementById("mm-preview");
        if (!dlg) { window.open(btn.getAttribute("data-link") || btn.getAttribute("data-embed"), "_blank", "noopener"); return; }
        var frame = dlg.querySelector("iframe"), box = dlg.querySelector("[data-box]");
        dlg.querySelector("[data-title]").textContent = btn.getAttribute("data-title") || "Preview";
        dlg.querySelector("[data-artist]").textContent = btn.getAttribute("data-artist") || "";
        var link = dlg.querySelector("[data-open]");
        link.href = btn.getAttribute("data-link") || "#";
        link.textContent = btn.getAttribute("data-kind") === "instagram" ? "Open on Instagram ↗" : "Open on YouTube ↗";
        var more = dlg.querySelector("[data-more]");
        more.href = btn.getAttribute("data-href") || "#";
        more.hidden = !btn.getAttribute("data-href");
        box.dataset.kind = btn.getAttribute("data-kind") || "youtube";
        frame.src = btn.getAttribute("data-embed");
        dlg.showModal ? dlg.showModal() : dlg.setAttribute("open", "");
        dlg.addEventListener("close", function () { frame.src = "about:blank"; }, { once: true });
    }
    document.addEventListener("click", function (e) {
        var b = e.target.closest("[data-embed]");
        if (b) { e.preventDefault(); e.stopPropagation(); preview(b); }
    });

    // Payment result banner (PhonePe returns to /library/?payment=...).
    document.addEventListener("DOMContentLoaded", function () {
        var params = new URLSearchParams(window.location.search);
        var p = params.get("payment");
        if (document.querySelector("[data-payment-banner]")) p = null; // page shows its own banner
        if (p === "success") toast("success", "Payment confirmed — your download is ready.");
        else if (p === "failed") toast("error", "Payment failed or was cancelled. You were not charged.");
        else if (p === "pending") toast("info", "Payment is processing. This page will update shortly.");

        var overlay = document.getElementById("mm-pay-overlay");
        if (overlay) {
            overlay.addEventListener("keydown", function (e) {
                if (e.key === "Escape" && overlay.dataset.state !== "pending") hideOverlay();
            });
            overlay.querySelector("[data-close]").addEventListener("click", hideOverlay);
        }
    });
})();
