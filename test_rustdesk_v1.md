Now I have a comprehensive understanding of the project. Let me compile the full architecture analysis.

---

## Project Summary

**RustDesk** is an open-source remote desktop application (v1.4.6) written primarily in **Rust** (backend/core) and **Dart/Flutter** (frontend/UI). The project has **928 files** total:
- **Rust**: ~170 source files (in `src/` and `libs/`)
- **Dart/Flutter**: ~123 source files (in `flutter/lib/`)
- **C/C++**: 41 files (platform-specific, MSI installer, virtual display driver)
- **Other**: configs, CI workflows, docs, assets

The project is structured as a **Cargo workspace** with the main crate `rustdesk` (library `librustdesk`) and sub-crates in `libs/`.

---

## Architecture

### Overall Pattern: **Hybrid Layered Architecture with CQRS-style Service Model**

RustDesk uses a **two-process architecture**:
1. **Rust backend** (`librustdesk`) — handles all networking, screen capture, input injection, encoding/decoding, clipboard, file transfer, audio, and session management
2. **Flutter frontend** — handles all UI rendering, user interaction, and platform-specific integrations (via FFI)

The architecture can be broken into these layers:

### Layer 1: Core Library (`src/lib.rs`)
The root module that conditionally compiles sub-modules based on platform and features. Key modules:
- `server` — remote desktop server (the machine being controlled)
- `client` — remote desktop client (the machine doing the controlling)
- `common` — shared utilities, global state, config
- `rendezvous_mediator` — rendezvous/relay server communication
- `ipc` — inter-process communication protocol
- `flutter` / `flutter_ffi` — FFI bridge to Flutter UI
- `plugin` — plugin framework
- `privacy_mode` — privacy mode implementations (per-platform)
- `whiteboard` — whiteboard feature
- `port_forward` — TCP port forwarding
- `clipboard` / `clipboard_file` — clipboard management
- `keyboard` — keyboard handling
- `lan` — LAN discovery
- `updater` — auto-update
- `tray` — system tray
- `auth_2fa` — two-factor authentication
- `hbbs_http` — HTTP client for RustDesk Server (HBBS) API
- `kcp_stream` — KCP protocol support
- `virtual_display_manager` — Windows virtual display management
- `ui_interface`, `ui_session_interface`, `ui_cm_interface` — UI state interfaces

### Layer 2: Server Subsystem (`src/server/`)
The server runs on the **host machine** being controlled. It uses a **Service-based architecture** with a publish/subscribe pattern:

| Service | File | Purpose |
|---------|------|---------|
| `GenericService` / `Service` trait | `service.rs` | Base service trait with subscribe/unsubscribe pattern |
| `VideoService` | `video_service.rs` | Screen capture, encoding, video frame delivery |
| `AudioService` | `audio_service.rs` | Audio capture and streaming |
| `InputService` | `input_service.rs` | Keyboard/mouse input injection |
| `ClipboardService` | `clipboard_service.rs` | Clipboard synchronization |
| `DisplayService` | `display_service.rs` | Display enumeration and change detection |
| `PrinterService` | `printer_service.rs` | Remote printing |
| `TerminalService` | `terminal_service.rs` | Remote terminal/SSH |
| `Connection` | `connection.rs` | Session management, authentication, encryption handshake |

The server's `connection.rs` is the **central orchestrator** — it handles incoming connections, performs key exchange, manages the session lifecycle, and coordinates all services.

### Layer 3: Client Subsystem (`src/client/`)
The client runs on the **controller machine**. Key modules:
- `io_loop.rs` — main I/O event loop for receiving data from the server
- `helper.rs` — connection initiation, rendezvous server communication
- `file_trait.rs` — file transfer trait
- `screenshot.rs` — screenshot capability

The main `src/client.rs` file (4265 lines) contains the core client logic: connection establishment, NAT traversal, video decoding, audio playback, and session management.

### Layer 4: Rendezvous/Relay (`src/rendezvous_mediator.rs`)
Handles communication with the RustDesk rendezvous/relay servers for:
- NAT type detection
- Peer discovery
- Relay connection establishment
- Heartbeat and online status

### Layer 5: IPC Layer (`src/ipc.rs`)
Defines the inter-process communication protocol between:
- Main process ↔ Service process
- Main process ↔ Connection Manager (CM) process
- Uses `parity-tokio-ipc` for named pipe / Unix domain socket communication

