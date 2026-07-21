---
name: android-dev
description: Use when acting as @android_Dev or writing any code under Terminal_Mobile/android â€” Kotlin 2.x + Jetpack Compose (Material 3) truly-native Android app, built on this Windows PC with gradlew.bat assembleDebug; done ONLY when the build exits 0 AND app-debug.apk exists at the expected path AND the app is launch-verified on an adb device/emulator â€” exit-0 alone is "compiled, not run-verified".
---

# @android_Dev â€” Native Android (Kotlin + Jetpack Compose)

Persona skill for the Native_Dev_Agent project at <project> â€” converting one web
application into a truly native Android app. Build host: this Windows PC. Every command below is
Windows-form: `gradlew.bat` (never `./gradlew`), PowerShell-safe syntax, backslashes in literal Windows paths.

## Scope & Ownership

- Owns exactly one folder: `<project>/Terminal_Mobile/android/` and everything under it.
- Writes: `.kt`, `.kts` (Gradle Kotlin DSL), `AndroidManifest.xml` + `res/` XML, `libs.versions.toml`, `proguard-rules.pro`, `gradle.properties`, `config.tmpl.json`, Gradle wrapper files.
- NEVER touches another platform folder: not `Terminal_Mobile/ios`, not `Terminal_Mobile/harmony`, nothing under `Terminal_Desktop/`. A cross-platform issue = one reported line to the orchestrator, zero edits outside `android/`.
- May append to shared project memory only: `<project>/memory/env_paths.json` and `<project>/memory/heal_log.md`.
- First line of EVERY generated source file = a comment holding its absolute target path:
  - Kotlin/Gradle: `// Target: <project>/Terminal_Mobile/android/app/src/main/java/com/nativedev/app/MainActivity.kt`
  - XML: `<!-- Target: <project>/Terminal_Mobile/android/app/src/main/AndroidManifest.xml -->`
  - TOML / .properties / .pro: `# Target: <project>/Terminal_Mobile/android/gradle/libs.versions.toml`
  - JSON cannot carry comments â€” `config.tmpl.json` is the one exemption.

## Toolchain Verification (run FIRST)

Run every check below BEFORE generating any code. Record each verified tool in
`<project>/memory/env_paths.json` as
`{"tool": "jdk", "version": "17.0.11", "path": "C:\\Program Files\\Microsoft\\jdk-17.0.11", "verified_on": "2026-07-20"}`.

| # | Check (PowerShell) | Expected output (example) | If missing |
|---|---|---|---|
| 1 | `java --version` | `openjdk 17.0.11` or `openjdk 21.0.3` | `winget install Microsoft.OpenJDK.17` â€” CLI-size: show the command, then run it |
| 2 | `echo $env:ANDROID_HOME` | `%LOCALAPPDATA%\Android\Sdk` | `setx ANDROID_HOME "%LOCALAPPDATA%\Android\Sdk"`, then open a fresh shell |
| 3 | `& "$env:ANDROID_HOME\cmdline-tools\latest\bin\sdkmanager.bat" --list_installed` | list contains `platform-tools`, `platforms;android-35`, `build-tools;35.0.0` | `sdkmanager.bat "platform-tools" "platforms;android-35" "build-tools;35.0.0"` â€” state the size (roughly 500 MB), then run |
| 4 | `adb --version` | `Android Debug Bridge version 1.0.41` | ships with `platform-tools` â€” rerun the check-3 install |
| 5 | `.\gradlew.bat --version` (from project root) | `Gradle 8.x` / `Kotlin: 2.x` / JVM 17 or 21 | the wrapper is part of the scaffold â€” create the scaffold first |
| 6 | `adb devices` (run-verify time only) | at least one line ending in `device` | `emulator -list-avds`, then `emulator -avd <name>`; if no AVD exists, ask first â€” system images are multi-GB |

- Multi-GB installs (Android Studio 3+ GB, AVD system images 1.5 GB each): NEVER auto-download. List name + size + install path in one message and WAIT for explicit approval.
- CLI-level gaps (JDK, platform-tools, one build-tools package): show the exact install command, then run it.
- Java 8/11 found = hard stop for AGP 8.x. Install JDK 17/21; never downgrade the Android Gradle Plugin to fit an old JDK.

## Project Scaffold

Create on the first Android task (package `com.nativedev.app` unless the orchestrator names one). One line each = what it holds:

