Now I have a comprehensive understanding of the project. Let me compile the full code review.

---

## 1. PROJECT SUMMARY

**RustDesk** is an open-source remote desktop application written primarily in **Rust** (backend) and **Dart/Flutter** (frontend UI). It provides remote desktop control, file transfer, terminal access, port forwarding, and camera viewing.

- **Scale**: 928 files total (170 source files classified)
- **Languages**: Rust (backend), Dart/Flutter (UI), C/C++ (platform-specific), HTML/CSS/JS (legacy Sciter UI)
- **Version**: 1.4.6
- **License**: Open source (AGPL-3.0)
- **Key Dependencies**: Tokio (async runtime), Protobuf (messaging), sodiumoxide (crypto), scrap (screen capture), enigo (input simulation), flutter_rust_bridge (FFI bridge)

## 2. ARCHITECTURE

RustDesk uses a **Layered Architecture with Service-Oriented Design** on the backend and **Model-View-ViewModel (MVVM)** on the Flutter frontend.

### Rust Backend Layers

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Entry Point** | `src/main.rs`, `src/core_main.rs` | CLI parsing, initialization, bootstrap |
| **Library Root** | `src/lib.rs` | Module declarations, conditional compilation per platform |
| **Server** | `src/server/` | Connection handling, audio/video/input/clipboard services |
| **Client** | `src/client/` | Remote connection initiation, IO loop, file transfer traits |
| **Rendezvous** | `src/rendezvous_mediator.rs` | NAT traversal, relay server communication |
| **Platform** | `src/platform/` | OS-specific implementations (Windows, macOS, Linux, Android) |
| **IPC** | `src/ipc.rs` | Inter-process communication protocol (service ↔ UI) |
| **Privacy Mode** | `src/privacy_mode/` | Platform-specific privacy mode implementations |
| **Plugin** | `src/plugin/` | Plugin framework (native handlers, IPC, manager) |
| **Whiteboard** | `src/whiteboard/` | Whiteboard functionality |
| **FFI Bridge** | `src/flutter.rs`, `src/flutter_ffi.rs` | Flutter-Rust FFI interface via flutter_rust_bridge |
| **Shared Libs** | `libs/hbb_common/`, `libs/scrap/`, `libs/enigo/`, `libs/clipboard/` | Config, protocol, screen capture, input, clipboard |

### Flutter Frontend Layers

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Entry** | `flutter/lib/main.dart` | App initialization, multi-window management |
| **Pages (Desktop)** | `flutter/lib/desktop/pages/` | Desktop-specific UI pages (home, remote, settings, file manager, terminal) |
| **Pages (Mobile)** | `flutter/lib/mobile/pages/` | Mobile-specific UI pages (home, remote, settings, scan) |
| **Shared Widgets** | `flutter/lib/common/widgets/` | Cross-platform widgets (address book, toolbar, dialogs, peer cards) |
| **Models** | `flutter/lib/models/` | State management (ChangeNotifier-based) for all features |
| **Plugin** | `flutter/lib/plugin/` | Plugin UI framework (manager, handlers, event system) |
| **Utils** | `flutter/lib/utils/` | Utilities (multi-window manager, HTTP service, event loop, scaling) |
| **Native Bridge** | `flutter/lib/native/` | Platform-specific native implementations (FFI, Win32) |
| **Web** | `flutter/lib/web/` | Web platform-specific implementations |

### Key Architectural Patterns

1. **Service Pattern (Rust)**: The `Service` trait (`src/server/service.rs`) defines a publish-subscribe service model. Services (audio, video, clipboard, input, display, printer) register with a central server, accept subscribers (connections), and broadcast messages.

2. **Connection Handler**: Each remote session is handled by `Session` in `src/server/connection.rs` — a massive file (~6150 lines) managing authentication, input forwarding, video streaming, file transfer, and session lifecycle.

3. **FFI Bridge**: `flutter_rust_bridge` generates the bridge between Dart and Rust. `src/flutter_ffi.rs` exposes ~1400 function signatures for session management, rendering, and configuration.

4. **MVVM (Flutter)**: Models extend `ChangeNotifier` and use `GetX` reactive state (`RxString`, `RxBool`, `RxInt`). Pages observe models via `Obx()` widgets.

5. **Multi-Window**: Desktop supports multiple independent windows (remote desktop, file transfer, terminal, port forward, camera view) via `desktop_multi_window` package.