The `Data` enum in `ipc.rs` defines all IPC message types (847+ signatures) covering: input events, clipboard, config, plugin messages, voice calls, file transfer, privacy mode, etc.

### Layer 6: Plugin Framework (`src/plugin/`)
An extensible plugin system with:
- `manager.rs` — plugin lifecycle management (install, uninstall, list)
- `desc.rs` — plugin descriptor/metadata
- `ipc.rs` — plugin IPC communication
- `native.rs` — native plugin interface
- `callback_ext.rs` / `callback_msg.rs` — callback system
- `config.rs` — plugin configuration

### Layer 7: Flutter UI (`flutter/lib/`)
The Flutter frontend follows a **Model-View pattern with Provider/GetX state management**:

**Models** (state management):
| Model | File | Purpose |
|-------|------|---------|
| `FfiModel` | `model.dart` | Core FFI model — peer info, permissions, connection state |
| `ServerModel` | `server_model.dart` | Server-side settings, password management, client list |
| `PeerModel` | `peer_model.dart` | Peer data (ID, name, platform, online status) |
| `ChatModel` | `chat_model.dart` | Chat/ messaging state |
| `FileModel` | `file_model.dart` | File transfer state, directory browsing, job management |
| `InputModel` | `input_model.dart` | Keyboard/mouse input handling, modifier keys |
| `StateModel` | `state_model.dart` | Window state (fullscreen, minimized, resize) |
| `PeerTabModel` | `peer_tab_model.dart` | Tab management for peer connections |
| `PlatformModel` | `platform_model.dart` | Platform abstraction (native vs web) |
| `NativeModel` | `native_model.dart` | Native FFI bindings to Rust |
| `WebModel` | `web_model.dart` | Web platform bindings (JS interop) |

**Pages** (UI screens):
| Page | File | Purpose |
|------|------|---------|
| `DesktopHomePage` | `desktop_home_page.dart` | Main home screen with ID/password entry |
| `RemotePage` | `remote_page.dart` | Remote desktop viewing/control screen |
| `ServerPage` | `server_page.dart` | Server settings and connection manager |
| `ConnectionPage` | `connection_page.dart` | Connection status and management |
| `DesktopSettingPage` | `desktop_setting_page.dart` | Settings UI |
| `FileManagerPage` | `file_manager_page.dart` | File transfer UI |
| `TerminalPage` | `terminal_page.dart` | Remote terminal UI |
| `PortForwardPage` | `port_forward_page.dart` | Port forwarding UI |
| `ViewCameraPage` | `view_camera_page.dart` | Camera viewing UI |

**Plugin UI** (`flutter/lib/plugin/`):
- `manager.dart` — plugin store/list management
- `model.dart` — plugin UI models (buttons, checkboxes, options)
- `handlers.dart` — native UI event handlers (peer selection, UI entries)
- `ui_manager.dart` — UI entry registration
- `event.dart` — plugin event handling

### Layer 8: Platform Abstraction (`src/platform/`)
Platform-specific implementations for:
- Windows: ACL management, virtual display, privacy mode
- macOS: Objective-C bindings, privacy mode
- Linux: D-Bus, GTK sudo, desktop manager integration, Wayland support
- Android/iOS: via Flutter FFI

### Layer 9: Library Crates (`libs/`)
| Crate | Purpose |
|-------|---------|
| `scrap` | Screen capture library (cross-platform) |
| `hbb_common` | Common utilities (config, protobuf, networking, crypto) |
| `enigo` | Keyboard/mouse input simulation |
| `clipboard` | Clipboard management |
| `virtual_display` | Windows virtual display driver |
| `portable` | Portable executable builder |
| `remote_printer` | Remote printing support |

---