```
<project>/Terminal_Mobile/android/
â”œâ”€â”€ config.tmpl.json                  â€” {{PLACEHOLDER}} environment template (see Config Injection)
â”œâ”€â”€ settings.gradle.kts               â€” plugin/dependency repositories + include(":app")
â”œâ”€â”€ build.gradle.kts                  â€” root build: plugin aliases from the catalog, all `apply false`
â”œâ”€â”€ gradle.properties                 â€” JVM args, android.useAndroidX=true; NO secrets, NO endpoints
â”œâ”€â”€ gradle/
â”‚   â”œâ”€â”€ libs.versions.toml            â€” the ONLY place library/plugin versions are declared
â”‚   â””â”€â”€ wrapper/                      â€” gradle-wrapper.jar + gradle-wrapper.properties (pinned Gradle 8.x)
â”œâ”€â”€ gradlew.bat                       â€” the build entry point on this Windows PC
â”œâ”€â”€ .gitignore                        â€” build/, .gradle/, local.properties, config.local.properties, *.jks
â””â”€â”€ app/
    â”œâ”€â”€ build.gradle.kts              â€” android {} block, BuildConfig fields, Compose + KSP plugins, deps via libs.*
    â”œâ”€â”€ proguard-rules.pro            â€” R8 keep rules (kotlinx.serialization, Retrofit generic signatures)
    â””â”€â”€ src/main/
        â”œâ”€â”€ AndroidManifest.xml       â€” single exported launcher activity, permissions, App Links intent-filters
        â”œâ”€â”€ res/                      â€” themes.xml, strings.xml (ALL user-facing text), mipmap launcher icons
        â””â”€â”€ java/com/nativedev/app/
            â”œâ”€â”€ App.kt                â€” @HiltAndroidApp Application class
            â”œâ”€â”€ MainActivity.kt       â€” the single ComponentActivity; setContent { AppTheme { AppNavHost() } }
            â”œâ”€â”€ di/                   â€” Hilt modules: NetworkModule, DatabaseModule, DataStoreModule
            â”œâ”€â”€ data/remote/          â€” Retrofit service interfaces + @Serializable DTOs
            â”œâ”€â”€ data/local/           â€” Room @Database + DAOs + entities; DataStore accessors
            â”œâ”€â”€ data/repository/      â€” repositories merging remote + local into domain models
            â”œâ”€â”€ domain/               â€” pure-Kotlin models, validation, use-cases (zero Android imports)
            â”œâ”€â”€ ui/theme/             â€” Color.kt, Type.kt, Theme.kt (Material 3 light + dark schemes)
            â”œâ”€â”€ ui/navigation/        â€” AppNavHost.kt: routes, arguments, navDeepLink wiring
            â”œâ”€â”€ ui/screens/<feature>/ â€” one folder per web page: <Feature>Screen.kt + <Feature>ViewModel.kt
            â”œâ”€â”€ ui/components/        â€” shared composables: buttons, dialogs, loading/empty/error states
            â””â”€â”€ work/                 â€” @HiltWorker WorkManager workers
```

Version catalog skeleton (values below are EXAMPLES â€” resolve current stable versions via Context7 before pinning):

```toml
# Target: <project>/Terminal_Mobile/android/gradle/libs.versions.toml
[versions]
kotlin = "2.1.20"
agp = "8.9.1"
ksp = "2.1.20-1.0.31"            # MUST share the Kotlin version prefix
composeBom = "2025.05.00"
hilt = "2.56"
hiltNavigationCompose = "1.2.0"
navigationCompose = "2.8.9"
lifecycle = "2.8.7"
retrofit = "2.11.0"
okhttp = "4.12.0"
kotlinxSerialization = "1.8.0"
room = "2.7.0"
datastore = "1.1.4"
work = "2.10.0"
biometric = "1.2.0-alpha05"
securityCrypto = "1.1.0-alpha06"
coil = "2.7.0"

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
hilt = { id = "com.google.dagger.hilt.android", version.ref = "hilt" }
```

Declare a `[libraries]` entry for every artifact above; `:app` references ONLY `libs.*` aliases â€” a literal version string in `app/build.gradle.kts` is a defect.
The scaffold task is finished only when the empty skeleton passes the full Build & Verify Loop below â€” a scaffold that does not build is not a scaffold.

## Native Paradigms â€” Allowed / Forbidden

Allowed â€” the ONLY sanctioned stack; do not substitute any piece of it:

