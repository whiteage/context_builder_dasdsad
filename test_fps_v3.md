Now I have a comprehensive understanding of the architecture. Let me compile the context document.

---

## Context Document: Weapon and Player Systems in FPSSample

### Project Summary

This is **FPSSample**, a Unity-based first-person shooter sample project by Unity Technologies. It uses Unity's **ECS (Entity Component System)** architecture with a custom networking layer, HDRP rendering, and Visual Effect Graph. The project has **1,513 C# source files** across ~12,727 total files (including assets, shaders, prefabs). The codebase demonstrates a networked multiplayer FPS with client-server separation, ability-based combat, and a modular game mode system.

### Architecture

**Architecture Type: ECS + Component-Based with Client/Server Split**

The project uses Unity ECS (`Unity.Entities`) with a custom **GameWorld** wrapper. The architecture is organized into:

1. **Modules** (`Assets/Scripts/Game/Modules/`) — Self-contained feature modules:
   - **Character** — Character spawning, movement, animation, abilities
   - **Player** — Local player input, command buffering, player state
   - **Item** — Weapon items (TerraformerWeaponA, RobotWeaponA)
   - **Projectile** — Projectile spawning, movement, impact
   - **Grenade** — Grenade-specific logic
   - **HitCollision** — Hit detection, splash damage, collision queries
   - **Presentation** — Visual presentation entities
   - **Ragdoll** — Death ragdoll physics
   - **ReplicatedEntity** — Network replication base
   - **SpectatorCam** — Spectator camera
   - **Effect** — Visual effects

2. **Systems** (`Assets/Scripts/Game/Systems/`) — Cross-cutting systems:
   - **Damage** — Damage events, health state, damage history
   - **GameMode** — Game mode logic (Deathmatch, Assault), spawn points, teams
   - **InputSystem** — Input handling
   - **PlayerCamera** — Camera management
   - **Chat** — Chat system

3. **Client/Server Split**: Each module has `*ModuleClient.cs` and `*ModuleServer.cs` variants. Systems use `[DisableAutoCreation]` and are manually registered.

4. **Ability System**: Characters have an `AbilityCollection` (ECS buffer) containing ability entities. Each ability has `PredictedState`, `InterpolatedState`, `Settings`, and `LocalState` components. Abilities are activated/deactivated via `AbilityControl` state machine.

### Key Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `Assets/Scripts/Game/Modules/Item/ItemModule.cs` | Registers all weapon systems (TerraformerWeaponA, RobotWeaponA) | Entry point for weapon systems |
| `Assets/Scripts/Game/Modules/Item/TerraformerWeaponA/TerraformerWeaponA.cs` | Terraformer weapon component + update system (auto rifle + rocket launcher) | Primary weapon implementation |
| `Assets/Scripts/Game/Modules/Item/RobotWeaponA/RobotWeaponA.cs` | Robot weapon component + update system (chaingun + grenade launcher) | Secondary weapon implementation |
| `Assets/Scripts/Game/Modules/Character/Behaviours/AbilityCollection.cs` | Ability controller — manages activation/deactivation of abilities | Core ability state machine |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_AutoRifle.cs` | Auto-rifle ability (primary fire for Terraformer) | Weapon ability |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Chaingun.cs` | Chaingun ability (primary fire for Robot) | Weapon ability |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_ProjectileLauncher.cs` | Projectile launcher ability (secondary fire for Terraformer — rockets) | Weapon ability |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_GrenadeLauncher.cs` | Grenade launcher ability (secondary fire for Robot) | Weapon ability |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Melee.cs` | Melee ability (both weapons) | Weapon ability |
| `Assets/Scripts/Game/Modules/Player/PlayerModuleClient.cs` | Client player module — input sampling, command buffering, local player | Player input pipeline |
| `Assets/Scripts/Game/Modules/Player/PlayerModuleServer.cs` | Server player module — player creation/cleanup | Player lifecycle |
| `Assets/Scripts/Game/Modules/Player/Components/PlayerState.cs` | Player state component (playerId, teamIndex, controlledEntity) | Core player data |
| `Assets/Scripts/Game/Modules/Player/UserCommand.cs` | User input command struct (buttons, look, movement) | Input representation |
| `Assets/Scripts/Game/Modules/Character/Components/Character.cs` | Character component (eyeHeight, heroType, presentations) | Core character data |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterPredicted.cs` | Predicted character state (position, velocity, locoState, action) | Character state machine |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterReplicated.cs` | Replicated character data (heroTypeIndex, abilityCollection) | Network sync |
| `Assets/Scripts/Game/Modules/Character/HeroTypeAsset.cs` | Hero definition (health, movement, abilities, items) | Character/weapon binding |
| `Assets/Scripts/Game/Systems/Damage/HealthState.cs` | Health component with damage application | Damage pipeline |
| `Assets/Scripts/Game/Systems/Damage/DamageEvent.cs` | Damage event buffer element | Damage pipeline |
| `Assets/Scripts/Game/Modules/HitCollision/SplashDamageSystem.cs` | Splash damage (explosions) processing | Damage pipeline |
| `Assets/Scripts/Game/Systems/GameMode/GameModeSystemServer.cs` | Server game mode — player join/respawn/kill handling | Game flow |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Server character module — spawn/despawn/damage handling | Character lifecycle |
| `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | Base ECS system classes (generic typed systems) | Foundation |

