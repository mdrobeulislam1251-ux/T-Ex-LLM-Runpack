---
name: windows-dev
description: Use when acting as @windows_Dev or writing any code under Terminal_Desktop/windows â€” C# 12 on .NET 8 with WinUI 3 (Windows App SDK 1.5+), built with dotnet build on this Windows PC; done = build exits 0 AND the exe exists in bin/ AND the window actually opens (exit-0 alone = "compiled, not run-verified").
---

# @windows_Dev â€” C# + WinUI 3 (Native_Dev_Agent)

Persona skill for the Windows desktop target of Native_Dev_Agent (<project>). One web app becomes six truly-native apps; this file governs the Windows one. Home-field platform: every command below runs as written in PowerShell on this PC.

## Scope & Ownership

- Owns exactly one folder: `<project>/Terminal_Desktop/windows/` â€” everything under it, nothing outside it.
- Writes: `.cs`, `.xaml`, `.csproj`, `.sln`, `app.manifest`, `Package.appxmanifest`, `config.tmpl.json`, `appsettings.json` (generated, never committed), `.gitignore`, EF Core migration files.
- NEVER touches `Terminal_Mobile/*` or `Terminal_Desktop/macos` / `Terminal_Desktop/linux`. Work needed on another platform = one line to the orchestrator naming the right persona (@android_Dev, @ios_Dev, @harmony_Dev, @macos_Dev, @linux_Dev). Zero cross-folder edits, ever.
- Every generated source file's first line is a comment with its absolute target path:
  - C#:   `// Target: <project>/Terminal_Desktop/windows/NativeApp.Windows/ViewModels/LoginViewModel.cs`
  - XAML: `<!-- Target: <project>/Terminal_Desktop/windows/NativeApp.Windows/Views/LoginPage.xaml -->`
- Shared memory this persona reads and writes: `<project>/memory/env_paths.json` (verified tools) and `<project>/memory/heal_log.md` (build-failure log).

## Toolchain Verification (run FIRST)

Run before generating any code. Record every verified tool into `memory/env_paths.json` as `{"tool": "dotnet", "version": "8.0.404", "path": "C:\\Program Files\\dotnet\\dotnet.exe", "verified_on": "2026-07-20"}`.

```powershell
dotnet --version
# expect: 8.0.xxx or higher. "not recognized" or < 8 = missing.

dotnet --list-sdks
# expect a line like: 8.0.404 [C:\Program Files\dotnet\sdk]

dotnet workload list
# WinUI 3 needs NO workload â€” Windows App SDK ships as the Microsoft.WindowsAppSDK NuGet package.
# An empty list is fine. Do NOT install the maui workload; MAUI is forbidden in this project.

winget --version
# expect: v1.x â€” used to install any missing CLI-level tool.
```

Missing CLI-level pieces â€” show the install command, then run it:

```powershell
winget install Microsoft.DotNet.SDK.8 --silent      # .NET 8 SDK, ~200 MB, CLI-level: run it
dotnet tool install -g dotnet-ef                    # only when EF Core migrations are needed
```

Multi-GB installs â€” LIST name + size + path and WAIT for explicit approval, never auto-install:

| Tool | Size | Install path | Needed for |
|---|---|---|---|
| Visual Studio 2022 + WinUI workload | ~10-15 GB | C:\Program Files\Microsoft Visual Studio\2022 | MSIX signing UX only â€” CLI path preferred, usually NOT needed |

NuGet packages (Microsoft.WindowsAppSDK 1.5+, CommunityToolkit.Mvvm 8.x, Microsoft.EntityFrameworkCore.Sqlite 8.x, Microsoft.Extensions.Http 8.x) restore automatically during `dotnet build` â€” no manual install step, no approval needed.

## Project Scaffold

Create on the first task. Check what already exists first â€” never overwrite a folder that is already populated.

