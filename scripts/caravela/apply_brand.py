#!/usr/bin/env python3
"""Apply the Caravela desktop brand to a Hermes checkout.

This replaces caravela-source.patch. A frozen unified diff dies on the first
upstream move (seen 2026-09-21, 09-22, 09-29: compile exits in ~4s, the
update wrapper then installs a stale GitHub AppImage and reports success).

What this does:
  - Adds the branding slot, Caravela theme, and forced default skin.
  - Points the empty-chat wordmark, sidebar mark, and backdrop at brand assets.
  - Makes Update prefer ~/caravela-installer/automation/posix-update-wrapper.sh
    so a click never falls through to stock Hermes posix.sh.
  - Rewrites standalone user-facing "Hermes" to "Caravela".

What this never touches:
  - Wire names: X-Hermes-Session-Token, HERMES_*, hermes://, lowercase hermes.
  - The Python backend. That stays upstream Hermes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PRODUCT = "Caravela"
SKIP_DIRS = {
    "node_modules", "dist", "release", "build", ".git", "out",
    "linux-unpacked", "win-unpacked",
}
TEXT_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs", ".html", ".css", ".json", ".md"}
# Standalone Hermes only. Hyphen/word chars on either side protect
# X-Hermes-Session-Token, launchHermesDesktop, hermes-agent, HERMES_HOME.
HERMES_WORD = re.compile(r"(?<![\w-])Hermes(?![\w-])")

THEME_BLOCK = r'''
/**
 * Caravela — brand identity for Caravela.
 * Navy / parchment / signal at 70/20/10. Signal is accent and focus only.
 */
export const caravelaTheme: DesktopTheme = {
  name: 'caravela',
  label: 'Caravela',
  description: 'Navy, parchment, and signal orange — chart the course',
  colors: {
    background: '#FBF8F2',
    foreground: '#0A2540',
    card: '#FFFFFF',
    cardForeground: '#0A2540',
    muted: '#F4EEE3',
    mutedForeground: '#3D4A5C',
    popover: '#FFFFFF',
    popoverForeground: '#0A2540',
    primary: '#123A6E',
    primaryForeground: '#FBF8F2',
    secondary: '#F4EEE3',
    secondaryForeground: '#123A6E',
    accent: '#E86A1C',
    accentForeground: '#FBF8F2',
    border: '#D9CFBC',
    input: '#D9CFBC',
    ring: '#E86A1C',
    midground: '#123A6E',
    composerRing: '#123A6E',
    destructive: '#B42318',
    destructiveForeground: '#FBF8F2',
    sidebarBackground: '#F4EEE3',
    sidebarBorder: '#D9CFBC',
    userBubble: '#F4EEE3',
    userBubbleBorder: '#D9CFBC'
  },
  darkColors: {
    background: '#0A2540',
    foreground: '#F4EEE3',
    card: '#123A6E',
    cardForeground: '#F4EEE3',
    muted: '#173E78',
    mutedForeground: '#A8B4C8',
    popover: '#123A6E',
    popoverForeground: '#F4EEE3',
    primary: '#F4EEE3',
    primaryForeground: '#0A2540',
    secondary: '#173E78',
    secondaryForeground: '#F4EEE3',
    accent: '#E86A1C',
    accentForeground: '#0A2540',
    border: '#1F4A8A',
    input: '#1F4A8A',
    ring: '#E86A1C',
    midground: '#E86A1C',
    composerRing: '#E86A1C',
    destructive: '#C0473A',
    destructiveForeground: '#F4EEE3',
    sidebarBackground: '#08203A',
    sidebarBorder: '#1F4A8A',
    userBubble: '#173E78',
    userBubbleBorder: '#2E6FBF'
  },
  typography: {
    fontSans: `"Inter Tight", "Work Sans", ${SYSTEM_SANS}`,
    fontMono: `"JetBrains Mono", ${SYSTEM_MONO}`,
    fontUrl:
      'https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap'
  },
  branding: {
    productName: 'Caravela',
    brandMarkUrl: 'brand/caravela/glyph.png',
    backdropUrl: 'brand/caravela/backdrop.svg',
    wordmarkUrl: 'brand/caravela/wordmark.png',
    backdropMode: 'motif'
  }
}

'''

BRANDING_TYPES = '''
/** Window title, sidebar mark, backdrop, wordmark. Other themes omit this. */
export interface DesktopBranding {
  productName?: string
  brandMarkUrl?: string
  backdropUrl?: string
  wordmarkUrl?: string
  /** 'motif' renders the asset full-cover with no photo invert/blend. */
  backdropMode?: 'photo' | 'motif'
}

'''

UPDATER_HOOK = '''  const home = process.env.HOME || os.homedir()
  const caravelaWrapper = path.join(home, 'caravela-installer', 'automation', 'posix-update-wrapper.sh')
  if (exists(caravelaWrapper)) {
    return {
      command: '/bin/bash',
      args: [caravelaWrapper],
      scriptPath: caravelaWrapper
    }
  }

'''


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def write(path: Path, text: str) -> None:
    path.write_text(text)
    print(f"[ok] {path}")


def ensure_types(path: Path) -> None:
    text = path.read_text()
    if "interface DesktopBranding" not in text:
        needle = "export interface DesktopTheme {"
        if needle not in text:
            die(f"DesktopTheme interface missing in {path}")
        text = text.replace(needle, BRANDING_TYPES + needle, 1)
    if "branding?: DesktopBranding" not in text:
        needle = "  customCSS?: string\n}"
        if needle not in text:
            die(f"customCSS field missing in {path}; cannot attach branding")
        text = text.replace(
            needle,
            "  customCSS?: string\n  branding?: DesktopBranding\n}",
            1,
        )
    write(path, text)


def ensure_theme(path: Path) -> None:
    text = path.read_text()
    if "export const caravelaTheme" not in text:
        needle = "export const BUILTIN_THEMES"
        if needle not in text:
            die(f"BUILTIN_THEMES missing in {path}")
        text = text.replace(needle, THEME_BLOCK + needle, 1)
    if "caravela: caravelaTheme" not in text:
        text = text.replace(
            "cyberpunk: cyberpunkTheme\n}",
            "cyberpunk: cyberpunkTheme,\n  caravela: caravelaTheme\n}",
            1,
        )
        if "caravela: caravelaTheme" not in text:
            die("could not register caravela in BUILTIN_THEMES")
    text = re.sub(
        r"export const DEFAULT_SKIN_NAME = '[^']+'",
        "export const DEFAULT_SKIN_NAME = 'caravela'",
        text,
        count=1,
    )
    if "DEFAULT_SKIN_NAME = 'caravela'" not in text:
        die("DEFAULT_SKIN_NAME assignment missing")
    write(path, text)


def ensure_brand_mark(path: Path) -> None:
    text = path.read_text()
    if "theme.branding?.brandMarkUrl" in text:
        print(f"[ok] brand mark already wired {path}")
        return
    old = """export function BrandMark({ className, ...props }: React.ComponentProps<'span'>) {
  const { renderedMode } = useTheme()
  const dark = renderedMode === 'dark'

  return (
    <span className={cn('inline-flex size-14 shrink-0 items-center justify-center', className)} {...props}>
      <img alt=\"\" className=\"size-full object-contain\" src={assetPath(dark ? 'nous-girl-dark.png' : 'nous-girl.png')} />
    </span>
  )
}"""
    new = """export function BrandMark({ className, ...props }: React.ComponentProps<'span'>) {
  const { renderedMode, theme } = useTheme()
  const branded = theme.branding?.brandMarkUrl
  const dark = renderedMode === 'dark'
  const src = branded
    ? assetPath(branded)
    : assetPath(dark ? 'nous-girl-dark.png' : 'nous-girl.png')

  return (
    <span className={cn('inline-flex size-14 shrink-0 items-center justify-center', className)} {...props}>
      <img alt=\"\" className=\"size-full object-contain\" src={src} />
    </span>
  )
}"""
    if old not in text:
        print(f"[warn] BrandMark shape changed in {path}; sidebar mark stays upstream")
        return
    write(path, text.replace(old, new, 1))


def ensure_backdrop(path: Path) -> None:
    text = path.read_text()
    if "backdropMode" in text and "useTheme" in text:
        print(f"[ok] backdrop already wired {path}")
        return
    if "export function Backdrop()" not in text:
        die(f"Backdrop() missing in {path}")
    if "import { useTheme }" not in text:
        text = "import { useTheme } from '@/themes'\n" + text
    old = """export function Backdrop() {
  const on = useStore($backdrop)

  if (!on) {
    return null
  }

  return (
    <div aria-hidden className=\"pointer-events-none absolute inset-0 z-2 opacity-[0.025] mix-blend-difference\">
      <img
        alt=\"\"
        className=\"h-[160dvh] w-auto min-w-dvw object-cover object-left-top [filter:invert(var(--backdrop-invert-mul,1))]\"
        fetchPriority=\"low\"
        src={assetPath('ds-assets/filler-bg0.jpg')}
      />
    </div>
  )
}"""
    new = """export function Backdrop() {
  const on = useStore($backdrop)
  const { theme } = useTheme()
  const branding = theme.branding
  const backdropUrl = branding?.backdropUrl
  const motif = branding?.backdropMode === 'motif' && backdropUrl

  if (!on && !motif) {
    return null
  }

  if (motif) {
    return (
      <div aria-hidden className=\"pointer-events-none absolute inset-0 z-2\" role=\"img\" aria-label=\"Caravela atmospheric backdrop\">
        <img alt=\"\" className=\"h-full w-full object-cover\" fetchPriority=\"low\" src={assetPath(backdropUrl)} />
      </div>
    )
  }

  return (
    <div aria-hidden className=\"pointer-events-none absolute inset-0 z-2 opacity-[0.025] mix-blend-difference\">
      <img
        alt=\"\"
        className=\"h-[160dvh] w-auto min-w-dvw object-cover object-left-top [filter:invert(var(--backdrop-invert-mul,1))]\"
        fetchPriority=\"low\"
        src={assetPath(backdropUrl ?? 'ds-assets/filler-bg0.jpg')}
      />
    </div>
  )
}"""
    if old not in text:
        print(f"[warn] Backdrop() shape changed in {path}; backdrop stays upstream")
        return
    write(path, text.replace(old, new, 1))


def ensure_intro(path: Path) -> None:
    text = path.read_text()
    if "theme.branding?.wordmarkUrl" in text:
        print(f"[ok] intro wordmark already wired {path}")
        return
    if "import { useTheme }" not in text:
        text = text.replace("import { useI18n } from '@/i18n'\n", "import { useI18n } from '@/i18n'\nimport { useTheme } from '@/themes'\n", 1)
    text = text.replace("const WORDMARK = 'HERMES AGENT'\n\n", "", 1)
    old = """  const { t } = useI18n()
  const rotationSeed = mountSeed + (seed ?? 0)"""
    new = """  const { t } = useI18n()
  const { theme } = useTheme()
  const wordmarkUrl = theme.branding?.wordmarkUrl
  const productName = theme.branding?.productName ?? 'Caravela'
  const wordmark = productName.toUpperCase()
  const wordmarkSrc = wordmarkUrl ? `${import.meta.env.BASE_URL}${wordmarkUrl.replace(/^\\//, '')}` : null
  const rotationSeed = mountSeed + (seed ?? 0)"""
    if old not in text:
        print(f"[warn] Intro() hook shape changed in {path}; wordmark stays upstream")
        return
    text = text.replace(old, new, 1)
    old_mark = """        <Wordmark className=\"mb-1\" text={WORDMARK} />"""
    new_mark = """        {wordmarkSrc ? (
          <div aria-label={wordmark} className=\"mx-auto mb-1 flex w-[calc(100%-1rem)] items-center justify-center\">
            <img alt={wordmark} className=\"h-16 w-auto max-w-full object-contain\" src={wordmarkSrc} />
          </div>
        ) : (
          <Wordmark className=\"mb-1\" text={wordmark} />
        )}"""
    if old_mark not in text:
        print(f"[warn] Wordmark render missing in {path}")
        return
    write(path, text.replace(old_mark, new_mark, 1))


