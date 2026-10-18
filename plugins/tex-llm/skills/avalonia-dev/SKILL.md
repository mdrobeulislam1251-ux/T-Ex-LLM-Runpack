---
name: avalonia-dev
description: Use when building a cross-platform desktop app from ONE C#/.NET codebase for Windows + macOS + Linux (optionally mobile/browser) with Avalonia UI (XAML + MVVM, Skia-rendered native binaries — no WebView). The sanctioned native-compiled cross-platform tier; done ONLY when dotnet build exits 0 AND the published binary exists AND the window launches on a target OS — exit-0 alone is "compiled, not run-verified".
---

# Avalonia Dev — Cross-Platform Native Desktop (.NET)

One C#/.NET codebase → Windows, macOS, Linux (and Android/iOS/Browser-WASM if needed), drawn by Skia into real native binaries. NOT a WebView, NOT Electron. This is the sanctioned cross-platform-native tier — pick it when one team + one codebase across the desktop OSes beats per-platform fidelity (`native-app-delivery` has the decision rule).

## When Avalonia vs per-platform native

- **Avalonia** (this skill): LOB/business/tooling/dev-tools apps that must run on all 3 desktop OSes from one codebase, small team, consistent look intended. .NET shop already.
- **Per-platform native** (`windows-dev`/`macos-dev`/`linux-dev`): the product IS the UX, needs best-in-class per-OS feel or deep platform APIs, and you can staff each platform.

## Toolchain verification (run FIRST)

Record each verified tool to `memory/env_paths.json` (tool, version, path, verified_on). PowerShell shown; POSIX twin in parentheses.

| # | Check | Expected | If missing |
|---|---|---|---|
| 1 | `dotnet --version` | `8.0.x` or `9.0.x` | `winget install Microsoft.DotNet.SDK.8` (mac/linux: official installer/apt). Avalonia 11 needs .NET 6+; use 8 LTS |
| 2 | `dotnet --list-sdks` | at least one `8.0` or `9.0` SDK | as above |
| 3 | `dotnet new list avalonia` (after templates installed) | avalonia.app / avalonia.mvvm / avalonia.xplat listed | `dotnet new install Avalonia.Templates` |
| 4 | build tools per TARGET OS you PUBLISH on | native publish for an OS needs that OS or a CI runner | cross-compile produces the assembly; a runnable self-contained binary for macOS/Linux is best built/verified on that OS (or its CI) |

Cross-platform honesty: `dotnet build` works anywhere, but **run-verification of a macOS/Linux build happens on macOS/Linux** (or WSL2 for Linux). On Windows you verify the Windows target; say plainly "generated, not run-verified on <os>" for the others until a real run.

## Scaffold (MVVM, compiled bindings)

`dotnet new avalonia.mvvm -o <App>` (desktop) or `dotnet new avalonia.xplat -o <App>` (adds Android/iOS/Browser heads). Structure:

```
<App>/
├── <App>.csproj              — <TargetFramework>net8.0</TargetFramework>, Avalonia + CommunityToolkit.Mvvm refs
├── Program.cs                — entry: BuildAvaloniaApp().StartWithClassicDesktopLifetime(args)
├── App.axaml / App.axaml.cs  — Application, styles/themes (FluentTheme), DataTemplates
├── ViewLocator.cs            — maps ViewModel -> View by name
├── Views/                    — MainWindow.axaml (+ .axaml.cs); one .axaml per screen
├── ViewModels/               — MainWindowViewModel.cs : ViewModelBase (ObservableObject)
├── Models/                   — plain C# domain types
└── Assets/                   — icons, images (avares:// resources)
```

- **`.axaml`** is Avalonia's XAML extension (not `.xaml`). First line of generated source files carries its target path comment per the pack's portability rule.
- **Compiled bindings ON**: set `x:DataType` on the root of each view and `<AvaloniaXamlIlCompiledBindingsByDefault>true</...>` — turns binding typos into build errors instead of silent runtime blanks.