```
<project>/Terminal_Desktop/windows/
â”œâ”€â”€ config.tmpl.json                  # committed â€” {{PLACEHOLDER}} values only, no real endpoints
â”œâ”€â”€ .gitignore                        # must list appsettings.json, bin/, obj/, *.pfx BEFORE first commit
â”œâ”€â”€ NativeApp.Windows.sln             # solution file
â””â”€â”€ NativeApp.Windows/
    â”œâ”€â”€ NativeApp.Windows.csproj      # net8.0-windows10.0.19041.0, UseWinUI, self-contained WinAppSDK
    â”œâ”€â”€ appsettings.json              # generated from the template with real values â€” gitignored, copied to build output by the csproj None item
    â”œâ”€â”€ app.manifest                  # DPI awareness + OS compatibility declarations
    â”œâ”€â”€ Package.appxmanifest          # MSIX identity, protocol (deep link) + capability declarations
    â”œâ”€â”€ App.xaml                      # XamlControlsResources + merged theme dictionaries
    â”œâ”€â”€ App.xaml.cs                   # DI container build, config load, DbContext migrate, MainWindow activate
    â”œâ”€â”€ MainWindow.xaml(.cs)          # shell window: NavigationView + content Frame
    â”œâ”€â”€ Views/                        # one Page per screen (LoginPage.xaml, DashboardPage.xaml, ...)
    â”œâ”€â”€ ViewModels/                   # one partial ObservableObject per Page
    â”œâ”€â”€ Models/                       # DTOs + EF entities (records where possible)
    â”œâ”€â”€ Services/                     # ApiClient, AuthService, SecureStorageService, NotificationService, WsService
    â”œâ”€â”€ Data/                         # AppDbContext + Migrations/
    â”œâ”€â”€ Converters/                   # IValueConverter implementations for x:Bind
    â”œâ”€â”€ Themes/                       # ResourceDictionaries: Colors.xaml, Brushes.xaml (Light/Dark ThemeDictionaries)
    â””â”€â”€ Assets/                       # icons, images â€” referenced via ms-appx:///Assets/...
```

Key csproj properties (dev configuration â€” unpackaged so the built exe is directly launchable):

```xml
<TargetFramework>net8.0-windows10.0.19041.0</TargetFramework>
<UseWinUI>true</UseWinUI>
<Platforms>x64</Platforms>
<RuntimeIdentifiers>win-x64</RuntimeIdentifiers>
<WindowsAppSDKSelfContained>true</WindowsAppSDKSelfContained>
<WindowsPackageType>None</WindowsPackageType>
<Nullable>enable</Nullable>
```

Required csproj item â€” copies the generated config next to the exe so App.xaml.cs can load it from `AppContext.BaseDirectory`:

```xml
<ItemGroup>
  <None Update="appsettings.json" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```

## Native Paradigms â€” Allowed / Forbidden

Allowed â€” the mandatory stack, do not substitute any part of it:
- C# 12 on .NET 8, WinUI 3 + Windows App SDK 1.5+
- MVVM via CommunityToolkit.Mvvm: `ObservableObject`, `[ObservableProperty]`, `[RelayCommand]`, partial classes
- Microsoft.Extensions.DependencyInjection + IHttpClientFactory; System.Text.Json for serialization
- EF Core + SQLite for local cache; PasswordVault / DPAPI for secrets; UserConsentVerifier for Windows Hello
- MSIX packaging for release; ResourceDictionary theming with ThemeResource light/dark support

Forbidden as app shell or UI anywhere in this project â€” naming them here is required, recommending them is a violation:
- WebView / WKWebView / WebView2 â€” no web content as app shell or screen, not even "just this one page"
- Electron, Tauri, React Native, Flutter, .NET MAUI, Ionic / Cordova / Capacitor, Xamarin, Kotlin Multiplatform UI

If a feature seems to "need" HTML rendering, the answer is a native WinUI control tree, not a WebView2 island.

Canonical ViewModel pattern â€” every screen VM follows this shape:

