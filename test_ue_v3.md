Now I have a comprehensive understanding of the project. Let me compile the full code review.

---

## 1. PROJECT SUMMARY

**Project:** EpicSurvivalGame — a third-person survival game for Unreal Engine 5.2, made entirely in C++. Originally built as a tutorial series for Epic Games (2015), now open-source.

**Tech Stack:**
- **Engine:** Unreal Engine 5.2 (originally UE4-era codebase, ported forward)
- **Language:** C++ (75 .cpp files, 38 .h files) — 43 classes, 380 methods
- **Build:** UnrealBuildTool (SurvivalGame.Build.cs)
- **Plugins:** OnlineSubsystemSteam (enabled), ExtendedRifleMod (content-only), MyFlashlightMod (content-only)
- **Scale:** 103 total files, ~971 lines in SCharacter.cpp alone (largest file)

**Key Note from README:** The project uses *very old* standards and conventions (2015-era UE4). Not representative of modern UE5 practices.

---

## 2. ARCHITECTURE

**Architecture Type:** Unreal Engine Game Framework (Actor/Component-based) with layered folder organization.

**Layer Structure (by folder):**

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Game Framework** | `World/` | GameMode, GameState, GameInstance, PlayerStart, TimeOfDayManager |
| **Player** | `Player/` | BaseCharacter, Character, PlayerController, PlayerState, CameraManager, SpectatorPawn, LocalPlayer |
| **Items** | `Items/` | Weapon, WeaponInstant, WeaponPickup, UsableActor, PickupActor, ConsumableActor, BombActor, Flashlight, ImpactEffect, DamageType |
| **AI** | `AI/` | ZombieCharacter, ZombieAIController, BotWaypoint, BTTasks |
| **Components** | `Components/` | CharacterMovementComponent, CarryObjectComponent |
| **UI** | `UI/` | HUD |
| **Mutators** | `Mutators/` | Base Mutator, WeaponReplacement Mutator |
| **Core** | `Core/` | GameplayStatics (utility library) |
| **Editor** | `Editor/` | SoundNodeLocalPlayer |
| **Root** | `SurvivalGame/` | STypes.h (shared enums/structs), module entry point |

**Inheritance Hierarchy:**
```
AGameMode → ASGameMode → ASCoopGameMode, ASOpenWorldGameMode
ACharacter → ASBaseCharacter (ABSTRACT) → ASCharacter, ASZombieCharacter
AActor → ASWeapon (ABSTRACT) → ASWeaponInstant
AActor → ASUsableActor (ABSTRACT) → ASBombActor, ASConsumableActor, ASFlashlight, ASPickupActor
AActor → ASTimeOfDayManager
AInfo → ASMutator (ABSTRACT) → ASMutator_WeaponReplacement
APlayerController → ASPlayerController
APlayerState → ASPlayerState
AGameState → ASGameState
AHUD → ASHUD
APlayerCameraManager → ASPlayerCameraManager
APlayerStart → ASPlayerStart
USpringArmComponent → USCarryObjectComponent
UCharacterMovementComponent → USCharacterMovementComponent
UBTTask_BlackboardBase → UBTTask_FindBotWaypoint, UBTTask_FindPatrolLocation
```

**Key Architectural Patterns:**
- **GameMode-centric:** ASGameMode owns game rules, bot spawning, day/night cycle, mutator chain, damage/kill logic
- **Mutator Chain Pattern** (from UT): ASMutator forms a linked list (`NextMutator`), called by GameMode's `CheckRelevance()` to modify/replace/destroy actors
- **Server-Authoritative RPC:** All gameplay actions use `Server, Reliable, WithValidation` pattern (sprinting, targeting, firing, pickup, drop, throw, rotate)
- **Replicated State:** Key state uses `UPROPERTY(Replicated)` or `UPROPERTY(Transient, ReplicatedUsing=OnRep_*)` for client sync
- **Day/Night Cycle:** SGameState tracks elapsed time, SGameMode drives bot spawning at night, STimeOfDayManager handles visual/sound transitions
- **Inventory System:** SCharacter holds TArray of ASWeapon*, slot-based (Hands/Primary/Secondary via EInventorySlot)

---

## 3. RELATED FILES

All 38 header files and 37 implementation files are relevant for a full architecture review. Here are the most architecturally significant ones:

| # | File | Entity Type | Purpose & Relevance |
|---|------|-------------|---------------------|
| 1 | `SurvivalGame/Source/SurvivalGame/Public/World/SGameMode.h` | GameMode | Central game rules: spawning, day/night, damage, mutators, bot management. The orchestrator. |
| 2 | `SurvivalGame/Source/SurvivalGame/Public/Player/SBaseCharacter.h` | Character (Base) | Abstract base for all characters. Health, damage/death pipeline, sprinting, targeting, hit replication via FTakeHitInfo. |
| 3 | `SurvivalGame/Source/SurvivalGame/Public/Player/SCharacter.h` | Character (Player) | Player-specific: inventory, weapon handling, hunger, movement input, carry object, camera. Largest class. |
| 4 | `SurvivalGame/Source/SurvivalGame/Public/Items/SWeapon.h` | Weapon | Abstract weapon base. State machine (Idle/Firing/Equipping/Reloading), RPC fire handling, ammo, animations, sounds. |
| 5 | `SurvivalGame/Source/SurvivalGame/Public/Items/SWeaponInstant.h` | Weapon (Instant) | Hitscan weapon implementation. Server-side hit detection, impact/trail effects, damage application. |
| 6 | `SurvivalGame/Source/SurvivalGame/Public/Player/SPlayerController.h` | Controller | Player input, HUD state management, chat messages, spectating, suicide. |
| 7 | `SurvivalGame/Source/SurvivalGame/Public/World/SGameState.h` | GameState | Replicated game state: score, day/night tracking, elapsed time, broadcast messages. |
| 8 | `SurvivalGame/Source/SurvivalGame/Public/World/STimeOfDayManager.h` | Service | Day/night visual manager: directional light, skylight, ambient sound loops. |
| 9 | `SurvivalGame/Source/SurvivalGame/Public/AI/SZombieCharacter.h` | AI Character | Zombie AI: perception (see/hear player), melee attack, audio loops, bot behavior type. |
| 10 | `SurvivalGame/Source/SurvivalGame/Public/AI/SZombieAIController.h` | AI Controller | Blackboard-driven AI: waypoints, target enemy, behavior tree setup. |
| 11 | `SurvivalGame/Source/SurvivalGame/Public/Mutators/SMutator.h` | Mutator | Base mutator with linked-list chain pattern. InitGame + CheckRelevance hooks. |
| 12 | `SurvivalGame/Source/SurvivalGame/Public/Mutators/SMutator_WeaponReplacement.h` | Mutator | Concrete mutator: replaces weapon pickups in the level. |
| 13 | `SurvivalGame/Source/SurvivalGame/Public/Items/SUsableActor.h` | Item (Base) | Abstract base for all usable items (bomb, consumable, flashlight, pickup). Focus/use interface. |
| 14 | `SurvivalGame/Source/SurvivalGame/Public/Items/SPickupActor.h` | Item (Pickup) | Respawnable pickup base. Replicated active state, sound effects. |
| 15 | `SurvivalGame/Source/SurvivalGame/Public/UI/SHUD.h` | HUD | HUD drawing, state management (EHUDState), message events. |
| 16 | `SurvivalGame/Source/SurvivalGame/Public/Components/SCarryObjectComponent.h` | Component | Carry/throw/drop/rotate objects. Full RPC pattern for multiplayer. |
| 17 | `SurvivalGame/Source/SurvivalGame/Public/Player/SPlayerState.h` | PlayerState | Per-player replicated state: kills, deaths, score, team number. |
| 18 | `SurvivalGame/Source/SurvivalGame/STypes.h` | Types | Shared enums (EInventorySlot, EBotBehaviorType) and FTakeHitInfo struct for damage replication. |
| 19 | `SurvivalGame/Source/SurvivalGame/Public/World/SCoopGameMode.h` | GameMode | Coop-specific: match end conditions, restart logic, night-ended handling. |
| 20 | `SurvivalGame/Source/SurvivalGame/Public/World/SOpenWorldGameMode.h` | GameMode | Open world variant: spectating restrictions. |

---

## 4. DEPENDENCY GRAPH

**Module-Level Dependencies (from Build.cs):**
```
SurvivalGame module depends on:
  Core, CoreUObject, Engine, InputCore, AIModule, GameplayTasks,
  NavigationSystem, OnlineSubsystem, PhysicsCore
```

**File-Level Dependency Chains (key relationships):**

