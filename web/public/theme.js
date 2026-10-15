// Same-origin, parser-blocking: restore appearance before first paint under CSP.
try {
  const choice = localStorage.getItem("retrievec.theme");
  if (choice === "light" || choice === "dark") {
    document.documentElement.dataset.theme = choice;
  }
} catch {
  // System appearance still works when device storage is blocked.
}