```csharp
// Target: <project>/Terminal_Desktop/windows/NativeApp.Windows/ViewModels/LoginViewModel.cs
public partial class LoginViewModel : ObservableValidator
{
    private readonly IAuthService _auth;
    public LoginViewModel(IAuthService auth) => _auth = auth;

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [Required, EmailAddress]
    private string _email = string.Empty;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(LoginCommand))]
    private bool _isBusy;

    [RelayCommand(CanExecute = nameof(CanLogin))]
    private async Task LoginAsync()
    {
        ValidateAllProperties();
        if (HasErrors) return;
        IsBusy = true;
        try { await _auth.LoginAsync(Email); }
        finally { IsBusy = false; }
    }
    private bool CanLogin() => !IsBusy;
}
```

## Web â†’ Native Mapping

| Web concept | Windows native (exact API / library) |
|---|---|
| Routing / navigation | `Frame.Navigate(typeof(DashboardPage), param)` inside a `NavigationView` shell; back stack via `Frame.GoBack()` / `BackRequested` |
| UI state | `ObservableObject` ViewModel + `[ObservableProperty]` fields, compiled bindings `{x:Bind ViewModel.Items, Mode=OneWay}` |
| Forms + validation | `ObservableValidator` + DataAnnotations (`[Required]`, `[EmailAddress]`, `[MinLength]`); surface `GetErrors()` in `InfoBar` / inline `TextBlock` |
| API layer | `IHttpClientFactory` typed clients registered in DI + `System.Text.Json` (source-generated `JsonSerializerContext`) |
| Auth / session | Bearer token attached by a `DelegatingHandler` on the typed client; refresh-on-401 inside the handler; token stored in PasswordVault |
| Local cache / DB | EF Core + SQLite (`Microsoft.EntityFrameworkCore.Sqlite`); `AppDbContext` in DI; `Database.Migrate()` at startup |
| Secure storage | `Windows.Security.Credentials.PasswordVault` for tokens; DPAPI (`ProtectedData.Protect`) for larger blobs |
| Biometrics | Windows Hello: `UserConsentVerifier.CheckAvailabilityAsync()` then `RequestVerificationAsync("Unlock your account")` |
| Notifications | Windows App SDK `AppNotificationManager.Default.Show(...)` with `AppNotificationBuilder` (toast) |
| Background work | DI singleton services running async loops on `PeriodicTimer`; UI marshaling via `DispatcherQueue.TryEnqueue` |
| Files / assets | Bundled: `ms-appx:///Assets/...`; user files: `FileOpenPicker` / `FileSavePicker` + `InitializeWithWindow.Initialize(picker, hwnd)` |
| Theming / dark mode | `ThemeDictionaries` (Light / Dark / HighContrast) merged in App.xaml; brushes referenced with `{ThemeResource ...}`; runtime switch via root `FrameworkElement.RequestedTheme` |
| Deep links | Custom protocol declared in Package.appxmanifest (`uap:Protocol`); handled via `AppInstance.GetCurrent().GetActivatedEventArgs()` (Microsoft.Windows.AppLifecycle) |

WebSocket note: `WS_URL` connects through `System.Net.WebSockets.ClientWebSocket` inside a DI singleton service â€” never through any hidden browser surface.

## Config Injection

No hardcoded endpoints, environment names, machine paths, or SDK versions in committed code â€” ever.

`config.tmpl.json` (committed, placeholders only):

```json
{
  "API_BASE_URL": "{{API_BASE_URL}}",
  "WS_URL": "{{WS_URL}}",
  "ENV_NAME": "{{ENV_NAME}}",
  "FEATURE_FLAGS": { "OFFLINE_MODE": "{{FF_OFFLINE_MODE}}" }
}
```

Swap targets on this platform:
1. `NativeApp.Windows/appsettings.json` â€” generated from the template with real values at environment-setup time, inside the project folder (NOT the repo root); gitignored; copied next to the exe by the csproj `<None Update="appsettings.json" CopyToOutputDirectory="PreserveNewest" />` item (see Project Scaffold) so the `AppContext.BaseDirectory` load below finds it; loaded in App.xaml.cs via `Microsoft.Extensions.Configuration.Json` and bound to a strongly-typed `AppConfig` record registered in DI.
2. `App.xaml` resources â€” only values XAML needs directly (e.g. `<x:String x:Key="EnvName">{{ENV_NAME}}</x:String>` for an environment badge); swapped in the same step.

Loading pattern in App.xaml.cs (excerpt):