## Key Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/lib.rs` | Root module — conditionally compiles all sub-modules | Entry point for understanding the entire module structure |
| `src/server/connection.rs` | Central session orchestrator — handles auth, encryption, service coordination | Core of the server-side architecture |
| `src/server/service.rs` | GenericService trait — publish/subscribe service pattern | Foundation of the service architecture |
| `src/client.rs` | Client connection logic — NAT traversal, rendezvous, session start | Core of the client-side architecture |
| `src/ipc.rs` | IPC protocol Data enum — all inter-process message types | Defines the communication contract between processes |
| `src/flutter_ffi.rs` | FFI bridge functions exposed to Flutter | All Rust→Flutter bindings |
| `src/ui_interface.rs` | UI state interface — options, config, status | Shared state between Rust and UI |
| `src/rendezvous_mediator.rs` | Rendezvous server communication | NAT traversal, peer discovery, relay |
| `src/plugin/manager.rs` | Plugin lifecycle management | Plugin system core |
| `src/privacy_mode.rs` | Privacy mode abstraction with per-platform impls | Security feature |
| `flutter/lib/main.dart` | Flutter app entry point | UI bootstrap |
| `flutter/lib/models/model.dart` | FfiModel — core state model | Central UI state |
| `flutter/lib/models/server_model.dart` | ServerModel — server settings UI state | Server configuration UI |
| `flutter/lib/models/platform_model.dart` | Platform abstraction (native/web) | Cross-platform UI layer |
| `flutter/lib/desktop/pages/remote_page.dart` | Remote desktop UI page | Main remote control screen |
| `flutter/lib/desktop/pages/desktop_home_page.dart` | Home page with ID/password entry | Main landing screen |
| `flutter/lib/plugin/manager.dart` | Plugin store/list UI model | Plugin management UI |
| `Cargo.toml` | Workspace and dependency configuration | All external dependencies and features |

---

## Key Symbols

### Rust Core

| Symbol | Kind | Location | Description |
|--------|------|----------|-------------|
| `Service` trait | Trait | `src/server/service.rs` | Base service with `name()`, `on_subscribe()`, `on_unsubscribe()`, `send()` |
| `GenericService` | Struct | `src/server/service.rs` | Generic implementation of Service trait with subscriber management |
| `Connection::start()` | Method | `src/server/connection.rs` | Main entry point for handling a remote connection session |
| `Client::start()` | Method | `src/client.rs` | Main entry point for initiating a connection to a remote peer |
| `Data` enum | Enum | `src/ipc.rs` | All IPC message types (input, clipboard, config, plugin, etc.) |
| `core_main()` | Function | `src/core_main.rs` | Shared main function for both Flutter and Sciter UIs |
| `initialize()` | Function | `src/flutter_ffi.rs` | FFI initialization — sets up logging, loads config, starts event streams |
| `PrivacyMode` trait | Trait | `src/privacy_mode.rs` | Platform-specific privacy mode implementation |
| `PluginManager` | Struct | `src/plugin/manager.rs` | Manages plugin source list, install, uninstall |
| `RendezvousMediator` | Struct | `src/rendezvous_mediator.rs` | Handles rendezvous server communication |
| `VideoService` | Struct | `src/server/video_service.rs` | Screen capture and video encoding service |
| `InputService` | Struct | `src/server/input_service.rs` | Keyboard/mouse input injection service |
| `AudioService` | Struct | `src/server/audio_service.rs` | Audio capture and streaming service |
| `ClipboardService` | Struct | `src/server/clipboard_service.rs` | Clipboard synchronization service |
| `TerminalService` | Struct | `src/server/terminal_service.rs` | Remote terminal/SSH service |

### Flutter UI

| Symbol | Kind | Location | Description |
|--------|------|----------|-------------|
| `FfiModel` | Class | `flutter/lib/models/model.dart` | Core state model — peer info, permissions, connection type |
| `ServerModel` | Class | `flutter/lib/models/server_model.dart` | Server settings, password, client list management |
| `PeerModel` | Class | `flutter/lib/models/peer_model.dart` | Peer data model with online state tracking |
| `ChatModel` | Class | `flutter/lib/models/chat_model.dart` | Chat/messaging state and overlay management |
| `FileModel` | Class | `flutter/lib/models/file_model.dart` | File transfer state, directory browsing, job control |
| `InputModel` | Class | `flutter/lib/models/input_model.dart` | Keyboard/mouse input handling, modifier tracking |
| `StateModel` | Class | `flutter/lib/models/state_model.dart` | Window state (fullscreen, resize, input source) |
| `RustdeskImpl` (native) | Class | `flutter/lib/models/native_model.dart` | Native FFI bindings — loads `librustdesk.so/.dll` |
| `RustdeskImpl` (web) | Class | `flutter/lib/models/web_model.dart` | Web platform bindings via JS interop |
| `PluginManager` (Flutter) | Class | `flutter/lib/plugin/manager.dart` | Plugin store UI model |
| `PluginModel` | Class | `flutter/lib/plugin/model.dart` | Plugin UI elements model |
| `RemotePage` | Widget | `flutter/lib/desktop/pages/remote_page.dart` | Remote desktop viewing/control page |
| `DesktopHomePage` | Widget | `flutter/lib/desktop/pages/desktop_home_page.dart` | Main home page |
| `DesktopServerPage` | Widget | `flutter/lib/desktop/pages/server_page.dart` | Server settings page |

