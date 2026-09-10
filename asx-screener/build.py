#!/usr/bin/env python3
"""
Wrap app.html (the shared UI, also used as the Claude Artifact) into
index.html — a standalone, installable PWA with the iOS home-screen
metadata Safari needs. Run after editing app.html:

    python build.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "app.html").read_text()

# app.html holds <title>/<style>/<link> first, then the page body.
SPLIT = '<div class="wrap">'
head_src, body_src = src.split(SPLIT, 1)
body_src = SPLIT + body_src

HEAD = """<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Screen ASX shares for a P/E under 10, positive cash flow, and no pharma or mining explorers.">

<!-- Home-screen app (iOS + Android) -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Deep Value">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#eef0f4" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0b0f15" media="(prefers-color-scheme: dark)">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
"""

RESET_AND_IOS = """
<style>
  /* base reset (the Artifact host supplies this; a standalone page needs its own) */
  :root{color-scheme:light dark}
  html{-webkit-text-size-adjust:100%}
  body{margin:0}
  img{max-width:100%}
  [hidden]{display:none!important}

  /* Installed-app chrome: keep content clear of the notch / home indicator,
     and stop the rubber-band scroll showing a mismatched ground. */
  body{
    background:var(--ground);
    min-height:100svh;
    padding-left:env(safe-area-inset-left);
    padding-right:env(safe-area-inset-right);
  }
  .wrap{
    padding-top:env(safe-area-inset-top);
    padding-bottom:calc(env(safe-area-inset-bottom) + 48px);
  }
  /* No text selection flicker or tap highlight when used as an app */
  .switch,.rank,input[type=range],summary{-webkit-tap-highlight-color:transparent}
  .switch,.rank,summary{-webkit-user-select:none;user-select:none}
</style>
</head>
<body>
"""

SW = """
<script>
  if ("serviceWorker" in navigator && location.protocol === "https:") {
    addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(()=>{}));
  }
</script>
</body>
</html>
"""

(HERE / "index.html").write_text(HEAD + head_src.strip() + RESET_AND_IOS + body_src.rstrip() + SW)
print("wrote index.html")