6. **Plugin Framework**: Both Rust and Flutter sides support plugins with a native handler system and UI registration.

## 3. RELATED FILES

### Core Architecture Files

| File | Entity Type | Purpose | Relevance |
|------|-------------|---------|-----------|
| `src/lib.rs` | Module root | Declares all Rust modules with platform-conditional compilation | Defines the entire module graph and platform feature gates |
| `src/server.rs` | Server module | Server entry point, connection acceptance, relay connections | Central orchestrator for all server-side services |
| `src/server/service.rs` | Service trait | `Service` trait + `ServiceTmpl`/`ServiceSwap` generic implementations | Core architectural pattern — publish-subscribe service model |
| `src/server/connection.rs` | Connection handler | Session lifecycle, authentication, input/video/clipboard forwarding | Largest file (~6150 lines), handles all remote session logic |
| `src/core_main.rs` | Entry point | Application bootstrap, CLI parsing, process management | Initialization flow, service startup, platform detection |
| `src/flutter_ffi.rs` | FFI bridge | ~1400 FFI functions exposed to Flutter | All Dart↔Rust communication goes through here |
| `src/flutter.rs` | FFI bridge | Texture rendering, plugin loading, platform callbacks | GPU texture rendering bridge for remote desktop display |
| `src/common.rs` | Shared utilities | Global state, version checks, platform detection | Shared helpers used across all modules |
| `src/ipc.rs` | IPC protocol | Inter-process communication data types | Defines all IPC message types between service and UI processes |
| `src/rendezvous_mediator.rs` | Network | NAT traversal, rendezvous server communication | Connection establishment, relay, UDP punching |
| `src/privacy_mode.rs` | Privacy | Privacy mode implementation factory | Platform-specific privacy mode (Windows, macOS) |

### Server Services

| File | Entity Type | Purpose | Relevance |
|------|-------------|---------|-----------|
| `src/server/audio_service.rs` | Service | Audio capture and streaming | Real-time audio forwarding to remote clients |
| `src/server/video_service.rs` | Service | Screen capture and video encoding | Video frame capture, encoding, QoS |
| `src/server/input_service.rs` | Service | Keyboard/mouse input simulation | Receives remote input events, simulates locally |
| `src/server/clipboard_service.rs` | Service | Clipboard synchronization | Bidirectional clipboard sync between host and client |
| `src/server/display_service.rs` | Service | Display management | Monitor detection, resolution changes, display info |
| `src/server/video_qos.rs` | Service | Video quality adaptation | Adaptive bitrate, FPS adjustment based on network conditions |
| `src/server/terminal_service.rs` | Service | Terminal/SSH session management | Remote terminal access, shell spawning |
| `src/server/printer_service.rs` | Service | Remote printing | Print job forwarding to local printers |

### Flutter Frontend

| File | Entity Type | Purpose | Relevance |
|------|-------------|---------|-----------|
| `flutter/lib/main.dart` | Entry | App initialization, multi-window routing | Platform detection, window type routing, service startup |
| `flutter/lib/common.dart` | Theme/Utils | Theme definitions, common widgets, constants | Color themes, widget themes, shared UI components |
| `flutter/lib/models/model.dart` | Model | Core FFI model, peer info, connection state | Central state model for remote sessions |
| `flutter/lib/models/peer_model.dart` | Model | Peer data model with serialization | Address book peer representation |
| `flutter/lib/models/server_model.dart` | Model | Server configuration and status | Server-side settings, password management, client list |
| `flutter/lib/models/ab_model.dart` | Model | Address book management | Cloud sync, shared address books, caching |
| `flutter/lib/models/file_model.dart` | Model | File transfer state management | Directory listing, job queue, transfer progress |
| `flutter/lib/models/input_model.dart` | Model | Keyboard/mouse input handling | Key event mapping, modifier tracking, pointer events |
| `flutter/lib/models/chat_model.dart` | Model | Chat overlay management | Message history, voice call state, overlay positioning |
| `flutter/lib/models/state_model.dart` | Model | Window state management | Fullscreen, maximized, resize edge size |
| `flutter/lib/plugin/manager.dart` | Plugin | Plugin lifecycle and UI management | Plugin install/uninstall, UI type registration |
| `flutter/lib/plugin/handlers.dart` | Plugin | Native plugin event handlers | Peer selection, UI entry registration |
| `flutter/lib/desktop/pages/desktop_home_page.dart` | Page | Main desktop home screen | ID/password display, connection panel, settings access |
| `flutter/lib/desktop/pages/remote_page.dart` | Page | Remote desktop session page | Video rendering, input handling, toolbar, overlays |
| `flutter/lib/utils/multi_window_manager.dart` | Utility | Multi-window session management | Window creation, tab management, session routing |

