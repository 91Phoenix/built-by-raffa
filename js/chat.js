(function () {
  var apiUrl = (window.BRADICODE_API_URL || "").replace(/\/+$/, "");
  var log = document.getElementById("chat-log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var button = form.querySelector("button");
  var history = [];

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function addMessage(role, text) {
    var wrap = el("div", "chat-msg chat-" + role);
    var body = el("div", "chat-bubble");
    renderText(body, text);
    wrap.appendChild(body);
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    return wrap;
  }

  // Minimal markdown: paragraphs, "- " bullets, **bold**, `code`.
  function renderText(container, text) {
    var blocks = text.split(/\n{2,}/);
    blocks.forEach(function (block) {
      var lines = block.split("\n");
      var isList = lines.every(function (l) { return /^\s*[-*] /.test(l) || !l.trim(); });
      if (isList && lines.some(function (l) { return l.trim(); })) {
        var ul = document.createElement("ul");
        lines.forEach(function (l) {
          if (!l.trim()) return;
          var li = document.createElement("li");
          renderInline(li, l.replace(/^\s*[-*] /, ""));
          ul.appendChild(li);
        });
        container.appendChild(ul);
      } else {
        var p = document.createElement("p");
        renderInline(p, block);
        container.appendChild(p);
      }
    });
  }

  function renderInline(node, text) {
    var re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    var last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) node.appendChild(document.createTextNode(text.slice(last, m.index)));
      var tok = m[0];
      if (tok.charAt(0) === "`") node.appendChild(el("code", null, tok.slice(1, -1)));
      else node.appendChild(el("strong", null, tok.slice(2, -2)));
      last = m.index + tok.length;
    }
    if (last < text.length) node.appendChild(document.createTextNode(text.slice(last)));
  }

  function addSources(wrap, sources) {
    if (!sources || !sources.length) return;
    var box = el("div", "chat-sources");
    box.appendChild(el("span", "chat-sources-label", "Read:"));
    sources.forEach(function (s) {
      var a = el("a", null, s.title);
      a.href = s.url;
      box.appendChild(a);
    });
    wrap.appendChild(box);
  }

  function setBusy(busy) {
    input.disabled = busy;
    button.disabled = busy;
    button.textContent = busy ? "Thinking…" : "Ask";
  }

  if (!apiUrl) {
    addMessage("assistant", "The chat backend is not configured yet: set BRADICODE_API_URL in js/config.js.");
    setBusy(true);
    return;
  }

  addMessage("assistant", "Ask me whether Raffaele has worked with something: a tool, an architecture, a kind of problem. I answer only from the posts and link the ones I read.");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var message = input.value.trim();
    if (!message) return;
    addMessage("user", message);
    input.value = "";
    setBusy(true);
    var pending = addMessage("assistant", "…");

    fetch(apiUrl + "/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: message, history: history.slice(-10) })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        pending.remove();
        if (!res.ok) {
          addMessage("assistant", "Sorry: " + (res.body.error || "something went wrong."));
          return;
        }
        var wrap = addMessage("assistant", res.body.answer);
        addSources(wrap, res.body.sources);
        history.push({ role: "user", content: message });
        history.push({ role: "assistant", content: res.body.answer });
      })
      .catch(function () {
        pending.remove();
        addMessage("assistant", "Sorry: the chat backend did not answer.");
      })
      .then(function () { setBusy(false); input.focus(); });
  });
})();
