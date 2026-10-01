#!/usr/bin/env python3
"""Rebrand the Hermes desktop electron-builder config to "Caravela" (Layer 2).

Operates on a fresh checkout of hermes-agent. Rewrites the product-identity
fields in apps/desktop/package.json's `build` block and the window <title> in
index.html so the produced installers and the binary present as Caravela.

What it does NOT touch: the Python backend, ~/.hermes, the `hermes` CLI, the
gateway. Those stay Hermes by design — updates and fundamentals ride on the
upstream project. Only the visible desktop-shell identity changes.

Usage:
    python3 rebrand.py <path-to-hermes-agent-checkout>
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PRODUCT = "Caravela"
APP_ID = "com.caravela.app"

HERE = Path(__file__).resolve().parent


def _resolve_assets() -> Path:
    """Installer layout is ../assets. The Windows kit copies assets beside this file."""
    beside = HERE / "assets"
    if (beside / "brand").is_dir():
        return beside
    return HERE.parent / "assets"


ASSETS = _resolve_assets()


def _patch_build_block(b: dict) -> None:
    b["appId"] = APP_ID
    b["productName"] = PRODUCT
    b["executableName"] = PRODUCT
    b["artifactName"] = "Caravela-${version}-${os}-${arch}.${ext}"
    for proto in b.get("protocols", []):
        proto["name"] = "Caravela Protocol"
    mac = b.setdefault("mac", {})
    ext = mac.setdefault("extendInfo", {})
    ext["CFBundleDisplayName"] = PRODUCT
    ext["CFBundleName"] = PRODUCT
    ext["CFBundleExecutable"] = PRODUCT
    win = b.setdefault("win", {})
    win["legalTrademarks"] = PRODUCT
    nsis = b.setdefault("nsis", {})
    nsis["shortcutName"] = PRODUCT
    nsis["uninstallDisplayName"] = PRODUCT
    lin = b.setdefault("linux", {})
    lin["synopsis"] = "Caravela — chart the course."
    lin["maintainer"] = "Caravela <brand@caravela.example>"
    dmg = b.setdefault("dmg", {})
    dmg["title"] = "Install Caravela"


def patch_product_identity(desktop: Path) -> None:
    """Current Hermes keeps packaging identity out of package.json.

    electron-builder.config.cjs reads product-identity.cjs. A missing
    package.json `build` key is that layout, not a failed checkout.
    """
    ident = desktop / "product-identity.cjs"
    if not ident.exists():
        print(f"[warn] no package.json build block and no {ident}")
        return
    src = ident.read_text()
    src = src.replace(
        "appId: `com.nousresearch.${name.kebab}${kebabSuffix}`",
        "appId: 'com.caravela.app'",
    )
    src = src.replace("display: 'Hermes'", "display: 'Caravela'")
    src = src.replace("pascal: 'Hermes'", "pascal: 'Caravela'")
    ident.write_text(src)
    print(f"[ok] rebranded {ident}")

    cfg = desktop / "electron-builder.config.cjs"
    if cfg.exists():
        text = cfg.read_text()
        text = text.replace(
            "maintainer: 'Nous Research <support@nousresearch.com>'",
            "maintainer: 'Caravela <brand@caravela.example>'",
        )
        text = text.replace(
            "'Native desktop shell for Caravela Agent.'",
            "'Caravela — chart the course.'",
        )
        text = text.replace(
            "'Native desktop shell for Hermes Agent.'",
            "'Caravela — chart the course.'",
        )
        # Local packs must not talk to GitHub. electron-builder 27 still
        # constructs the github publisher from this block after the AppImage
        # exists, and dies if GH_TOKEN is unset. The release upload is `gh`,
        # not electron-builder. A leaked token is worse: it auto-publishes.
        old_publish = """  publish: channelRequest ? null : !channel
    ? null
    : [
        publicUrl
          ? { provider: 'generic', url: publicUrl, channel }
          : { provider: 'github', owner, repo, channel }
      ],"""
        if old_publish not in text:
            raise SystemExit(
                "electron-builder.config.cjs publish block moved — "
                "update rebrand.py before packaging, or the build will "
                "die on a missing GH_TOKEN after the AppImage is written."
            )
        text = text.replace(
            old_publish,
            "  publish: null,\n  nativeModules: { npmRebuild: false },",
            1,
        )
        cfg.write_text(text)
        print(f"[ok] rebranded {cfg} (publish disabled)")


def patch_package_json(pkg_path: Path) -> None:
    data = json.loads(pkg_path.read_text())

    data["productName"] = PRODUCT
    data["executableName"] = PRODUCT
    # fpm (.deb/.rpm) requires a homepage; the stock package.json omits it.
    data.setdefault("homepage", "https://github.com/CaravelaLabs/CaravelaWinDesktop")
    data.setdefault("description", "Caravela — chart the course.")

    if "build" in data:
        _patch_build_block(data["build"])
    else:
        print(f"[ok] {pkg_path} has no build block (identity is product-identity.cjs)")
        patch_product_identity(pkg_path.parent)

    pkg_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"[ok] rebranded {pkg_path}")


def patch_index_html(html_path: Path) -> None:
    html = html_path.read_text()
    html = re.sub(r"<title>[^<]*</title>", "<title>Caravela</title>", html, count=1)
    html_path.write_text(html)
    print(f"[ok] rebranded {html_path}")


def patch_main_electron(main_path: Path) -> None:
    # Runtime AppUserModelId must match build.appId, otherwise the Windows
    # taskbar resolves the running window against the OLD Hermes shortcut
    # registration and shows the Hermes icon (and toasts break).
    src = main_path.read_text()
    if APP_ID in src and "com.nousresearch.hermes" not in src:
        print(f"[ok] AUMID already {APP_ID} in {main_path}")
        return
    if "com.nousresearch.hermes" not in src:
        print(f"[warn] AUMID string not found in {main_path} — upstream changed? Check taskbar icon on Windows.")
        return
    src = src.replace("com.nousresearch.hermes", APP_ID)
    main_path.write_text(src)
    print(f"[ok] rebranded AUMID in {main_path}")


def _targeted(path: Path, pairs: list[tuple[str, str]]) -> None:
    src = path.read_text()
    for old, new in pairs:
        if old not in src:
            print(f"[warn] '{old}' not found in {path} — upstream changed? Verify by hand.")
            continue
        src = src.replace(old, new)
    path.write_text(src)
    print(f"[ok] rebranded {path}")


def patch_bootstrap_installer(root: Path) -> None:
    """Rebrand apps/bootstrap-installer (the 'Hermes Setup' updater Tauri app).

    This is the window users see when clicking "Update now" — it must present
    as Caravela Setup. Internals stay Hermes by design: the staged filename
    (hermes-setup.exe — the desktop's resolveUpdaterBinary looks it up by that
    exact name), HERMES_HOME, the `hermes` CLI it drives, and its git remotes.
    """
    bi = root / "apps" / "bootstrap-installer"
    if not bi.exists():
        print("[warn] apps/bootstrap-installer missing — upstream restructured? Setup app NOT rebranded.")
        return

    # 1. Frontend copy: replace standalone 'Hermes' words (strings + comments)
    #    without touching identifiers (launchHermesDesktop, -HermesHome,
    #    Hermes-Setup.exe are all protected by the [\w-] boundaries).
    for f in sorted((bi / "src").rglob("*")):
        if f.suffix not in (".ts", ".tsx"):
            continue
        s = f.read_text()
        s2 = s.replace("Hermes Agent", "Caravela")
        s2 = re.sub(r"(?<![\w-])Hermes(?![\w-])", "Caravela", s2)
        if s2 != s:
            f.write_text(s2)
    print(f"[ok] rebranded setup-app frontend copy in {bi / 'src'}")

    # 2. Brand mark: swap the upstream mascot for the Caravela glyph.
    glyph = ASSETS / "brand" / "caravela" / "glyph.png"
    shutil.copy(glyph, bi / "public" / "caravela-glyph.png")
    (bi / "public" / "nous-girl.jpg").unlink(missing_ok=True)
    _targeted(bi / "src" / "components" / "brand-mark.tsx",
              [("nous-girl.jpg", "caravela-glyph.png")])

    # 3. Tauri identity (display fields only; identifier + [[bin]] name stay —
    #    the binary is renamed to hermes-setup.exe at staging time regardless).
    conf_path = bi / "src-tauri" / "tauri.conf.json"
    conf = json.loads(conf_path.read_text())
    conf["productName"] = PRODUCT
    conf["app"]["windows"][0]["title"] = "Caravela Setup"
    bundle = conf.setdefault("bundle", {})
    bundle["shortDescription"] = "Caravela Setup"
    bundle["longDescription"] = "Installs Caravela on your machine."
    bundle["publisher"] = PRODUCT
    conf_path.write_text(json.dumps(conf, indent=2) + "\n")
    print(f"[ok] rebranded {conf_path}")

    # 4. Windows side-by-side manifest (controls the exe's display description).
    _targeted(bi / "src-tauri" / "hermes-setup.manifest",
              [("Hermes Setup", "Caravela Setup")])

    # 5. Rust: user-visible strings AND the rebuilt-desktop lookup paths.
    #    CRITICAL: our desktop rebrand sets executableName=Caravela, so the
    #    local rebuild produces win-unpacked/Caravela.exe (Caravela.app on mac).
    #    Stock code looks for Hermes.exe and would fail to launch post-update.
    _targeted(bi / "src-tauri" / "src" / "bootstrap.rs", [
        ('"Hermes.exe"', '"Caravela.exe"'),
        ("Hermes.app", "Caravela.app"),
        ('Contents/MacOS", "Hermes")', 'Contents/MacOS", "Caravela")'),
        ('join("Hermes")', 'join("Caravela")'),
        ("built Hermes desktop", "built Caravela desktop"),
        ("launching Hermes desktop", "launching Caravela desktop"),
    ])
    _targeted(bi / "src-tauri" / "src" / "lib.rs",
              [("error while running Hermes Setup", "error while running Caravela Setup")])

    # 6. Window/taskbar icons for the setup app itself.
    # Missing Pillow on a Windows update must not abort the desktop compile.
    icons_dir = bi / "src-tauri" / "icons"
    try:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                [sys.executable, str(HERE / "make-icons.py"),
                 str(ASSETS / "brand-kit" / "logo" / "glyph" / "caravela-glyph-1024.png"), td],
                check=True,
            )
            tmp = Path(td)
            from PIL import Image
            master = Image.open(tmp / "icon.png").convert("RGBA")
            master.resize((32, 32), Image.LANCZOS).save(icons_dir / "32x32.png")
            master.resize((128, 128), Image.LANCZOS).save(icons_dir / "128x128.png")
            master.resize((256, 256), Image.LANCZOS).save(icons_dir / "128x128@2x.png")
            shutil.copy(tmp / "icon.ico", icons_dir / "icon.ico")
            if (tmp / "icon.icns").exists():
                shutil.copy(tmp / "icon.icns", icons_dir / "icon.icns")
        print(f"[ok] regenerated setup-app icons in {icons_dir}")
    except Exception as exc:
        print(f"[warn] setup-app icons skipped ({exc}); desktop compile does not need them")

    # 7. npm metadata (cosmetic).
    pkg_path = bi / "package.json"
    pkg = json.loads(pkg_path.read_text())
    pkg["description"] = "Caravela Setup — installer/updater UI for Caravela."
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")
    print(f"[ok] rebranded {pkg_path}")


def patch_product_git_origin(root: Path) -> None:
    """Caravela installs clone/update from CaravelaWinDesktop, not Nous.

    hermes update follows git origin. If origin stays NousResearch, clicking
    Update rebuilds the Hermes GUI. Only touch installer entrypoints — do not
    rewrite LICENSE / UPSTREAM_README credits.
    """
    pairs = [
        (
            "git@github.com:NousResearch/hermes-agent.git",
            "git@github.com:CaravelaLabs/CaravelaWinDesktop.git",
        ),
        (
            "https://github.com/NousResearch/hermes-agent.git",
            "https://github.com/CaravelaLabs/CaravelaWinDesktop.git",
        ),
        (
            "https://github.com/NousResearch/hermes-agent/archive/",
            "https://github.com/CaravelaLabs/CaravelaWinDesktop/archive/",
        ),
        (
            "https://raw.githubusercontent.com/NousResearch/hermes-agent/",
            "https://raw.githubusercontent.com/CaravelaLabs/CaravelaWinDesktop/",
        ),
    ]
    rels = [
        Path("scripts/install.sh"),
        Path("scripts/install.ps1"),
        Path("apps/bootstrap-installer/src-tauri/src/install_script.rs"),
    ]
    for rel in rels:
        path = root / rel
        if not path.exists():
            print(f"[warn] {path} missing — product git origin NOT rewritten")
            continue
        text = path.read_text()
        new = text
        for old, repl in pairs:
            new = new.replace(old, repl)
        if new != text:
            path.write_text(new)
            print(f"[ok] product git origin → CaravelaWinDesktop in {path}")
        else:
            print(f"[warn] no NousResearch hermes-agent URL in {path}")


def patch_desktop_packaged_executable(root: Path) -> None:
    """Make hermes desktop --build-only accept win-unpacked/Caravela.exe.

    Stock _desktop_packaged_executable only looks for Hermes.exe. electron-builder
    productName=Caravela writes Caravela.exe, so Update packed a valid app,
    reported failure, and relaunched Program Files.
    """
    path = root / "hermes_cli" / "main.py"
    if not path.exists():
        print(f"[warn] {path} missing — Windows exe detector NOT patched")
        return
    src = path.read_text()
    if "_desktop_windows_exe_names" in src:
        print(f"[ok] exe detector already honors productName in {path}")
        return
    old = '''def _desktop_packaged_executable(desktop_dir: Path) -> Optional[Path]:
    """Return the current platform's unpacked Electron app executable."""
    release_dir = desktop_dir / "release"
    if sys.platform == "darwin":
        candidates = list(release_dir.glob("mac*/Hermes.app/Contents/MacOS/Hermes"))
    elif sys.platform == "win32":
        candidates = [
            release_dir / "win-unpacked" / "Hermes.exe",
            release_dir / "win-ia32-unpacked" / "Hermes.exe",
            release_dir / "win-arm64-unpacked" / "Hermes.exe",
        ]