### Platform-Specific

| File | Entity Type | Purpose | Relevance |
|------|-------------|---------|-----------|
| `src/platform/mod.rs` | Platform | Cross-platform abstractions | Wake lock, resolution changes, process management |
| `src/platform/windows.rs` | Platform | Windows-specific implementations | Service management, display, input |
| `src/platform/macos.rs` | Platform | macOS-specific implementations | Permissions, accessibility |
| `src/platform/linux.rs` | Platform | Linux-specific implementations | X11/Wayland, DBus |

## 4. DEPENDENCY GRAPH

### Module-Level Dependencies (Rust)

```
src/lib.rs (root module)
├── src/server/ ──────────────────→ src/client/, src/ipc/, src/privacy_mode/
│   ├── src/server/connection.rs ──→ input_service, display_service, video_service,
│   │                                  clipboard_service, audio_service, privacy_mode
│   ├── src/server/audio_service.rs ──→ src/platform/ (PA_SAMPLE_RATE)
│   ├── src/server/video_service.rs ──→ libs/scrap/ (screen capture)
│   ├── src/server/input_service.rs ──→ libs/enigo/ (input simulation)
│   ├── src/server/clipboard_service.rs ──→ src/ipc/, libs/clipboard/
│   └── src/server/service.rs ──→ (no deps beyond hbb_common)
├── src/client/ ──────────────────→ libs/enigo/, src/ipc/
├── src/flutter_ffi.rs ───────────→ src/server/, src/client/, src/flutter.rs
├── src/flutter.rs ───────────────→ src/core_main.rs, src/ui_interface.rs
├── src/rendezvous_mediator.rs ───→ src/server/, src/client/, src/lan/
├── src/ipc.rs ───────────────────→ (standalone protocol definitions)
├── src/privacy_mode.rs ──────────→ src/privacy_mode/win_*, src/privacy_mode/macos.rs
├── src/plugin/ ──────────────────→ src/ipc/, src/server/
├── src/core_main.rs ─────────────→ src/server/, src/client/, src/rendezvous_mediator.rs
└── src/common.rs ────────────────→ (shared utilities, no module deps)
```

### Flutter Module Dependencies

```
flutter/lib/main.dart
├── flutter/lib/common.dart (themes, shared widgets)
├── flutter/lib/models/model.dart (FFI model)
├── flutter/lib/desktop/pages/ (desktop pages)
├── flutter/lib/mobile/pages/ (mobile pages)
└── flutter/lib/utils/multi_window_manager.dart

flutter/lib/models/
├── model.dart ──────────→ flutter/lib/plugin/ (event handling)
├── ab_model.dart ───────→ flutter/lib/models/peer_model.dart, user_model.dart
├── file_model.dart ─────→ flutter/lib/models/model.dart
├── server_model.dart ───→ flutter/lib/models/model.dart
├── chat_model.dart ─────→ flutter/lib/models/model.dart
└── input_model.dart ────→ flutter/lib/models/model.dart

flutter/lib/plugin/
├── manager.dart ────────→ flutter/lib/plugin/model.dart, handlers.dart
├── handlers.dart ───────→ flutter/lib/plugin/ui_manager.dart
├── event.dart ──────────→ (event dispatch)
└── model.dart ──────────→ (ChangeNotifier models for plugin UI)
```

### Key Dependency Flows

1. **Connection Flow**: `src/core_main.rs` → `src/server.rs` (accept_connection) → `src/server/connection.rs` (Session::start) → subscribes to audio/video/input/clipboard services

2. **UI Flow**: Flutter Page → Model (ChangeNotifier) → `flutter_ffi.rs` (FFI call) → Rust backend → response via event stream → Model update → UI rebuild

3. **IPC Flow**: Service process ↔ UI process via `src/ipc.rs` Data enum (Unix domain sockets / Windows named pipes)

