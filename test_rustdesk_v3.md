I now have comprehensive information. Here is the architecture analysis:

---

## Architecture Analysis: RustDesk

### 1. PROJECT SUMMARY

**RustDesk** is an open-source remote desktop application (v1.4.6) written primarily in **Rust** (backend) with a **Flutter/Dart** (frontend) GUI. It has 928 files total, 580 classes, and 25,642 methods. The project is structured as a **hybrid native + cross-platform app** using a **layered architecture** with Rust powering the core networking, protocol, and platform-specific services, and Flutter providing the UI layer across desktop (Windows/macOS/Linux) and mobile (Android/iOS).

### 2. ARCHITECTURE

**Architecture type: Layered + Service-Oriented with FFI Bridge**

The system has three major layers:

**Layer 1 — Rust Core (src/)**
- **Network & Protocol Layer**: `rendezvous_mediator.rs` (NAT traversal, relay), `kcp_stream.rs` (KCP transport), `lan.rs` (LAN discovery), `port_forward.rs`
- **Client Layer** (`src/client/`): `io_loop.rs` (connection loop), `helper.rs`, `file_trait.rs`, `screenshot.rs`
- **Server Layer** (`src/server/`): `connection.rs` (session management), `video_service.rs`, `audio_service.rs`, `input_service.rs`, `clipboard_service.rs`, `display_service.rs`, `terminal_service.rs`, `printer_service.rs`
- **Platform Abstraction** (`src/platform/`): OS-specific implementations for Windows, macOS, Linux (input, display, privileges)
- **IPC Layer** (`src/ipc.rs`): Inter-process communication between service and UI processes
- **UI Interface** (`src/ui_interface.rs`, `src/ui_session_interface.rs`, `src/ui_cm_interface.rs`): Abstract interfaces for UI communication
- **Plugin Framework** (`src/plugin/`): Extensible plugin system
- **FFI Bridge** (`src/flutter.rs`, `src/flutter_ffi.rs`): Exposes Rust functions to Flutter via `flutter_rust_bridge`

**Layer 2 — Flutter/Dart UI (flutter/lib/)**
- **Entry Point**: `main.dart` — handles multi-window, mobile, and desktop app initialization
- **Common Layer** (`common/`): Shared widgets, state management (`shared_state.dart`), HBBS client (`hbbs/`), formatters
- **Desktop Layer** (`desktop/`): Pages (screens), screens (remote/file transfer/terminal), widgets (toolbar, popup menus, tab bar)
- **Mobile Layer** (`mobile/`): Mobile-specific widgets and pages
- **Web Layer** (`web/`): Web-specific bridge and renderer
- **Models** (`models/`): State models (peer, file, chat, input, server, state, etc.)
- **Plugin System** (`plugin/`): Plugin manager, handlers, event system, UI manager
- **Utils** (`utils/`): Event loop, HTTP service, multi-window manager, platform channels

**Layer 3 — Native Libraries (libs/)**
- `scrap/`: Screen capture library
- `enigo/`: Keyboard/mouse input simulation
- `clipboard/`: Clipboard management
- `hbb_common/`: Shared protocol types and utilities
- `virtual_display/`: Virtual display driver (Windows)

**Communication Flow:**
```
Flutter UI <--FFI (flutter_rust_bridge)--> Rust Core <--TCP/KCP--> Remote Peer
                                              |
                                         Platform Services
                                        (input, display, audio)
```

### 3. RELATED FILES

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/lib.rs` | Root module declarations | Defines all Rust modules and conditional compilation |
| `src/server/connection.rs` | Server-side session handler | Core connection lifecycle, authentication, message routing |
| `src/client/io_loop.rs` | Client-side connection loop | Handles peer communication, message dispatch, reconnection |
| `src/flutter_ffi.rs` | FFI bridge functions | Exposes ~100+ functions to Flutter via `flutter_rust_bridge` |
| `src/flutter.rs` | Flutter integration | Texture rendering, plugin loading, core main entry |
| `src/core_main.rs` | Application bootstrap | CLI parsing, service startup, process management |
| `src/rendezvous_mediator.rs` | NAT traversal & relay | Rendezvous server communication, UDP punching, relay setup |
| `src/server/video_service.rs` | Video capture & encoding | Screen capture, frame scheduling, capturer management |
| `src/server/input_service.rs` | Input simulation | Keyboard/mouse event injection, modifier handling |
| `src/ipc.rs` | Inter-process communication | Service-to-UI message protocol (enums for all message types) |
| `src/ui_interface.rs` | UI abstraction | Options management, ID resolution, install/update |
| `src/ui_session_interface.rs` | Session UI state | Connection state, permissions, display settings |
| `src/common.rs` | Shared utilities | Version checks, platform detection, global state |
| `flutter/lib/main.dart` | Flutter entry point | Multi-window management, app initialization |
| `flutter/lib/common.dart` | Shared Flutter code | Theme, widgets, constants, platform detection |
| `flutter/lib/models/state_model.dart` | Reactive state | Connection status, display info, peer state |
| `flutter/lib/plugin/handlers.dart` | Plugin event handlers | UI event routing to plugins |

### 4. DEPENDENCY GRAPH

**Module-level dependencies (Rust src/):**
```
src/lib.rs (root module)
  ├── src/server/ ──> src/common.rs, src/ipc.rs, libs/scrap, libs/enigo
  ├── src/client/ ──> src/common.rs, src/ipc.rs, libs/enigo, libs/clipboard
  ├── src/flutter_ffi.rs ──> src/flutter.rs, src/server/, src/client/
  ├── src/flutter.rs ──> src/core_main.rs, libs (texture plugins)
  ├── src/core_main.rs ──> src/server/, src/client/, src/rendezvous_mediator.rs
  ├── src/rendezvous_mediator.rs ──> src/server/, src/lan.rs
  ├── src/ipc.rs ──> src/common.rs, hbb_common
  ├── src/ui_interface.rs ──> src/common.rs, hbb_common
  ├── src/ui_session_interface.rs ──> hbb_common
  └── src/platform/ ──> platform-specific native code (C++, ObjC)