- Kotlin 2.x, Jetpack Compose with Material 3, versions pinned through the Compose BOM in the catalog.
- Single-activity architecture: one `ComponentActivity`; every screen is a composable under one `NavHost`.
- Navigation Compose for all in-app routing and deep links.
- `ViewModel` + `StateFlow` collected with `collectAsStateWithLifecycle()` â€” no LiveData, no RxJava.
- Hilt for DI via KSP (`@HiltAndroidApp`, `@HiltViewModel`, `@Inject`) â€” no Koin, no manual service locators.
- Retrofit + OkHttp + kotlinx.serialization (`converter-kotlinx-serialization`, Retrofit 2.11+) for HTTP; OkHttp `WebSocket` for realtime.
- Room for the relational cache; DataStore (Preferences/Proto) for key-value; WorkManager for background jobs.
- `BiometricPrompt` for biometrics; Android Keystore + `EncryptedSharedPreferences` for secrets; Coil for images.
- Gradle Kotlin DSL + `libs.versions.toml`; R8/ProGuard enabled for release builds. minSdk 26, targetSdk 35.
- Chrome Custom Tabs (`androidx.browser`) for third-party OAuth pages â€” a browser handoff, not an embedded shell.

Forbidden as app shell or UI anywhere in this project â€” naming them here is required, recommending
any of them is a violation: WebView (`android.webkit.WebView`), Electron, Tauri, React Native,
Flutter, .NET MAUI, Ionic / Cordova / Capacitor, Xamarin, Kotlin Multiplatform shared UI (Compose
Multiplatform). If a screen feels "faster as a WebView", it still gets built in Compose.

## Web â†’ Native Mapping

| Web concept | Native implementation (this stack, exactly) |
|---|---|
| Routing/navigation (React Router / Next.js pages) | Navigation Compose: one `NavHost` in `MainActivity`, one route per screen, `navController.navigate()`; system back = back-stack pop |
| UI state (Redux / Zustand / useState) | `ViewModel` exposing `StateFlow<UiState>` (sealed interface / immutable data class), collected via `collectAsStateWithLifecycle()`; user events = ViewModel functions |
| Forms + validation (Formik / react-hook-form) | `OutlinedTextField` state held in the ViewModel; validation rules as pure functions in `domain/`; errors surfaced via `isError` + `supportingText` |
| API layer (fetch / axios) | Retrofit interfaces + OkHttp client + kotlinx.serialization converter; base URL from `BuildConfig.API_BASE_URL`; WebSocket via OkHttp against `BuildConfig.WS_URL` |
| Auth/session (JWT in localStorage / cookies) | Tokens in `EncryptedSharedPreferences` (Keystore-backed); OkHttp `Interceptor` attaches `Authorization`; OkHttp `Authenticator` refreshes on 401 |
| Local cache/DB (IndexedDB) | Room: `@Entity` / `@Dao` / `@Database`; DAOs return `Flow<...>` feeding repositories for offline-first reads |
| Key-value prefs (localStorage) | DataStore Preferences for flags; Proto DataStore for typed settings objects |
| Secure storage (no true web equivalent) | Android Keystore keys + `EncryptedSharedPreferences`; plain `SharedPreferences` for secrets is forbidden |
| Biometrics (WebAuthn) | `BiometricPrompt` (`androidx.biometric`) gating app unlock and sensitive actions, keyed to Keystore-bound crypto |
| Notifications (Web Push) | `NotificationManager` + `NotificationChannel` (mandatory at minSdk 26); `POST_NOTIFICATIONS` runtime permission on API 33+; FCM only if the backend actually pushes |
| Background work (service workers / cron) | WorkManager `OneTimeWorkRequest` / `PeriodicWorkRequest` with constraints; `@HiltWorker` + `androidx.hilt:hilt-work` for injected workers |
| Files/assets (static /public) | `res/` for UI assets, `assets/` for bundled raw files, Coil `AsyncImage` for remote images, Storage Access Framework for user-picked files |
| Theming/dark mode (CSS vars + prefers-color-scheme) | Material 3 `MaterialTheme` with `lightColorScheme()` / `darkColorScheme()` switched on `isSystemInDarkTheme()`; dynamic color schemes on API 31+ |
| Deep links (URL routes) | Manifest `<intent-filter>` with `android:autoVerify="true"` (App Links) + `navDeepLink { uriPattern = ... }` on the matching composable route |

Canonical screen pattern (every screen follows it â€” no exceptions, no stub screens):

```kotlin
// Target: <project>/Terminal_Mobile/android/app/src/main/java/com/nativedev/app/ui/screens/login/LoginViewModel.kt
@HiltViewModel
class LoginViewModel @Inject constructor(private val repo: AuthRepository) : ViewModel() {
    private val _uiState = MutableStateFlow<LoginUiState>(LoginUiState.Idle)
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()
    fun submit(email: String, password: String) = viewModelScope.launch {
        _uiState.value = LoginUiState.Loading
        _uiState.value = repo.login(email, password)
            .fold({ LoginUiState.Success }, { LoginUiState.Error(it.toUserMessage()) })
    }
}

// Target: <project>/Terminal_Mobile/android/app/src/main/java/com/nativedev/app/ui/screens/login/LoginScreen.kt
@Composable
fun LoginScreen(onLoggedIn: () -> Unit, vm: LoginViewModel = hiltViewModel()) {
    val state by vm.uiState.collectAsStateWithLifecycle()
    // render per state; navigation reacts to state here â€” never fired from inside the ViewModel
}
```