### Key Symbols

**Player Layer:**
- `PlayerState : MonoBehaviour` — `playerId`, `teamIndex`, `controlledEntity` (Entity), `score`
- `UserCommand : IReplicatedComponent` — `Button` flags: `Jump`, `PrimaryFire`, `SecondaryFire`, `Reload`, `Melee`, etc.
- `UserCommandComponent` — ECS component wrapping `UserCommand` with `renderTick`, `resetCommandTick`
- `LocalPlayer : MonoBehaviour` — `playerId`, `playerState`, `controlledEntity`, `command` (UserCommand)
- `PlayerModuleClient` — Registers systems: `HandlePlayerCameraControlSpawn`, `UpdatePlayerCameras`, `ResolvePlayerReference`, `UpdateServerEntityComponent`. Handles input sampling, command buffering, command sending.
- `PlayerModuleServer` — Creates/cleans up `PlayerState` entities

**Character Layer:**
- `Character : MonoBehaviour` — `eyeHeight`, `heroTypeData`, `presentations`, `teamId`, `TeleportTo()`
- `CharacterPredictedData : IComponentData, IPredictedComponent` — `position`, `velocity`, `locoState` (Stand/GroundMove/Jump/DoubleJump/InAir), `action` (None/PrimaryFire/SecondaryFire/Reloading/Melee), `sprinting`, `cameraProfile`, `damageDirection`
- `CharacterReplicatedData : IComponentData, IReplicatedComponent` — `heroTypeIndex`, `abilityCollection` (Entity), `FindAbilityWithComponent()`
- `CharacterPresentationSetup : MonoBehaviour` — `geomtry`, `itemAttachBone`, `character` (Entity), `IsVisible`
- `HeroTypeAsset : ScriptableObject` — `health`, `characterMovementSettings`, `abilities` (WeakAssetReference), `items` (ItemEntry[])

**Ability System:**
- `CharBehaviourFactory` (abstract) — `Create(EntityManager, List<Entity>)` — base factory for abilities
- `AbilityCollection : CharBehaviourFactory` — Creates ability entities, manages `AbilityEntry[]` with `canRunWith`/`canInterrupt` rules
- `AbilityControl : IComponentData` — `active`, `behaviorState` (Idle/RequestActive/Active/Cooldown), `requestDeactivate`
- `DefaultBehaviourController_Update` — ECS system that runs ability activation/deactivation logic each frame
- `Ability_AutoRifle : CharBehaviourFactory` — States: Idle/Fire/Reload. Uses `fireButton`, `reloadButton`. Tracks `ammoInClip`, `COF` (cone of fire). Creates hitscan damage.
- `Ability_Chaingun : CharBehaviourFactory` — States: Idle/Fire/Reload. Tracks `fireRate` (ramps up), `ammoInClip`. Creates projectile spawn requests.
- `Ability_ProjectileLauncher : CharBehaviourFactory` — Single-shot projectile. Creates `ProjectileRequest` with `projectileAssetGuid`.
- `Ability_GrenadeLauncher : CharBehaviourFactory` — Phases: Idle/Active/Cooldown. Creates grenade with velocity.
- `Ability_Melee : CharBehaviourFactory` — Phases: Idle/Punch/Hold. Uses `RaySphereQueryReciever` for hit detection. Applies `DamageEvent` directly.

