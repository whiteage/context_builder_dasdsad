Now I have enough information to produce the architecture analysis. Let me compile it.

Here is the architecture analysis of FPSSample:

---

## 1. PROJECT SUMMARY

**FPSSample** is Unity's official multiplayer FPS sample project (Unity Technologies). It demonstrates a complete client-server FPS game using Unity's ECS (Entity Component System), HDRP rendering, and a custom networking layer.

- **Scale**: 12,727 files total, 1,513 C# source files, 2152 classes, 8239 methods
- **Languages**: C# (primary), HLSL (199), Shader (103), YAML (7781 — Unity assets/prefabs/scenes)
- **Tech Stack**: Unity 2018+ with HDRP, Unity ECS (pre-Entities 1.0), Unity Transport Package, Visual Effect Graph, PlayableGraph animation, Asset Bundles
- **Documentation**: `Documentation/` folder with Animation.md, Characters.md, GettingStarted.md, SourceCode.md

## 2. ARCHITECTURE

**Type**: Client-Server Game Architecture with ECS (Entity Component System) + Layered Modules

```
Game (MonoBehaviour entry point)
  |
  +-- GameLoop (ClientGameLoop / ServerGameLoop / ThinClientGameLoop)
  |     |
  |     +-- GameWorld (ECS World wrapper)
  |           |
  |           +-- Modules (Character, Player, Projectile, Grenade, Effect, etc.)
  |           |     Each Module has: Shared + Server + Client variants
  |           |     Each Module contains: Systems (ECS ComponentSystems)
  |           |
  |           +-- Systems (GameMode, Damage, Movable, Chat, etc.)
  |           |
  |           +-- Entity (GameWorld, SceneEntity)
  |
  +-- Networking (custom, not UNET)
  |     NetworkClient + NetworkServer + NetworkConnection
  |     Bit-level serialization (BitInputStream/OutputStream)
  |     Delta compression, prediction, snapshot system
  |
  +-- Frontend (UI menus: MainMenu, JoinMenu, OptionsMenu, ScoreBoard)
  |
  +-- Audio (SoundSystem, SoundBank, SoundDef)
  |
  +-- ECS (BaseComponentDataSystem, BaseComponentSystem)
  |
  +-- Utils (BundledResourceManager, DebugDraw, Primitives, etc.)
```

**Key architectural layers**:

1. **Game Loop Layer** (`Game/Main/`) — Entry points: `Game.cs` (MonoBehaviour), `ClientGameLoop`, `ServerGameLoop`, `PreviewGameLoop`, `ThinClientGameLoop`
2. **Game World Layer** (`Game/Entity/`) — `GameWorld` wraps Unity ECS `World` + `EntityManager`
3. **Module Layer** (`Game/Modules/`) — Feature modules (Character, Player, Projectile, Grenade, Effect, HitCollision, Item, Ragdoll, ReplicatedEntity, SpectatorCam, Presentation). Each module has `*ModuleShared`, `*ModuleServer`, `*ModuleClient` classes.
4. **System Layer** (`Game/Systems/` + inside Modules) — ECS ComponentSystems that process entities
5. **Networking Layer** (`Networking/`) — Custom transport-agnostic networking with `NetworkClient`, `NetworkServer`, `NetworkConnection`, bit-level serialization, delta compression, prediction
6. **Frontend Layer** (`Game/Frontend/`) — UI menus and HUD
7. **ECS Infrastructure** (`ECS/`) — `BaseComponentDataSystem<T1..T5>` generic base classes

**Dependency flow**: Game -> GameLoop -> GameWorld -> Modules -> Systems -> ECS. Networking is consumed by GameLoops. Frontend is standalone UI.