'''
    new = '''def _desktop_windows_exe_names(desktop_dir: Path) -> list:
    """electron-builder output name: branded productName, then Hermes.exe."""
    names: list[str] = []
    pkg = desktop_dir / "package.json"
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        build = data.get("build") if isinstance(data, dict) else {}
        if not isinstance(build, dict):
            build = {}
        for key in (
            build.get("executableName"),
            build.get("productName"),
            data.get("executableName") if isinstance(data, dict) else None,
            data.get("productName") if isinstance(data, dict) else None,
        ):
            if isinstance(key, str):
                n = key.strip()
                if n and n not in names:
                    names.append(n)
    except Exception:
        pass
    if "Hermes" not in names:
        names.append("Hermes")
    return [n if n.lower().endswith(".exe") else f"{n}.exe" for n in names]


def _desktop_packaged_executable(desktop_dir: Path) -> Optional[Path]:
    """Return the current platform's unpacked Electron app executable."""
    release_dir = desktop_dir / "release"
    if sys.platform == "darwin":
        candidates = list(release_dir.glob("mac*/Hermes.app/Contents/MacOS/Hermes"))
    elif sys.platform == "win32":
        candidates = [
            release_dir / folder / name
            for name in _desktop_windows_exe_names(desktop_dir)
            for folder in ("win-unpacked", "win-ia32-unpacked", "win-arm64-unpacked")
        ]
