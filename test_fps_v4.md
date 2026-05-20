I now have comprehensive understanding of the project. Let me compile the full architecture analysis.

---

## Project Summary

**FPSSample** is a Unity-based first-person shooter sample project by Unity Technologies, built to demonstrate high-quality multiplayer FPS gameplay using Unity's ECS (Entity Component System), HDRP (High Definition Render Pipeline), and custom networking stack. The project is approximately **12,727 files** total, with **1,513 C# source files**, **199 HLSL shader files**, and **103 shader files**. It uses Unity's **C# Job System**, **Burst Compiler**, and **ECS** for performance-critical systems.

---

## Architecture

### Architecture Type: **Custom ECS-based Layered Architecture with Client/Server Split**

The project follows a **client-server authoritative model** with **client-side prediction** and **server reconciliation**. The architecture is organized into distinct layers:

#### Layer 1: Game Loop Layer (`Assets/Scripts/Game/Main/`)
- **`Game.cs`** — The root MonoBehaviour with `DefaultExecutionOrder(-1000)`. Initializes all systems, manages game loop transitions, handles input, and runs the main update loop.
- **`ClientGameLoop.cs`** — Client-side game loop. Creates `ClientGameWorld` with client-specific modules (CharacterModuleClient, ProjectileModuleClient, etc.) and handles input, prediction, rendering.
- **`ServerGameLoop.cs`** — Server-side game loop. Creates `ServerGameWorld` with server-specific modules (CharacterModuleServer, ProjectileModuleServer, etc.) and handles authoritative simulation.
- **`PreviewGameLoop.cs`** — Single-player preview mode combining both client and server modules locally.
- **`ThinClientGameLoop.cs`** — Headless client for stress testing.

#### Layer 2: Entity Layer (`Assets/Scripts/Game/Entity/`)
- **`GameWorld.cs`** — Wraps Unity's ECS `World`. Manages entity spawning/despawning, scene entity registration, and provides the core `EntityManager` access.
- **`SceneEntity.cs`** — Simple MonoBehaviour marker component identifying entities in scenes that should be added to GameWorld.

#### Layer 3: Module Layer (`Assets/Scripts/Game/Modules/`)
Each module follows a **Client/Server/Shared** pattern:
- **Character** — Character movement, animation, abilities, hero types
- **Player** — Local player, user commands, player state
- **Projectile** — Projectile spawning, movement, hit detection
- **HitCollision** — Ray/sphere collision queries, hit detection
- **ReplicatedEntity** — Network entity replication, state synchronization
- **Presentation** — Visual presentation entities
- **Effect** — VFX and hit scan effects
- **Item** — Weapon/item definitions and behaviors
- **Grenade** — Grenade entity factory
- **Ragdoll** — Ragdoll physics
- **SpectatorCam** — Spectator camera

#### Layer 4: System Layer (`Assets/Scripts/Game/Systems/`)
- **GameMode** — Game mode management (Deathmatch, Assault), team management, spawn points
- **Damage** — Damage events, health state, damage history
- **DamageArea** — Area-of-effect damage
- **DestructibleProp** — Destructible environment objects
- **InputSystem** — Input accumulation and user command generation
- **Chat** — Chat system
- **Movable** — Moving platforms
- **NamePlate** — Player name plates
- **Teleporter** — Teleportation volumes
- **Platform** — Platform movement

#### Layer 5: Networking Layer (`Assets/Scripts/Networking/`)
- **`NetworkClient.cs`** / **`NetworkServer.cs`** — Client and server network transport
- **`NetworkConnection.cs`** — Connection management, fragmentation, reliability
- **`NetworkSchema.cs`** — Schema-based serialization with delta compression
- **`NetworkPrediction.cs`** — Snapshot prediction for bandwidth optimization
- **`BitInputStream.cs`** / **`BitOutputStream.cs`** — Bit-level serialization
- **`SocketTransport.cs`** — UDP socket transport implementation

#### Layer 6: Audio Layer (`Assets/Scripts/Audio/`)
- **`ISoundSystem.cs`** — Sound system interface
- **`SoundSystem.cs`** — Implementation with emitter pooling, spatial audio
- **`SoundBank.cs`** / **`SoundDef.cs`** — Sound asset definitions

#### Layer 7: Core/Utility Layer
- **`ConfigVars.cs`** — Configurable variables with attribute injection
- **`LevelManager.cs`** — Level loading/unloading with build stripping
- **`SimpleBundleManager.cs`** — Asset bundle loading
- **`BundledResourceManager.cs`** — Resource management with GUID-based asset loading
- **`BaseComponentDataSystem.cs`** — Generic ECS component system base classes

