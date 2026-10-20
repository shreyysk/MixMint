const { chromium } = require('playwright');
const fs = require('fs');
const b64 = f => fs.readFileSync(f).toString('base64');
const F = process.env.BRAND_FONTS || __dirname + '/fonts/';  // ClashDisplay-700.woff2, Satoshi-500.woff2 (fontshare.com), logo-white.png, logo-black.png
const css = `
@font-face{font-family:Clash;src:url(data:font/woff2;base64,${b64(F+'ClashDisplay-700.woff2')}) format('woff2');font-weight:700}
@font-face{font-family:Satoshi;src:url(data:font/woff2;base64,${b64(F+'Satoshi-500.woff2')}) format('woff2');font-weight:500}
*{margin:0;padding:0;box-sizing:border-box}
:root{--mint:#00FFB3;--deep:#007A55;--ink:#0A0A0F;--cream:#F5F0E8;--amber:#FFB800}
body{font-family:Satoshi,sans-serif;font-weight:500;overflow:hidden}
.c{position:relative;overflow:hidden;display:flex;flex-direction:column}
.h{font-family:Clash,sans-serif;font-weight:700;letter-spacing:-.01em;word-spacing:.12em;line-height:.98}
.dark{background:var(--ink);color:#F0F0F5}
.cream{background:var(--cream);color:#1A1410}
.mintbg{background:var(--mint);color:var(--ink)}
.m{color:var(--mint)} .d{color:var(--deep)}
.glow{position:absolute;border-radius:50%;filter:blur(120px);opacity:.55}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px);background-size:60px 60px}
.pill{display:inline-block;border:2px solid currentColor;border-radius:999px;padding:.35em 1em;font-weight:500}
.btn{display:inline-block;background:var(--mint);color:var(--ink);border-radius:999px;padding:.55em 1.3em;font-family:Clash;font-weight:700}
.wm{display:flex;align-items:center;gap:.35em;font-family:Clash;font-weight:700}
.wm img{height:1.15em}
.bars{position:absolute;display:flex;gap:10px;align-items:flex-end}
.bars i{display:block;width:14px;background:var(--mint);border-radius:7px;opacity:.9}
`;
const LW = 'data:image/png;base64,' + b64(F + 'logo-white.png');
const LB = 'data:image/png;base64,' + b64(F + 'logo-black.png');
const bars = (n, h, seed = 3) => '<div class="bars-inner" style="display:flex;gap:10px;align-items:flex-end">' + Array.from({ length: n }, (_, i) => `<i style="display:block;width:14px;border-radius:7px;background:var(--mint);height:${Math.round(h * (0.25 + 0.75 * Math.abs(Math.sin(i * seed * 0.37 + 1))))}px"></i>`).join('') + '</div>';
const wm = (logo, size, color = '') => `<div class="wm" style="font-size:${size}px;${color}"><img src="${logo}">MixMint</div>`;