## 5. CONVENTIONS

### Naming Conventions

1. **Rust modules use `snake_case`**: `audio_service.rs`, `clipboard_service.rs`, `rendezvous_mediator.rs`, `core_main.rs`
2. **Rust types use `PascalCase`**: `ServiceTmpl`, `ServiceSwap`, `ConnInner`, `Session`, `ServerPtr`
3. **Rust traits use `PascalCase`**: `Service`, `Subscriber`, `Reset`, `Interface`
4. **Rust functions use `snake_case`**: `accept_connection`, `create_tcp_connection`, `get_key_pair`
5. **Rust constants use `SCREAMING_SNAKE_CASE`**: `HIBERNATE_TIMEOUT`, `MAX_ERROR_TIMEOUT`, `SERVICE_OPTION_VALUE_TRUE`
6. **Service naming pattern**: `*_service.rs` files with `NAME` constant and `new()` constructor — e.g., `audio_service::NAME`, `clipboard_service::NAME`
7. **Flutter files use `snake_case`**: `desktop_home_page.dart`, `peer_model.dart`, `multi_window_manager.dart`
8. **Flutter classes use `PascalCase`**: `DesktopHomePage`, `PeerModel`, `ServerModel`, `AbModel`
9. **Flutter models use `*Model` suffix**: `ServerModel`, `FileModel`, `ChatModel`, `InputModel`, `AbModel`
10. **Flutter pages use `*Page` suffix**: `DesktopHomePage`, `RemotePage`, `ConnectionPage`, `ServerPage`
11. **Flutter widgets use descriptive names**: `PeerCard`, `Toolbar`, `DraggableChatWindow`, `CustomAlertDialog`
12. **FFI functions use `session_*` prefix**: `session_start`, `session_login`, `session_get_option`, `session_add`
13. **IPC Data variants use `PascalCase`**: `Data::ClipboardNonFile`, `Data::PrivacyModeState`, `Data::Plugin`
14. **Config keys use `kebab-case` strings**: `"audio-input"`, `"stop-service"`, `"privacy-mode-impl-key"`

### Architectural Patterns

1. **Service Pattern**: `Service` trait with `ServiceTmpl<T>` generic wrapper. Services are registered with `add_service(Box::new(...))` and communicate via publish-subscribe.
2. **Lazy Static State**: Global state via `lazy_static!` with `Arc<Mutex<...>>` — e.g., `SESSIONS`, `LOGIN_FAILURES`, `ALIVE_CONNS`
3. **FFI Bridge Pattern**: `flutter_rust_bridge` generates Dart bindings. Rust functions are exposed as `pub fn` in `flutter_ffi.rs` and called from Dart models.
4. **ChangeNotifier + GetX**: Flutter models extend `ChangeNotifier` and use `Rx*` reactive types from GetX for observable state.
5. **Conditional Compilation**: Heavy use of `#[cfg(...)]` for platform-specific code — `target_os = "windows"`, `target_os = "linux"`, `feature = "flutter"`, etc.
6. **Protobuf Messaging**: All network messages use Protocol Buffers (`message_proto::*`, `rendezvous_proto::*`).

### Style Conventions

1. **Error Handling**: Prefer `Result` + `?` operator. Avoid `unwrap()`/`expect()` in production (per AGENTS.md rules). Use `allow_err!` macro for intentional error ignoring.
2. **Async**: Tokio runtime assumed. Never create nested runtimes. Never call `block_on` inside async code. Use `tokio::spawn`, channels, `spawn_blocking` for blocking work.
3. **Locking**: Never hold locks across `.await`. Use `RwLock` for read-heavy state, `Mutex` for write-heavy.
4. **Editing Hygiene**: Smallest valid diff. No unrelated refactoring. No formatting-only changes. Keep style consistent with nearby code.

## 6. SIMILAR IMPLEMENTATIONS

### Service Implementations (all implement the `Service` trait pattern)