def ensure_title(path: Path) -> None:
    text = path.read_text()
    if "theme.branding?.productName" in text:
        print(f"[ok] window title already wired {path}")
        return
    needle = "  const root = document.documentElement\n"
    if needle not in text:
        die(f"applyTheme root assignment missing in {path}")
    text = text.replace(
        needle,
        needle + "  document.title = theme.branding?.productName ?? 'Caravela'\n",
        1,
    )
    write(path, text)


def ensure_updater(path: Path) -> None:
    text = path.read_text()
    if "posix-update-wrapper.sh" in text:
        print(f"[ok] update wrapper already preferred {path}")
        return
    needle = "  const scriptPath = path.join(updateRoot, 'scripts', 'desktop-update', 'posix.sh')\n"
    if needle not in text:
        print(f"[warn] posix.sh handoff missing in {path}; Linux wrapper not hooked")
        return
    write(path, text.replace(needle, UPDATER_HOOK + needle, 1))


def ensure_index(path: Path) -> None:
    text = path.read_text()
    text = text.replace('<meta name="theme-color" content="#0a0a0a" />', '<meta name="theme-color" content="#123A6E" />', 1)
    text = text.replace("bg = dark ? '#111111' : '#f7f7f7'", "bg = dark ? '#0A2540' : '#FBF8F2'", 1)
    text = HERMES_WORD.sub(PRODUCT, text)
    write(path, text)