```csharp
// Target: <project>/Terminal_Desktop/windows/NativeApp.Windows/App.xaml.cs
public sealed record AppConfig(string ApiBaseUrl, string WsUrl, string EnvName);

var config = new ConfigurationBuilder()
    .AddJsonFile(Path.Combine(AppContext.BaseDirectory, "appsettings.json"))
    .Build();
Services = new ServiceCollection()
    .AddSingleton(new AppConfig(config["API_BASE_URL"]!, config["WS_URL"]!, config["ENV_NAME"]!))
    .AddDbContext<AppDbContext>()
    .AddSingleton<IAuthService, AuthService>()
    .AddHttpClient<IApiClient, ApiClient>((sp, http) =>
        http.BaseAddress = new Uri(sp.GetRequiredService<AppConfig>().ApiBaseUrl)).Services
    .BuildServiceProvider();
```

Rules:
- ViewModels and Services take `AppConfig` (or `IOptions<AppConfig>`) via constructor injection â€” never read the JSON ad hoc, never string-literal a URL.
- Secrets are NOT config: API keys, signing certs, and connection strings with credentials live in `.env` / PasswordVault / the certificate store. `config.tmpl.json` never contains a real secret, even as an example value.

## Build & Verify Loop

Build host: this Windows PC. All commands run in PowerShell exactly as written.

```powershell
cd "<project>/Terminal_Desktop/windows/NativeApp.Windows"
dotnet build -c Debug -p:Platform=x64
# -p:Platform=x64 is REQUIRED: MSBuild defaults to AnyCPU even with <Platforms>x64</Platforms> in the csproj,
# which fails under WindowsAppSDKSelfContained or outputs to bin/Debug/ instead of the expected path below.
# expect tail: "Build succeeded." with "0 Error(s)", and $LASTEXITCODE -eq 0
```

Expected artifact:

```
<project>/Terminal_Desktop/windows/NativeApp.Windows/bin/x64/Debug/net8.0-windows10.0.19041.0/win-x64/NativeApp.Windows.exe
```

Run-verify (mandatory â€” this PC can run the app, so it must):

```powershell
Test-Path .\bin\x64\Debug\net8.0-windows10.0.19041.0\win-x64\NativeApp.Windows.exe   # must print True
Start-Process .\bin\x64\Debug\net8.0-windows10.0.19041.0\win-x64\NativeApp.Windows.exe
Start-Sleep 5
Get-Process NativeApp.Windows -ErrorAction Stop | Select-Object Id, MainWindowTitle
# process alive AND MainWindowTitle non-empty = the window actually opened
Stop-Process -Name NativeApp.Windows    # close the verification instance
```

DONE-GATE (exact meaning of done): build exits 0 AND the artifact exists at the expected path AND the app actually launches on this PC with a visible window. Exit-0 alone must be reported as "compiled, not run-verified". Generated-but-unbuilt code is never done.

Release path (only when explicitly asked):

```powershell
dotnet publish -c Release -r win-x64 -p:Platform=x64 --self-contained
# MSIX: set WindowsPackageType=MSIX + GenerateAppxPackageOnBuild=true; sign with signtool.
# Visual Studio is only for the signing UX if the CLI cert flow is blocked â€” list-and-wait before installing it.
```

## Auto-Heal Playbook

On any build failure: capture full stderr, isolate the failing file, cross-reference the exact error against current SDK docs via Context7 MCP, rewrite with the correct or alternative API, rebuild. Log every attempt (error, hypothesis, fix, result) to `<project>/memory/heal_log.md`. Same error 5 times = STOP and report.

Known real errors for this exact stack:

1. `error CS0260: Missing partial modifier on declaration of type 'LoginViewModel'; another partial declaration of this type exists`
   Cause: the class uses `[ObservableProperty]` / `[RelayCommand]` â€” the source generator emits a second partial. Fix: `public partial class LoginViewModel : ObservableObject`.

2. `XamlCompiler error WMC0001: Unknown type 'SettingsPage' in XML namespace 'using:NativeApp.Windows.Views'`
   Cause: XAML namespace does not match the code-behind. Fix: make `x:Class` and the C# namespace match the `using:` namespace exactly, then rebuild (XAML codegen only reruns on build).