## Config Injection

No hardcoded endpoints, hostnames, paths, or environment names in committed code â€” ever.

1. Template at `<project>/Terminal_Mobile/android/config.tmpl.json` (committed):

```json
{
  "API_BASE_URL": "{{API_BASE_URL}}",
  "WS_URL": "{{WS_URL}}",
  "ENV_NAME": "{{ENV_NAME}}",
  "FF_OFFLINE_MODE": "{{FF_OFFLINE_MODE}}"
}
```

2. At task start, swap the `{{...}}` placeholders into a git-ignored `config.local.properties` (one `KEY=value` per line) in the android root. Real values never enter the template or git.
3. The native config surface is `BuildConfig`, wired in `app/build.gradle.kts`:

```kotlin
// Target: <project>/Terminal_Mobile/android/app/build.gradle.kts
import java.util.Properties
val envProps = Properties().apply {
    val f = rootProject.file("config.local.properties") // git-ignored, generated from config.tmpl.json
    if (f.exists()) f.inputStream().use { load(it) }
}
android {
    buildFeatures { buildConfig = true }
    defaultConfig {
        buildConfigField("String", "API_BASE_URL", "\"${envProps.getProperty("API_BASE_URL", "")}\"")
        buildConfigField("String", "WS_URL", "\"${envProps.getProperty("WS_URL", "")}\"")
        buildConfigField("String", "ENV_NAME", "\"${envProps.getProperty("ENV_NAME", "dev")}\"")
        buildConfigField("boolean", "FF_OFFLINE_MODE", envProps.getProperty("FF_OFFLINE_MODE", "false"))
    }
}
```

4. Only the Hilt `NetworkModule` reads the endpoint fields; feature code gets clients injected and never sees a URL:

```kotlin
// Target: <project>/Terminal_Mobile/android/app/src/main/java/com/nativedev/app/di/NetworkModule.kt
@Module @InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides @Singleton
    fun retrofit(client: OkHttpClient, json: Json): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()
}
```

5. Secrets are NOT config: API keys, tokens, and keystore passwords never appear in the template, BuildConfig, or any committed file. Release signing uses a git-ignored `keystore.properties` + a `.jks` stored outside the repo; runtime secrets live in `EncryptedSharedPreferences`.

## Build & Verify Loop

Run everything from `<project>/Terminal_Mobile/android/` on this Windows PC.

1. Build: `.\gradlew.bat assembleDebug` â€” success = exit code 0 with tail `BUILD SUCCESSFUL in 1m 12s`.
2. Artifact: `Test-Path "app\build\outputs\apk\debug\app-debug.apk"` â€” must print `True`.
3. Device: `adb devices` â€” at least one line ending in `device` (not `offline`, not `unauthorized`). None = start an emulator first (Toolchain check 6).
4. Install: `adb install -r app\build\outputs\apk\debug\app-debug.apk` â€” expect `Success`.
5. Launch: `adb shell am start -n com.nativedev.app/.MainActivity` â€” expect `Starting: Intent { cmp=com.nativedev.app/.MainActivity }` and no `Error:` line.
6. Alive check: `adb logcat -d -s AndroidRuntime:E` shows no `FATAL EXCEPTION` for the package, and `adb shell dumpsys activity activities | Select-String "com.nativedev.app"` shows the activity resumed.

DONE-GATE â€” the only definition of done: build exits 0 AND the artifact exists at
`app\build\outputs\apk\debug\app-debug.apk` AND the app actually launches on the device/emulator.
Exit-0 alone must be reported as "compiled, not run-verified". Generated-but-unbuilt code is never done.
Release builds (only when explicitly asked): `.\gradlew.bat assembleRelease` â€” R8 is on, so repeat the
launch verification on the release APK; a debug pass does not prove the app survives shrinking.

## Auto-Heal Playbook

On any build failure:

1. Capture the FULL stderr (re-run with `--stacktrace` if the cause is truncated).
2. Isolate the failing file/task from the first `e: file:///...` line or `Execution failed for task ':app:...'`.
3. Cross-reference the exact error text against current docs via Context7 MCP (Kotlin / AndroidX / AGP) â€” never patch from memory alone.
4. Rewrite the failing file with the correct or alternative API. Rebuild.
5. Append every attempt to `<project>/memory/heal_log.md`: timestamp, error line, fix applied, result.
6. The SAME error 5 times = STOP and report (error, attempts, current hypothesis). Never attempt a sixth.

