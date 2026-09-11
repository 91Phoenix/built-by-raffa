(function () {
  var inPosts = window.location.pathname.includes("/posts/");
  var home = inPosts ? "../index.html" : "./";
  var posts = inPosts ? "./index.html" : "posts/index.html";
  var chat = inPosts ? "../chat.html" : "chat.html";
  var onChat = window.location.pathname.endsWith("/chat.html");
  var imgRoot = inPosts ? "../" : "./";

  var nav = document.getElementById("nav-slot");
  nav.innerHTML =
    '<a href="' + home + '" class="brand" aria-label="Bradicode home">' +
    '<img src="' + imgRoot + 'img/icon.png" alt="" class="logo-icon">' +
    '<span class="logo-text">Bradicode</span>' +
    '</a>' +
    '<div class="nav-right">' +
    '<a href="' + home + '" class="nav-link' + (inPosts || onChat ? '' : ' active') + '">Home</a>' +
    '<a href="' + posts + '" class="nav-link' + (inPosts ? ' active' : '') + '">Posts</a>' +
    '<a href="' + chat + '" class="nav-link' + (onChat ? ' active' : '') + '">Ask</a>' +
    '<button class="theme-toggle" aria-label="Toggle theme" title="Toggle theme">&#9790;</button>' +
    "</div>";

  var toggleBtn = nav.querySelector(".theme-toggle");
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    toggleBtn.innerHTML = theme === "dark" ? "&#9788;" : "&#9790;";
  }
  toggleBtn.addEventListener("click", function () {
    var current = document.documentElement.getAttribute("data-theme");
    var next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("theme", next); } catch (e) {}
  });

  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(saved || (prefersDark ? "dark" : "light"));

  // Wide tables inside articles scroll horizontally on small screens
  // instead of stretching the page.
  var tables = document.querySelectorAll("article table");
  for (var i = 0; i < tables.length; i++) {
    var t = tables[i];
    if (t.parentNode.classList.contains("table-wrap")) continue;
    var wrap = document.createElement("div");
    wrap.className = "table-wrap";
    t.parentNode.insertBefore(wrap, t);
    wrap.appendChild(t);
  }

  var footer = document.getElementById("footer-slot");
  footer.innerHTML =
    '<div class="footer-row">' +
    '<span>&copy; 2026 Bradicode</span>' +
    '<div class="footer-links">' +
    '<a href="mailto:raffaele.rotella@gmail.com">Email</a>' +
    '<a href="https://www.linkedin.com/in/raffaelerot/" target="_blank" rel="noopener noreferrer">LinkedIn</a>' +
    '</div>' +
    '</div>';
})();