**Weapon Layer:**
- `TerraformerWeaponA : MonoBehaviour` — `[ClientOnlyComponent]`. References: `muzzle`, `primaryFireSound`, `primaryMuzzleFlash`, `hitscanEffect`, `secondaryFireSound`, `secondaryMuzzleFlash`, `meleeImpactSound`, `meleeImpactEffect`. Uses `TickEventHandler` for fire events.
- `RobotWeaponA : MonoBehaviour` — `[ClientOnlyComponent]`. Has `GunBarrelSetup` (barrels array, muzzle flashes, fire sound, animation curve). Uses `TickEventHandler` for fire events.
- `UpdateTerraformerWeaponA : BaseComponentSystem<CharacterPresentationSetup, TerraformerWeaponA>` — Client-side visual update system. Reads `Ability_AutoRifle.InterpolatedState` for primary fire, `Ability_ProjectileLauncher.InterpolatedState` for secondary, `Ability_Melee.InterpolatedState` for melee.
- `System_RobotWeaponA : BaseComponentSystem<RobotWeaponA, CharacterPresentationSetup>` — Client-side visual update system. Reads `Ability_Chaingun.InterpolatedState` for primary, `Ability_GrenadeLauncher.InterpolatedState` for secondary, `Ability_Melee.InterpolatedState` for melee.

**Damage Pipeline:**
- `HealthStateData : IComponentData, IReplicatedComponent` — `health`, `maxHealth`, `deathTick`, `killedBy`. `ApplyDamage(ref DamageEvent, int tick)`
- `DamageEvent : IBufferElementData` — `instigator` (Entity), `damage` (float), `direction`, `impulse`. `AddEvent()` static method.
- `DamageHistoryData : IComponentData, IReplicatedComponent` — Tracks `inflictedDamage` (tick, lethal)
- `SplashDamageSystem` — Processes `SplashDamageRequest`, does sphere overlap, applies damage with falloff

### Dependencies

**Module-level dependency flow:**
```
GameModeSystemServer
  └─> PlayerModuleServer (creates PlayerState)
       └─> CharacterModuleServer (spawns Character from PlayerState)
            └─> AbilityCollection (creates ability entities)
                 └─> Ability_AutoRifle / Ability_Chaingun / etc.
                      └─> ProjectileModuleServer (spawns projectiles)
                      └─> HitCollisionModule (splash damage)
                           └─> DamageSystem (HealthState, DamageEvent)
```

**Key dependency chains:**

- `PlayerState.controlledEntity` → `Character` (Entity)
- `CharacterReplicatedData.abilityCollection` → `AbilityCollection` (Entity with `EntityGroupChildren` buffer)
- `AbilityCollection` children → individual ability entities (each has `CharBehaviour`, `AbilityControl`, and ability-specific components)
- `CharacterPresentationSetup.character` → back-reference to `Character` entity
- Weapon update systems (`UpdateTerraformerWeaponA`, `System_RobotWeaponA`) depend on `CharacterPresentationSetup` + weapon component

**Client/Server split:**
- Server runs: `CharacterModuleServer`, `PlayerModuleServer`, `GameModeSystemServer`, ability `*_Update` and `*_RequestActive` systems
- Client runs: `CharacterModuleClient`, `PlayerModuleClient`, weapon visual update systems, `*_InterpolatedState` reading

### Conventions