## MVVM pattern (CommunityToolkit.Mvvm — modern default)

```csharp
// ViewModels/MainWindowViewModel.cs
public partial class MainWindowViewModel : ViewModelBase
{
    [ObservableProperty] private string _greeting = "Ready";
    [ObservableProperty] private bool _isBusy;

    [RelayCommand(CanExecute = nameof(CanRun))]
    private async Task RunAsync()
    {
        IsBusy = true;
        try { Greeting = await _service.DoWorkAsync(); }
        finally { IsBusy = false; }
    }
    private bool CanRun() => !IsBusy;
}
```
```xml
<!-- Views/MainWindow.axaml -->
<Window xmlns="https://github.com/avaloniaui" x:Class="App.Views.MainWindow"
        xmlns:vm="using:App.ViewModels" x:DataType="vm:MainWindowViewModel">
  <StackPanel Margin="16" Spacing="8">
    <TextBlock Text="{Binding Greeting}"/>
    <Button Content="Run" Command="{Binding RunCommand}" IsEnabled="{Binding !IsBusy}"/>
  </StackPanel>
</Window>
```

- `[ObservableProperty]` on `_camelCase` generates the `PascalCase` property + change notification. `[RelayCommand]` on `DoAsync` generates `DoCommand`. Never hand-write `INotifyPropertyChanged`.
- Design-time preview data: `Design.DataContext` in the axaml so the Rider/VS previewer renders.
- UI styling: `FluentTheme` (light+dark) in App.axaml; use `Classes` + selectors, not per-control copy-paste. Accessibility/contrast rules come from `ui-ux-design`.

## Build, run, publish

```sh
dotnet build                                   # compile check (exit 0 = compiled, NOT verified)
dotnet run                                     # launches the window on THIS OS — the real check
# self-contained native binaries per OS:
dotnet publish -c Release -r win-x64    --self-contained -p:PublishSingleFile=true
dotnet publish -c Release -r osx-arm64  --self-contained -p:PublishSingleFile=true
dotnet publish -c Release -r linux-x64  --self-contained -p:PublishSingleFile=true
```
RIDs: `win-x64`, `win-arm64`, `osx-x64`, `osx-arm64`, `linux-x64`, `linux-arm64`. Output under `bin/Release/net8.0/<rid>/publish/`.

## Errors → fixes

| Verbatim output | Fix |
|---|---|
| `AVLN2000 ... Unable to resolve type ... from namespace` in .axaml | Missing `xmlns:` alias or wrong `using:` — declare the namespace on the root element |
| Binding shows blank, no error | Compiled bindings off or wrong `x:DataType` — set it on the view root; typos then become build errors |
| `XamlIlLoaderException ... Cannot find compiled binding` | `x:DataType` doesn't match the ViewModel actually set — align the type |
| `System.PlatformNotSupportedException` at runtime | Called a Windows-only API on mac/Linux — guard with `OperatingSystem.IsWindows()` or use a cross-platform API |
| Previewer blank in IDE | Add `Design.DataContext`; ensure the project builds — the previewer runs the built assembly |
| `The framework 'Microsoft.NETCore.App', version 'x' was not found` on a target box | Publish `--self-contained` (bundles the runtime) or install the matching .NET runtime there |
| Fonts/icons missing after publish | Reference via `avares://<App>/Assets/...` and mark as `AvaloniaResource`, not a loose file path |

## Done-gates

- **Avalonia app done** = `dotnet build` exits 0 AND `dotnet run` opens the window on at least one target OS AND the published self-contained binary exists at the RID path. Exit-0 alone = "compiled, not run-verified".
- **Cross-platform claim done** = run-verified on EACH OS you claim (Windows here, macOS/Linux on their own host/CI) — a Windows-only run does not prove the macOS build; label unverified targets honestly.
- **UI done** = compiled bindings on, light+dark theme render, keyboard reachable (`ui-ux-design` gates) — verified in the running window, not the previewer alone.
