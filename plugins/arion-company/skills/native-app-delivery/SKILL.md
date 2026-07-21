---
name: native-app-delivery
description: Use when building truly-native apps for Android, iOS, macOS, Windows, Linux, or HarmonyOS — or converting a web app to native. Defines the pipeline, the truly-native-only rule, build-host honesty, config injection, auto-heal, and routes to the six platform skills.
---

# Native App Delivery

One doctrine above six platform skills. The platform skills (`android-dev`, `ios-dev`, `macos-dev`, `windows-dev`, `linux-dev`, `harmony-dev`) hold the exact toolchains, scaffolds, and build loops — this skill holds the rules that apply to all of them.

## Truly native only (hard rule)

Forbidden as the app shell/UI: WebView / WKWebView / WebView2, Electron, Tauri, React Native, Flutter, .NET MAUI, Ionic / Cordova / Capacitor, Xamarin, Kotlin Multiplatform UI. Shipping a wrapper = failed task. If the user explicitly WANTS a wrapper stack, that's their call — but say plainly it isn't native and route accordingly.

## Platform routing

| Target | Skill | Stack |
|---|---|---|
| Android | `android-dev` | Kotlin + Jetpack Compose (Material 3) |
| iOS | `ios-dev` | Swift + SwiftUI |
| HarmonyOS | `harmony-dev` | ArkTS + ArkUI |
| Windows | `windows-dev` | C# .NET 8 + WinUI 3 |
| macOS | `macos-dev` | Swift + SwiftUI (macOS) |
| Linux | `linux-dev` | Rust + GTK4 |

**One platform per task.** The Android task never edits the iOS folder. A cross-platform issue = one reported line to the orchestrator, zero edits outside your platform.

## Build-host honesty (probe, don't pretend)

Before promising a build, probe what THIS machine can actually build:

- Windows host: Android, Windows, HarmonyOS directly; Linux via WSL2 (`wsl -l -v`).
- iOS/macOS: require a Mac — locally or over SSH. No Mac reachable = generate code + build instructions, and say plainly "generated, not build-verified — needs a Mac".
- Never build on production servers.

Toolchain gaps found by the platform skill's checks: CLI-sized pieces (SDK packages, workloads, crates) — show the exact install command, then run it. Multi-GB installs (Android Studio, Xcode, DevEco, Visual Studio) — name + size + target path, then WAIT for approval. No silent big downloads.

## Conversion pipeline (web → native, or spec → native)

1. **ANALYZE** — inventory the source: routes/screens, UI states, API calls, auth flows, assets. Write it to `memory/web_analysis.md` in the project.
2. **ABSTRACT** — a platform-NEUTRAL spec (state machines, API contracts, asset manifest) in a `core/` folder as Markdown/JSON. No compilable code there.
3. **GENERATE** — native code per platform, following that platform's skill exactly.
4. **BUILD-VERIFY** — loop until the done-gate passes.

Each platform implements the same spec natively — the spec is the single source of truth, never another platform's code.

## Config injection

Each platform folder keeps `config.tmpl.json` with `{{PLACEHOLDER}}` values (`API_BASE_URL`, `WS_URL`, `ENV_NAME`, feature flags). Generation swaps placeholders into the platform's native config surface: BuildConfig / xcconfig / appsettings / `module.json5` / build features. Secrets never appear in templates, code, or committed files — env/keystore only (`app-security`).

## Auto-heal protocol (build failures)

1. Capture the FULL stderr — never diagnose from the last line alone.
2. Isolate the failing file/task from the first error line.
3. Cross-reference the exact error against current SDK docs — APIs move; your memory of them is stale by default.
4. Rewrite using the corrected API; rebuild.
5. Log each attempt (error + fix applied) to `memory/heal_log.md`.
6. **Same error five times = STOP and report** — don't guess a sixth time.

## Done-gate (all three, no exceptions)

1. Build exits 0, AND
2. the artifact exists at the expected output path (`.apk`, `.app`, `.exe`, `.hap`, binary), AND
3. the app demonstrably launches on a host that can run it (device, emulator, simulator, window opens).

Exit 0 alone = report as **"compiled, not run-verified"**. Generated-but-unbuilt code is never "done".

## Memory convention

`memory/env_paths.json` — every verified tool (name, version, path, verified_on). `memory/heal_log.md` — every build failure + fix. Read both before resuming native work; update after any environment change. This is what makes session two faster than session one.