'''
    if old not in src:
        print(f"[warn] _desktop_packaged_executable win32 block not found in {path} — upstream changed?")
        return
    path.write_text(src.replace(old, new, 1))
    print(f"[ok] Windows exe detector honors package.json productName in {path}")


def patch_main_desktop_exe(root: Path) -> None:
    """Current Hermes looks up the exe in main_desktop.py, not main.py.

    A Caravela.exe the detector does not see is an update that 'did not compile'.
    Match the current list comprehension, then any leftover Hermes.exe literal.
    """
    path = root / "hermes_cli" / "main_desktop.py"
    if not path.exists():
        return
    src = path.read_text()
    if "Caravela.exe" in src:
        print(f"[ok] {path} already accepts Caravela.exe")
        return
    old = '''        candidates = [
            release_dir / d / "Hermes.exe" for d in ("win-unpacked", "win-ia32-unpacked", "win-arm64-unpacked")
        ]'''
    new = '''        candidates = [
            release_dir / d / name
            for name in ("Caravela.exe", "Hermes.exe")
            for d in ("win-unpacked", "win-ia32-unpacked", "win-arm64-unpacked")
        ]'''
    if old in src:
        path.write_text(src.replace(old, new, 1))
        print(f"[ok] {path} accepts Caravela.exe")
        return
    if 'release_dir / d / "Hermes.exe"' in src:
        path.write_text(src.replace(
            'release_dir / d / "Hermes.exe"',
            'release_dir / d / n for n in ("Caravela.exe", "Hermes.exe")',
            1,
        ))
        print(f"[ok] {path} accepts Caravela.exe (loose match)")
        return
    print(f"[warn] Windows exe lookup not found in {path} — Update will not see Caravela.exe")


def install_brand_kit(root: Path) -> None:
    """Copy the brander outside the files a later Hermes reset would need from GitHub.

    Windows Update saves this directory to %LOCALAPPDATA% before git reset --hard.
    """
    kit = root / "scripts" / "caravela"
    kit.mkdir(parents=True, exist_ok=True)
    for name in ("apply_brand.py", "rebrand.py", "make-icons.py", "caravela-windows.ps1"):
        src = HERE / name
        if src.exists():
            shutil.copy(src, kit / name)
    brand = ASSETS / "brand"
    glyph = ASSETS / "brand-kit" / "logo" / "glyph"
    if brand.is_dir():
        dest = kit / "assets" / "brand"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(brand, dest, dirs_exist_ok=True)
    if glyph.is_dir():
        dest = kit / "assets" / "brand-kit" / "logo" / "glyph"
        dest.mkdir(parents=True, exist_ok=True)
        for f in glyph.glob("caravela-glyph-1024.png"):
            shutil.copy(f, dest / f.name)
    print(f"[ok] brand kit in {kit}")


def patch_cmd_gui_shortcut_retarget(root: Path) -> None:
    """After a successful pack, retarget Start Menu/Desktop off Program Files."""
    path = root / "hermes_cli" / "main.py"
    if not path.exists():
        return
    src = path.read_text()
    if "_register_caravela_windows_shortcuts" in src:
        print(f"[ok] cmd_gui already retargets Windows shortcuts in {path}")
        return
    helper = '''