```
SGameMode.h
  → Mutators/SMutator.h (mutator chain)
  → Player/SPlayerController.h, SPlayerState.h, SCharacter.h
  → World/SGameState.h, SPlayerStart.h
  → AI/SZombieAIController.h, SZombieCharacter.h
  → Items/SWeapon.h
  → UI/SHUD.h
  → STypes.h

SCharacter.h
  → SBaseCharacter.h (parent)
  → Items/SUsableActor.h, SWeapon.h, SWeaponPickup.h
  → Components/SCharacterMovementComponent.h, SCarryObjectComponent.h
  → Player/SPlayerController.h

SWeapon.h
  → Player/SCharacter.h (owning pawn)

SWeaponInstant.h
  → SWeapon.h (parent)

SZombieCharacter.h
  → SBaseCharacter.h (parent)

SCarryObjectComponent.h
  → (standalone component, no game-specific deps)

SMutator_WeaponReplacement.h
  → SMutator.h (parent)
  → Items/SWeapon.h
```

**Call Graph (key chains):**

```
ASGameMode::PreInitializeComponents()
  → SetTimer(DefaultTimer)  // 1-second tick

ASGameMode::DefaultTimer()
  → Checks night state via SGameState
  → SpawnBotHandler() during night

ASGameMode::Killed()
  → SPlayerState::AddKill() / AddDeath()
  → SGameState::AddScore()

ASCharacter::SetupPlayerInputComponent()
  → BindAxis: MoveForward, MoveRight
  → BindAction: Jump, Crouch, Sprint, Fire, Reload, Use, etc.

ASWeapon::StartFire()
  → DetermineWeaponState()
  → HandleFiring()
  → ServerStartFire() [RPC]
  → FireWeapon() [PURE_VIRTUAL in base]

ASWeaponInstant::FireWeapon()
  → WeaponTrace() (line trace)
  → ProcessInstantHit()
  → ServerNotifyHit() [RPC]
  → DealDamage()

ASBaseCharacter::TakeDamage()
  → CanDie() → Die() → OnDeath()
  → ReplicateHit() → OnRep_LastTakeHitInfo()
```

---

## 5. CONVENTIONS

### Naming Conventions

| # | Rule | Examples from codebase |
|---|------|----------------------|
| 1 | **Prefix `A` for Actor classes** | `ASGameMode`, `ASBaseCharacter`, `ASWeapon`, `ASBombActor`, `ASPlayerController` |
| 2 | **Prefix `U` for UObject/Component classes** | `USCarryObjectComponent`, `USCharacterMovementComponent`, `USGameInstance`, `USGameplayStatics` |
| 3 | **Prefix `F` for structs** | `FTakeHitInfo`, `FReplacementInfo` |
| 4 | **Prefix `E` for enums** | `EInventorySlot`, `EBotBehaviorType`, `EWeaponState`, `EHUDState`, `EHUDMessage` |
| 5 | **Prefix `S` for project-specific classes** | All classes: `SGameMode`, `SCharacter`, `SWeapon`, `SHUD`, `SBotWaypoint` |
| 6 | **Suffix `_Implementation` for RPC/BlueprintNativeEvent bodies** | `ServerSetSprinting_Implementation`, `ServerSuicide_Implementation`, `InitGame_Implementation`, `CheckRelevance_Implementation` |
| 7 | **Suffix `_Validate` for Server RPC validation** | `ServerSetSprinting_Validate`, `ServerSuicide_Validate`, `ServerStartFire_Validate` |
| 8 | **Suffix `Component` for ActorComponents** | `SCharacterMovementComponent`, `SCarryObjectComponent` |
| 9 | **Suffix `Controller` for AController classes** | `ASPlayerController`, `ASZombieAIController` |
| 10 | **Suffix `State` for AGameState/APlayerState** | `ASGameState`, `ASPlayerState` |
| 11 | **Suffix `Manager` for manager actors** | `ASPlayerCameraManager`, `ASTimeOfDayManager` |
| 12 | **Suffix `Actor` for item/usable actors** | `ASUsableActor`, `ASBombActor`, `ASConsumableActor`, `ASPickupActor` |
| 13 | **Suffix `Type` for UDamageType** | `USDamageType` |
| 14 | **Prefix `b` for bool properties** | `bWantsToRun`, `bIsTargeting`, `bIsDying`, `bAllowFriendlyFireDamage`, `bSpawnZombiesAtNight` |
| 15 | **Prefix `OnRep_` for ReplicatedUsing callbacks** | `OnRep_LastTakeHitInfo`, `OnRep_BurstCounter`, `OnRep_IsActive`, `OnRep_MyPawn`, `OnRep_HitLocation`, `OnRep_Reload` |

### Architectural Patterns