---

## Key Files

| File | Purpose | Why Relevant |
|------|---------|-------------|
| `Assets/Scripts/Game/Main/Game.cs` | Root game class, initializes all systems | Entry point, manages game loops, config vars, input |
| `Assets/Scripts/Game/Main/ClientGameLoop.cs` | Client-side game loop | Creates client modules, handles prediction/rendering |
| `Assets/Scripts/Game/Main/ServerGameLoop.cs` | Server-side game loop | Authoritative simulation, handles client commands |
| `Assets/Scripts/Game/Entity/GameWorld.cs` | ECS world wrapper | Core entity management, spawning/despawning |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs` | Client character module | Client-side character systems, presentation, camera |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Server character module | Authoritative character spawning, damage handling |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleShared.cs` | Shared character systems | System collections organized by update phase |
| `Assets/Scripts/Game/Modules/Character/CharacterSystemShared.cs` | Shared character logic | Spawn, despawn, presentation state, ground test |
| `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntityModuleClient.cs` | Client replication | Entity spawn/update/despawn from network, rollback, interpolation |
| `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntityModuleServer.cs` | Server replication | Entity registration, snapshot generation |
| `Assets/Scripts/Game/Systems/GameMode/GameModeSystemServer.cs` | Server game mode | Game mode lifecycle, player join/respawn/kill |
| `Assets/Scripts/Game/Systems/GameMode/Modes/GameModeDeathmatch.cs` | Deathmatch mode | Team deathmatch logic, round management |
| `Assets/Scripts/Game/Systems/GameMode/Modes/GameModeAssault.cs` | Assault mode | Attack/defend capture point logic |
| `Assets/Scripts/Networking/NetworkClient.cs` | Network client | Connection management, command queuing, snapshot consumption |
| `Assets/Scripts/Networking/NetworkServer.cs` | Network server | Client management, snapshot generation, command processing |
| `Assets/Scripts/Networking/NetworkSchema.cs` | Schema serialization | Field types, delta compression, prediction plans |
| `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | ECS system base | Generic component system templates (1-3 components) |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterPredicted.cs` | Predicted state | Client-predicted character state with serialization |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterInterpolated.cs` | Interpolated state | Interpolated character state for smooth rendering |
| `Assets/Scripts/Game/Modules/Player/UserCommand.cs` | User input command | Serialized input: movement, look, buttons |
| `Assets/Scripts/Game/Modules/Player/LocalPlayer.cs` | Local player | Player state, command buffer, controlled entity |
| `Assets/Scripts/Game/Core/ConfigVars.cs` | Config variables | Attribute-injected runtime-configurable variables |
| `Assets/Scripts/Game/Core/LevelManager.cs` | Level management | Scene loading with build stripping (client/server) |
| `Assets/Scripts/Utils/BundledResource/BundledResourceManager.cs` | Resource management | GUID-based asset loading from bundles or editor |

---

## Key Symbols

### Core Game Loop
- **`Game`** (MonoBehaviour, `DefaultExecutionOrder(-1000)`) — Singleton root. Fields: `game`, `m_gameLoops`, `m_DebugOverlay`. Methods: `Init()`, `Update()`, `FixedUpdate()`, `LateUpdate()`, `RequestGameLoop()`, `IsHeadless()`.
- **`ClientGameLoop`** / **`ServerGameLoop`** / **`PreviewGameLoop`** / **`ThinClientGameLoop`** — Game loop implementations.

### Entity System
- **`GameWorld`** — Wraps ECS `World`. Methods: `Spawn()`, `RequestDespawn()`, `ProcessDespawns()`, `RegisterSceneEntities()`, `GetEntityManager()`, `GetECSWorld()`.
- **`SceneEntity`** (MonoBehaviour) — Marker component for scene entities.
- **`LocalPlayer`** (MonoBehaviour) — Fields: `playerId`, `playerState`, `networkClient`, `command`, `commandBuffer`, `controlledEntity`.

### Character System
- **`Character`** (MonoBehaviour) — Character entity. Methods: `TeleportTo()`, `ShowHistory()`.
- **`CharacterPredictedData`** (IComponentData) — Fields: `tick`, `velocity`, `position`, `action`, `locoState`, `sprinting`, `jumpCount`, `damageTick`. Methods: `Serialize()`, `Deserialize()`, `VerifyPrediction()`.
- **`CharacterInterpolatedData`** (IComponentData) — Fields: `position`, `rotation`, `aimYaw`, `aimPitch`, `moveYaw`, `charLocoState`, `sprintWeight`, `footIkOffset`, etc. Methods: `Serialize()`, `Deserialize()`, `Interpolate()`.
- **`CharacterModuleClient`** — Constructor creates systems: `HandleSpawnSystems`, `HandleDespawnSystems`, `AbilityRequestUpdateSystems`, `MovementStartSystems`, `MovementResolveSystems`, `AbilityStartSystems`, `AbilityResolveSystems`, `InterpolateSystems`, `LateUpdateSystems`.
- **`CharacterModuleServer`** — Constructor creates: `HandleCharacterSpawnRequests`, `HandleCharacterDespawnRequests`, `HandleDamage`, plus shared systems.
- **`CharacterModuleShared`** — Contains `SystemCollection` arrays for each update phase.

### Ability System
- **`IAbility`** — Abstract base. Method: `UpdateAbilityUI()`.
- **`AbilityCollection`** (ScriptableObject) — Factory-based ability creation. Contains `DefaultBehaviourController_Update` system that manages ability activation/deactivation with `canRunWith` and `canInterrupt` rules.
- **`CharBehaviorFactory`** — Factory for creating character behavior entities.

### Replicated Entity System
- **`ReplicatedEntityData`** (IComponentData) — Fields: `id`, `predictingPlayerId`, `assetGuid`. Methods: `Serialize()`, `Deserialize()`.
- **`ReplicatedEntityModuleClient`** — Methods: `ProcessEntitySpawn()`, `ProcessEntityUpdate()`, `ProcessEntityDespawns()`, `Rollback()`, `Interpolate()`, `StorePredictedState()`, `FinalizedStateHistory()`.
- **`ReplicatedEntityModuleServer`** — Methods: `ReserveSceneEntities()`, `HandleSpawning()`, `HandleDespawning()`, `GenerateEntitySnapshot()`.

### Networking
- **`NetworkClient`** — Delegates: `DataGenerator`, `MapUpdateProcessor`, `EntitySpawnProcessor`, `EntityDespawnProcessor`, `EntityUpdateProcessor`. Methods: `Connect()`, `Disconnect()`, `QueueCommand()`, `QueueEvent()`, `Update()`.
- **`NetworkServer`** — Delegates: `SnapshotGenerator`, `CommandProcessor`, `EventProcessor`. Methods: `RegisterEntity()`, `UnregisterEntity()`, `GenerateSnapshot()`, `HandleClientCommands()`.
- **`NetworkConnection`** — Handles fragmentation, reliability, acknowledgments.
- **`NetworkSchema`** — Field types: `FieldValueBool`, `FieldValueInt`, `FieldValueUInt`, `FieldValueFloat`, `FieldValueVector2`, `FieldValueVector3`, `FieldValueQuaternion`, `FieldValueString`. Contains `predictPlan` for prediction.

### Game Mode
- **`GameModeSystemServer`** — Config vars: `game.respawndelay`, `game.modename`. Methods: `Restart()`, `Shutdown()`, `OnPlayerJoin()`, `OnPlayerRespawn()`, `OnPlayerKilled()`. Creates game mode instances dynamically based on `game.modename`.
- **`GameModeDeathmatch`** — Phases: PreMatch, Active, PostMatch. Config vars: `game.dm.minplayers`, `game.dm.roundlength`.
- **`GameModeAssault`** — Capture point progression. Config vars: `game.assault.roundlength`, `game.assault.minplayers`.

### Damage System
- **`DamageEvent`** (IBufferElementData) — Fields: `instigator`, `damage`, `direction`, `impulse`. Buffer capacity: 16.
- **`HealthStateData`** (IReplicatedComponent) — Fields: `health`, `maxHealth`, `deathTick`. Methods: `SetMaxHealth()`, `ApplyDamage()`.

### ECS Infrastructure
- **`BaseComponentSystem<T>`** — Generic ECS system with `OnCreateManager()` building component group from type parameters + `ExtraComponentRequirements`, auto-excluding `DespawningEntity`.
- **`BaseComponentDataSystem<T>`** — Similar but for component data.
- **`BaseComponentSystem<T1,T2>`**, **`BaseComponentSystem<T1,T2,T3>`** — Multi-component variants.

### Config System
- **`ConfigVar`** — Fields: `name`, `description`, `_stringValue`, `_intValue`, `_floatValue`. Flags: `None`, `Save`, `ServerInfo`. Uses `ConfigVarAttribute` for automatic registration via reflection.

---

## Dependencies

### Module-Level Dependencies

```
Game.cs (root)
  ├── ClientGameLoop → ClientGameWorld
  │     ├── CharacterModuleClient
  │     ├── ProjectileModuleClient
  │     ├── HitCollisionModule
  │     ├── PlayerModuleClient
  │     ├── SpectatorCamModuleClient
  │     ├── EffectModuleClient
  │     ├── ReplicatedEntityModuleClient
  │     ├── ItemModule
  │     ├── RagdollModule
  │     ├── GameModeSystemClient
  │     ├── DestructiblePropSystemClient
  │     └── Various ECS systems (TwistSystem, FanSystem, etc.)
  │
  ├── ServerGameLoop → ServerGameWorld
  │     ├── CharacterModuleServer
  │     ├── ProjectileModuleServer
  │     ├── HitCollisionModule
  │     ├── PlayerModuleServer
  │     ├── SpectatorCamModuleServer
  │     ├── ReplicatedEntityModuleServer
  │     ├── ItemModule
  │     ├── GameModeSystemServer
  │     ├── ChatSystemServer
  │     ├── MovableSystemServer
  │     ├── ServerCameraSystem
  │     └── Various ECS systems
  │
  ├── PreviewGameLoop (combines client + server modules locally)
  │
  └── ThinClientGameLoop (headless stress test client)
