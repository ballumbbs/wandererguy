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
      indexPromise = fetch("/search-index.json").then(function (r) { return r.json(); }).catch(function () { return []; });
    }
    return indexPromise;
  }

  var ALIASES = { beaches: "beach", mountains: "mountain", hill: "hills", islands: "island", temples: "spiritual",
    temple: "spiritual", wildlife: "wildlife", safari: "wildlife", snowy: "snow", trekking: "trek", treks: "trek",
    honeymoon: "romantic", couples: "romantic", foreign: "abroad", international: "abroad", overseas: "abroad",
    forts: "heritage", fort: "heritage", palace: "heritage", history: "heritage", food: "food", party: "nightlife" };

  function norm(s) { return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }

  function score(item, terms) {
    var name = norm(item.n), place = norm(item.r + " " + item.c), tags = item.t.join(" "), line = norm(item.g);
    var total = 0;
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i], s = 0;
      var alias = ALIASES[t] || (t.length > 4 && t.slice(-1) === "s" ? t.slice(0, -1) : t);
      if (t === "abroad" || alias === "abroad") s = item.a ? 40 : 0;
      else if (t === "india" || t === "indian") s = item.a ? 0 : 30;
      else if (name.indexOf(t) === 0) s = 100;
      else if (name.indexOf(t) > -1) s = 70;
      else if (place.indexOf(t) > -1) s = 45;
      else if (tags.indexOf(alias) > -1) s = 35;
      else if (line.indexOf(t) > -1 || line.indexOf(alias) > -1) s = 15;
      if (!s) return 0; // every word must match something
      total += s;
    }
    return total;
  }

  function search(q, index) {
    var terms = norm(q).split(/[\s,]+/).filter(function (w) { return w && ["in", "the", "a", "to", "for", "of", "near", "from", "and", "trip", "weekend"].indexOf(w) < 0; });
    if (!terms.length) return [];
    return index.map(function (it) { return { it: it, s: score(it, terms) }; })
      .filter(function (x) { return x.s > 0; })
      .sort(function (a, b) { return b.s - a.s || a.it.n.localeCompare(b.it.n); })
      .map(function (x) { return x.it; });
  }

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  function thumb(it) {
    return it.i ? '<img src="' + esc(it.i) + '" alt="" loading="lazy">'
      : '<span class="art" style="--c1:' + it.c1 + ';--c2:' + it.c2 + '"><span>' + esc(it.n.charAt(0)) + "</span></span>";
  }

  /* ---------- live suggestions under every search box ---------- */
  document.querySelectorAll("[data-search]").forEach(function (form) {
    var input = form.querySelector("input"), list = form.querySelector(".suggest"), active = -1, results = [];
    if (!list) return;

    function close() { list.hidden = true; active = -1; input.setAttribute("aria-expanded", "false"); }
    function paint() {
      list.querySelectorAll("li").forEach(function (li, i) { li.classList.toggle("on", i === active); });
    }
    function show(items, q) {
      results = items.slice(0, 6);
      if (!q) return close();
      list.innerHTML = results.length
        ? results.map(function (it, i) {
            return '<li role="option" id="sg' + i + '"><a href="' + esc(it.u) + '">' + thumb(it) +
              '<span><strong>' + esc(it.n) + "</strong><em>" + esc(it.a ? it.c : it.r) + "</em></span></a></li>";
          }).join("") + '<li class="all"><a href="/search/?q=' + encodeURIComponent(q) + '">See all results for "' + esc(q) + '"</a></li>'
        : '<li class="none">No destination matches "' + esc(q) + '". Try a state, a country or a word like beach.</li>';
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      active = -1;
    }

    input.addEventListener("focus", loadIndex);
    input.addEventListener("input", function () {
      var q = input.value.trim();
      loadIndex().then(function (idx) { show(search(q, idx), q); });
    });
    input.addEventListener("keydown", function (e) {
      if (list.hidden) return;
      if (e.key === "ArrowDown") { active = Math.min(active + 1, results.length - 1); paint(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { active = Math.max(active - 1, -1); paint(); e.preventDefault(); }
      else if (e.key === "Enter" && active > -1) { location.href = results[active].u; e.preventDefault(); }
      else if (e.key === "Escape") { close(); }
    });
    document.addEventListener("click", function (e) { if (!form.contains(e.target)) close(); });
  });

  /* ---------- search results page ---------- */
  var resultsEl = document.querySelector("[data-results]");
  if (resultsEl) {
    var q = new URLSearchParams(location.search).get("q") || "";
    var inp = document.querySelector("[data-results-input]"), countEl = document.querySelector("[data-results-count]");
    inp.value = q;
    if (!q) { countEl.textContent = "Type a city, state, country or the kind of trip you want."; inp.focus(); }
    else loadIndex().then(function (idx) {
      var res = search(q, idx);
      countEl.textContent = res.length ? res.length + (res.length === 1 ? " destination" : " destinations") + ' for "' + q + '"'
        : 'No destination matches "' + q + '". Try a state, a country, or a word like beach, mountains or heritage.';
      resultsEl.innerHTML = res.map(function (it) {
        return '<a class="ticket" href="' + esc(it.u) + '"><div class="ticket-img">' + thumb(it) + '</div><div class="ticket-body"><h3>' +
          esc(it.n) + '</h3><p class="where">' + esc(it.a ? it.c : it.r) + '</p><p class="line">' + esc(it.g) + "</p></div></a>";
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