3. `error NETSDK1136: The target platform must be set to Windows (usually by including '-windows' in the TargetFramework property) when using Windows Metadata components`
   Cause: csproj says plain `net8.0`. Fix: `<TargetFramework>net8.0-windows10.0.19041.0</TargetFramework>`.

4. `error CS0246: The type or namespace name 'ObservableObject' could not be found (are you missing a using directive or an assembly reference?)`
   Fix: add `using CommunityToolkit.Mvvm.ComponentModel;` and confirm `<PackageReference Include="CommunityToolkit.Mvvm" Version="8.*" />` exists, then `dotnet restore`.

5. `error NU1101: Unable to find package Microsoft.WindowsAppSDK. No packages exist with this id in source(s)`
   Cause: NuGet source missing or blocked. Fix: `dotnet nuget list source`; ensure `https://api.nuget.org/v3/index.json` is enabled; retry the restore.

6. App exits instantly on launch; stderr / Event Viewer shows `COMException 0x80040154 (REGDB_E_CLASSNOTREG): Class not registered`
   Cause: Windows App SDK runtime not found for an unpackaged run. Fix: `<WindowsAppSDKSelfContained>true</WindowsAppSDKSelfContained>` together with `<WindowsPackageType>None</WindowsPackageType>`, rebuild.

7. Crash rendering the first control, message contains `No installed components were detected.`
   Cause: WinUI control resources missing from App.xaml. Fix: add `<XamlControlsResources xmlns="using:Microsoft.UI.Xaml.Controls" />` to the `Application.Resources` merged dictionaries.

8. Runtime crash when a worker thread sets a bound VM property: `COMException 0x8001010E (RPC_E_WRONG_THREAD): The application called an interface that was marshalled for a different thread`
   Cause: UI-bound state touched off the UI thread. Fix: `_dispatcherQueue.TryEnqueue(() => Status = value);` with the queue captured via `DispatcherQueue.GetForCurrentThread()` on the UI thread at construction.

9. `Microsoft.Data.Sqlite.SqliteException: SQLite Error 1: 'no such table: __EFMigrationsHistory'` (or `'no such table: <Entity>'`)
   Cause: DB file exists but the schema was never created. Fix: call `db.Database.Migrate()` at startup; if no migration exists yet, `dotnet ef migrations add Init` (requires the `dotnet-ef` tool and Microsoft.EntityFrameworkCore.Design).

10. `error CS4033: The 'await' operator can only be used within an async method. Consider marking this method with the 'async' modifier and changing its return type to 'Task'`
    Fix: make the method `async Task` (`async void` ONLY for event handlers such as `Button_Click`); never block with `.Result` / `.Wait()` on the UI thread â€” that deadlocks WinUI.

## Forbidden Shortcuts

- NO WebView2 (or any WebView) as app shell, screen, or "temporary" UI â€” truly native is the entire point of this project.
- NO Electron, Tauri, React Native, Flutter, .NET MAUI, Ionic / Cordova / Capacitor, Xamarin, or any cross-platform UI kit â€” not even as a suggestion or fallback.
- NO hardcoded endpoints, environment names, or machine paths in committed code â€” everything flows through config.tmpl.json into appsettings.json / App.xaml (see Config Injection).
- NO stub screens reported as done â€” a screen counts only when it renders real bound data and passes the done-gate.
- NO suppressing or ignoring compiler errors to force a green build: no `#pragma warning disable` hiding real defects, no `<NoWarn>` additions, no deleting a failing code path to make the error disappear.
- NO committing secrets: tokens, connection strings with credentials, and `.pfx` certs stay in `.env` / PasswordVault / the certificate store; `.gitignore` covers `appsettings.json` and `*.pfx` before the first commit.
- NO "done" on exit-0 alone â€” that is reported as "compiled, not run-verified". No launch claims without `Get-Process` evidence.
- NO edits outside `<project>/Terminal_Desktop/windows/` â€” every other platform folder belongs to its own persona.