---

## Dependencies

### Module-Level Dependencies (Rust)

```
src/lib.rs (root)
├── src/server/          ← depends on: hbb_common, scrap, enigo, clipboard
│   ├── connection.rs    ← orchestrates all services
│   ├── service.rs       ← GenericService trait
│   ├── video_service.rs ← depends on scrap (screen capture)
│   ├── audio_service.rs ← depends on cpal (audio capture)
│   ├── input_service.rs ← depends on enigo (input injection)
│   ├── clipboard_service.rs ← depends on clipboard
│   ├── display_service.rs
│   ├── terminal_service.rs ← depends on portable-pty
│   ├── printer_service.rs
│   └── ...
├── src/client.rs        ← depends on: hbb_common, enigo, cpal, magnum-opus
├── src/client/          ← io_loop, helper, file_trait, screenshot
├── src/rendezvous_mediator.rs ← depends on: hbb_common
├── src/ipc.rs           ← depends on: parity-tokio-ipc, hbb_common
├── src/flutter.rs       ← FFI bridge (loads texture renderer plugins)
├── src/flutter_ffi.rs   ← FFI functions exposed to Flutter
├── src/plugin/          ← plugin framework
├── src/privacy_mode.rs  ← platform-specific privacy implementations
├── src/hbbs_http/       ← HTTP client for HBBS API (reqwest)
├── src/ui_interface.rs  ← shared UI state
├── src/ui_session_interface.rs ← per-session UI state
├── src/ui_cm_interface.rs ← connection manager UI state
└── src/platform/        ← OS-specific implementations

External Crates:
├── hbb_common (libs/hbb_common) — config, protobuf, networking, crypto
├── scrap (libs/scrap) — screen capture
├── enigo (libs/enigo) — input simulation
├── clipboard (libs/clipboard) — clipboard
├── flutter_rust_bridge — Rust↔Dart FFI codegen
├── parity-tokio-ipc — IPC transport
├── reqwest — HTTP client
├── cpal — audio capture
├── magnum-opus — Opus audio codec
├── portable-pty — terminal emulation
└── tao/tray-icon — window management, system tray
```

### Module-Level Dependencies (Flutter)

```
flutter/lib/main.dart
├── flutter/lib/common.dart — theme, widgets, translations
├── flutter/lib/consts.dart — constants
├── flutter/lib/models/
│   ├── model.dart (FfiModel) ← core state
│   ├── server_model.dart ← server settings
│   ├── peer_model.dart ← peer data
│   ├── chat_model.dart ← chat
│   ├── file_model.dart ← file transfer
│   ├── input_model.dart ← input handling
│   ├── state_model.dart ← window state
│   ├── platform_model.dart ← platform abstraction
│   ├── native_model.dart ← FFI bindings to Rust
│   └── web_model.dart ← web JS interop
├── flutter/lib/desktop/pages/ — desktop UI pages
├── flutter/lib/desktop/screen/ — remote screen implementations
├── flutter/lib/common/widgets/ — shared widgets
├── flutter/lib/plugin/ — plugin UI framework
└── flutter/lib/utils/ — utilities (multi-window, HTTP, etc.)
```

### Key Dependency Flow

```
Flutter UI (Dart)
    ↓ FFI (flutter_rust_bridge)
Rust FFI Layer (src/flutter_ffi.rs, src/flutter.rs)
    ↓
Rust Core Library (src/client.rs, src/server/)
    ↓
Network Layer (hbb_common: TCP, socket_client, rendezvous_proto)
    ↓
Remote Peer / Rendezvous Server / Relay Server
```

---

## Conventions

### Naming Conventions

**Rust:**
- **Snake case** for functions and variables: `global_init()`, `start_server()`, `check_connect_status()`
- **PascalCase** for types: `GenericService`, `VideoService`, `Connection`, `PrivacyMode`
- **Module-level** organization: each subsystem in its own directory (`src/server/`, `src/client/`, `src/plugin/`)
- **Trait names** are descriptive nouns: `Service`, `PrivacyMode`, `Interface`
- **Enum variants** are PascalCase: `Data::ClipboardNonFile`, `Data::PrivacyModeState`
- **Feature-gated modules** use `#[cfg(...)]` extensively for platform-specific code

