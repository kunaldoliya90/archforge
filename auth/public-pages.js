// Pages marked `<!-- public -->`. build.py lists them, and the files they use, in
// /_public/manifest.json, and writes a copy of each page under /_public/ whose sidebar
// and search show only public pages.

export const PUBLIC_PREFIX = "/_public";

const NONE = { pages: new Set(), files: new Set() };

// Fetched once per Edge instance; every deployment starts new instances, so it's never stale.
let manifest = null;

export function loadPublicManifest(origin) {
  manifest ??= fetch(`${origin}${PUBLIC_PREFIX}/manifest.json`)
    .then((res) => {
      if (!res.ok) throw new Error(`manifest: HTTP ${res.status}`);
      return res.json();
    })
    .then((m) => ({ pages: new Set(m.pages), files: new Set(m.files) }))
    .catch(() => {
      manifest = null; // Retry on the next request; until then nothing is public.
      return NONE;
    });
  return manifest;
}

// "/guide/intro" and "/guide/intro/" are the same page; "/assets/a.png" is a file.
export function pageKey(pathname) {
  const last = pathname.split("/").pop();
  return pathname.endsWith("/") || last.includes(".") ? pathname : `${pathname}/`;
}
