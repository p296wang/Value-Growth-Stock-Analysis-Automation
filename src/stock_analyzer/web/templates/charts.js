// Dependency-free SVG charts for the report page. Data comes from the #chart-data JSON block.
(function () {
  "use strict";
  var dataEl = document.getElementById("chart-data");
  if (!dataEl) return;
  var DATA = JSON.parse(dataEl.textContent);
  var NS = "http://www.w3.org/2000/svg";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var SYMBOL = DATA.currency === "USD" ? "$" : "";
  var SUFFIX = DATA.currency && DATA.currency !== "USD" ? " " + DATA.currency : "";

  // ---- helpers ------------------------------------------------------------------

  function svg(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function html(tag, cls, text, parent) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }

  function fmtMoney(v) {
    if (v == null) return "N/A";
    var sign = v < 0 ? "-" : "", a = Math.abs(v);
    var units = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];
    for (var i = 0; i < units.length; i++) {
      if (a >= units[i][0]) return sign + SYMBOL + (a / units[i][0]).toFixed(a / units[i][0] >= 100 ? 0 : 1) + units[i][1] + SUFFIX;
    }
    return sign + SYMBOL + a.toFixed(0) + SUFFIX;
  }

  function fmtPrice(v) {
    if (v == null) return "N/A";
    return (v < 0 ? "-" : "") + SYMBOL + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + SUFFIX;
  }

  function fmtPct(v, digits) {
    if (v == null) return "N/A";
    return v.toFixed(digits == null ? 1 : digits) + "%";
  }

  function fmtSignedPct(frac) {
    return (frac >= 0 ? "+" : "−") + Math.abs(frac * 100).toFixed(1) + "%";
  }

  function parseDate(iso) {
    var p = iso.split("-");
    return Date.UTC(+p[0], +p[1] - 1, +p[2]);
  }

  function fmtDate(iso, style) {
    var p = iso.split("-"), m = MONTHS[+p[1] - 1];
    if (style === "month") return m + " '" + p[0].slice(2);
    if (style === "day") return m + " " + (+p[2]);
    return m + " " + (+p[2]) + ", " + p[0];
  }

  // Round tick values: 1, 2, 2.5 or 5 x 10^n
  function niceTicks(min, max, count) {
    if (min === max) { min -= 1; max += 1; }
    var raw = (max - min) / Math.max(1, count - 1);
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var norm = raw / mag;
    var step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
    var lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
    var ticks = [];
    for (var t = lo; t <= hi + step / 2; t += step) ticks.push(Math.abs(t) < step / 1e6 ? 0 : t);
    return ticks;
  }

  function measure(text) {
    // rough width of 11px system-ui text, used to keep labels inside the plot
    return text.length * 6.4;
  }

  // One tooltip per chart; values lead, labels follow; line keys identify series
  function Tooltip(wrap) {
    var tip = html("div", "chart-tip", null, wrap);
    tip.setAttribute("role", "status");
    tip.hidden = true;
    return {
      show: function (x, title, rows) {
        tip.textContent = "";
        html("div", "chart-tip-title", title, tip);
        rows.forEach(function (r) {
          var row = html("div", "chart-tip-row", null, tip);
          if (r.color) {
            var key = html("span", "chart-tip-key " + (r.shape || "line"), null, row);
            key.style.background = "var(" + r.color + ")";
          }
          html("strong", null, r.value, row);
          if (r.label) html("span", "chart-tip-label", r.label, row);
        });
        tip.hidden = false;
        var w = tip.offsetWidth, W = wrap.clientWidth;
        tip.style.left = Math.max(0, Math.min(W - w, x + 14 + w > W ? x - w - 14 : x + 14)) + "px";
      },
      hide: function () { tip.hidden = true; }
    };
  }

  function legend(container, series, shape) {
    if (series.length < 2) return;
    var box = html("div", "chart-legend", null, container);
    series.forEach(function (s) {
      var item = html("span", "chart-legend-item", null, box);
      var key = html("span", "chart-legend-key " + shape, null, item);
      key.style.background = "var(" + s.color + ")";
      html("span", null, s.name, item);
    });
  }

  function tableView(card, headers, rowsFn) {
    var details = card.querySelector(".table-view");
    if (!details) return;
    details.addEventListener("toggle", function () {
      if (!details.open) return;
      var holder = details.querySelector(".table-view-body");
      holder.textContent = "";
      var table = html("table", "kv data-table", null, holder);
      var tr = html("tr", null, null, html("thead", null, null, table));
      headers.forEach(function (h, i) { html("th", i ? "num" : null, h, tr); });
      var body = html("tbody", null, null, table);
      rowsFn().forEach(function (r) {
        var row = html("tr", null, null, body);
        r.forEach(function (c, i) { html("td", i ? "num" : null, c, row); });
      });
    });
  }

  function onResize(el, fn) {
    var frame = null, lastW = 0;
    var run = function () {
      frame = null;
      if (el.clientWidth && el.clientWidth !== lastW) { lastW = el.clientWidth; fn(); }
    };
    if (window.ResizeObserver) new ResizeObserver(function () { if (!frame) frame = requestAnimationFrame(run); }).observe(el);
    else window.addEventListener("resize", run);
    run();
  }

  // Shared frame: gridlines + y labels; returns scale helpers
  function frame(root, W, H, m, ticks, fmtTick) {
    var plotH = H - m.top - m.bottom;
    var lo = ticks[0], hi = ticks[ticks.length - 1];
    var y = function (v) { return m.top + plotH - (v - lo) / (hi - lo) * plotH; };
    var grid = svg("g", { "class": "grid" }, root);
    ticks.forEach(function (t) {
      svg("line", { x1: m.left, x2: W - m.right, y1: y(t), y2: y(t), "class": t === 0 && lo < 0 ? "baseline" : "gridline" }, grid);
      svg("text", { x: m.left - 8, y: y(t), dy: "0.32em", "text-anchor": "end", "class": "tick" }, grid).textContent = fmtTick(t);
    });
    return { y: y, plotH: plotH };
  }

  // ---- price history: single-series line + area wash, range tabs, crosshair -------------

  function priceChart(card) {
    var all = DATA.prices;
    if (!all || all.length < 2) { card.hidden = true; return; }
    var wrap = card.querySelector(".chart-wrap");
    var summary = card.querySelector(".chart-summary");
    var tabs = card.querySelectorAll(".range-tabs button");
    var tip = Tooltip(wrap);
    var lastT = parseDate(all[all.length - 1][0]);
    var ranges = { "6M": 182, "1Y": 365, "5Y": 1826, "Max": Infinity };
    var labels = { "6M": "past 6 months", "1Y": "past year", "5Y": "past 5 years", "Max": "since " + all[0][0].slice(0, 4) };
    var firstT = parseDate(all[0][0]);
    var range = lastT - firstT >= 365 * 864e5 ? "1Y" : "Max";
    var pts = [], state = null;

    tabs.forEach(function (b) {
      var days = ranges[b.dataset.range];
      if (days !== Infinity && lastT - firstT < days * 864e5 * 0.9) b.disabled = true;
      b.addEventListener("click", function () { range = b.dataset.range; draw(); });
    });

    function select() {
      var cutoff = lastT - ranges[range] * 864e5;
      pts = all.filter(function (p) { return parseDate(p[0]) >= cutoff; });
      tabs.forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.range === range); });
      var change = pts[pts.length - 1][1] / pts[0][1] - 1;
      summary.textContent = "";
      var delta = html("span", "delta " + (change >= 0 ? "up" : "down"), (change >= 0 ? "▲ " : "▼ ") + fmtSignedPct(change), summary);
      delta.setAttribute("aria-label", (change >= 0 ? "Up " : "Down ") + Math.abs(change * 100).toFixed(1) + "%");
      html("span", "muted", " " + labels[range], summary);
    }

    function draw() {
      select();
      var W = wrap.clientWidth, H = 280, m = { top: 14, right: 76, bottom: 30, left: 56 };
      wrap.querySelectorAll("svg").forEach(function (s) { s.remove(); });
      var root = svg("svg", { width: W, height: H, viewBox: "0 0 " + W + " " + H, role: "img",
        "aria-label": "Share price, " + labels[range] + ", from " + fmtPrice(pts[0][1]) + " to " + fmtPrice(pts[pts.length - 1][1]) });
      wrap.insertBefore(root, wrap.firstChild);
      var vals = pts.map(function (p) { return p[1]; });
      var ticks = niceTicks(Math.min.apply(null, vals), Math.max.apply(null, vals), 5);
      var whole = ticks.every(function (t) { return t === Math.round(t); });
      var f = frame(root, W, H, m, ticks, function (t) {
        return whole ? SYMBOL + t.toLocaleString("en-US") + SUFFIX : fmtPrice(t);
      });
      var t0 = parseDate(pts[0][0]), t1 = parseDate(pts[pts.length - 1][0]);
      var plotW = W - m.left - m.right;
      var x = function (iso) { return m.left + (t1 === t0 ? 0 : (parseDate(iso) - t0) / (t1 - t0) * plotW); };

      var line = "", area = "";
      pts.forEach(function (p, i) { line += (i ? "L" : "M") + x(p[0]).toFixed(1) + "," + f.y(p[1]).toFixed(1); });
      var bottom = m.top + f.plotH;
      area = line + "L" + x(pts[pts.length - 1][0]).toFixed(1) + "," + bottom + "L" + m.left + "," + bottom + "Z";
      svg("path", { d: area, "class": "area s1" }, root);
      svg("path", { d: line, "class": "line s1" }, root);

      // x-axis labels: evenly spaced in time (history is weekly further back, daily recently)
      var times = pts.map(function (p) { return parseDate(p[0]); });
      function nearestTime(t) {
        var lo = 0, hi = times.length - 1;
        while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (times[mid] < t) lo = mid; else hi = mid; }
        return t - times[lo] < times[hi] - t ? lo : hi;
      }
      var style = range === "6M" ? "day" : "month";
      var n = Math.max(2, Math.min(6, Math.floor(plotW / 80)));
      for (var i = 0; i < n; i++) {
        var p = pts[nearestTime(t0 + i * (t1 - t0) / (n - 1))];
        svg("text", { x: x(p[0]), y: H - 8, "text-anchor": i === 0 ? "start" : i === n - 1 ? "end" : "middle", "class": "tick" }, root).textContent = fmtDate(p[0], style);
      }

      // end marker + direct label on the latest value
      var last = pts[pts.length - 1];
      svg("circle", { cx: x(last[0]), cy: f.y(last[1]), r: 4, "class": "dot s1" }, root);
      svg("text", { x: x(last[0]) + 10, y: f.y(last[1]), dy: "0.32em", "class": "end-label" }, root).textContent = fmtPrice(last[1]);

      // crosshair
      var cross = svg("g", { "class": "crosshair", visibility: "hidden" }, root);
      var vline = svg("line", { y1: m.top, y2: bottom, "class": "cross-line" }, cross);
      var cdot = svg("circle", { r: 4, "class": "dot s1" }, cross);
      var hit = svg("rect", { x: m.left, y: m.top, width: plotW, height: f.plotH, "class": "hit" }, root);

      function show(i) {
        state = i;
        var p = pts[i], px = x(p[0]);
        vline.setAttribute("x1", px); vline.setAttribute("x2", px);
        cdot.setAttribute("cx", px); cdot.setAttribute("cy", f.y(p[1]));
        cross.setAttribute("visibility", "visible");
        tip.show(px, fmtDate(p[0]), [{ value: fmtPrice(p[1]), label: "close", color: "--series-1" }]);
      }
      function hide() { state = null; cross.setAttribute("visibility", "hidden"); tip.hide(); }
      hit.addEventListener("pointermove", function (e) {
        var r = root.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
        show(nearestTime(t0 + (px - m.left) / plotW * (t1 - t0)));
      });
      hit.addEventListener("pointerleave", hide);
      wrap.onkeydown = function (e) {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        var step = Math.max(1, Math.round(pts.length / 60));
        var i = state == null ? pts.length - 1 : state + (e.key === "ArrowRight" ? step : -step);
        show(Math.max(0, Math.min(pts.length - 1, i)));
      };
      wrap.onfocus = function () { show(state == null ? pts.length - 1 : state); };
      wrap.onblur = hide;
    }

    tableView(card, ["Month end", "Close"], function () {
      var byMonth = {};
      pts.forEach(function (p) { byMonth[p[0].slice(0, 7)] = p; });
      return Object.keys(byMonth).sort().reverse().map(function (k) {
        return [fmtDate(byMonth[k][0]), fmtPrice(byMonth[k][1])];
      });
    });
    onResize(wrap, draw);
  }

  // ---- grouped columns by fiscal year (revenue & net income, EPS) ---------------------

  function columnChart(card, cats, series, fmt, opts) {
    opts = opts || {};
    var wrap = card.querySelector(".chart-wrap");
    legend(card.querySelector(".chart-head-extra"), series, "rect");
    var tip = Tooltip(wrap);
    var state = null;

    function barPath(x, base, top, w) {
      // 4px rounded data end, square at the baseline
      var h = Math.abs(base - top), r = Math.min(4, h, w / 2);
      if (h < 0.5) return "";
      if (top < base) {
        return "M" + x + "," + base + "V" + (top + r) + "Q" + x + "," + top + " " + (x + r) + "," + top +
          "H" + (x + w - r) + "Q" + (x + w) + "," + top + " " + (x + w) + "," + (top + r) + "V" + base + "Z";
      }
      return "M" + x + "," + base + "V" + (top - r) + "Q" + x + "," + top + " " + (x + r) + "," + top +
        "H" + (x + w - r) + "Q" + (x + w) + "," + top + " " + (x + w) + "," + (top - r) + "V" + base + "Z";
    }

    function draw() {
      var W = wrap.clientWidth, H = opts.height || 230, m = { top: 18, right: 12, bottom: 30, left: 56 };
      wrap.querySelectorAll("svg").forEach(function (s) { s.remove(); });
      var root = svg("svg", { width: W, height: H, viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": opts.label || "" });
      wrap.insertBefore(root, wrap.firstChild);
      var vals = [];
      series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) vals.push(v); }); });
      var ticks = niceTicks(Math.min(0, Math.min.apply(null, vals)), Math.max(0, Math.max.apply(null, vals)), 5);
      var f = frame(root, W, H, m, ticks, fmt);
      var plotW = W - m.left - m.right, band = plotW / cats.length;
      var gap = 2, k = series.length;
      var barW = Math.min(24, (band * 0.72 - gap * (k - 1)) / k);
      var groupW = barW * k + gap * (k - 1);
      var base = f.y(0);
      var groups = [];

      cats.forEach(function (c, i) {
        var g = svg("g", { "class": "bar-group" }, root);
        var gx = m.left + band * i + (band - groupW) / 2;
        series.forEach(function (s, j) {
          var v = s.values[i];
          if (v == null) return;
          svg("path", { d: barPath(gx + j * (barW + gap), base, f.y(v), barW), "class": "bar " + s.cls }, g);
        });
        svg("text", { x: m.left + band * (i + 0.5), y: H - 8, "text-anchor": "middle", "class": "tick" }, root).textContent = c;
        groups.push(g);
      });
      if (ticks[0] < 0) svg("line", { x1: m.left, x2: W - m.right, y1: base, y2: base, "class": "baseline" }, root);
      else svg("line", { x1: m.left, x2: W - m.right, y1: base, y2: base, "class": "axis" }, root);

      // direct label on the latest bar of a single-series chart, if it fits above/below
      if (k === 1) {
        var li = cats.length - 1, lv = series[0].values[li];
        if (lv != null) {
          var lx = m.left + band * (li + 0.5), ly = f.y(lv) + (lv >= 0 ? -6 : 14);
          svg("text", { x: lx, y: ly, "text-anchor": "middle", "class": "end-label" }, root).textContent = fmt(lv);
        }
      }

      // hover: the whole fiscal-year band is the hit target; the group lifts, others dim
      cats.forEach(function (c, i) {
        var hit = svg("rect", { x: m.left + band * i, y: m.top, width: band, height: f.plotH, "class": "hit" }, root);
        hit.addEventListener("pointerenter", function () { show(i); });
        hit.addEventListener("pointerleave", hide);
      });
      function show(i) {
        state = i;
        groups.forEach(function (g, j) { g.classList.toggle("dim", j !== i); });
        tip.show(m.left + band * (i + 0.5), opts.titleFor ? opts.titleFor(i) : cats[i], series.map(function (s) {
          return { value: fmt(s.values[i]), label: s.name, color: s.color, shape: "rect" };
        }));
      }
      function hide() { state = null; groups.forEach(function (g) { g.classList.remove("dim"); }); tip.hide(); }
      wrap.onkeydown = function (e) {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        show(Math.max(0, Math.min(cats.length - 1, (state == null ? cats.length - 1 : state) + (e.key === "ArrowRight" ? 1 : -1))));
      };
      wrap.onfocus = function () { show(state == null ? cats.length - 1 : state); };
      wrap.onblur = hide;
    }

    tableView(card, ["Fiscal year"].concat(series.map(function (s) { return s.name; })), function () {
      return cats.map(function (c, i) { return [c].concat(series.map(function (s) { return fmt(s.values[i]); })); }).reverse();
    });
    onResize(wrap, draw);
  }

  // ---- multi-series lines by fiscal year (margins) -----------------------------------

  function lineChart(card, cats, series, fmt, opts) {
    opts = opts || {};
    var wrap = card.querySelector(".chart-wrap");
    legend(card.querySelector(".chart-head-extra"), series, "line");
    var tip = Tooltip(wrap);
    var state = null;

    function draw() {
      var W = wrap.clientWidth, H = opts.height || 230, m = { top: 18, right: 64, bottom: 30, left: 56 };
      wrap.querySelectorAll("svg").forEach(function (s) { s.remove(); });
      var root = svg("svg", { width: W, height: H, viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": opts.label || "" });
      wrap.insertBefore(root, wrap.firstChild);
      var vals = [];
      series.forEach(function (s) { s.values.forEach(function (v) { if (v != null) vals.push(v); }); });
      var ticks = niceTicks(Math.min(0, Math.min.apply(null, vals)), Math.max.apply(null, vals), 5);
      var f = frame(root, W, H, m, ticks, function (t) { return fmtPct(t, 0); });
      var plotW = W - m.left - m.right;
      var x = function (i) { return m.left + (cats.length === 1 ? plotW / 2 : i / (cats.length - 1) * plotW); };

      cats.forEach(function (c, i) {
        svg("text", { x: x(i), y: H - 8, "text-anchor": cats.length === 1 ? "middle" : i === 0 ? "start" : i === cats.length - 1 ? "end" : "middle", "class": "tick" }, root).textContent = c;
      });

      // end labels only when they don't collide (>= 14px apart); the legend always carries identity
      var ends = [];
      series.forEach(function (s) {
        var d = "", started = false;
        s.values.forEach(function (v, i) {
          if (v == null) { started = false; return; }
          d += (started ? "L" : "M") + x(i).toFixed(1) + "," + f.y(v).toFixed(1);
          started = true;
        });
        svg("path", { d: d, "class": "line " + s.cls }, root);
        s.values.forEach(function (v, i) { if (v != null) svg("circle", { cx: x(i), cy: f.y(v), r: 4, "class": "dot " + s.cls }, root); });
        var li = s.values.length - 1;
        if (s.values[li] != null) ends.push({ y: f.y(s.values[li]), text: fmt(s.values[li]) });
      });
      ends.sort(function (a, b) { return a.y - b.y; });
      var clear = ends.every(function (e, i) { return i === 0 || e.y - ends[i - 1].y >= 14; });
      if (clear) ends.forEach(function (e) {
        svg("text", { x: x(cats.length - 1) + 10, y: e.y, dy: "0.32em", "class": "end-label" }, root).textContent = e.text;
      });

      var cross = svg("line", { y1: m.top, y2: m.top + f.plotH, "class": "cross-line", visibility: "hidden" }, root);
      var hit = svg("rect", { x: m.left - 12, y: m.top, width: plotW + 24, height: f.plotH, "class": "hit" }, root);
      function show(i) {
        state = i;
        cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
        tip.show(x(i), opts.titleFor ? opts.titleFor(i) : cats[i], series.map(function (s) {
          return { value: fmt(s.values[i]), label: s.name, color: s.color };
        }));
      }
      function hide() { state = null; cross.setAttribute("visibility", "hidden"); tip.hide(); }
      hit.addEventListener("pointermove", function (e) {
        var r = root.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
        show(cats.length === 1 ? 0 : Math.max(0, Math.min(cats.length - 1, Math.round((px - m.left) / plotW * (cats.length - 1)))));
      });
      hit.addEventListener("pointerleave", hide);
      wrap.onkeydown = function (e) {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        show(Math.max(0, Math.min(cats.length - 1, (state == null ? cats.length - 1 : state) + (e.key === "ArrowRight" ? 1 : -1))));
      };
      wrap.onfocus = function () { show(state == null ? cats.length - 1 : state); };
      wrap.onblur = hide;
    }

    tableView(card, ["Fiscal year"].concat(series.map(function (s) { return s.name; })), function () {
      return cats.map(function (c, i) { return [c].concat(series.map(function (s) { return fmt(s.values[i]); })); }).reverse();
    });
    onResize(wrap, draw);
  }

  // ---- wire up ------------------------------------------------------------------------

  function card(name) { return document.querySelector('[data-chart="' + name + '"]'); }
  function fyTitle(rows) { return function (i) { return "Fiscal year ending " + fmtDate(rows[i].end); }; }

  var priceCard = card("price");
  if (priceCard) priceChart(priceCard);

  var fin = DATA.financials || [];
  var finCard = card("financials");
  if (finCard) {
    if (fin.length < 2) finCard.hidden = true;
    else columnChart(finCard, fin.map(function (r) { return r.year; }), [
      { name: "Revenue", cls: "s1", color: "--series-1", values: fin.map(function (r) { return r.revenue; }) },
      { name: "Net income", cls: "s2", color: "--series-2", values: fin.map(function (r) { return r.net_income; }) }
    ], fmtMoney, { label: "Annual revenue and net income", titleFor: fyTitle(fin) });
  }

  var eps = DATA.eps || [];
  var epsCard = card("eps");
  if (epsCard) {
    if (eps.length < 2) epsCard.hidden = true;
    else columnChart(epsCard, eps.map(function (r) { return r.year; }), [
      { name: "Diluted EPS", cls: "s1", color: "--series-1", values: eps.map(function (r) { return r.eps; }) }
    ], fmtPrice, { label: "Annual diluted earnings per share", titleFor: fyTitle(eps) });
  }

  var marginCard = card("margins");
  if (marginCard) {
    var defs = [
      { key: "gross_margin", name: "Gross", cls: "s1", color: "--series-1" },
      { key: "operating_margin", name: "Operating", cls: "s2", color: "--series-2" },
      { key: "net_margin", name: "Net", cls: "s3", color: "--series-3" }
    ];
    var mSeries = defs.filter(function (d) {
      return fin.some(function (r) { return r[d.key] != null; });
    }).map(function (d) {
      return { name: d.name, cls: d.cls, color: d.color, values: fin.map(function (r) { return r[d.key]; }) };
    });
    if (fin.length < 2 || !mSeries.length) marginCard.hidden = true;
    else {
      // name only the margins this company reports (financial firms have no gross/operating lines)
      var names = mSeries.map(function (s) { return s.name.toLowerCase(); });
      var joined = names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1] : names[0];
      marginCard.querySelector(".chart-sub").textContent =
        joined.charAt(0).toUpperCase() + joined.slice(1) + " margin by fiscal year";
      lineChart(marginCard, fin.map(function (r) { return r.year; }), mSeries, fmtPct,
      { label: "Profit margins by fiscal year", titleFor: fyTitle(fin) });
    }
  }
})();