def sweep(desktop: Path) -> int:
    n = 0
    for path in desktop.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.stat().st_size > 4_000_000:
            continue
        text = path.read_text(errors="replace")
        new = HERMES_WORD.sub(PRODUCT, text)
        if new != text:
            path.write_text(new)
            n += 1
    print(f"[ok] rewrote standalone Hermes → {PRODUCT} in {n} files")
    return n


def verify(desktop: Path) -> None:
    presets = (desktop / "src/themes/presets.ts").read_text()
    types = (desktop / "src/themes/types.ts").read_text()
    updater = (desktop / "electron/updater-process.ts").read_text()
    intro = (desktop / "src/components/chat/intro.tsx").read_text()
    html = (desktop / "index.html").read_text()
    main = (desktop / "electron/main.ts").read_text()
    checks = [
        ("caravela theme", "name: 'caravela'" in presets),
        ("default skin", "DEFAULT_SKIN_NAME = 'caravela'" in presets),
        ("branding type", "branding?: DesktopBranding" in types),
        ("auth header kept", "X-Hermes-Session-Token" in main),
        ("auth header not renamed", "X-Caravela-Session-Token" not in main),
    ]
    soft = [
        ("update wrapper", "posix-update-wrapper.sh" in updater),
        ("wordmark", "wordmarkUrl" in intro),
        ("title", "<title>Caravela</title>" in html),
    ]
    bad = [name for name, ok in checks if not ok]
    if bad:
        die("brand verify failed: " + ", ".join(bad))
    missed = [name for name, ok in soft if not ok]
    if missed:
        print("[warn] brand soft-miss: " + ", ".join(missed))
    print("[ok] brand verify passed")


def main() -> None:
    if len(sys.argv) != 2:
        die("usage: apply_brand.py <hermes-agent-checkout>")
    root = Path(sys.argv[1]).resolve()
    desktop = root / "apps" / "desktop"
    if not desktop.is_dir():
        die(f"not a hermes checkout: {root}")
    ensure_types(desktop / "src/themes/types.ts")
    ensure_theme(desktop / "src/themes/presets.ts")
    ensure_brand_mark(desktop / "src/components/brand-mark.tsx")
    ensure_backdrop(desktop / "src/components/Backdrop.tsx")
    ensure_intro(desktop / "src/components/chat/intro.tsx")
    ensure_title(desktop / "src/themes/context.tsx")
    ensure_updater(desktop / "electron/updater-process.ts")
    ensure_index(desktop / "index.html")
    sweep(desktop)
    verify(desktop)


if __name__ == "__main__":
    main()
