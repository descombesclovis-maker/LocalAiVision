/* LocalAiStudio premium runtime — vanilla, dependency-free, every feature optional */
(function () {
  "use strict";
  var d = document, w = window, root = d.documentElement, body = d.body;
  root.classList.add("js");
  var reduce = w.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = w.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var $$ = function (s, c) { return Array.prototype.slice.call((c || d).querySelectorAll(s)); };
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  var css = function (n) { return getComputedStyle(root).getPropertyValue(n).trim(); };

  /* loader */
  var loader = d.querySelector(".pm-loader");
  if (loader) {
    try { if (sessionStorage.getItem("pm-seen")) { loader.remove(); loader = null; } else sessionStorage.setItem("pm-seen", "1"); } catch (_) { /* private mode */ }
  }
  if (loader) {
    var num = loader.querySelector("span"), n = 0;
    var tick = setInterval(function () { n = Math.min(100, n + 7 + Math.random() * 14); if (num) num.textContent = Math.floor(n); if (n >= 100) { clearInterval(tick); setTimeout(function () { loader.classList.add("done"); }, 120); } }, 60);
  }

  /* split text */
  $$("[data-split]").forEach(function (el) {
    var i = 0;
    var walk = function (node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (c) {
        if (c.nodeType === 3) {
          var frag = d.createDocumentFragment();
          c.textContent.split(/(\s+)/).forEach(function (part) {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(d.createTextNode(" ")); return; }
            var o = d.createElement("span"); o.className = "w";
            var s = d.createElement("span"); s.textContent = part; s.style.setProperty("--i", i++);
            o.appendChild(s); frag.appendChild(o);
          });
          node.replaceChild(frag, c);
        } else if (c.nodeType === 1 && !c.classList.contains("ed-img")) { walk(c); }
        else if (c.nodeType === 1) { c.style.setProperty("--i", i++); }
      });
    };
    walk(el);
    el.classList.add("pm-split");
  });

  /* reveal */
  /* clip-path hides an element from IntersectionObserver, so masked reveals observe their parent */
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      var t = e.target, list = (t._rv || []).slice();
      if ((t.hasAttribute("data-reveal") && t.getAttribute("data-reveal") !== "mask") || t.hasAttribute("data-split")) list.push(t);
      list.forEach(function (x) { x.classList.add("is-in"); });
      io.unobserve(t);
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
  $$("[data-reveal],[data-split]").forEach(function (el) {
    if (el.getAttribute("data-reveal") === "mask") { var pa = el.parentElement; pa._rv = (pa._rv || []).concat(el); io.observe(pa); }
    else io.observe(el);
  });
  setTimeout(function () { $$("[data-split]").forEach(function (el) { if (el.getBoundingClientRect().top < w.innerHeight) el.classList.add("is-in"); }); }, loader ? 900 : 50);

  /* header */
  var header = d.querySelector(".pm-header"), lastY = 0;
  var burger = d.querySelector(".pm-burger");
  if (burger) burger.addEventListener("click", function () { body.classList.toggle("menu-open"); burger.setAttribute("aria-expanded", body.classList.contains("menu-open")); });
  $$(".pm-menu a").forEach(function (a) { a.addEventListener("click", function () { body.classList.remove("menu-open"); }); });
  var here = (location.pathname.split("/").pop() || "index.html");
  $$(".pm-nav a, .pm-menu a").forEach(function (a) { if (a.getAttribute("href") === here) a.classList.add("active"); });

  /* page transition */
  var curtain = d.querySelector(".pm-curtain");
  if (curtain && !reduce) {
    $$("a[href$='.html']").forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || a.target === "_blank") return;
        e.preventDefault(); curtain.classList.add("on");
        setTimeout(function () { location.href = a.getAttribute("href"); }, 520);
      });
    });
    w.addEventListener("pageshow", function () { curtain.classList.remove("on"); });
  }

  /* cursor + magnetic + tilt */
  if (fine && !reduce) {
    var cur = d.querySelector(".pm-cursor");
    var mx = -100, my = -100, cx = -100, cy = -100;
    w.addEventListener("mousemove", function (e) { mx = e.clientX; my = e.clientY; }, { passive: true });
    if (cur) {
      (function loop() { cx += (mx - cx) * 0.2; cy += (my - cy) * 0.2; cur.style.transform = "translate3d(" + cx + "px," + cy + "px,0)"; requestAnimationFrame(loop); })();
      d.addEventListener("mouseover", function (e) { if (e.target.closest && e.target.closest("a,button,[data-hover]")) cur.classList.add("hover"); });
      d.addEventListener("mouseout", function (e) { if (e.target.closest && e.target.closest("a,button,[data-hover]")) cur.classList.remove("hover"); });
    }
    $$(".pm-btn,.pm-circle,[data-magnetic]").forEach(function (b) {
      b.addEventListener("mousemove", function (e) { var r = b.getBoundingClientRect(); b.style.transform = "translate(" + (e.clientX - r.left - r.width / 2) * 0.25 + "px," + (e.clientY - r.top - r.height / 2) * 0.35 + "px)"; });
      b.addEventListener("mouseleave", function () { b.style.transform = ""; });
    });
    $$("[data-tilt]").forEach(function (c) {
      c.addEventListener("mousemove", function (e) { var r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height; c.style.setProperty("--mx", x * 100 + "%"); c.style.setProperty("--my", y * 100 + "%"); c.style.transform = "rotateY(" + (x - 0.5) * 10 + "deg) rotateX(" + (0.5 - y) * 10 + "deg)"; });
      c.addEventListener("mouseleave", function () { c.style.transform = ""; });
    });
    var peek = d.querySelector(".pm-peek"), peekImg = peek && peek.querySelector("img");
    $$("[data-peek]").forEach(function (r) {
      r.addEventListener("mouseenter", function () { if (!peek) return; peekImg.src = r.getAttribute("data-peek"); peek.classList.add("on"); });
      r.addEventListener("mousemove", function (e) { if (peek) { peek.style.left = e.clientX + "px"; peek.style.top = e.clientY + "px"; } });
      r.addEventListener("mouseleave", function () { if (peek) peek.classList.remove("on"); });
    });
  }

  /* scroll-driven: parallax, story, horizontal, statement, process, header */
  var par = $$("[data-parallax]"), hs = $$(".hs"), sts = $$(".statement"), procs = $$(".process");
  var onScroll = function () {
    var y = w.scrollY, vh = w.innerHeight;
    if (header) { header.classList.toggle("is-scrolled", y > 40); header.classList.toggle("is-hidden", y > lastY && y > 400 && !body.classList.contains("menu-open")); }
    lastY = y;
    if (reduce) return;
    par.forEach(function (el) { var r = el.getBoundingClientRect(); if (r.bottom < -200 || r.top > vh + 200) return; var s = parseFloat(el.getAttribute("data-parallax")) || 0.15; el.style.transform = "translate3d(0," + ((r.top + r.height / 2 - vh / 2) * -s) + "px,0)"; });
    hs.forEach(function (sec) {
      var track = sec.querySelector(".hs-track"); if (!track || w.innerWidth <= 800) return;
      var dist = track.scrollWidth - w.innerWidth; sec.style.height = (vh + dist) + "px";
      var p = clamp(-sec.getBoundingClientRect().top / dist, 0, 1); track.style.transform = "translate3d(" + (-p * dist) + "px,0,0)";
    });
    sts.forEach(function (sec) {
      var r = sec.getBoundingClientRect(), words = sec._w || (sec._w = $$(".sw", sec));
      var p = clamp((vh * 0.85 - r.top) / (r.height * 0.9), 0, 1), k = Math.floor(p * words.length);
      words.forEach(function (wd, i) { wd.classList.toggle("on", i < k); });
    });
    procs.forEach(function (pr) { var r = pr.getBoundingClientRect(); pr.style.setProperty("--p", clamp((vh * 0.6 - r.top) / r.height, 0, 1) * 100 + "%"); });
  };
  w.addEventListener("scroll", function () { requestAnimationFrame(onScroll); }, { passive: true });
  w.addEventListener("resize", onScroll);
  onScroll();

  $$(".story").forEach(function (st) {
    var media = $$(".story-media .pm-media", st), steps = $$(".story-step", st), count = st.querySelector(".story-count");
    var sio = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var i = steps.indexOf(e.target);
        steps.forEach(function (s, j) { s.classList.toggle("on", j === i); });
        media.forEach(function (m, j) { m.classList.toggle("on", j === i % media.length); });
        if (count) count.textContent = String(i + 1).padStart(2, "0") + "/" + String(steps.length).padStart(2, "0");
      });
    }, { rootMargin: "-45% 0px -45% 0px" });
    steps.forEach(function (s) { sio.observe(s); });
    if (steps[0]) steps[0].classList.add("on");
  });

  /* counters */
  var cio = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return; cio.unobserve(e.target);
      var el = e.target, to = parseFloat(el.getAttribute("data-count")) || 0, dec = (String(to).split(".")[1] || "").length, t0 = performance.now();
      (function step(t) { var p = clamp((t - t0) / 1800, 0, 1), v = to * (1 - Math.pow(1 - p, 4)); el.textContent = v.toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec }); if (p < 1) requestAnimationFrame(step); })(t0);
    });
  }, { threshold: 0.5 });
  $$("[data-count]").forEach(function (el) { cio.observe(el); });

  /* configurator */
  $$("[data-cfg]").forEach(function (cfg) {
    var base = parseFloat(cfg.getAttribute("data-base")) || 0, cur2 = cfg.getAttribute("data-currency") || "€";
    var list = cfg.querySelector(".cfg-list"), total = cfg.querySelector(".cfg-total b");
    var render = function () {
      var sum = base; list.innerHTML = "";
      $$(".cfg-opt.on", cfg).forEach(function (o) { sum += parseFloat(o.getAttribute("data-price")) || 0; var s = d.createElement("span"); s.textContent = o.getAttribute("data-label"); list.appendChild(s); });
      total.textContent = sum.toLocaleString("fr-FR", { minimumFractionDigits: sum % 1 ? 2 : 0, maximumFractionDigits: 2 }) + " " + cur2;
    };
    $$(".cfg-group", cfg).forEach(function (g) {
      var single = g.getAttribute("data-type") !== "multi";
      $$(".cfg-opt", g).forEach(function (o) {
        o.addEventListener("click", function () {
          if (single) $$(".cfg-opt", g).forEach(function (x) { if (x !== o) x.classList.remove("on"); });
          o.classList.toggle("on", single ? true : !o.classList.contains("on")); render();
        });
      });
      if (single) { var first = g.querySelector(".cfg-opt"); if (first) first.classList.add("on"); }
    });
    render();
  });

  /* tabs */
  $$("[data-tabs]").forEach(function (t) {
    var btns = $$(".tabs button", t), panels = $$(".tab-panel", t);
    btns.forEach(function (b, i) { b.addEventListener("click", function () { btns.forEach(function (x, j) { x.classList.toggle("on", i === j); }); panels.forEach(function (p, j) { p.classList.toggle("on", i === j); }); }); });
  });

  /* testimonials */
  $$("[data-quotes]").forEach(function (q) {
    var items = $$(".quote", q), bars = $$(".q-bars button", q), i = 0, timer;
    var show = function (k) { i = (k + items.length) % items.length; items.forEach(function (x, j) { x.classList.toggle("on", j === i); }); bars.forEach(function (b, j) { b.classList.remove("on"); if (j === i) { void b.offsetWidth; b.classList.add("on"); } }); clearTimeout(timer); timer = setTimeout(function () { show(i + 1); }, 6000); };
    bars.forEach(function (b, j) { b.addEventListener("click", function () { show(j); }); });
    if (items.length) show(0);
  });

  /* forms (demo) */
  $$(".pm-form").forEach(function (f) { f.addEventListener("submit", function (e) { e.preventDefault(); f.classList.add("sent"); f.reset(); }); });
  $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* 3D network canvas */
  $$("canvas[data-network]").forEach(function (cv) {
    var ctx = cv.getContext("2d"); if (!ctx) return;
    var accent = css("--accent") || "#3be8ff", text = css("--text") || "#fff", mode = cv.getAttribute("data-network");
    var pts = [], N = mode === "grid" ? 0 : 260, W, H, DPR = Math.min(2, w.devicePixelRatio || 1), rot = 0, tx = 0, ty = 0, vis = true;
    if (mode === "grid") { for (var gx = -10; gx <= 10; gx++) for (var gz = -10; gz <= 10; gz++) pts.push([gx * 0.12, 0, gz * 0.12]); }
    else { for (var k = 0; k < N; k++) { var th = Math.acos(1 - 2 * (k + 0.5) / N), ph = Math.PI * (1 + Math.sqrt(5)) * k; pts.push([Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)]); } }
    var links = []; for (var a = 0; a < pts.length; a++) for (var b = a + 1; b < pts.length; b++) { var dx = pts[a][0] - pts[b][0], dy = pts[a][1] - pts[b][1], dz = pts[a][2] - pts[b][2]; if (dx * dx + dy * dy + dz * dz < (mode === "grid" ? 0.0150 : 0.075)) links.push([a, b]); }
    var arcs = []; for (var q2 = 0; q2 < 7; q2++) arcs.push([Math.floor(Math.random() * pts.length), Math.floor(Math.random() * pts.length), Math.random()]);
    var size = function () { var r = cv.getBoundingClientRect(); W = r.width; H = r.height; cv.width = W * DPR; cv.height = H * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0); };
    size(); w.addEventListener("resize", size);
    cv.parentElement.addEventListener("mousemove", function (e) { var r = cv.getBoundingClientRect(); tx = ((e.clientX - r.left) / r.width - 0.5) * 0.6; ty = ((e.clientY - r.top) / r.height - 0.5) * 0.4; });
    new IntersectionObserver(function (es) { vis = es[0].isIntersecting; }).observe(cv);
    var proj = function (p, s) {
      var cy = Math.cos(rot + tx), sy = Math.sin(rot + tx), cx2 = Math.cos(0.35 + ty), sx = Math.sin(0.35 + ty);
      var x = p[0] * cy - p[2] * sy, z = p[0] * sy + p[2] * cy, y = p[1] * cx2 - z * sx; z = p[1] * sx + z * cx2;
      var f = 2.6 / (2.6 + z); return [W * (mode === "grid" ? 0.5 : 0.62) + x * s * f, H * (mode === "grid" ? 0.62 : 0.5) + y * s * f, f, z];
    };
    (function frame() {
      requestAnimationFrame(frame); if (!vis) return;
      if (!reduce) rot += 0.0016;
      var s = Math.min(W, H) * (mode === "grid" ? 1.1 : 0.42), P = pts.map(function (p) { return proj(p, s); });
      ctx.clearRect(0, 0, W, H); ctx.lineWidth = 0.6;
      ctx.strokeStyle = text; links.forEach(function (l) { var A = P[l[0]], B = P[l[1]]; ctx.globalAlpha = 0.05 + 0.18 * ((A[2] + B[2]) / 2 - 0.6); ctx.beginPath(); ctx.moveTo(A[0], A[1]); ctx.lineTo(B[0], B[1]); ctx.stroke(); });
      P.forEach(function (p, i2) { ctx.globalAlpha = clamp(p[2] - 0.45, 0.1, 1); ctx.fillStyle = i2 % 17 === 0 ? accent : text; ctx.beginPath(); ctx.arc(p[0], p[1], (i2 % 17 === 0 ? 2.4 : 1.1) * p[2], 0, 6.283); ctx.fill(); });
      ctx.strokeStyle = accent; ctx.lineWidth = 1.4;
      arcs.forEach(function (ar) { ar[2] += 0.004; if (ar[2] > 1) { ar[0] = Math.floor(Math.random() * pts.length); ar[1] = Math.floor(Math.random() * pts.length); ar[2] = 0; } var A = P[ar[0]], B = P[ar[1]], mx2 = (A[0] + B[0]) / 2, my2 = (A[1] + B[1]) / 2 - 60, t = ar[2]; ctx.globalAlpha = Math.sin(t * Math.PI) * 0.9; ctx.beginPath(); ctx.moveTo(A[0], A[1]); for (var u = 0; u <= t; u += 0.04) { var qx = (1 - u) * (1 - u) * A[0] + 2 * (1 - u) * u * mx2 + u * u * B[0], qy = (1 - u) * (1 - u) * A[1] + 2 * (1 - u) * u * my2 + u * u * B[1]; ctx.lineTo(qx, qy); } ctx.stroke(); });
      ctx.globalAlpha = 1;
    })();
  });
})();
