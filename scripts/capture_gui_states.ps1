param(
    [string]$OutputDir = ".\.omo\evidence\task-7-pdf-fidelity-dnd\screenshots"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destination = [System.IO.Path]::GetFullPath((Join-Path $repo $OutputDir))
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class NativeWindow {
    public delegate bool EnumWindowsProc(IntPtr handle, IntPtr parameter);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr handle, out uint processId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr handle, StringBuilder text, int count);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr handle);
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetWindowRect(IntPtr handle, out RECT rect);
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool GetClientRect(IntPtr handle, out RECT rect);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr handle);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr handle, IntPtr deviceContext, uint flags);
    public static IntPtr FindForProcess(int processId, string titlePrefix) {
        IntPtr match = IntPtr.Zero;
        EnumWindows((handle, parameter) => {
            uint owner;
            GetWindowThreadProcessId(handle, out owner);
            if (owner != (uint)processId || !IsWindowVisible(handle)) return true;
            var title = new StringBuilder(512);
            GetWindowText(handle, title, title.Capacity);
            if (title.ToString().StartsWith(titlePrefix, StringComparison.Ordinal)) {
                match = handle;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return match;
    }
}
"@

$states = @("default", "valid-drop", "invalid-drop", "busy", "success", "warning", "error")
$sizes = @(@(760, 620), @(800, 680), @(1200, 900))
$semantic = @{
    "default" = "info-blue"
    "valid-drop" = "drop-valid-blue"
    "invalid-drop" = "drop-rejected-red"
    "busy" = "info-blue"
    "success" = "success-green"
    "warning" = "warning-yellow"
    "error" = "error-red"
}
$manifest = [System.Collections.Generic.List[object]]::new()

foreach ($size in $sizes) {
    foreach ($state in $states) {
        $width = $size[0]
        $height = $size[1]
        $name = "$state-$width`x$height.png"
        $path = Join-Path $destination $name
        $windowTitle = "HWPX GUI QA - $state-$width`x$height"
        $args = @("tests\gui_state_harness.py", "--state", $state, "--width", $width, "--height", $height, "--hold-seconds", "10")
        $process = Start-Process -FilePath "python" -ArgumentList $args -WorkingDirectory $repo -PassThru
        try {
            $deadline = (Get-Date).AddSeconds(20)
            $windowHandle = [IntPtr]::Zero
            while ($windowHandle -eq [IntPtr]::Zero -and (Get-Date) -lt $deadline) {
                Start-Sleep -Milliseconds 100
                $windowHandle = [NativeWindow]::FindForProcess($process.Id, "HWPX GUI QA -")
            }
            if ($windowHandle -eq [IntPtr]::Zero) { throw "GUI window not found: $windowTitle" }
            [NativeWindow]::SetForegroundWindow($windowHandle) | Out-Null
            Start-Sleep -Milliseconds 700
            $rect = [NativeWindow+RECT]::new()
            if (-not [NativeWindow]::GetClientRect($windowHandle, [ref]$rect)) { throw "Could not read GUI client bounds: $windowTitle" }
            $captureWidth = $rect.Right - $rect.Left
            $captureHeight = $rect.Bottom - $rect.Top
            if ($captureWidth -le 0 -or $captureHeight -le 0) { throw "Invalid GUI bounds: $windowTitle" }
            $bitmap = [System.Drawing.Bitmap]::new($captureWidth, $captureHeight)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            try {
                $deviceContext = $graphics.GetHdc()
                try {
                    if (-not [NativeWindow]::PrintWindow($windowHandle, $deviceContext, 1)) { throw "Could not render GUI window: $windowTitle" }
                } finally {
                    $graphics.ReleaseHdc($deviceContext)
                }
                $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
            } finally {
                $graphics.Dispose()
                $bitmap.Dispose()
            }
        } finally {
            if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
            $process.Dispose()
        }
        $item = Get-Item -LiteralPath $path
        if ($item.Length -le 0) { throw "Blank screenshot: $path" }
        $manifest.Add([pscustomobject]@{ state = $state; semantic = $semantic[$state]; label = $state; width = $width; height = $height; path = $path; bytes = $item.Length })
    }
}

$manifestPath = Join-Path $destination "manifest.json"
$manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $manifestPath -Encoding utf8
if ($manifest.Count -ne 21) { throw "Expected 21 screenshots, found $($manifest.Count)" }
Write-Output "Captured $($manifest.Count) screenshots"