```

**Flutter/Dart module dependencies:**
```
flutter/lib/main.dart
  ├── flutter/lib/common.dart (theme, widgets, platform detection)
  ├── flutter/lib/consts.dart (constants)
  ├── flutter/lib/common/shared_state.dart (reactive state)
  ├── flutter/lib/models/* (state models)
  ├── flutter/lib/desktop/pages/* (screen pages)
  ├── flutter/lib/desktop/screen/* (remote/file/terminal screens)
  ├── flutter/lib/plugin/* (plugin system)
  └── flutter/lib/utils/* (multi-window, HTTP, event loop)
```

**FFI Bridge (key call chain):**
```
Flutter (Dart) ──flutter_rust_bridge──> src/flutter_ffi.rs
  ├── session_start() ──> src/server/connection.rs::start()
  ├── session_login() ──> connection login flow
  ├── peer_get_sessions_count() ──> sessions::get_session_count()
  ├── start_global_event_stream() ──> event dispatch
  └── initialize() ──> global_init(), load_custom_client()
```

### 5. CONVENTIONS

**Naming:**
1. **Rust**: `snake_case` for functions/variables, `PascalCase` for types/enums
2. **Dart**: `camelCase` for functions/variables, `PascalCase` for classes
3. **Service suffix**: `*_service.rs` — `audio_service`, `video_service`, `input_service`, `clipboard_service`, `terminal_service`, `printer_service`
4. **Interface suffix**: `*_interface.rs` — `ui_interface`, `ui_session_interface`, `ui_cm_interface`
5. **Model suffix**: `*_model.dart` — `peer_model`, `file_model`, `state_model`, `server_model`, `chat_model`
6. **Page suffix**: `*_page.dart` — `desktop_home_page`, `remote_page`, `server_page`
7. **Screen suffix**: `desktop_*_screen.dart` — `desktop_remote_screen`, `desktop_file_transfer_screen`
8. **Widget suffix**: descriptive widget names — `peer_card`, `tabbar_widget`, `popup_menu`
9. **Enum naming**: `PascalCase` — `SvcStatus`, `JobState`, `WindowsTarget`, `MsgFromUi`
10. **FFI functions**: `snake_case` — `session_start`, `session_login`, `start_global_event_stream`

**Architectural patterns:**
- **Service pattern**: Each server capability is a separate service (`VideoService`, `AudioService`, `InputService`) registered in `Server::services`
- **FFI bridge pattern**: Rust exposes functions via `flutter_rust_bridge` with `StreamSink` for async events
- **Reactive state**: Flutter uses `RxBool`, `RxDouble` from `get` package for reactive state management
- **Multi-window**: Flutter uses `desktop_multi_window` package for separate windows (remote, file transfer, terminal)
- **IPC message enum**: `ipc.rs` defines a massive enum `IpcMessage` with all inter-process message variants
- **Conditional compilation**: Heavy use of `#[cfg(...)]` for platform-specific code

**Style:**
- Rust: `async`/`await` throughout, `tokio` runtime, `Mutex`/`RwLock` for shared state
- Error handling: `allow_err!` macro, `Result` returns, `unwrap_or_default()` for fallbacks
- Flutter: `StatefulWidget`/`StatelessWidget` pattern, `BuildContext` for theming

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Similarity |
|-------|------|------------|
| `VideoService` | `src/server/video_service.rs` | Service pattern — same as `AudioService`, `InputService`, `ClipboardService` |
| `InputService` | `src/server/input_service.rs` | Service pattern — registered via `add_service(Box::new(...))` |
| `Connection` | `src/server/connection.rs` | Session handler — similar lifecycle to `IoLoop` in client |
| `IoLoop` | `src/client/io_loop.rs` | Client-side counterpart to server `Connection` |
| `DesktopRemoteScreen` | `flutter/lib/desktop/screen/desktop_remote_screen.dart` | Screen widget — similar to `DesktopFileTransferScreen`, `DesktopTerminalScreen` |
| `PeerModel` | `flutter/lib/models/peer_model.dart` | State model — similar pattern to `FileModel`, `ChatModel`, `ServerModel` |

### 7. TASK CONTEXT

This is a **remote desktop application** with a Rust backend and Flutter frontend. The Rust core handles all networking (TCP/KCP), protocol encoding (protobuf via `hbb_common`), screen capture (`scrap`), input simulation (`enigo`), clipboard sync, audio, and platform-specific services. The Flutter UI provides the user interface across desktop, mobile, and web platforms, communicating with Rust via `flutter_rust_bridge` FFI.

Key architectural points:
- The `src/server/` directory contains all server-side services (video, audio, input, clipboard, terminal, printer) — each is a self-contained module with a `service_name_prefix()` and `run()` method
- The `src/client/` directory handles the client-side connection loop and file transfer
- `src/flutter_ffi.rs` is the bridge — it exposes ~100+ functions to Dart, each handling a specific operation (session management, login, file ops, settings)
- `src/ipc.rs` defines the inter-process communication protocol between the service process and UI process
- The Flutter side uses a page/screen/widget pattern: `pages/` for full-screen views, `screen/` for remote session screens, `widgets/` for reusable components
- State management uses reactive `Rx` types from the `get` package
- Multi-window support is handled via `desktop_multi_window` package with window types: remote, file transfer, view camera, port forward, terminal

### 8. RELEVANT CODE SNIPPETS

**Snippet 1 — Rust module structure (src/lib.rs, lines 1-15):**
```rust
mod keyboard;
pub mod platform;
pub use platform::{
    clip_cursor, get_cursor, get_cursor_data, get_cursor_pos, get_focused_display,
    set_cursor_pos, start_os_service,
};
mod server;
pub use self::server::*;
mod client;
mod lan;
mod rendezvous_mediator;
pub use self::rendezvous_mediator::*;
pub mod common;
pub mod ipc;
```
*Shows the top-level module organization and conditional compilation patterns.*

**Snippet 2 — Service registration pattern (src/server.rs, lines ~30-50):**
```rust
add_service(Box::new(audio_service::new()));
add_service(Box::new(display_service::new()));
add_service(Box::new(clipboard_service::new(clipboard_service::NAME.to_owned())));
add_service(Box::new(input_service::new_cursor()));
add_service(Box::new(input_service::new_pos()));
add_service(Box::new(printer_service::new(printer_service::NAME.to_owned())));
```
*Shows the service registration pattern — each capability is a boxed service added to the server.*

**Snippet 3 — FFI bridge function pattern (src/flutter_ffi.rs, lines ~50-70):**
```rust
pub fn session_add_sync(
    session_id: SessionID,
    id: String,
    is_file_transfer: bool,
    is_view_camera: bool,
    is_port_forward: bool,
    is_rdp: bool,
    is_terminal: bool,
    ...
) -> String {
    session_add(&session_id, &id, ...);
    if let Err(e) = ... {
        SyncReturn(format!("Failed to add session with id {}, {}", &id, e))
    }
    SyncReturn("".to_owned())
}
```
*Shows the FFI bridge pattern — synchronous functions return `SyncReturn`, async ones use `StreamSink`.*

**Snippet 4 — Flutter multi-window entry (flutter/lib/main.dart, lines ~30-50):**
```dart
if (args.isNotEmpty && args.first == 'multi_window') {
    setWindowId(kWindowId!);
    switch (kWindowType) {
        case kAppTypeDesktopRemote:
            runMultiWindow(argument, kAppTypeDesktopRemote);
        case kAppTypeDesktopFileTransfer:
            runMultiWindow(argument, kAppTypeDesktopFileTransfer);
        ...
    }
}
```
*Shows the multi-window architecture — each window type runs a separate Flutter app instance.*

**Snippet 5 — IPC message enum (src/ipc.rs, lines ~30-50):**
```rust
pub enum IpcMessage {
    SendConfirm(Vec<u8>),
    Sequence(String),
    KeyDown(enigo::Key),
    KeyUp(enigo::Key),
    KeyClick(enigo::Key),
    GetKeyState(enigo::Key),
    MoveTo(i32, i32),
    MoveRelative(i32, i32),
    Down(enigo::MouseButton),
    Up(enigo::MouseButton),
    ...
}
```
*Shows the IPC protocol — a large enum covering all message types between service and UI processes.*