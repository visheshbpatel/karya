// Classic (non-module) script, loaded in <head> before CSS paints, so the saved theme is applied with no flash.
(function () {
  try {
    var t = localStorage.getItem("karya.theme");
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  } catch (e) { /* storage unavailable: follow the system */ }
})();