const A = {
  'og-default': [1200, 630, `<div class="c dark" style="width:1200px;height:630px;padding:70px">
    <div class="glow" style="width:600px;height:600px;background:var(--mint);right:-200px;top:-260px;opacity:.35"></div><div class="grid"></div>
    ${wm(LW, 46)}
    <div class="h" style="font-size:112px;margin-top:70px">Home of<br><span class="m">DJ Releases.</span></div>
    <div style="font-size:30px;margin-top:34px;color:#B8B8C8;max-width:760px">Edits, remixes, album &amp; sample packs from India's DJs · mixmint.site</div>
    <div style="position:absolute;right:70px;bottom:70px">${bars(14, 180)}</div></div>`],
  'profile-mint': [1080, 1080, `<div class="c mintbg" style="width:1080px;height:1080px;align-items:center;justify-content:center"><img src="${LB}" style="height:560px"></div>`],
  'profile-dark': [1080, 1080, `<div class="c dark" style="width:1080px;height:1080px;align-items:center;justify-content:center"><div class="glow" style="width:700px;height:700px;background:var(--mint);opacity:.25"></div><img src="${LW}" style="height:560px;position:relative"></div>`],
  'telegram-avatar': [640, 640, `<div class="c mintbg" style="width:640px;height:640px;align-items:center;justify-content:center;border-radius:0"><img src="${LB}" style="height:330px"></div>`],
  'youtube-banner': [2560, 1440, `<div class="c dark" style="width:2560px;height:1440px;align-items:center;justify-content:center;text-align:center">
    <div class="grid"></div><div class="glow" style="width:1400px;height:700px;background:var(--mint);opacity:.22;top:200px"></div>
    <div style="position:relative;width:1546px">${wm(LW, 86, 'justify-content:center')}
    <div class="h" style="font-size:150px;margin-top:30px">Home of <span class="m">DJ Releases.</span></div>
    <div style="font-size:40px;margin-top:26px;color:#B8B8C8">New edits, mashups &amp; sample packs every week · mixmint.site</div></div></div>`],
  'x-header': [1500, 500, `<div class="c dark" style="width:1500px;height:500px;padding:0 90px;justify-content:center;align-items:flex-end;text-align:right">
    <div class="grid"></div><div class="glow" style="width:700px;height:500px;background:var(--mint);opacity:.25;left:-200px"></div>
    <div class="h" style="font-size:96px;position:relative">Home of <span class="m">DJ Releases.</span></div>
    <div style="font-size:30px;margin-top:20px;color:#B8B8C8;position:relative">Buy from the DJs who made it · mixmint.site</div></div>`],
  'linkedin-banner': [1584, 396, `<div class="c dark" style="width:1584px;height:396px;padding:0 90px;justify-content:center;align-items:flex-end;text-align:right">
    <div class="glow" style="width:600px;height:500px;background:var(--mint);opacity:.25;left:-150px"></div>
    <div class="h" style="font-size:76px;position:relative">India's marketplace for <span class="m">DJ music.</span></div>
    <div style="font-size:26px;margin-top:16px;color:#B8B8C8;position:relative">DJs keep 85% · weekly payouts · mixmint.site</div></div>`],
  'post-launch': [1080, 1350, `<div class="c dark" style="width:1080px;height:1350px;padding:90px">
    <div class="grid"></div><div class="glow" style="width:800px;height:800px;background:var(--mint);opacity:.3;right:-300px;bottom:-200px"></div>
    ${wm(LW, 44)}<div class="pill m" style="margin-top:110px;font-size:28px;align-self:flex-start">Now live</div>
    <div class="h" style="font-size:150px;margin-top:40px">Home of<br><span class="m">DJ<br>Releases.</span></div>
    <div style="font-size:36px;margin-top:50px;color:#C8C8D4;line-height:1.35">Private edits, remixes &amp; packs straight from India's DJs. Preview, pay, download in seconds.</div>
    <div style="margin-top:auto;font-size:34px"><span class="btn">mixmint.site</span></div></div>`],
  'post-djs': [1080, 1350, `<div class="c mintbg" style="width:1080px;height:1350px;padding:90px">
    ${wm(LB, 44)}<div class="pill" style="margin-top:100px;font-size:28px;align-self:flex-start">For DJs</div>
    <div class="h" style="font-size:132px;margin-top:40px">Sell your edits.<br>Keep 85%.</div>
    <div style="font-size:38px;margin-top:50px;line-height:1.5">✓ Your own store page<br>✓ Instant, secure downloads<br>✓ Paid to UPI or bank every week<br>✓ Sample packs &amp; tool kits too</div>
    <div style="margin-top:auto;font-size:34px;font-family:Clash;font-weight:700">Apply free → mixmint.site/sell</div></div>`],
  'post-samples': [1080, 1350, `<div class="c cream" style="width:1080px;height:1350px;padding:90px">
    ${wm(LB, 44)}<div class="pill d" style="margin-top:100px;font-size:28px;align-self:flex-start">New on MixMint</div>
    <div class="h" style="font-size:140px;margin-top:40px">Sample<br>packs <span class="d">&amp;</span><br>DJ tool kits.</div>
    <div style="font-size:36px;margin-top:50px;line-height:1.4;color:#5A5048">Loops, one-shots, acapellas, intros and FX. Tulu, Kannada, Bollywood, house and more.</div>
    <div style="position:absolute;right:90px;bottom:220px">${bars(9, 220, 5)}</div>
    <div style="margin-top:auto;font-size:34px"><span class="btn" style="background:#1A1410;color:var(--mint)">mixmint.site/releases</span></div></div>`],
  'post-how': [1080, 1350, `<div class="c dark" style="width:1080px;height:1350px;padding:90px">
    ${wm(LW, 44)}<div class="h" style="font-size:110px;margin-top:90px">How it<br><span class="m">works.</span></div>
    ${[['1', 'Preview', 'Watch the DJ\'s YouTube or Reel preview.'], ['2', 'Pay', 'UPI, cards, wallets. Just your email.'], ['3', 'Download', 'Full-quality file, instantly. Yours forever.']].map(([n, t, d]) => `<div style="display:flex;gap:36px;margin-top:64px;align-items:flex-start"><div class="h m" style="font-size:96px;width:80px">${n}</div><div><div class="h" style="font-size:56px">${t}</div><div style="font-size:32px;color:#B8B8C8;margin-top:12px">${d}</div></div></div>`).join('')}
    <div style="margin-top:auto;font-size:34px"><span class="btn">mixmint.site</span></div></div>`],
  'story-launch': [1080, 1920, `<div class="c dark" style="width:1080px;height:1920px;padding:140px 90px;justify-content:center">
    <div class="grid"></div><div class="glow" style="width:900px;height:900px;background:var(--mint);opacity:.3;left:-200px;top:300px"></div>
    <div style="position:relative">${wm(LW, 54)}<div class="h" style="font-size:170px;margin-top:80px">Home of<br><span class="m">DJ<br>Releases.</span></div>
    <div style="font-size:44px;margin-top:60px;color:#C8C8D4">Now live in India.</div>
    <div style="margin-top:90px;font-size:44px"><span class="btn">Tap the link ↑</span></div></div>
    <div style="position:absolute;left:90px;bottom:160px">${bars(20, 160, 2)}</div></div>`],
  'story-djs': [1080, 1920, `<div class="c mintbg" style="width:1080px;height:1920px;padding:140px 90px;justify-content:center">
    ${wm(LB, 54)}<div class="h" style="font-size:150px;margin-top:90px">DJs,<br>get paid<br>for your<br>edits.</div>
    <div style="font-size:46px;margin-top:70px;line-height:1.5">Keep 85% of every sale.<br>Weekly payouts to UPI.<br>Apply free in 2 minutes.</div>
    <div style="margin-top:90px;font-size:44px;font-family:Clash;font-weight:700">mixmint.site/sell</div></div>`],
  'reel-cover': [1080, 1920, `<div class="c dark" style="width:1080px;height:1920px;padding:0 90px;justify-content:center;text-align:center;align-items:center">
    <div class="glow" style="width:900px;height:900px;background:var(--mint);opacity:.28"></div>
    <img src="${LW}" style="height:260px;position:relative"><div class="h" style="font-size:130px;margin-top:70px;position:relative">NEW<br><span class="m">DROP</span></div>
    <div style="font-size:44px;margin-top:40px;color:#C8C8D4;position:relative">Replace with track title</div></div>`],
  'flyer-a4': [1240, 1754, `<div class="c dark" style="width:1240px;height:1754px;padding:110px">
    <div class="grid"></div><div class="glow" style="width:1000px;height:1000px;background:var(--mint);opacity:.25;right:-400px;top:-300px"></div>
    ${wm(LW, 60)}<div class="h" style="font-size:150px;margin-top:120px;position:relative">Your edits<br>deserve a<br><span class="m">price tag.</span></div>
    <div style="font-size:42px;margin-top:70px;line-height:1.55;color:#D0D0DA;position:relative">MixMint is India's store for DJ music. Sell edits, mashups, album packs and sample packs. Keep 85%. Get paid every week to UPI or bank.</div>
    <div style="display:flex;gap:30px;margin-top:80px">${[['85%', 'you keep'], ['₹0', 'to join'], ['Weekly', 'payouts']].map(([a, b]) => `<div style="flex:1;border:2px solid rgba(255,255,255,.15);border-radius:28px;padding:36px"><div class="h m" style="font-size:74px">${a}</div><div style="font-size:30px;color:#B8B8C8;margin-top:10px">${b}</div></div>`).join('')}</div>
    <div style="margin-top:auto;font-size:52px"><span class="btn">mixmint.site/sell</span></div></div>`],
};
(async () => {
  const br = await chromium.launch();
  const only = process.argv[2];
  for (const [name, [w, h, body]] of Object.entries(A)) {
    if (only && only !== name) continue;
    const p = await br.newPage({ viewport: { width: w, height: h } });
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>${body}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: `${process.env.OUT || __dirname + '/out'}/${name}.png` });
    await p.close();
  }
  await br.close();
  console.log('done');
})();
