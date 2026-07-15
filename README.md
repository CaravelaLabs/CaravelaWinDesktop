<p align="center">
  <img src="apps/desktop/public/brand/caravela/wordmark.png" alt="Caravela" width="420">
</p>

<h1 align="center">Caravela Desktop</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Work%20in%20Progress-orange?style=for-the-badge" alt="Work in Progress">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT">
  <img src="https://img.shields.io/badge/Platform-Windows%20x64-blue?style=for-the-badge" alt="Windows x64">
</p>

> **⚠️ Work in Progress** — This repository hosts the in-development desktop client that **Caravela** is building for its customers. It is not yet a finished product: expect rough edges, breaking changes, and frequent rebases on upstream. Use at your own risk until a stable release is announced.

## What is this?

**Caravela Desktop** is Caravela's branded desktop agent client. It is a downstream distribution of the excellent open-source [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com), re-themed and packaged under the Caravela visual identity for Caravela's customers.

What this fork changes relative to upstream:

- **Branding & theme** — Caravela visual identity (logo, wordmark, colors, backdrop) applied across the desktop app, installer, and updater.
- **User-facing copy** — product name shown in the UI, dialogs, notifications, and update flow reads "Caravela".
- **Release channel** — installers (`caravela-<version>-win-x64.exe`, versioned by release date, e.g. `caravela-2026.7.15-win-x64.exe`) are built and published on this repository's [Releases](../../releases) page; the app's self-update mechanism points here.

What this fork does **not** change: the agent's functionality. All core capabilities are upstream Hermes Agent — see the preserved original documentation in [`UPSTREAM_README.md`](UPSTREAM_README.md) and the upstream docs at [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/docs/).

## Download & install

**[⬇ Download the latest Windows installer](https://github.com/CaravelaCompute/CaravelaWinDesktop/releases/latest)** — grab the `caravela-<version>-win-x64.exe` asset and run it.

Every release on the [Releases](../../releases) page ships the installer as an attached asset, so a working download is always available here. The app self-updates from this repository afterwards.

## Staying current with upstream

This repository automatically tracks upstream `hermes-agent` releases: when Nous Research tags a new version, our build pipeline rebases the Caravela branding layer on top of it, rebuilds the Windows installer, and publishes a matching release here.

## License, attribution & compliance

This project is a fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), which is licensed under the **MIT License**, Copyright (c) 2025 Nous Research.

In accordance with the MIT License:

- The original license text and copyright notice are preserved unmodified in [`LICENSE`](LICENSE).
- The original project README is preserved in [`UPSTREAM_README.md`](UPSTREAM_README.md).
- All modifications made in this fork (branding, copy, packaging, release automation) are also released under the MIT License.

Caravela is not affiliated with, endorsed by, or sponsored by Nous Research. "Hermes" and "Nous Research" are names of the upstream project and its authors; they are referenced here solely for attribution. All credit for the underlying agent technology goes to Nous Research and the hermes-agent contributors.

## Security

Please do not report security issues in public issues. See [`SECURITY.md`](SECURITY.md) (upstream policy) — for issues specific to the Caravela distribution, contact Caravela directly.