| Pattern | Usage | Evidence |
|---------|-------|----------|
| **Server-Authoritative RPC** | All gameplay actions use `UFUNCTION(Server, Reliable, WithValidation)` | `ServerSetSprinting`, `ServerSetTargeting`, `ServerStartFire`, `ServerPickup`, `ServerDrop`, `ServerThrow`, `ServerRotate`, `ServerUse`, `ServerSuicide` |
| **Multicast RPC for FX** | Visual/sound replication via `UFUNCTION(Reliable/Unreliable, NetMulticast)` | `BroadcastGameMessage`, `BroadcastUpdateAudioLoop`, `SimulateMeleeStrike`, `SimulateExplosion`, `SimulateFuzeFX`, `OnPickupMulticast`, `OnDropMulticast`, `OnRotateMulticast` |
| **Client RPC for UI** | HUD state/messages sent via `UFUNCTION(Client, Reliable)` | `ClientHUDStateChanged`, `ClientHUDMessage`, `ClientReceiveChatMessage` |
| **ReplicatedUsing + OnRep** | Property change notification pattern | `LastTakeHitInfo(OnRep_LastTakeHitInfo)`, `BurstCounter(OnRep_BurstCounter)`, `bIsActive(OnRep_IsActive)` |
| **BlueprintNativeEvent** | C++ default with Blueprint override | `InitGame`, `CheckRelevance`, `OnStateChanged` |
| **BlueprintImplementableEvent** | Blueprint-only override point | `FindBotSpawnTransform`, `K2_SimulateExplosion`, `MessageReceived` |
| **Mutator Chain** | Linked list of mutators called by GameMode | `ASMutator::NextMutator`, `ASGameMode::BaseMutator`, `CheckRelevance()` chain |
| **Abstract Base Classes** | `UCLASS(ABSTRACT)` for base classes | `ASBaseCharacter`, `ASWeapon`, `ASUsableActor`, `ASPickupActor`, `ASMutator`, `ASTimeOfDayManager` |
| **Constructor with FObjectInitializer** | UE4-era pattern for passing to Super | `ASBaseCharacter(const class FObjectInitializer& ObjectInitializer)` |

### Style Conventions

| Convention | Details |
|------------|---------|
| **Header includes** | Project headers use relative paths from Source root: `#include "Player/SCharacter.h"` |
| **Category grouping** | UPROPERTY categories use `Category = "Group\|Subgroup"` e.g. `"Bomb\|Effects"`, `"PlayerCondition"` |
| **Section comments** | Large comment blocks with `/* text */` and `/********/` separators |
| **Override keyword** | All virtual overrides use `override` keyword |
| **const methods** | Getters marked `const`: `GetMaxHealth() const`, `IsAlive() const` |
| **RPC naming** | `ServerXxx` / `ServerXxx_Implementation` / `ServerXxx_Validate` triplet pattern |
| **Timer handles** | `FTimerHandle` member variables with `TimerHandle_` prefix |
| **Copyright header** | `// Copyright 1998-2015 Epic Games, Inc. All Rights Reserved.` on all files |

---

## 6. SIMILAR IMPLEMENTATIONS

| Base Class / Pattern | Similar Classes | File | Why Similar |
|----------------------|-----------------|------|-------------|
| **ASBaseCharacter** (ABSTRACT ACharacter) | `ASCharacter` | `Player/SCharacter.h` | Extends ASBaseCharacter, adds player-specific input/inventory/hunger |
| | `ASZombieCharacter` | `AI/SZombieCharacter.h` | Extends ASBaseCharacter, adds AI perception/melee |
| **ASWeapon** (ABSTRACT AActor) | `ASWeaponInstant` | `Items/SWeaponInstant.h` | Extends ASWeapon, implements hitscan firing |
| | `ASFlashlight` | `Items/SFlashlight.h` | Extends ASWeapon, implements light toggle |
| **ASUsableActor** (ABSTRACT AActor) | `ASBombActor` | `Items/SBombActor.h` | Extends ASUsableActor, implements explosive |
| | `ASConsumableActor` | `Items/SConsumableActor.h` | Extends ASUsableActor, implements consumable |
| | `ASFlashlight` | `Items/SFlashlight.h` | Also extends ASUsableActor (dual inheritance: Weapon + Usable) |
| | `ASPickupActor` | `Items/SPickupActor.h` | Extends ASUsableActor, implements respawning pickup |
| | `ASWeaponPickup` | `Items/SWeaponPickup.h` | Extends ASPickupActor, weapon-specific pickup |
| **ASMutator** (ABSTRACT AInfo) | `ASMutator_WeaponReplacement` | `Mutators/SMutator_WeaponReplacement.h` | Extends ASMutator, weapon replacement logic |
| **ASGameMode** | `ASCoopGameMode` | `World/SCoopGameMode.h` | Extends ASGameMode, coop match rules |
| | `ASOpenWorldGameMode` | `World/SOpenWorldGameMode.h` | Extends ASGameMode, open world spectating |
| **UBTTask_BlackboardBase** | `UBTTask_FindBotWaypoint` | `AI/BTTask_FindBotWaypoint.h` | Behavior tree task for waypoint |
| | `UBTTask_FindPatrolLocation` | `AI/BTTask_FindPatrolLocation.h` | Behavior tree task for patrol |
| **Server RPC Triplet Pattern** | `ServerSetSprinting` / `_Implementation` / `_Validate` | `SBaseCharacter.h` | Standard RPC pattern used across all Server RPCs |
| | `ServerStartFire` / `_Implementation` / `_Validate` | `SWeapon.h` | Same pattern for weapon firing |
| | `ServerPickup` / `_Implementation` / `_Validate` | `SCarryObjectComponent.h` | Same pattern for object carry |

