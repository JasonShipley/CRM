#!/usr/bin/env python3
"""Draw the Home Screen icons from the MCE mark in favicon.svg.

    python3 renderer/assets/icons/make_icons.py

Uses the Playwright Chromium the container already has, so there is nothing to
install. The PNGs are committed; re-run this only when the mark changes.

The full-bleed icons are what iOS rounds into its own tile. The maskable one keeps
the bars inside the middle 60%, which is the area Android always shows.
"""
import os
import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent


def mark(size, inset):
    """The favicon's three bars on black, drawn at `size` with `inset` padding
    (a fraction of the side) around the 32-unit design."""
    pad = size * inset
    s = (size - 2 * pad) / 32
    bars = [(5, 7, 22, "#ff6602"), (5, 14.25, 15, "#c8c7c7"), (5, 21.5, 19, "#c8c7c7")]
    rects = "".join(
        f'<rect x="{pad + x * s:.2f}" y="{pad + y * s:.2f}" width="{w * s:.2f}" '
        f'height="{3.5 * s:.2f}" fill="{c}"/>' for x, y, w, c in bars)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}"><rect width="{size}" height="{size}" '
            f'fill="#111111"/>{rects}</svg>')


ICONS = {
    "apple-touch-icon-180.png": (180, 0.06),
    "icon-192.png": (192, 0.06),
    "icon-512.png": (512, 0.06),
    "icon-512-maskable.png": (512, 0.2),
}


def main():
    with sync_playwright() as p:
        # the container's preinstalled Chromium, when the pip Playwright is a
        # different build from the one that downloaded it
        exe = os.environ.get("CHROMIUM_PATH") or (
            "/opt/pw-browsers/chromium"
            if os.path.exists("/opt/pw-browsers/chromium") else None)
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        for name, (size, inset) in ICONS.items():
            page = browser.new_page(viewport={"width": size, "height": size},
                                    device_scale_factor=1)
            page.set_content(f'<html><body style="margin:0">{mark(size, inset)}</body></html>')
            page.screenshot(path=str(HERE / name), omit_background=False,
                            clip={"x": 0, "y": 0, "width": size, "height": size})
            page.close()
            print("wrote", name)
        browser.close()


if __name__ == "__main__":
    main()