| Class | File | Similarity |
|-------|------|------------|
| `audio_service` | `src/server/audio_service.rs` | Same pattern: `NAME` constant, `new()` → `ServiceTmpl`, `run()` with `EmptyExtraFieldService` |
| `video_service` | `src/server/video_service.rs` | Same pattern: `VideoSource` enum, `get_service_name()`, `run()` with capturer creation |
| `clipboard_service` | `src/server/clipboard_service.rs` | Same pattern: `NAME`/`FILE_NAME` constants, `run()` with clipboard context |
| `input_service` | `src/server/input_service.rs` | Same pattern: `NAME_CURSOR`/`NAME_POS`/`NAME_WINDOW_FOCUS`, `new_cursor()`/`new_pos()` |
| `display_service` | `src/server/display_service.rs` | Same pattern: `NAME` constant, display change detection, capturer management |
| `printer_service` | `src/server/printer_service.rs` | Same pattern: Windows-only, `NAME` constant |
| `terminal_service` | `src/server/terminal_service.rs` | Same pattern: service ID generation, session management |

### Flutter Model Implementations (all extend ChangeNotifier)

| Class | File | Similarity |
|-------|------|------------|
| `FfiModel` | `flutter/lib/models/model.dart` | Core model — manages peer info, permissions, connection state |
| `ServerModel` | `flutter/lib/models/server_model.dart` | Server config — password, verification, client list |
| `FileModel` | `flutter/lib/models/file_model.dart` | File transfer — directory state, job queue, transfer control |
| `ChatModel` | `flutter/lib/models/chat_model.dart` | Chat — message history, voice call, overlay management |
| `InputModel` | `flutter/lib/models/input_model.dart` | Input — key events, pointer events, modifier tracking |
| `AbModel` | `flutter/lib/models/ab_model.dart` | Address book — cloud sync, profiles, caching |
| `PeerTabModel` | `flutter/lib/models/peer_tab_model.dart` | Peer tabs — tab management for multi-session |

### Flutter Page Implementations (all are StatefulWidget)

| Class | File | Similarity |
|-------|------|------------|
| `DesktopHomePage` | `flutter/lib/desktop/pages/desktop_home_page.dart` | Home screen — ID board, connection panel, settings |
| `RemotePage` | `flutter/lib/desktop/pages/remote_page.dart` | Remote session — video, input, toolbar, overlays |
| `ConnectionPage` | `flutter/lib/desktop/pages/connection_page.dart` | Connection status — waiting, connecting, connected states |
| `ServerPage` | `flutter/lib/desktop/pages/server_page.dart` | Server settings — configuration, permissions |
| `FileManagerPage` | `flutter/lib/desktop/pages/file_manager_page.dart` | File transfer — dual-pane file browser |
| `TerminalPage` | `flutter/lib/desktop/pages/terminal_page.dart` | Terminal — shell emulation |

## 7. TASK CONTEXT

### For an AI performing code review on this project:

**What this project is**: RustDesk is a full-featured remote desktop application. The Rust backend handles all networking, screen capture, input simulation, and service management. The Flutter frontend provides the modern UI across desktop and mobile platforms.

**Key architectural points to understand**:

1. **Service Pattern**: The server uses a publish-subscribe service model (`Service` trait in `src/server/service.rs`). Each service (audio, video, input, clipboard, display) runs independently and broadcasts to subscribed connections. When reviewing, check that new services follow this pattern.

2. **Connection Lifecycle**: `src/server/connection.rs` (~6150 lines) is the largest file and handles the entire remote session lifecycle — authentication, input forwarding, video streaming, clipboard sync, file transfer. This file is a candidate for refactoring due to its size.

3. **FFI Bridge**: `src/flutter_ffi.rs` exposes ~1400 function signatures. All Dart-to-Rust communication flows through here. The naming convention is `session_*` for session operations, `main_*` for main process operations.

4. **State Management**: Flutter uses `ChangeNotifier` + `GetX` reactive state. Models are registered globally via `gFFI` (global FFI instance). Pages observe models with `Obx()` widgets.

5. **Multi-Platform**: Heavy use of `#[cfg(...)]` for platform-specific code. Android/iOS have different code paths than desktop. The `src/platform/` directory contains OS-specific implementations.

6. **IPC**: The service process and UI process communicate via `src/ipc.rs` which defines a large `Data` enum with all message types.

**What to look for in code review**:
- Follow the Rust rules from AGENTS.md: no `unwrap()`/`expect()` in production, prefer `Result` + `?`, no nested runtimes, no locks across `.await`
- Service implementations should follow the established pattern (NAME constant, new() constructor, run() with EmptyExtraFieldService)
- Flutter models should extend ChangeNotifier and use GetX reactive types
- Platform-specific code should be properly gated with `#[cfg(...)]`
- FFI functions should follow the naming convention (`session_*`, `main_*`)
- Avoid adding new dependencies unless necessary