---

## 7. TASK CONTEXT

**For the AI performing the code review:**

This is an **Unreal Engine 5.2 C++ project** (ported from UE4-era 2015 code). The codebase follows **Unreal Engine's Game Framework** architecture with these key systems:

### What to look at:
1. **GameMode (SGameMode)** — Central orchestrator. Handles game rules, bot spawning, day/night cycle, damage modification, mutator chain. Check for proper use of `Super::` calls, timer management, and RPC patterns.

2. **Character Hierarchy (SBaseCharacter → SCharacter / SZombieCharacter)** — SBaseCharacter is ABSTRACT and handles health, damage pipeline (TakeDamage → CanDie → Die → OnDeath → PlayHit), sprinting, targeting, and hit replication via FTakeHitInfo struct. SCharacter adds inventory, weapon handling, hunger system, movement input, and carry object interaction.

3. **Weapon System (SWeapon → SWeaponInstant)** — SWeapon is ABSTRACT with a state machine (Idle/Firing/Equipping/Reloading). Uses Server RPCs for fire handling. SWeaponInstant implements hitscan with server-side hit detection and client-side simulation.

4. **Multiplayer Pattern** — All gameplay actions use `UFUNCTION(Server, Reliable, WithValidation)` with the triplet pattern (ServerXxx / ServerXxx_Implementation / ServerXxx_Validate). Visual/sound effects use NetMulticast RPCs. State changes use `ReplicatedUsing=OnRep_*`.

5. **Mutator System** — Linked-list chain pattern from UT. Base mutator (ASMutator) with `InitGame` and `CheckRelevance` hooks. GameMode calls `CheckRelevance` on each actor.

6. **Day/Night Cycle** — SGameState tracks elapsed time. SGameMode drives bot spawning at night. STimeOfDayManager handles visual transitions.

### What to be careful about:
- **Old UE4 conventions** — The README explicitly warns this uses old standards. Watch for deprecated patterns, manual timer management instead of FTimerManager best practices, and pre-UE5-style includes.
- **SCharacter.cpp is 971 lines** — This is the largest file and likely violates single-responsibility. It handles input, inventory, weapons, hunger, carry objects, and death.
- **RPC Validation** — Some `_Validate` functions return `true` without actual validation (common in tutorials). Check if any are exploitable.
- **No module graph data** — The dependency analyzer found 0 edges, meaning all dependencies are within the single module. No modular architecture.
- **Plugins are content-only** — ExtendedRifleMod and MyFlashlightMod have no C++ code, only content.

---

## 8. RELEVANT CODE SNIPPETS

### Snippet 1: Server RPC Triplet Pattern (SBaseCharacter.h lines 61-66)
```cpp
// File: SurvivalGame/Source/SurvivalGame/Public/Player/SBaseCharacter.h
UFUNCTION(Server, Reliable, WithValidation)
void ServerSetSprinting(bool NewSprinting);

void ServerSetSprinting_Implementation(bool NewSprinting);

bool ServerSetSprinting_Validate(bool NewSprinting);
```
**Why relevant:** This is the canonical RPC pattern used across the entire project. Every gameplay action follows this triplet. The `_Validate` functions are often empty/returning true, which is a security concern for a multiplayer game.