```

### Key Dependency Chains

1. **Input Flow**: `Game.Input` → `InputSystem.AccumulateInput()` → `UserCommand` → `LocalPlayer.commandBuffer` → `NetworkClient.QueueCommand()` → Network → `NetworkServer.ProcessCommand()` → `ServerGameLoop.HandleClientCommands()`

2. **Entity Replication Flow (Server→Client)**: `ServerGameLoop.ServerTickUpdate()` → `ReplicatedEntityModuleServer.GenerateEntitySnapshot()` → `NetworkServer.GenerateSnapshot()` → Network → `NetworkClient.Update()` → `ReplicatedEntityModuleClient.ProcessEntitySpawn/Update/Despawn()` → Client ECS world

3. **Prediction Flow**: `ClientGameLoop.Update()` → `ReplicatedEntityModuleClient.StorePredictedState()` → Simulate → `ReplicatedEntityModuleClient.FinalizedStateHistory()` → Compare with server state → Rollback if needed

4. **Damage Flow**: `DamageEvent.AddEvent()` → `CharacterModuleServer.HandleDamage.OnUpdate()` → `HealthStateData.ApplyDamage()` → Death check → `GameModeSystemServer.OnPlayerKilled()` → Respawn timer → `GameModeSystemServer.OnPlayerRespawn()` → `CharacterModuleServer.SpawnCharacter()`

---

## Conventions

### Naming Conventions
- **PascalCase** for all class names, method names, public fields, properties
- **camelCase** for private fields (prefixed with `m_` for member variables, e.g., `m_GameWorld`, `m_NetworkClient`, `m_DespawnRequests`)
- **Interfaces**: Prefix `I` (e.g., `IAbility`, `ISoundSystem`, `IComponentData`, `IReplicatedComponentSerializerFactory`)
- **Suffixes**:
  - `System` — ECS systems (e.g., `HandleCharacterSpawn`, `GroundTest`, `UpdateTeleportation`, `TwistSystem`, `FanSystem`)
  - `Module` — Module classes (e.g., `CharacterModuleClient`, `ProjectileModuleServer`, `HitCollisionModule`)
  - `Data` — Component data structs (e.g., `CharacterPredictedData`, `CharacterInterpolatedData`, `HealthStateData`, `ReplicatedEntityData`)
  - `Event` — Event structs (e.g., `DamageEvent`, `CharacterEvents`)
  - `Handler` — Animation/behavior handlers (e.g., `ActionAnimationHandler`, `AimVerticalHandler`)
  - `Factory` — Entity factories (e.g., `ProjectileEntityFactory`, `GrenadeEntityFactory`, `CharBehaviorFactory`)
  - `Registry` — Asset registries (e.g., `HeroTypeRegistry`, `ProjectileRegistry`, `ReplicatedEntityRegistry`)
  - `Definition` — Type definitions (e.g., `CharacterTypeDefinition`, `ProjectileTypeDefinition`, `ItemTypeDefinition`)
  - `Settings` — Module settings ScriptableObjects (e.g., `CharacterModuleSettings`, `PlayerModuleSettings`, `ProjectileModuleSettings`)
  - `Asset` — ScriptableObject assets (e.g., `HeroTypeAsset`)
  - `Collection` — Collection components (e.g., `AbilityCollection`, `ReplicatedEntityCollection`)
  - `Owner` — Owner components (e.g., `AbilityOwner`, `HitCollisionOwner`, `PresentationOwner`)

### Architectural Patterns

1. **Client/Server Split Pattern**: Every major module has `*ModuleClient` and `*ModuleServer` variants (e.g., `CharacterModuleClient`/`CharacterModuleServer`, `ProjectileModuleClient`/`ProjectileModuleServer`, `ReplicatedEntityModuleClient`/`ReplicatedEntityModuleServer`). Shared logic goes in `*ModuleShared` or `*SystemsShared`.

2. **ECS Component System Pattern**: Systems inherit from `BaseComponentSystem<T>` or `BaseComponentDataSystem<T>` which auto-build component groups from generic type parameters and exclude `DespawningEntity`. Systems override `Update(Entity entity, T data)`.

3. **Module Update Phase Pattern**: `CharacterModuleShared` organizes systems into ordered `SystemCollection` arrays: `m_HandleSpawnSystems`, `m_HandleDespawnSystems`, `m_AbilityRequestUpdateSystems`, `m_MovementStartSystems`, `m_MovementResolveSystems`, `m_AbilityStartSystems`, `m_AbilityResolveSystems`, `m_InterpolateSystems`, `m_LateUpdateSystems`. Each phase is called explicitly in order.

4. **Replicated Component Pattern**: Data that syncs over network implements `IReplicatedComponent` with `Serialize()`/`Deserialize()` methods and a static `CreateSerializerFactory()` method. Examples: `CharacterPredictedData`, `HealthStateData`, `ReplicatedEntityData`.

5. **Interpolated Component Pattern**: Smooth rendering data implements `IInterpolatedComponent` with `Serialize()`, `Deserialize()`, and `Interpolate()` methods. Example: `CharacterInterpolatedData`.

6. **Factory Pattern**: Entity creation uses factory classes (e.g., `CharBehaviorFactory`, `ProjectileEntityFactory`, `GrenadeEntityFactory`) that are referenced in ScriptableObject assets.

7. **ConfigVar Pattern**: Runtime-configurable variables declared as static fields with `[ConfigVar(Name = "...", DefaultValue = "...", Description = "...")]` attribute. Auto-registered via reflection in `ConfigVar.Init()`.

8. **Game Loop Pattern**: Game loops implement a state machine pattern with `Add(state, enterFn, updateFn, leaveFn)` and `SwitchTo(state)`.

9. **Game Mode Strategy Pattern**: `GameModeSystemServer` dynamically creates game mode instances (`GameModeDeathmatch`, `GameModeAssault`) based on `game.modename` config var, using a common interface (`Initialize`, `Update`, `Restart`, `Shutdown`, `OnPlayerJoin`, `OnPlayerKilled`, `OnPlayerRespawn`).

10. **Dependency Injection via Constructor**: Modules receive their dependencies through constructors (e.g., `CharacterModuleClient(GameWorld world, BundledResourceManager resourceSystem)`).

### Style Conventions
- **Async**: Not used. The project uses Unity's ECS job system (`ScheduleBatch`, `Complete()`) for parallelism.
- **Error Handling**: `Assert()` for debug assertions, `LogError()` for runtime errors, `LogWarning()` for non-fatal issues.
- **Validation**: `VerifyPrediction()` method on predicted state compares client prediction with server state.
- **Serialization**: Custom bit-level serialization via `NetworkWriter`/`NetworkReader` with quantized floats (`WriteFloatQ`, `WriteVector3Q`).
- **Profiling**: `BeginSample()`/`EndSample()` calls throughout for Unity Profiler integration.
- **Debug Visualization**: `GameDebug` class, `DrawLine()`, debug overlay text rendering.

---

## Similar Implementations

### 1. `CharacterModuleClient` / `CharacterModuleServer` / `CharacterModulePreview`
- **Pattern**: Client/Server/Preview split for the same domain
- **Similar to**: `ProjectileModuleClient`/`ProjectileModuleServer`, `PlayerModuleClient`/`PlayerModuleServer`, `ReplicatedEntityModuleClient`/`ReplicatedEntityModuleServer`, `SpectatorCamModuleClient`/`SpectatorCamModuleServer`
- **Why similar**: All follow the same pattern of creating client/server-specific ECS systems, registering them in the GameWorld, and providing `Shutdown()` cleanup.

### 2. `GameModeDeathmatch` / `GameModeAssault`
- **Pattern**: Strategy pattern for game modes
- **Similar to**: Both implement the same interface (`Initialize`, `Update`, `Restart`, `Shutdown`, `OnPlayerJoin`, `OnPlayerKilled`, `OnPlayerRespawn`) and are dynamically selected by `GameModeSystemServer`.

### 3. `CharacterPredictedData` / `CharacterInterpolatedData` / `HealthStateData` / `ReplicatedEntityData`
- **Pattern**: Replicated/Interpolated component data
- **Why similar**: All implement `Serialize()`/`Deserialize()` methods, have static `CreateSerializerFactory()` methods, and use the custom network serialization system with quantized fields.

---

## Context for the Task

### Architecture Summary

The FPSSample project is a **client-server authoritative multiplayer FPS** built on Unity's ECS. The architecture is organized around:

1. **GameWorld** — wraps Unity ECS `World`, manages entity lifecycle
2. **Modules** — domain-specific groupings (Character, Projectile, Player, etc.) each split into Client/Server/Shared
3. **Systems** — ECS `ComponentSystem` subclasses that operate on specific component combinations
4. **ReplicatedEntity** — network-synchronized entities with prediction, interpolation, and rollback
5. **GameMode** — strategy-pattern game modes (Deathmatch, Assault) managed by `GameModeSystemServer`

### Key Code Snippets

**1. Module Construction Pattern (ClientGameWorld constructor):**
```csharp
public ClientGameWorld(GameWorld world, NetworkClient networkClient, ...) {
    new CharacterModuleClient(m_GameWorld, resourceSystem);
    new ProjectileModuleClient(m_GameWorld, resourceSystem);
    new HitCollisionModule(m_GameWorld, 1, 1);
    new PlayerModuleClient(m_GameWorld);
    new SpectatorCamModuleClient(m_GameWorld);
    new EffectModuleClient(m_GameWorld, resourceSystem);
    new ReplicatedEntityModuleClient(m_GameWorld, resourceSystem);
    new ItemModule(m_GameWorld);
    new RagdollModule(m_GameWorld);
    // ECS systems
    new TwistSystem(m_GameWorld);
    new FanSystem(m_GameWorld);
    new TranslateScaleSystem(m_GameWorld);
}
```

**2. ECS Component System Base Pattern:**
```csharp
public class HandleCharacterSpawn : BaseComponentSystem<CharacterSpawnRequest> {
    protected override void OnCreateManager() {
        base.OnCreateManager(); // builds component group from T + ExtraComponentRequirements
        // additional setup
    }
    protected override void OnUpdate() {
        // iterate entities with CharacterSpawnRequest
        for (var i = 0; i < requestArray.Length; i++) {
            SpawnCharacter(m_world, playerState, request.position, ...);
            DestroyEntity(requestEntityArray[i]);
        }
    }
}
```

**3. Network Replication Flow (Server → Client):**
```csharp
// Server: Generate snapshot for each entity
NetworkServer.GenerateSnapshot(ISnapshotGenerator snapshotGenerator, float simTime) {
    foreach (var connection in m_Connections) {
        foreach (var entity in m_Entities) {
            snapshotGenerator.GenerateEntitySnapshot(entity.id, ref writer);
        }
    }
}

// Client: Process received snapshot
ReplicatedEntityModuleClient.ProcessEntityUpdate(int serverTick, int id, ref NetworkReader reader) {
    var replicatedEntity = m_EntityCollection.Find(id);
    replicatedEntity.Deserialize(ref context, ref reader);
    // Store in history buffer for interpolation
}
```

### What to Focus On for Code Review

- **Module lifecycle**: Modules are created in constructors but `Shutdown()` must be called explicitly. Verify all modules are properly shut down.
- **ECS system registration**: Systems are added via `m_world.GetECSWorld().Add(system)` — ensure no double-registration.
- **Prediction correctness**: `CharacterPredictedData.VerifyPrediction()` compares client prediction with server state — check threshold values.
- **Network serialization**: Quantized floats (`WriteFloatQ`, `WriteVector3Q`) with precision parameters — verify precision is adequate.
- **Resource management**: `BundledResourceManager.GetSingleAssetResource()` caches loaded assets — verify no memory leaks.
- **ConfigVar injection**: Static fields with `[ConfigVar]` attribute are auto-registered — verify naming conventions (lowercase, dot-separated).