## 3. RELATED FILES

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| Game.cs | `Assets/Scripts/Game/Main/Game.cs` | MonoBehaviour | Entry point, initializes game loops, config vars, input |
| ClientGameLoop.cs | `Assets/Scripts/Game/Main/ClientGameLoop.cs` | GameLoop | Client-side orchestration: creates modules, calls Update/Interpolate/LateUpdate |
| ServerGameLoop.cs | `Assets/Scripts/Game/Main/ServerGameLoop.cs` | GameLoop | Server-side orchestration: creates modules, handles commands, tick update |
| GameWorld.cs | `Assets/Scripts/Game/Entity/GameWorld.cs` | Entity | Wraps ECS World, manages spawn/despawn, scene entities |
| BaseComponentDataSystem.cs | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | System | Generic ECS system base (1-5 component params), auto-creates component groups |
| NetworkClient.cs | `Assets/Scripts/Networking/NetworkClient.cs` | Service | Client networking: connect, send commands, receive snapshots |
| NetworkServer.cs | `Assets/Scripts/Networking/NetworkServer.cs` | Service | Server networking: manage connections, generate snapshots, handle commands |
| CharacterModuleServer.cs | `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Module | Server character logic: spawn, despawn, damage handling |
| CharacterModuleClient.cs | `Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs` | Module | Client character logic: presentation, interpolation, camera |
| CharacterSystemShared.cs | `Assets/Scripts/Game/Modules/Character/CharacterSystemShared.cs` | System | Shared ECS systems: spawn, despawn, teleportation, ground test |
| GameModeSystemServer.cs | `Assets/Scripts/Game/Systems/GameMode/GameModeSystemServer.cs` | System | Server game mode logic: player join/respawn/kill, timer |
| ReplicatedEntity.cs | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntity.cs` | Entity | Replicated entity component with serialization/deserialization |
| Ability_Sprint.cs | `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Sprint.cs` | Factory | Example ability: sprint with predicted state, serialization |
| BuildAttributes.cs | `Assets/Scripts/Build/BuildAttributes.cs` | Attribute | ServerOnly/ClientOnly/DevelopmentOnly component stripping attributes |
| LevelManager.cs | `Assets/Scripts/Game/Core/LevelManager.cs` | Service | Level loading/unloading with layered scenes, code stripping |

## 4. DEPENDENCY GRAPH

**Module-level dependencies** (from `Assets/Scripts/`):

```
Game/Main (Game.cs, ClientGameLoop, ServerGameLoop)
  |-- Game/Entity (GameWorld)
  |-- Game/Modules/* (Character, Player, Projectile, etc.)
  |-- Game/Systems/* (GameMode, Damage, Movable, etc.)
  |-- Game/Core (LevelManager, ConfigVars)
  |-- Game/Frontend (UI menus)
  |-- Networking (NetworkClient, NetworkServer)
  |-- ECS (BaseComponentDataSystem)
  |-- Audio (SoundSystem)
  |-- Utils (BundledResourceManager, DebugDraw)
  |-- Build (BuildAttributes)

Networking/
  |-- (uses Unity Transport Package from Packages/)
  |-- Compression/
  |-- Matchmaking/

Game/Modules/Character/
  |-- Game/Entity (GameWorld)
  |-- ECS (BaseComponentDataSystem)
  |-- Utils/BundledResource
  |-- Game/Modules/Player (UserCommand)
  |-- Game/Modules/HitCollision
  |-- Game/Systems/Damage
```

**Key dependency patterns**:
- Modules depend on `GameWorld` and ECS base classes
- Systems depend on `GameWorld` (passed via constructor)
- `GameWorld` wraps Unity ECS `World` and `EntityManager`
- Networking is consumed by GameLoops but modules don't directly depend on it
- `BundledResourceManager` is passed to modules for asset loading

**Call graph (simplified update loop)**:
```
Game.Update()
  -> ClientGameLoop.Update(frameDuration)
    -> HandleTime() / ResolveReferenceFromLocalPlayerToPlayer()
    -> CharacterModuleClient.Interpolate()
    -> CharacterModuleClient.UpdatePresentation()
    -> CharacterModuleClient.LateUpdate()
    -> CharacterModuleClient.CameraUpdate()
    -> NetworkClient.Update() (receive snapshots)
    -> NetworkClient.SendData() (send commands)

Game.FixedUpdate()
  -> ServerGameLoop.ServerTickUpdate()
    -> HandleClientCommands()
    -> CharacterModuleServer.HandleSpawns()
    -> CharacterModuleServer.MovementStart/Resolve()
    -> CharacterModuleServer.AbilityStart/Resolve()
    -> GameModeSystemServer.Update()
    -> NetworkServer.GenerateSnapshot()
```

## 5. CONVENTIONS