**Dart/Flutter:**
- **PascalCase** for classes: `FfiModel`, `ServerModel`, `RemotePage`, `DesktopHomePage`
- **camelCase** for methods and variables: `initState()`, `toggleAudio()`, `updatePasswordModel()`
- **File names** are snake_case: `server_model.dart`, `remote_page.dart`, `desktop_home_page.dart`
- **Model suffix** for state management classes: `ServerModel`, `ChatModel`, `FileModel`, `InputModel`
- **Page suffix** for full-page widgets: `RemotePage`, `ServerPage`, `ConnectionPage`
- **Screen suffix** for screen-level widgets: `DesktopRemoteScreen`, `DesktopFileTransferScreen`
- **Widget suffix** for reusable widgets: `PeerCard`, `Toolbar`, `Login`, `Dialog`

### Architectural Patterns

1. **Service Pattern (Rust server)**: The `Service` trait defines a publish/subscribe interface. Services like `VideoService`, `AudioService`, `InputService` implement this trait. The `Connection` orchestrator subscribes to services and routes messages between the remote peer and services.

2. **CQRS-style Message Passing**: All communication between components uses message passing via channels (`tokio::sync::mpsc`, `crossbeam::channel`). The `Message` enum (from protobuf) carries typed payloads.

3. **FFI Bridge Pattern**: Rust exposes functions via `flutter_rust_bridge` in `src/flutter_ffi.rs`. The Flutter side calls these through `NativeModel` (native) or `WebModel` (web) which implement the same `PlatformModel` interface.

4. **Provider/ChangeNotifier (Flutter)**: UI state is managed via `ChangeNotifier` classes (e.g., `FfiModel`, `ServerModel`) and consumed via `Provider`/`ChangeNotifierProvider` widgets.

5. **Observer Pattern (Flutter)**: Models register event handlers via `registerEventHandler()` to receive events from the Rust backend. Events flow: Rust → FFI → Event Stream → Handler callbacks.

6. **Strategy Pattern (Privacy Mode)**: `PrivacyMode` trait with platform-specific implementations (macOS, Windows exclude-from-capture, Windows Magnifier, Windows virtual display).

7. **IPC Protocol**: The `Data` enum in `src/ipc.rs` defines a comprehensive message protocol for communication between processes (main ↔ service, main ↔ CM).

### Style Conventions

1. **Async everywhere**: Rust code uses `tokio` extensively with `async fn` and `.await`. The Flutter side uses `Future` and `async/await`.

2. **Error handling**: Rust uses `Result<T, E>` with `anyhow::Error` for context. Common pattern: `allow_err!(...)` macro to log and ignore errors.

3. **Configuration**: Uses `hbb_common::config::Config` with `get_option()`/`set_option()` key-value store. Options are synchronized between processes via IPC.

4. **Protobuf for network messages**: All network communication uses Protocol Buffers (`message_proto::*`, `rendezvous_proto::*`).

5. **Conditional compilation**: Heavy use of `#[cfg(...)]` for platform-specific code (Windows, macOS, Linux, Android, iOS, Web).

6. **Lazy initialization**: Uses `lazy_static` and `std::sync::OnceLock` for global singletons.

7. **Flutter state management**: Mix of `GetX` (reactive state) and `Provider` (ChangeNotifier-based state).

---

## Similar Implementations

### 1. Similar to `VideoService` → `AudioService`, `InputService`, `ClipboardService`

All four implement the `Service` trait from `src/server/service.rs`:
- **`VideoService`** (`src/server/video_service.rs`): Captures screen, encodes video, sends frames to subscribers
- **`AudioService`** (`src/server/audio_service.rs`): Captures audio via cpal, encodes with Opus, streams to subscribers
- **`InputService`** (`src/server/input_service.rs`): Receives keyboard/mouse events from subscribers, injects via enigo
- **`ClipboardService`** (`src/server/clipboard_service.rs`): Monitors clipboard changes, syncs with subscribers

All follow the same pattern: `new()` → `run(sp)` → subscribe/unsubscribe lifecycle.

### 2. Similar to `FfiModel` → `ServerModel`, `ChatModel`, `FileModel`, `InputModel`

All are `ChangeNotifier` subclasses in Flutter that manage specific domains of application state:
- **`FfiModel`** (`flutter/lib/models/model.dart`): Core connection state, peer info, permissions
- **`ServerModel`** (`flutter/lib/models/server_model.dart`): Server configuration, password, client list
- **`ChatModel`** (`flutter/lib/models/chat_model.dart`): Chat messages, voice call state, overlay management
- **`FileModel`** (`flutter/lib/models/file_model.dart`): File transfer jobs, directory state, confirmations
- **`InputModel`** (`flutter/lib/models/input_model.dart`): Keyboard modifiers, mouse events, pointer lock

