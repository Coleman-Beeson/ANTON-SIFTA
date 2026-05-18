#!/usr/bin/env bash
# Build a tiny macOS app bundle that requests Camera permission through
# AVFoundation with NSCameraUsageDescription present in Info.plist.

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$(dirname "$DIR")"
STATE_DIR="${REPO_DIR}/.sifta_state"
SRC_FILE="${STATE_DIR}/sifta_camera_tcc_src.swift"
APP_DIR="${STATE_DIR}/SiftaCameraTCC.app"
BIN_DIR="${APP_DIR}/Contents/MacOS"
INFO_PLIST="${APP_DIR}/Contents/Info.plist"

mkdir -p "$STATE_DIR"

cat > "$SRC_FILE" <<'EOF'
import AppKit
import AVFoundation
import Foundation

let receiptURL = URL(fileURLWithPath: "/tmp/sifta_camera_tcc_result.txt")

func receipt(_ line: String) {
    let payload = "\(Date()) \(line)\n"
    if let data = payload.data(using: .utf8) {
        if FileManager.default.fileExists(atPath: receiptURL.path),
           let handle = try? FileHandle(forWritingTo: receiptURL) {
            try? handle.seekToEnd()
            try? handle.write(contentsOf: data)
            try? handle.close()
        } else {
            try? data.write(to: receiptURL)
        }
    }
    print(line)
}

func statusName(_ status: AVAuthorizationStatus) -> String {
    switch status {
    case .authorized: return "authorized"
    case .denied: return "denied"
    case .restricted: return "restricted"
    case .notDetermined: return "notDetermined"
    @unknown default: return "unknown"
    }
}

func printDevices() {
    let devices = AVCaptureDevice.DiscoverySession(
        deviceTypes: [.builtInWideAngleCamera, .external],
        mediaType: .video,
        position: .unspecified
    ).devices
    receipt("camera_devices=\(devices.map { $0.localizedName }.joined(separator: ","))")
}

func launchSiftaDesktop() {
    let exe = URL(fileURLWithPath: CommandLine.arguments[0]).standardizedFileURL
    let repo = exe
        .deletingLastPathComponent() // MacOS
        .deletingLastPathComponent() // Contents
        .deletingLastPathComponent() // SiftaCameraTCC.app
        .deletingLastPathComponent() // .sifta_state
        .deletingLastPathComponent() // repo

    let python = repo.appendingPathComponent(".venv/bin/python3")
    let desktop = repo.appendingPathComponent("sifta_os_desktop.py")
    guard FileManager.default.isExecutableFile(atPath: python.path),
          FileManager.default.fileExists(atPath: desktop.path) else {
        receipt("sifta_launch=missing_python_or_desktop repo=\(repo.path)")
        return
    }

    var env = ProcessInfo.processInfo.environment
    env["PYTHONPATH"] = "\(repo.path):\(env["PYTHONPATH"] ?? "")"
    env["SIFTA_DESKTOP_ENABLE_AUTOSTART"] = env["SIFTA_DESKTOP_ENABLE_AUTOSTART"] ?? "1"
    env["SIFTA_EYE_DELTA_ENABLE"] = env["SIFTA_EYE_DELTA_ENABLE"] ?? "1"
    env["SIFTA_LEDGER_COMPACT_ENABLE"] = env["SIFTA_LEDGER_COMPACT_ENABLE"] ?? "1"
    env["SIFTA_BURN_HARNESS_ENABLE"] = env["SIFTA_BURN_HARNESS_ENABLE"] ?? "1"
    let ollamaDir = "/Applications/Ollama.app/Contents/Resources"
    env["PATH"] = "\(ollamaDir):\(env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin")"

    let proc = Process()
    proc.executableURL = python
    proc.arguments = ["sifta_os_desktop.py"]
    proc.currentDirectoryURL = repo
    proc.environment = env
    do {
        try proc.run()
        receipt("sifta_launch=started pid=\(proc.processIdentifier)")
        proc.waitUntilExit()
        receipt("sifta_launch=exited status=\(proc.terminationStatus)")
    } catch {
        receipt("sifta_launch=error \(error)")
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)

        let before = AVCaptureDevice.authorizationStatus(for: .video)
        receipt("camera_authorization_before=\(statusName(before))")

        if before == .notDetermined {
            AVCaptureDevice.requestAccess(for: .video) { ok in
                receipt("camera_request_granted=\(ok)")
                let after = AVCaptureDevice.authorizationStatus(for: .video)
                receipt("camera_authorization_after=\(statusName(after))")
                if ok {
                    printDevices()
                    launchSiftaDesktop()
                }
                DispatchQueue.main.async {
                    NSApp.terminate(nil)
                }
            }
            return
        }

        if before == .authorized {
            printDevices()
            launchSiftaDesktop()
        }
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
EOF

rm -rf "$APP_DIR"
mkdir -p "$BIN_DIR"

cat > "$INFO_PLIST" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.antonpictures.siftacameratcc</string>
    <key>CFBundleName</key>
    <string>SiftaCameraTCC</string>
    <key>CFBundleExecutable</key>
    <string>sifta_camera_tcc</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSCameraUsageDescription</key>
    <string>SIFTA needs Camera access for Alice's visual organ on this local Mac.</string>
</dict>
</plist>
EOF

swiftc -O "$SRC_FILE" -o "${BIN_DIR}/sifta_camera_tcc"
codesign --force --sign - "$APP_DIR"

echo "$APP_DIR"