**Naming Conventions:**
- **PascalCase** for all class names, method names, properties
- **Interfaces**: `I` prefix (`IAbility`, `IComponentData`, `IReplicatedComponent`, `IPredictedComponent`)
- **Suffixes**: 
  - `*System` / `*SystemClient` / `*SystemServer` — ECS systems (e.g., `GameModeSystemServer`, `SplashDamageSystem`)
  - `*ModuleClient` / `*ModuleServer` / `*ModuleShared` — Module registration classes
  - `*Data` suffix for ECS component structs (e.g., `HealthStateData`, `CharacterPredictedData`, `CharacterReplicatedData`)
  - `*Definition` for ScriptableObject type definitions (e.g., `ItemTypeDefinition`, `ProjectileTypeDefinition`)
  - `*Asset` for ScriptableObject assets (e.g., `HeroTypeAsset`)
  - `*Factory` for entity factory classes (e.g., `CharBehaviourFactory`, `ProjectileEntityFactory`)
  - `*Handler` for specific event handlers (e.g., `RobotWeaponClientProjectileSpawnHandler`)
- **Abilities**: `Ability_*` prefix (e.g., `Ability_AutoRifle`, `Ability_Chaingun`)
- **Components**: `Character*`, `Player*`, `*State` naming
- **Private fields**: `m_` prefix (e.g., `m_world`, `m_settings`, `m_LocalPlayer`)

**Architectural Patterns:**
- **ECS (Entity Component System)**: Unity ECS with `ComponentSystem` subclasses. Components are structs implementing `IComponentData`. Systems use `ComponentGroup` queries.
- **Client/Server Split**: Every module has separate client and server implementations. Systems are `[DisableAutoCreation]` and manually registered in module constructors.
- **Ability Pattern**: Abilities are entities created by `CharBehaviourFactory`. Each has `Settings` (immutable), `PredictedState` (server-authoritative, client-predicted), `InterpolatedState` (for visual interpolation), and `LocalState` (client-only). State machines use `SetPhase()`/`SetAction()` methods.
- **Replication Pattern**: Components implement `IReplicatedComponent` with `Serialize()`/`Deserialize()` methods. Predicted components implement `IPredictedComponent` with `VerifyPrediction()`.
- **Command Pattern**: `UserCommand` struct captures player input each frame. Commands are buffered, stored by tick, and sent to server. Server processes commands in order.
- **Damage Pipeline**: `DamageEvent` buffer elements are added to entities with `HealthStateData`. `SplashDamageSystem` uses `RaySphereQueryReciever` for AoE damage. Melee uses direct `RaySphereQueryReciever`.

**Style Conventions:**
- **Async**: Not used — all game logic is synchronous ECS update loops
- **Error handling**: `GameDebug.Assert()` for critical invariants, `GameDebug.Log()` for debug info, `GameDebug.LogError()` for errors
- **Validation**: `VerifyPrediction()` methods for client-side prediction verification
- **Serialization**: Custom `NetworkWriter`/`NetworkReader` with typed `Write*`/`Read*` methods (e.g., `WriteInt32`, `WriteVector3Q`, `WriteBoolean`)
- **ConfigVars**: `ConfigVar` attribute for runtime-configurable variables (e.g., `game.respawndelay`, `charbehaviour.showstate`)
- **Tick-based timing**: `TickEventHandler` for fire rate limiting, `DurationSinceTick()` for phase timing
- **Asset references**: `WeakAssetReference` for GUID-based asset references, `BundledResourceManager` for loading

### Similar Implementations

1. **`Ability_AutoRifle` and `Ability_Chaingun`** — Both follow the same pattern: `CharBehaviourFactory` subclass, `Settings`/`PredictedState`/`InterpolatedState`/`LocalState` components, `*_RequestActive` and `*_Update` systems, `GetPreferredState()` static method, phase-based state machine with `EnterFiringPhase()`/`EnterReloadingPhase()`/`EnterIdlePhase()`.

2. **`TerraformerWeaponA` and `RobotWeaponA`** — Both are `[ClientOnlyComponent]` MonoBehaviour components with `TickEventHandler` fields, sound/visual effect references, and paired update systems (`UpdateTerraformerWeaponA` / `System_RobotWeaponA`) that extend `BaseComponentSystem<CharacterPresentationSetup, T>`. Both read ability interpolated states to drive visual effects.