**Naming conventions** (from sample_signatures):
1. **Interfaces**: Prefix `I` — `ISoundSystem`, `INetworkDriver`, `INetworkInterface`, `IComponentData`, `IReplicatedComponent`
2. **Systems**: Suffix `System` or `Systems` — `SoundSystem`, `CharacterSystemShared`, `GameModeSystemServer`, `PlayerSystemsClient`, `HitCollisionSystems`
3. **Modules**: Suffix `Module` + `Shared`/`Server`/`Client` — `CharacterModuleShared`, `CharacterModuleServer`, `CharacterModuleClient`
4. **Game Loops**: Suffix `GameLoop` — `ClientGameLoop`, `ServerGameLoop`, `PreviewGameLoop`, `ThinClientGameLoop`
5. **Abilities**: Prefix `Ability_` — `Ability_Sprint`, `Ability_Emote` (with `CreateAssetMenu` attribute)
6. **AnimGraphs**: Prefix `AnimGraph_` — `AnimGraph_InAir` (extends `AnimGraphAsset`)
7. **Factories**: Suffix `Factory` — `GrenadeEntityFactory`, `ProjectileEntityFactory`
8. **Data components**: Suffix `Data` — `ReplicatedEntityData`, `HealthStateData`, `HitCollisionOwnerData`, `CharacterPredictedData`
9. **Settings/Config**: Suffix `Settings` or `Configuration` — `CharacterModuleSettings`, `GameConfiguration`, `GameModeSystemSettings`
10. **Behaviors**: Prefix `CharBehavior` or suffix `Behavior` — `CharBehaviour` (component), ability behaviors
11. **Events**: Suffix `Event` — `DamageEvent`, `NetworkEvent`, `CharacterEvents`
12. **Structs for ECS components**: PascalCase, often with `Data` suffix, `Serializable` attribute

**Architectural patterns**:
- **ECS (Entity Component System)**: All gameplay logic uses Unity ECS. Systems extend `BaseComponentSystem` or `BaseComponentDataSystem<T1..T5>`.
- **Module pattern**: Each feature (Character, Player, Projectile) has a Module class that owns a collection of ECS systems, with Shared/Server/Client variants.
- **Client-Server split**: Systems are annotated with `[ServerOnly]` / `[ClientOnly]` / `[DevelopmentOnly]` attributes. Code stripping removes irrelevant code per build type.
- **Prediction**: Abilities implement `IPredictedComponentSerializerFactory` with `Serialize`/`Deserialize`/`VerifyPrediction` for client-side prediction.
- **Replicated entities**: Entities implement `IReplicatedComponent` with `Serialize`/`Deserialize` for network state sync.
- **ConfigVars**: Global configuration via `ConfigVar(Name="...", DefaultValue="...")` attributes.
- **Dependency Injection**: Systems receive `GameWorld` and other dependencies via constructor.
- **Asset management**: `BundledResourceManager` with `WeakAssetReference` GUIDs for loading assets.

**Style conventions**:
- `DisableAutoCreation` attribute on systems (ECS manager auto-creation disabled)
- `CreateAssetMenu` attribute on ScriptableObject factories (abilities, anim graphs)
- `RequireComponent` on MonoBehaviours
- `BeginSample`/`EndSample` for profiling
- `Log` for debug output (custom `GameDebug` wrapper)
- `Assert` for validation

