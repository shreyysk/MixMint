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
        if (res.status === 401 || (res.status === 403 && data.detail && /credentials/i.test(data.detail))) {
            if (opts.redirectOnAuth !== false) loginRedirect();
            var authErr = new Error(data.error || "Please log in to continue.");
            authErr.status = res.status;
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
        try {
            var data = await api(url, { body: body || {} });
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

    async function download(tokenUrl, opts) {
        opts = opts || {};
        var restore = busy(opts.button, "Preparing secure link…");
        try {
            var hash = await deviceHash();
            var data = await api(tokenUrl, { body: { device_hash: hash }, headers: { "X-Device-Hash": hash } });
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

    window.MM = {
        api: api,
        busy: busy,
        checkout: checkout,
        csrf: csrf,
        deviceHash: deviceHash,
        download: download,
        toast: toast,
        loginRedirect: loginRedirect,
    };

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
