(function () {
  "use strict";

  /* Mobile navigation */
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  /* News: show the first 10, reveal the rest on request */
  var newsList = document.querySelector("[data-news-list]");
  if (newsList) {
    var extras = newsList.querySelectorAll(".is-extra");
    if (extras.length) {
      extras.forEach(function (el) { el.hidden = true; });
      var wrap = document.createElement("div");
      wrap.className = "show-more";
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--outline";
      btn.textContent = "Show more";
      btn.setAttribute("aria-expanded", "false");
      btn.addEventListener("click", function () {
        var first = extras[0];
        extras.forEach(function (el) { el.hidden = false; });
        wrap.remove();
        var link = first.querySelector("a[href]:not([tabindex])");
        if (link) link.focus();
      });
      wrap.appendChild(btn);
      newsList.insertAdjacentElement("afterend", wrap);
    }
  }

  /* Publications: topic filter + text search */
  var tools = document.querySelector("[data-pub-tools]");
  if (tools) {
    tools.hidden = false;
    var items = Array.prototype.slice.call(document.querySelectorAll(".pub"));
    var groups = Array.prototype.slice.call(document.querySelectorAll(".pub-group"));
    var chips = Array.prototype.slice.call(tools.querySelectorAll(".chip"));
    var search = tools.querySelector(".pub-search");
    var count = tools.querySelector(".pub-count");
    var empty = document.querySelector(".pub-empty");
    var activeTag = "";

    var apply = function () {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      items.forEach(function (li) {
        var tags = li.getAttribute("data-tags").split("|");
        var ok = (!activeTag || tags.indexOf(activeTag) !== -1) &&
                 (!q || li.getAttribute("data-text").indexOf(q) !== -1);
        li.hidden = !ok;
        if (ok) shown++;
      });
      groups.forEach(function (g) {
        g.hidden = !g.querySelector(".pub:not([hidden])");
      });
      count.textContent = "Showing " + shown + " of " + items.length + " publications";
      if (empty) empty.hidden = shown !== 0;
    };

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        activeTag = chip.getAttribute("data-tag");
        chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c === chip)); });
        apply();
      });
    });
    search.addEventListener("input", apply);
    apply();
  }

  /* Forms (only present when a form endpoint is configured in content/site.json) */
  document.querySelectorAll("form[data-endpoint]").forEach(function (form) {
    var status = form.querySelector(".form-status");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var submit = form.querySelector("button[type=submit]");
      submit.disabled = true;
      status.className = "form-status";
      status.textContent = "Sending…";
      fetch(form.getAttribute("data-endpoint"), {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" }
      }).then(function (res) {
        if (!res.ok) throw new Error("bad response");
        form.reset();
        status.className = "form-status is-ok";
        status.textContent = form.getAttribute("data-success") || "Thank you! Your message was sent.";
      }).catch(function () {
        status.className = "form-status is-err";
        status.textContent = "Sorry, something went wrong. Please try again or call us instead.";
      }).then(function () { submit.disabled = false; });
    });
  });

  /* Copy link on post pages */
  var copy = document.querySelector("[data-copy-link]");
  if (copy && navigator.clipboard) {
    copy.hidden = false;
    copy.addEventListener("click", function () {
      navigator.clipboard.writeText(copy.getAttribute("data-copy-link")).then(function () {
        var old = copy.textContent;
        copy.textContent = "Link copied";
        setTimeout(function () { copy.textContent = old; }, 2000);
      });
    });
  }
})();