3. **`Ability_ProjectileLauncher` and `Ability_GrenadeLauncher`** — Both create projectile/grenade spawn requests on fire. Both have `*_RequestActive` and `*_Update` systems. Both use `SetAction()` to update `CharacterPredictedData.Action`.

### Context for the Task

**Architecture Summary:**
The FPSSample uses a **client-server ECS architecture** where:
- **Player** owns a `PlayerState` with `controlledEntity` pointing to a **Character**
- **Character** has a `CharacterReplicatedData` with `abilityCollection` pointing to an **AbilityCollection** entity
- **AbilityCollection** contains child ability entities (AutoRifle, Chaingun, ProjectileLauncher, GrenadeLauncher, Melee)
- **Weapons** (`TerraformerWeaponA`, `RobotWeaponA`) are client-only visual components that read ability `InterpolatedState` to drive effects
- **Damage** flows through `DamageEvent` buffer → `HealthStateData.ApplyDamage()` → death detection

**Key Code Snippets:**

1. **Player → Character → Abilities chain** (from `CharacterReplicated.cs`):
```csharp
public struct CharacterReplicatedData : IComponentData, IReplicatedComponent
{
    public int heroTypeIndex;
    public Entity abilityCollection;
    
    public Entity FindAbilityWithComponent(EntityManager entityManager, Type abilityType)
    {
        var buffer = entityManager.GetBuffer<EntityGroupChildren>(abilityCollection);
        for (int j = 0; j < buffer.Length; j++)
        {
            var childEntity = buffer[j].entity;
            if (!entityManager.HasComponent<CharBehaviour>(childEntity)) continue;
            if (entityManager.HasComponent(childEntity, abilityType)) return childEntity;
        }
        return Entity.Null;
    }
}
```

2. **Weapon system reads ability state** (from `TerraformerWeaponA.cs`):
```csharp
protected override void Update(Entity entity, CharacterPresentationSetup charPresentation, TerraformerWeaponA weapon)
{
    if (!charPresentation.IsVisible) return;
    var charRepAll = EntityManager.GetComponentData<CharacterReplicatedData>(charPresentation.character);
    Update(m_world.worldTime, weapon, ref charRepAll);
}

void Update(GameTime time, TerraformerWeaponA weapon, ref CharacterReplicatedData charRepAll)
{
    var autoRifleAbility = charRepAll.FindAbilityWithComponent(EntityManager, typeof(Ability_AutoRifle.InterpolatedState));
    var autoRifleInterpolatedState = EntityManager.GetComponentData<Ability_AutoRifle.InterpolatedState>(autoRifleAbility);
    if (weapon.primaryFireEvent.Update(time, autoRifleInterpolatedState.fireTick))
    {
        // Play sound, muzzle flash, hitscan effect
    }
}
```

3. **Damage application** (from `HealthState.cs`):
```csharp
public struct HealthStateData : IComponentData, IReplicatedComponent
{
    public float health;
    public float maxHealth;
    public int deathTick;
    public Entity killedBy;

    public void ApplyDamage(ref DamageEvent damageEvent, int tick)
    {
        if (health <= 0) return;
        health -= damageEvent.damage;
        if (health <= 0)
        {
            killedBy = damageEvent.instigator;
            deathTick = tick;
            health = 0;
        }
    }
}
```

**What to know for the task:**
- Weapons are **client-only visual representations** that react to server-authoritative ability state
- Abilities run on the server (`*_Update` systems with `typeof(ServerEntity)` requirement) and replicate `InterpolatedState` to clients
- The `AbilityCollection` manages which abilities can run concurrently via `canRunWith`/`canInterrupt` arrays
- `UserCommand.Button` flags drive ability activation (e.g., `PrimaryFire` → `Ability_AutoRifle`/`Ability_Chaingun`)
- The `CharacterModuleServer.HandleDamage` system processes `DamageEvent` buffers and triggers death/ragdoll
- `SplashDamageSystem` handles AoE damage from explosions (rockets, grenades) using sphere overlap queries