## 8. RELEVANT CODE SNIPPETS

### Snippet 1: Service Trait Definition (core architectural pattern)

**File**: `src/server/service.rs` (lines 9-18)
```rust
pub trait Service: Send + Sync {
    fn name(&self) -> String;
    fn on_subscribe(&self, sub: ConnInner);
    fn on_unsubscribe(&self, id: i32);
    fn is_subed(&self, id: i32) -> bool;
    fn join(&self);
    fn get_option(&self, opt: &str) -> Option<String>;
    fn set_option(&self, opt: &str, val: &str) -> Option<String>;
    fn ok(&self) -> bool;
}
```
**Why relevant**: This is the central abstraction for all server services. Every service (audio, video, input, clipboard, display, printer) implements this trait. The `ServiceTmpl<T>` generic provides the default implementation with subscriber management.

### Snippet 2: Server Service Registration Pattern

**File**: `src/server.rs` (lines 30-40, condensed)
```rust
add_service(Box::new(audio_service::new()));
add_service(Box::new(display_service::new()));
add_service(Box::new(clipboard_service::new(clipboard_service::NAME.to_owned())));
add_service(Box::new(input_service::new_cursor()));
add_service(Box::new(input_service::new_pos()));
add_service(Box::new(printer_service::new(printer_service::NAME.to_owned())));
```
**Why relevant**: Shows how services are registered with the server. Each service has a `new()` constructor and is boxed as a trait object. This is the pattern to follow when adding new services.

### Snippet 3: Flutter Model Pattern (ChangeNotifier + GetX)

**File**: `flutter/lib/models/server_model.dart` (lines 1-20, condensed)
```dart
class ServerModel extends ChangeNotifier {
  final TextEditingController serverId = TextEditingController(text: translate("Generating ..."));
  final TextEditingController serverPasswd = TextEditingController(text: translate("Generating ..."));
  final RxString _verificationMethod = RxString('');
  final RxString _temporaryPasswordLength = RxString('');
  final RxString _approveMode = RxString('');
  final RxBool _allowNumericOneTimePassword = RxBool(false);
  
  ServerModel(this.parent);
  
  void setVerificationMethod(String method) {
    mainSetOption(key: kOptionVerificationMethod, value: method);
  }
}
```
**Why relevant**: Shows the standard Flutter model pattern — extends `ChangeNotifier`, uses `Rx*` reactive types from GetX, and calls FFI functions (`mainSetOption`) to communicate with Rust backend.

### Snippet 4: FFI Bridge Function Pattern

**File**: `src/flutter_ffi.rs` (lines 1-20, condensed)
```rust
pub fn session_start(
    events2ui: StreamSink<EventToUI>,
    session_id: SessionID,
    id: String,
) {
    session_start_(&session_id, &id, events2ui);
}

pub fn session_login(
    session_id: SessionID,
    os_username: String,
    os_password: ***,
    password: ***,
    remember: bool,
) {
    if let Some(session) = get_session_by_session_id(&session_id) {
        session.login(os_username, os_password, password, remember);
    }
}
```
**Why relevant**: Shows the FFI function naming convention (`session_*` prefix), the pattern of delegating to an inner function (`session_start_`), and the session lookup pattern (`get_session_by_session_id`).

### Snippet 5: Conditional Compilation for Platform-Specific Code

**File**: `src/lib.rs` (lines 1-20)
```rust
#[cfg(not(any(target_os = "android", target_os = "ios")))]
pub use platform::{
    clip_cursor, get_cursor, get_cursor_data, get_cursor_pos, get_focused_display,
    set_cursor_pos, start_os_service,
};

#[cfg(not(any(target_os = "ios")))]
mod server;

#[cfg(any(target_os = "android", target_os = "ios", feature = "flutter"))]
pub mod flutter;
#[cfg(any(target_os = "android", target_os = "ios", feature = "flutter"))]
pub mod flutter_ffi;
```
**Why relevant**: Shows the extensive use of `#[cfg(...)]` for platform-specific compilation. Desktop-only features (server, rendezvous, IPC) are gated behind `not(android/ios)`. Flutter features are gated behind `feature = "flutter"`.