def _register_caravela_windows_shortcuts(packaged_executable: Optional[Path]) -> None:
    """Point Start Menu/Desktop at unpacked Caravela.exe, not Program Files NSIS."""
    if sys.platform != "win32" or packaged_executable is None:
        return
    wrapper = PROJECT_ROOT / "scripts" / "desktop-update" / "caravela-windows.ps1"
    if not wrapper.exists():
        return
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", str(wrapper),
                "-InstallRoot", str(PROJECT_ROOT),
                "-RelaunchExe", str(packaged_executable),
                "-RetargetShortcuts",
            ],
            check=False,
            timeout=60,
            capture_output=True,
        )
    except Exception:
        logger.debug("Caravela shortcut retarget skipped", exc_info=True)


'''
    needle = "def _register_linux_desktop_entry() -> None:"
    if needle not in src:
        print(f"[warn] _register_linux_desktop_entry not found in {path}")
        return
    src = src.replace(needle, helper + needle, 1)
    call_old = "    _register_linux_desktop_entry()\n"
    call_new = (
        "    _register_linux_desktop_entry()\n"
        "    _register_caravela_windows_shortcuts(packaged_executable)\n"
    )
    if call_old not in src:
        print(f"[warn] _register_linux_desktop_entry() call not found in {path}")
        path.write_text(src)
        return
    src = src.replace(call_old, call_new, 1)
    path.write_text(src)
    print(f"[ok] cmd_gui retargets Windows shortcuts after pack in {path}")


def patch_install_ps1_desktop_exe(root: Path) -> None:
    """Fresh git installs look for Caravela.exe and write Caravela.lnk."""
    path = root / "scripts" / "install.ps1"
    if not path.exists():
        print(f"[warn] {path} missing — install.ps1 exe lookup NOT patched")
        return
    src = path.read_text()
    old_cands = '''    $exeCandidates = @(
        "$desktopDir\\release\\win-unpacked\\Hermes.exe",
        "$desktopDir\\release\\win-arm64-unpacked\\Hermes.exe"
    )'''
    new_cands = '''    $exeCandidates = @(
        "$desktopDir\\release\\win-unpacked\\Caravela.exe",
        "$desktopDir\\release\\win-arm64-unpacked\\Caravela.exe",
        "$desktopDir\\release\\win-unpacked\\Hermes.exe",
        "$desktopDir\\release\\win-arm64-unpacked\\Hermes.exe"
    )'''
    if "win-unpacked\\Caravela.exe" in src:
        print(f"[ok] install.ps1 already accepts Caravela.exe in {path}")
    elif old_cands not in src:
        print(f"[warn] install.ps1 exe candidate block not found in {path}")
    else:
        src = src.replace(old_cands, new_cands, 1)
        src = src.replace(
            "throw \"Desktop build completed but no Hermes.exe was found under $desktopDir\\release\\*-unpacked\\\"",
            "throw \"Desktop build completed but no Caravela.exe/Hermes.exe was found under $desktopDir\\release\\*-unpacked\\\"",
            1,
        )
        print(f"[ok] install.ps1 accepts Caravela.exe in {path}")
    old_lnk = '''            (Join-Path ([Environment]::GetFolderPath('Programs')) 'Hermes.lnk'),
            (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Hermes.lnk')'''
    new_lnk = '''            (Join-Path ([Environment]::GetFolderPath('Programs')) 'Caravela.lnk'),
            (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Caravela.lnk')'''
    if old_lnk in src:
        src = src.replace(old_lnk, new_lnk, 1)
        src = src.replace("$sc.Description = 'Hermes Agent'", "$sc.Description = 'Caravela'", 1)
        print(f"[ok] install.ps1 shortcuts are Caravela.lnk in {path}")
    elif "Caravela.lnk" in src:
        print(f"[ok] install.ps1 shortcuts already Caravela.lnk in {path}")
    else:
        print(f"[warn] install.ps1 shortcut targets not found in {path}")
    path.write_text(src)


def install_windows_update_wrapper(root: Path) -> None:
    src = HERE / "caravela-windows.ps1"
    dest = root / "scripts" / "desktop-update" / "caravela-windows.ps1"
    if not src.exists():
        print(f"[warn] {src} missing — Windows Update wrapper NOT installed")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    print(f"[ok] installed {dest}")

    updater = root / "apps" / "desktop" / "electron" / "updater-process.ts"
    if not updater.exists():
        return
    text = updater.read_text()
    needle = "    path.join(updateRoot, 'scripts', 'desktop-update', 'windows.ps1'),"
    insert = (
        "    path.join(updateRoot, 'scripts', 'desktop-update', 'caravela-windows.ps1'),\n"
        + needle
    )
    if "caravela-windows.ps1" in text:
        print(f"[ok] updater-process.ts already prefers caravela-windows.ps1")
        return
    if needle not in text:
        print(f"[warn] windows.ps1 candidate not found in {updater}")
        return
    updater.write_text(text.replace(needle, insert, 1))
    print(f"[ok] updater-process.ts prefers caravela-windows.ps1")


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    desktop = root / "apps" / "desktop"
    patch_package_json(desktop / "package.json")
    patch_index_html(desktop / "index.html")
    # upstream ts-ified the electron shell (main.cjs -> main.ts) in v2026.7.7
    main_electron = desktop / "electron" / "main.ts"
    if not main_electron.exists():
        main_electron = desktop / "electron" / "main.cjs"
    patch_main_electron(main_electron)
    patch_bootstrap_installer(root)
    patch_product_git_origin(root)
    patch_desktop_packaged_executable(root)
    patch_main_desktop_exe(root)
    install_brand_kit(root)
    patch_cmd_gui_shortcut_retarget(root)
    patch_install_ps1_desktop_exe(root)
    install_windows_update_wrapper(root)


if __name__ == "__main__":
    main()