## 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|-------|------|-------------|
| `Ability_Sprint` | `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Sprint.cs` | Extends `CharBehaviorFactory`, has `CreateAssetMenu`, implements predicted serialization |
| `AnimGraph_InAir` | `Assets/Scripts/Game/Modules/Character/Animation/AnimGraph/AnimGraph_InAir.cs` | Extends `AnimGraphAsset`, has `CreateAssetMenu`, implements `IAnimGraphInstance` |
| `GameModeDeathmatch` | `Assets/Scripts/Game/Systems/GameMode/Modes/GameModeDeathmatch.cs` | Game mode implementation, follows same pattern as `GameModeAssault` |
| `CharacterModuleServer` | `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Server module, mirrors `CharacterModuleClient` pattern |
| `ProjectileModuleServer` | `Assets/Scripts/Game/Modules/Projectile/ProjectileModuleServer.cs` | Server module, same pattern as CharacterModuleServer |
| `PlayerModuleServer` | `Assets/Scripts/Game/Modules/Player/PlayerModuleServer.cs` | Server module, same pattern |
| `GrenadeSystemServer` | `Assets/Scripts/Game/Modules/Grenade/GrenadeSystemServer.cs` | Server system, follows ECS ComponentSystem pattern |

## 7. TASK CONTEXT

FPSSample is a **client-server FPS game** built on Unity ECS with a custom networking layer. Key architectural points:

- **Entry point**: `Game.cs` (MonoBehaviour, `DefaultExecutionOrder(-1000)`) initializes game loops
- **Two main game loops**: `ClientGameLoop` (rendering + input) and `ServerGameLoop` (authoritative simulation)
- **ECS is central**: All gameplay entities are ECS entities. Systems extend `BaseComponentDataSystem<T1..T5>` which auto-creates component groups and iterates over matching entities
- **Module pattern**: Each feature (Character, Player, Projectile, Grenade, Effect, etc.) has a Module class that owns a collection of ECS systems. Modules have Shared/Server/Client variants
- **Networking**: Custom bit-level serialization (`NetworkWriter`/`NetworkReader`), delta compression, snapshot-based state sync, client-side prediction
- **Code stripping**: `[ServerOnly]`, `[ClientOnly]`, `[DevelopmentOnly]` attributes strip irrelevant code per build type
- **Asset management**: `BundledResourceManager` with `WeakAssetReference` GUIDs
- **ConfigVars**: Global config with `ConfigVar(Name="...", DefaultValue="...")` attribute
- **Animation**: PlayableGraph-based animation system with `AnimGraphAsset` ScriptableObjects
- **Abilities**: `CharBehaviorFactory` ScriptableObjects with predicted state serialization

When working with this codebase, always follow the Module pattern (Shared/Server/Client split), use ECS ComponentSystems extending `BaseComponentDataSystem`, and respect the `[ServerOnly]`/`[ClientOnly]` attribute conventions.

## 8. RELEVANT CODE SNIPPETS

**Snippet 1: GameWorld — ECS World wrapper** (from `Assets/Scripts/Game/Entity/GameWorld.cs`)
```csharp
// Line ~30: GameWorld wraps Unity ECS World
public GameWorld(string name = "world")
{
    m_ECSWorld = new World(name);
    m_EntityManager = m_ECSWorld.GetOrCreateManager<EntityManager>();
    // ...
}
public EntityManager GetEntityManager() { return m_EntityManager; }
public World GetECSWorld() { return m_ECSWorld; }
```

**Snippet 2: BaseComponentDataSystem — generic ECS system** (from `Assets/Scripts/ECS/BaseComponentDataSystem.cs`)
```csharp
// Line ~50: Generic system with 1-5 component params, auto-creates component group
[DisableAutoCreation]
public abstract class BaseComponentDataSystem<T1> : BaseComponentSystem
    where T1 : struct, IComponentData
{
    protected override void OnCreateManager() {
        var list = new List<ComponentType> { typeof(T1) };
        Add(ComponentType.Subtractive<DespawningEntity>());
        m_Group = GetComponentGroup(list.ToArray());
    }
    protected override void OnUpdate() {
        var entityArray = m_Group.GetEntityArray();
        for (var i = 0; i < entityArray.Length; i++)
            Update(entityArray[i], dataArray[i]);
    }
    protected abstract void Update(Entity entity, T1 data);
}
```

**Snippet 3: Module pattern — CharacterModuleServer** (from `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs`)
```csharp
// Line ~20: Module owns a collection of ECS systems, organized by update phase
public CharacterModuleServer(GameWorld world, BundledResourceManager resourceSystem) : base(world)
{
    m_HandleSpawnRequests = m_world.GetECSWorld().CreateManager<HandleCharacterSpawnRequests>(world, resourceSystem, true);
    m_HandleDespawnRequests = m_world.GetECSWorld().CreateManager<HandleCharacterDespawnRequests>(world);
    // ... more systems
}
```

**Snippet 4: Ability with predicted state** (from `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Sprint.cs`)
```csharp
// Line ~15: Ability factory with serialization for client-side prediction
[CreateAssetMenu(fileName = "Ability_Sprint", menuName = "FPS Sample/Abilities/Ability_Sprint")]
public class Ability_Sprint : CharBehaviorFactory {
    public struct PredictedState : IPredictedComponent<PredictedState> {
        public int active, terminating, terminateStartTick;
        public void Serialize(ref SerializeContext context, ref NetworkWriter writer) { ... }
        public void Deserialize(ref SerializeContext context, ref NetworkReader reader) { ... }
        public bool VerifyPrediction(ref PredictedState state) { ... }
    }
}
```

**Snippet 5: Build attributes for code stripping** (from `Assets/Scripts/Build/BuildAttributes.cs`)
```csharp
// Line ~1: Attributes that control which components exist per build type
[AttributeUsage(System.AttributeTargets.Class)]
public class ServerOnlyComponentAttribute : System.Attribute { }

[AttributeUsage(System.AttributeTargets.Class)]
public class ClientOnlyComponentAttribute : System.Attribute { }

[AttributeUsage(System.AttributeTargets.Class)]
public class DevelopmentOnlyComponentAttribute : System.Attribute { }
```