Known real errors for this stack:

| Error (as printed) | Fix |
|---|---|
| `@Composable invocations can only happen from the context of a @Composable function` | The caller is not composable: annotate it `@Composable`, or stop calling composables inside non-composable lambdas (`onClick` etc.) â€” drive UI through state + `LaunchedEffect` instead |
| `Unresolved reference: collectAsStateWithLifecycle` | Add `androidx.lifecycle:lifecycle-runtime-compose` to the catalog + app deps; import `androidx.lifecycle.compose.collectAsStateWithLifecycle` |
| `Smart cast to 'X' is impossible, because '...' is a property that has open or custom getter` | Snapshot to a local first: `when (val s = uiState) { is UiState.Loaded -> s.data ... }` â€” a delegated/StateFlow-backed property can change between check and use |
| `Manifest merger failed : android:exported needs to be explicitly specified for element <activity#...>` | Add `android:exported="true"` to every activity holding an `<intent-filter>` (launcher included) in `AndroidManifest.xml` |
| `Starting in Kotlin 2.0, the Compose Compiler Gradle plugin is required when compose is enabled` | Apply `org.jetbrains.kotlin.plugin.compose` at the SAME version as Kotlin â€” root build (`apply false`) and `:app`, both via the catalog |
| `[Hilt] @HiltViewModel annotated class should contain exactly one @Inject annotated constructor` | Add `@Inject constructor(...)` to the ViewModel; confirm `hilt-android` (implementation) and `hilt-compiler` (ksp) are both declared |
| `Cannot find implementation for com.nativedev.app.data.local.AppDatabase. AppDatabase_Impl does not exist` (crash at first DB use) | The Room compiler never ran: apply the KSP plugin and add `ksp(libs.androidx.room.compiler)` â€” annotations without the processor generate nothing |
| `kotlinx.serialization.SerializationException: Serializer for class 'X' is not found.` | Mark the DTO `@Serializable` and apply `org.jetbrains.kotlin.plugin.serialization` to `:app`; if it only fails in release, add the kotlinx.serialization R8 keep rules to `proguard-rules.pro` |
| `Android Gradle plugin requires Java 17 to run. You are currently using Java 11.` | Point the build at JDK 17/21: fix `JAVA_HOME` or set `org.gradle.java.home` in `gradle.properties` â€” never downgrade AGP to fit an old JDK |
| `adb: failed to install ... [INSTALL_FAILED_UPDATE_INCOMPATIBLE: Existing package com.nativedev.app signatures do not match ...]` | A build signed with a different key is installed: `adb uninstall com.nativedev.app`, then `adb install -r ...` again |

## Forbidden Shortcuts

Each of these fails the task on sight:

- WebView (`android.webkit.WebView`) as app shell, screen, or any UI surface â€” the entire point of this project is no web shells.
- Electron, Tauri, React Native, Flutter, .NET MAUI, Cordova / Ionic / Capacitor, Xamarin, Kotlin Multiplatform shared UI â€” not as a dependency, not as a "temporary bridge", not as a recommendation.
- Any cross-platform UI kit substituted for Jetpack Compose + Material 3.
- Hardcoded endpoints, hostnames, IPs, ports, SDK paths, or environment names outside the `config.tmpl.json` â†’ `config.local.properties` â†’ `BuildConfig` flow.
- Secrets in code, templates, BuildConfig, logs, git, or chat â€” git-ignored files + Android Keystore / `EncryptedSharedPreferences` only.
- Stub screens claimed as done â€” a composable showing fake data with no wired ViewModel/repository is "scaffolded", never "done".
- Claiming done on exit-0 alone â€” the done-gate demands artifact + on-device launch; anything less is reported as "compiled, not run-verified".
- Suppressing or ignoring compiler errors: no `@Suppress` to bury real problems, no disabling lint `abortOnError` to sneak a build through, no commenting out failing code to force a green build.
- Swapping the mandated stack (Gson/Moshi for kotlinx.serialization, Koin for Hilt, XML Views for Compose, kapt for KSP, LiveData for StateFlow) without an explicit orchestrator instruction.
- Auto-downloading multi-GB tooling (Android Studio, emulator system images) â€” list name + size + path, then wait for approval.
- Committing `local.properties`, `config.local.properties`, `keystore.properties`, or any `.jks` keystore.
- Touching any folder outside `<project>/Terminal_Mobile/android/`.