### Snippet 2: Mutator Chain Pattern (SGameMode.h lines 148-169)
```cpp
// File: SurvivalGame/Source/SurvivalGame/Public/World/SGameMode.h
UPROPERTY(EditAnywhere, Category = "Mutators")
TArray<TSubclassOf<class ASMutator>> MutatorClasses;

/* First mutator in the execution chain */
ASMutator* BaseMutator;

void AddMutator(TSubclassOf<ASMutator> MutClass);

UFUNCTION(BlueprintNativeEvent)
bool CheckRelevance(AActor* Other);

virtual bool CheckRelevance_Implementation(AActor* Other);
```
**Why relevant:** Shows the mutator chain pattern inherited from UT. GameMode creates mutators from `MutatorClasses`, links them via `NextMutator`, and calls `CheckRelevance` on each actor. This is a key architectural pattern for extensibility.

### Snippet 3: Damage/Death Pipeline (SBaseCharacter.h lines 103-130)
```cpp
// File: SurvivalGame/Source/SurvivalGame/Public/Player/SBaseCharacter.h
virtual float TakeDamage(float Damage, struct FDamageEvent const& DamageEvent, 
    class AController* EventInstigator, class AActor* DamageCauser) override;

virtual bool CanDie(float KillingDamage, FDamageEvent const& DamageEvent, 
    AController* Killer, AActor* DamageCauser) const;

virtual bool Die(float KillingDamage, FDamageEvent const& DamageEvent, 
    AController* Killer, AActor* DamageCauser);

virtual void OnDeath(float KillingDamage, FDamageEvent const& DamageEvent, 
    APawn* PawnInstigator, AActor* DamageCauser);

void ReplicateHit(float DamageTaken, struct FDamageEvent const& DamageEvent, 
    APawn* PawnInstigator, AActor* DamageCauser, bool bKilled);

UPROPERTY(Transient, ReplicatedUsing = OnRep_LastTakeHitInfo)
struct FTakeHitInfo LastTakeHitInfo;

UFUNCTION()
void OnRep_LastTakeHitInfo();
```
**Why relevant:** The complete damage pipeline. TakeDamage → CanDie → Die → OnDeath. Hit replication uses a custom struct (FTakeHitInfo) with `ReplicatedUsing` for client-side hit feedback. This is a well-structured pattern worth noting.

### Snippet 4: Weapon State Machine (SWeapon.h lines 10-17, 22-25)
```cpp
// File: SurvivalGame/Source/SurvivalGame/Public/Items/SWeapon.h
UENUM()
enum class EWeaponState
{
    Idle,
    Firing,
    Equipping,
    Reloading
};

UCLASS(ABSTRACT, Blueprintable)
class SURVIVALGAME_API ASWeapon : public AActor
{
    GENERATED_BODY()
    // ...
    void StartFire();
    void StopFire();
    EWeaponState GetCurrentState() const;
    virtual void FireWeapon() PURE_VIRTUAL(ASWeapon::FireWeapon, );
```
**Why relevant:** Shows the abstract weapon base with a state machine and `PURE_VIRTUAL` for the firing implementation. Subclasses (SWeaponInstant) implement `FireWeapon`. This is a clean template method pattern.

### Snippet 5: FTakeHitInfo Struct — Custom Damage Replication (STypes.h lines 32-129)
```cpp
// File: SurvivalGame/Source/SurvivalGame/STypes.h
USTRUCT()
struct FTakeHitInfo
{
    GENERATED_USTRUCT_BODY()

    UPROPERTY()
    float ActualDamage;
    UPROPERTY()
    UClass* DamageTypeClass;
    UPROPERTY()
    TWeakObjectPtr<class ASBaseCharacter> PawnInstigator;
    UPROPERTY()
    TWeakObjectPtr<class AActor> DamageCauser;
    UPROPERTY()
    uint8 DamageEventClassID;
    UPROPERTY()
    bool bKilled;

    FDamageEvent& GetDamageEvent()
    {
        switch (DamageEventClassID) { /* returns Point/Radial/General damage event */ }
    }

    void SetDamageEvent(const FDamageEvent& DamageEvent)
    {
        DamageEventClassID = DamageEvent.GetTypeID();
        switch (DamageEventClassID) { /* stores by type */ }
    }
};
```
**Why relevant:** Custom struct for replicating damage events across the network. Stores the damage event by type ID and reconstructs it on the client. Uses `TWeakObjectPtr` to avoid strong references. This is a sophisticated pattern for a 2015-era project.