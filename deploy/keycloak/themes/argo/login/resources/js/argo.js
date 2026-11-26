// Sostituisce la tendina della lingua di keycloak.v2 con una pill IT | EN (link normali:
// senza JavaScript resta la tendina originale).
document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("login-select-toggle");
  if (!select) return;
  const nav = document.createElement("nav");
  nav.className = "argo-lang";
  nav.setAttribute("aria-label", select.getAttribute("aria-label") || "Lingua");
  const links = [...select.options].map((o) => {
    const a = document.createElement("a");
    a.href = o.value;
    a.lang =
      new URL(o.value, location.href).searchParams.get("kc_locale") || "";
    a.textContent = (a.lang || o.text.trim()).toUpperCase();
    a.title = o.text.trim();
    if (o.selected) a.setAttribute("aria-current", "true");
    return a;
  });
  links.sort((x, y) => (y.lang === "it") - (x.lang === "it")); // italiano per primo
  nav.append(...links);
  select.closest(".pf-v5-c-form-control").replaceWith(nav);
});
