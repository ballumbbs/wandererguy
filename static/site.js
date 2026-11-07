(function () {
  "use strict";

  /* ---------- mobile menu ---------- */
  var menuBtn = document.querySelector(".menu-btn");
  if (menuBtn) {
    menuBtn.addEventListener("click", function () {
      var open = document.body.classList.toggle("menu-open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* ---------- search index (loaded once, on first use) ---------- */
  var indexPromise = null;
  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch("/search-index.json").then(function (r) { return r.json(); }).then(function (idx) {
        idx.forEach(function (it) { // pre-normalise once
          it._n = norm(it.n);
          it._words = it._n.split(/[\s\-()&,]+/).filter(Boolean);
          it._k = (it.h || []).map(function (k) { return { raw: k, n: norm(k) }; });
        });
        return idx;
      }).catch(function () { return []; });
    }
    return indexPromise;
  }

  var ALIASES = { beaches: "beach", mountains: "mountain", hill: "hills", islands: "island", temples: "spiritual",
    temple: "spiritual", wildlife: "wildlife", safari: "wildlife", snowy: "snow", trekking: "trek", treks: "trek",
    honeymoon: "romantic", couples: "romantic", foreign: "abroad", international: "abroad", overseas: "abroad",
    forts: "heritage", fort: "heritage", palace: "heritage", history: "heritage", food: "food", party: "nightlife" };

  // words too common to send someone straight to one place when they match a landmark name
  var GENERIC = ["beach", "lake", "temple", "fort", "palace", "market", "view", "point", "trek", "falls", "waterfall",
    "island", "hill", "hills", "park", "national", "museum", "river", "old", "town", "city", "area", "square", "road",
    "walk", "sunset", "sunrise", "cruise", "boat", "garden", "gardens", "valley", "street", "food", "night", "day", "trip"];

  var STOP = ["in", "the", "a", "to", "for", "of", "near", "from", "and", "trip", "weekend", "hotel", "hotels", "visit",
    "tour", "tours", "guide", "best", "places", "place", "things", "do", "go"];

  function norm(s) { return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[’']/g, ""); }

  function lev(a, b) { // edit distance, for typos like "manli" or "darjiling"
    if (Math.abs(a.length - b.length) > 2) return 9;
    var prev = [], cur, i, j;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      cur = [i];
      for (j = 1; j <= b.length; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[b.length];
  }

  /* Scores one destination. `strong` means every word pointed at this exact place
     (its name, a landmark in it, or a close spelling), so we can jump straight there. */
  function match(item, terms) {
    var place = norm(item.r + " " + item.c), tags = item.t.join(" "), line = norm(item.g);
    var total = 0, strong = true, hit = null;
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i], s = 0, st = false;
      var alias = ALIASES[t] || (t.length > 4 && t.slice(-1) === "s" ? t.slice(0, -1) : t);
      if (t === "abroad" || alias === "abroad") s = item.a ? 40 : 0;
      else if (t === "india" || t === "indian") s = item.a ? 0 : 30;
      else if (item._n.indexOf(t) === 0) { s = 100; st = true; }
      else if (item._n.indexOf(t) > -1) { s = 70; st = GENERIC.indexOf(t) < 0 && GENERIC.indexOf(alias) < 0; }
      else {
        for (var k = 0; k < item._k.length; k++) {
          var kw = item._k[k].n;
          if (kw.indexOf(t) === 0 || kw.indexOf(" " + t) > -1) {
            var generic = GENERIC.indexOf(t) > -1 || GENERIC.indexOf(alias) > -1 || t.length < 3;
            s = generic ? 25 : 60; st = !generic; if (st) hit = item._k[k].raw;
            break;
          }
        }
        if (!s && place.indexOf(t) > -1) s = 45;
        else if (!s && tags.indexOf(alias) > -1) s = 35;
        else if (!s && (line.indexOf(t) > -1 || line.indexOf(alias) > -1)) s = 15;
        if (!s && t.length >= 4) { // typo-tolerant name match
          var max = t.length >= 7 ? 2 : 1;
          for (var w = 0; w < item._words.length; w++) {
            if (lev(t, item._words[w]) <= max) { s = 50; st = true; break; }
          }
        }
      }
      if (!s) return null; // every word must match something
      if (!st) strong = false;
      total += s;
    }
    return { s: total, strong: strong, hit: hit };
  }

  function terms(q) {
    return norm(q).split(/[\s,]+/).filter(function (w) { return w && STOP.indexOf(w) < 0; });
  }

  function search(q, index) {
    var ts = terms(q);
    if (!ts.length) return [];
    return index.map(function (it) { var m = match(it, ts); return m ? { it: it, s: m.s, strong: m.strong, hit: m.hit } : null; })
      .filter(Boolean)
      .sort(function (a, b) { return b.s - a.s || (a.it.k === "experience" ? -1 : 0) || a.it.n.localeCompare(b.it.n); });
  }

  /* The one place a query clearly means, like Booking.com's "go straight to the city". */
  function bestPlace(results) {
    if (!results.length || !results[0].strong) return null;
    var second = results[1];
    if (second && second.strong && second.s >= results[0].s) return null; // ambiguous, e.g. two places share a word
    return results[0];
  }

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  function thumb(it) {
    return it.i ? '<img src="' + esc(it.i) + '" alt="" loading="lazy">'
      : '<span class="art" style="--c1:' + it.c1 + ';--c2:' + it.c2 + '"><span>' + esc(it.n.charAt(0)) + "</span></span>";
  }

  function subline(r) {
    var it = r.it, where = it.a ? it.c : it.r;
    if (it.k === "experience") where = "My trek story · " + where;
    return r.hit ? "Has " + r.hit + " · " + where : where;
  }

  function bookingUrl(q) { // live hotel search for places without a guide yet (keeps affiliate tracking)
    var cfg = window.WG || {};
    if (!cfg.booking) return "https://www.booking.com/searchresults.html?ss=" + encodeURIComponent(q);
    var v = encodeURIComponent(q);
    if (cfg.enc === 2) v = encodeURIComponent(v);
    return cfg.booking.replace("__Q__", v);
  }

  function goTo(url) { location.href = url; }

  /* ---------- live suggestions + direct jump under every search box ---------- */
  document.querySelectorAll("[data-search]").forEach(function (form) {
    var input = form.querySelector("input"), list = form.querySelector(".suggest"), active = -1, results = [], seq = 0;
    if (!list) return;

    function close() { list.hidden = true; active = -1; input.setAttribute("aria-expanded", "false"); }
    function paint() {
      list.querySelectorAll("li[data-i]").forEach(function (li) { li.classList.toggle("on", +li.dataset.i === active); });
    }
    function show(all, q) {
      results = all.slice(0, 6);
      if (!q) return close();
      var best = bestPlace(all);
      list.innerHTML = results.length
        ? results.map(function (r, i) {
            return '<li role="option" data-i="' + i + '"><a href="' + esc(r.it.u) + '">' + thumb(r.it) +
              '<span><strong>' + esc(r.it.n) + "</strong><em>" + esc(subline(r)) + "</em></span>" +
              (best && i === 0 ? '<kbd>Enter ↵</kbd>' : "") + "</a></li>";
          }).join("") + '<li class="all"><a href="/search/?all=1&q=' + encodeURIComponent(q) + '">See all results for "' + esc(q) + '"</a></li>'
        : '<li class="none">No guide for "' + esc(q) + '" yet.</li>' +
          '<li class="all"><a rel="sponsored nofollow noopener" target="_blank" href="' + esc(bookingUrl(q)) + '">Search hotels in "' + esc(q) + '" on Booking.com</a></li>';
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      active = best ? 0 : -1; // pre-select the place Enter will open
      paint();
    }

    input.addEventListener("focus", loadIndex);
    input.addEventListener("input", function () {
      var q = input.value.trim(), my = ++seq;
      loadIndex().then(function (idx) { if (my === seq) show(search(q, idx), q); });
    });
    input.addEventListener("keydown", function (e) {
      if (list.hidden) return;
      if (e.key === "ArrowDown") { active = Math.min(active + 1, results.length - 1); paint(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { active = Math.max(active - 1, -1); paint(); e.preventDefault(); }
      else if (e.key === "Escape") { close(); }
    });
    // Enter or the Search button: go straight to the place when the query clearly names one
    form.addEventListener("submit", function (e) {
      var q = input.value.trim();
      e.preventDefault();
      if (!q) { input.focus(); return; }
      if (!list.hidden && active > -1 && results[active]) return goTo(results[active].it.u);
      loadIndex().then(function (idx) {
        var all = search(q, idx), best = bestPlace(all);
        if (best) goTo(best.it.u);
        else if (all.length === 1) goTo(all[0].it.u);
        else goTo("/search/?q=" + encodeURIComponent(q));
      });
    });
    document.addEventListener("click", function (e) { if (!form.contains(e.target)) close(); });
  });

  /* ---------- search results page ---------- */
  var resultsEl = document.querySelector("[data-results]");
  if (resultsEl) {
    var q = new URLSearchParams(location.search).get("q") || "";
    var inp = document.querySelector("[data-results-input]"), countEl = document.querySelector("[data-results-count]");
    var noneEl = document.querySelector("[data-results-none]");
    inp.value = q;
    if (!q) { countEl.textContent = "Type a city, state, country, landmark or the kind of trip you want."; inp.focus(); }
    else loadIndex().then(function (idx) {
      var res = search(q, idx), best = bestPlace(res);
      if (best && !/[?&]all=1/.test(location.search)) { location.replace(best.it.u); return; }
      countEl.textContent = res.length ? res.length + (res.length === 1 ? " result" : " results") + ' for "' + q + '"'
        : 'No guide for "' + q + '" yet. Try a state, a country, or a word like beach, mountains or heritage.';
      if (!res.length && noneEl) {
        noneEl.hidden = false;
        noneEl.querySelector("[data-q-label]").textContent = q;
        noneEl.querySelector("a").href = bookingUrl(q);
      }
      resultsEl.innerHTML = res.map(function (r) {
        var it = r.it;
        return '<a class="ticket" href="' + esc(it.u) + '"><div class="ticket-img">' + thumb(it) + '</div><div class="ticket-body"><h3>' +
          esc(it.n) + '</h3><p class="where">' + esc(subline(r)) + '</p><p class="line">' + esc(it.g) + "</p></div></a>";
      }).join("");
    });
  }

  /* ---------- destinations filters ---------- */
  var filter = document.querySelector("[data-filter]");
  if (filter) {
    var params = new URLSearchParams(location.search);
    var state = { where: params.get("where") || "", mood: params.get("mood") || "", q: "" };
    var cells = filter.querySelectorAll(".cell"), countOut = filter.querySelector("[data-count]"), empty = filter.querySelector(".empty");
    var moodTags = {};
    filter.querySelectorAll("[data-mood]").forEach(function (b) { moodTags[b.dataset.mood] = (b.dataset.tags || "").split(" "); });

    function apply() {
      var n = 0, wanted = moodTags[state.mood] || [];
      cells.forEach(function (c) {
        var tags = c.dataset.tags.split(" ");
        var ok = (!state.where || c.dataset.where === state.where) &&
          (!state.mood || wanted.some(function (t) { return tags.indexOf(t) > -1; })) &&
          (!state.q || c.dataset.text.indexOf(state.q) > -1);
        c.hidden = !ok;
        if (ok) n++;
      });
      countOut.textContent = n;
      empty.hidden = n > 0;
      filter.querySelectorAll("[data-where]").forEach(function (b) { if (b.tagName === "BUTTON") b.classList.toggle("on", b.dataset.where === state.where); });
      filter.querySelectorAll("[data-mood]").forEach(function (b) { b.classList.toggle("on", b.dataset.mood === state.mood); });
      var p = new URLSearchParams();
      if (state.where) p.set("where", state.where);
      if (state.mood) p.set("mood", state.mood);
      history.replaceState(null, "", location.pathname + (p.toString() ? "?" + p : ""));
    }
    filter.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      if ("where" in b.dataset) state.where = b.dataset.where;
      if ("mood" in b.dataset) state.mood = b.dataset.mood;
      apply();
    });
    filter.querySelector("[data-q]").addEventListener("input", function (e) { state.q = norm(e.target.value.trim()); apply(); });
    apply();
  }
})();
