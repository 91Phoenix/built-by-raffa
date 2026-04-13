(function () {
  var inPosts = window.location.pathname.includes("/posts/");
  var home = inPosts ? "../index.html" : "./";
  var posts = inPosts ? "./index.html" : "posts/index.html";

  var imgRoot = inPosts ? "../" : "./";
  var nav = document.getElementById("nav-slot");
  nav.innerHTML =
    '<a href="' +
    home +
    '" class="logo-icon-link"><img src="' + imgRoot + 'img/icon.png" alt="" class="logo-icon"></a>' +
    '<a href="' +
    home +
    '" class="logo-text">Built by Raffa</a>' +
    '<div class="nav-right">' +
    '<a href="' +
    home +
    '" class="nav-link">Home</a>' +
    '<a href="' +
    posts +
    '" class="nav-link">Posts</a>' +
    '<button class="theme-toggle" aria-label="Toggle theme">&#9790;</button>' +
    "</div>";

  var toggleBtn = nav.querySelector(".theme-toggle");
  toggleBtn.addEventListener("click", function () {
    var html = document.documentElement;
    var current = html.getAttribute("data-theme");
    var next = current === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    toggleBtn.innerHTML = next === "dark" ? "&#9788;" : "&#9790;";
  });

  var saved = localStorage.getItem("theme");
  var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = saved || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
  toggleBtn.innerHTML = theme === "dark" ? "&#9788;" : "&#9790;";

  var footer = document.getElementById("footer-slot");
  footer.innerHTML =
    '<div class="footer-row">' +
    '<span>&copy; 2026 Built by Raffa</span>' +
    '<div class="footer-links">' +
    '<a href="mailto:raffaele.rotella@gmail.com">Email</a>' +
    '<a href="https://www.linkedin.com/in/raffaelerot/" target="_blank" rel="noopener noreferrer">LinkedIn</a>' +
    '</div>' +
    '</div>';
})();