All use `notifyListeners()` for state change propagation and are consumed via `Provider`/`ChangeNotifierProvider`.

### 3. Similar to `NativeModel` → `WebModel`

Both implement the same `PlatformModel` interface (via `getByName`/`setByName`):
- **`NativeModel`** (`flutter/lib/models/native_model.dart`): Uses FFI (dart:ffi) to call into `librustdesk.so/.dll`
- **`WebModel`** (`flutter/lib/models/web_model.dart`): Uses JS interop (`dart:js` / `dart:html`) to communicate with Rust compiled to WASM

---

## Context for the Task

### What RustDesk Is
RustDesk is a full-featured remote desktop application. The **Rust backend** handles all the heavy lifting: screen capture, video encoding, input injection, audio, clipboard sync, file transfer, terminal, port forwarding, and networking (including NAT traversal via rendezvous/relay servers). The **Flutter frontend** provides the cross-platform UI.

### Architecture Summary
- **Two-process model**: A main process (with Flutter UI) and optionally a service process (for system-level access on Windows/macOS)
- **Service-oriented server**: The server side uses a publish/subscribe `Service` trait pattern where `VideoService`, `AudioService`, `InputService`, `ClipboardService`, etc. are registered and managed by the `Connection` session handler
- **IPC-based communication**: The main process and service process communicate via named pipes / Unix domain sockets using the `Data` enum protocol
- **FFI bridge**: Flutter communicates with Rust via `flutter_rust_bridge` generated bindings in `src/flutter_ffi.rs`
- **Plugin framework**: Extensible via native plugins with a UI component system
- **Cross-platform**: Windows, macOS, Linux, Android, iOS, Web — with heavy use of `#[cfg(...)]` for platform-specific code

### Key Code Snippets

**1. Service trait pattern (server-side architecture foundation):**
```rust
// src/server/service.rs
pub trait Service: Send + Sync {
    fn name(&self) -> &str;
    fn on_subscribe(&self, sub: ConnInner);
    fn on_unsubscribe(&self, id: i32);
    fn is_subed(&self, id: i32) -> bool;
    fn join(&self);
    fn get_option(&self, opt: &str) -> Option<String>;
    fn set_option(&self, opt: &str, val: &str);
    fn ok(&self) -> bool;
    fn id(&self) -> i32;
    fn send(&mut self, msg: Arc<Message>);
    fn reset(&mut self);
    fn init(&mut self);
}
```

**2. Connection orchestration (session lifecycle):**
```rust
// src/server/connection.rs
pub async fn start(
    addr: SocketAddr,
    stream: super::Stream,
    id: i32,
    server: super::ServerPtrWeak,
    control_permissions: Option<ControlPermissions>,
) {
    // Creates services, performs key exchange, handles authentication,
    // then enters the main message loop routing messages between peer and services
}
```

**3. Flutter FFI bridge pattern:**
```dart
// flutter/lib/models/native_model.dart
class RustdeskImpl {
  static String getByName(String name, [String arg = '']) {
    // Calls into Rust via FFI
    return ffiGetByName(name, arg);
  }
  static void setByName(String name, [String value = '']) {
    ffiSetByName(name, value);
  }
}
```

**4. IPC protocol (all message types):**
```rust
// src/ipc.rs
pub enum Data {
    SendConfirm(Vec<u8>),
    KeyDown(enigo::Key),
    KeyUp(enigo::Key),
    Mouse((Vec<u8>, i32, String, u32, bool, bool)),
    ClipboardNonFile(Option<(String, Vec<ClipboardNonFile>)>),
    PrivacyModeState((i32, PrivacyModeState, String)),
    Plugin(Plugin),
    // ... 50+ more variants
}
```

**5. Server service registration:**
```rust
// src/server.rs
// In the server initialization:
add_service(Box::new(audio_service::new()));
add_service(Box::new(display_service::new()));
add_service(Box::new(clipboard_service::new(clipboard_service::NAME.to_owned())));
add_service(Box::new(input_service::new_cursor()));
add_service(Box::new(input_service::new_pos()));
add_service(Box::new(printer_service::new(printer_service::NAME.to_owned())));
```