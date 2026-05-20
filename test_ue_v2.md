Now I have enough information to produce the comprehensive architecture review. Let me compile everything.

---

## 1. PROJECT SUMMARY

**Project:** EpicSurvivalGame — a third-person survival game for Unreal Engine 5.2, originally built as a 6-part tutorial series for Epic Games (2015). Open-source C++ sample project by Tom Looman.

**Tech Stack:** Unreal Engine 5.2, C++ (75 files), C# (4 build files), YAML (1 config), 23 unknown (content/config). 43 classes, 380 methods.

**Scale:** 103 total files, 38 header files, 37 implementation files. Single UE module (`SurvivalGame`) with 2 content-only plugins (`ExtendedRifleMod`, `MyFlashlightMod`).

**Key Dependencies (Build.cs):** Core, CoreUObject, Engine, InputCore, AIModule, GameplayTasks, NavigationSystem, OnlineSubsystem (Steam), PhysicsCore.

---

## 2. ARCHITECTURE

**Type:** **Unreal Engine Game Framework** (UE4/5 standard class hierarchy) with **Layered/Feature-based** organization.

**Layers (by directory):**

| Layer | Directory | Responsibility |
|---|---|---|
| **Player** | `Public/Player/` | Character classes, controllers, camera, state, local player |
| **Items** | `Public/Items/` | Weapons, pickups, usable actors, damage types, effects |
| **World** | `Public/World/` | Game modes, game state, time-of-day system, player starts |
| **AI** | `Public/AI/` | Zombie characters, AI controllers, behavior tasks, waypoints |
| **Components** | `Public/Components/` | Movement component, carry object component |
| **UI** | `Public/UI/` | HUD rendering |
| **Mutators** | `Public/Mutators/` | Gameplay mutator chain (weapon replacement) |
| **Core** | `Public/Core/` | Gameplay statics utility |
| **Editor** | `Public/Editor/` | Sound node customization |

**Key Architecture Patterns:**

1. **UE4 Game Framework Inheritance:** All classes extend UE base classes (`ACharacter`, `AGameMode`, `APlayerController`, `AHUD`, `AActor`, etc.)
2. **Abstract Base + Concrete Subclass:** `ASBaseCharacter` → `ASCharacter` (player) + `ASZombieCharacter` (AI); `ASUsableActor` → `ASPickupActor` → `ASConsumableActor`/`ASWeaponPickup`; `ASWeapon` → `ASWeaponInstant` + `ASFlashlight`; `ASGameMode` → `ASCoopGameMode` + `ASOpenWorldGameMode`
3. **Mutator Chain Pattern:** Linked-list of mutators (`ASMutator` → `ASMutator_WeaponReplacement`) that intercept `CheckRelevance()` and `InitGame()` calls
4. **Server-Authoritative RPC:** All gameplay-affecting actions use `Server, Reliable, WithValidation` RPC pattern
5. **Day/Night Cycle:** `SGameState` tracks elapsed minutes, `SGameMode` drives the timer, `STimeOfDayManager` visualizes sun position
6. **Inventory System:** Slot-based (`EInventorySlot::Hands/Primary/Secondary`) with weapon switching, dropping, and pickup

---

## 3. RELATED FILES

| # | File | Entity Type | Purpose | Relevance |
|---|---|---|---|---|
| 1 | `SurvivalGame/Source/SurvivalGame/Public/Player/SBaseCharacter.h` | Character (Base) | Abstract base for all characters (player + AI). Health, damage, death, sprinting, targeting. | **Core** — foundation of all character classes |
| 2 | `SurvivalGame/Source/SurvivalGame/Public/Player/SCharacter.h` | Character (Player) | Player-specific: inventory, weapons, hunger, camera, input, carry objects. | **Core** — player character with full gameplay |
| 3 | `SurvivalGame/Source/SurvivalGame/Public/World/SGameMode.h` | GameMode | Core game rules: bot spawning, day/night, scoring, damage modification, mutator chain. | **Core** — central game logic orchestrator |
| 4 | `SurvivalGame/Source/SurvivalGame/Public/Items/SWeapon.h` | Weapon (Base) | Abstract weapon: firing, equipping, ammo, animation, replication. | **Core** — weapon system foundation |
| 5 | `SurvivalGame/Source/SurvivalGame/Public/Items/SWeaponInstant.h` | Weapon (Hitscan) | Hitscan weapon: trace, damage, impact effects, server-hit validation. | **Key** — concrete weapon implementation |
| 6 | `SurvivalGame/Source/SurvivalGame/Public/Items/SUsableActor.h` | Usable Actor (Base) | Abstract base for interactable actors (pickups, bombs). Focus/use interface. | **Key** — interaction system foundation |
| 7 | `SurvivalGame/Source/SurvivalGame/Public/Items/SPickupActor.h` | Pickup Actor | Respawnable pickup with replication, sound, and lifecycle. | **Key** — pickup system |
| 8 | `SurvivalGame/Source/SurvivalGame/Public/World/SGameState.h` | GameState | Replicated game state: score, day/night, elapsed time, broadcast messages. | **Key** — authoritative state for all clients |
| 9 | `SurvivalGame/Source/SurvivalGame/Public/AI/SZombieCharacter.h` | AI Character | Zombie AI: sensing (sight/hearing), melee attack, patrol/passive behavior. | **Key** — enemy implementation |
| 10 | `SurvivalGame/Source/SurvivalGame/Public/AI/SZombieAIController.h` | AI Controller | Zombie AI controller: blackboard, behavior tree, waypoint/target management. | **Key** — AI decision-making |
| 11 | `SurvivalGame/Source/SurvivalGame/Public/Player/SPlayerController.h` | Player Controller | Player input, spectating, HUD messages, chat, suicide. | **Key** — player input and state |
| 12 | `SurvivalGame/Source/SurvivalGame/Public/UI/SHUD.h` | HUD | HUD rendering, state management, center dot, message display. | **Supporting** — UI layer |
| 13 | `SurvivalGame/Source/SurvivalGame/Public/World/STimeOfDayManager.h` | Service/Manager | Sun rotation, sky light, ambient audio based on game state time. | **Supporting** — visual day/night |
| 14 | `SurvivalGame/Source/SurvivalGame/Public/Mutators/SMutator.h` | Mutator (Base) | Abstract mutator with linked-list chain pattern. | **Supporting** — gameplay modification |
| 15 | `SurvivalGame/Source/SurvivalGame/Public/Mutators/SMutator_WeaponReplacement.h` | Mutator (Concrete) | Replaces weapon classes in pickups and default inventory. | **Supporting** — concrete mutator example |
| 16 | `SurvivalGame/Source/SurvivalGame/Public/Items/SFlashlight.h` | Weapon (Flashlight) | Flashlight weapon: light toggle, equip/unequip, replication. | **Supporting** — alternative weapon type |
| 17 | `SurvivalGame/Source/SurvivalGame/Public/Items/SDamageType.h` | DamageType | Custom damage type with head/limb modifiers and can-die-from flag. | **Supporting** — damage customization |
| 18 | `SurvivalGame/Source/SurvivalGame/STypes.h` | Types/Enums | Shared enums (`EInventorySlot`, `EBotBehaviorType`) and `FTakeHitInfo` struct. | **Supporting** — shared type definitions |
| 19 | `SurvivalGame/Source/SurvivalGame/Public/World/SCoopGameMode.h` | GameMode (Coop) | Coop-specific: match end, night-end respawn, scoring. | **Supporting** — game mode variant |
| 20 | `SurvivalGame/Source/SurvivalGame/Public/World/SOpenWorldGameMode.h` | GameMode (Open World) | Open world variant: spectate override. | **Supporting** — game mode variant |

---

## 4. DEPENDENCY GRAPH

**Module-Level (from Build.cs):**
```
SurvivalGame (Runtime Module)
  ├── Core, CoreUObject, Engine (always)
  ├── InputCore (player input)
  ├── AIModule (AI controllers, behavior trees)
  ├── GameplayTasks (behavior tree tasks)
  ├── NavigationSystem (pathfinding)
  ├── OnlineSubsystem (Steam integration)
  └── PhysicsCore (physical materials)
```

**File-Level (from #include analysis in .cpp files):**

**SGameMode.cpp** (central hub) imports:
- `Player/SPlayerController.h`, `Player/SPlayerState.h`, `Player/SCharacter.h`, `Player/SSpectatorPawn.h`
- `World/SGameState.h`, `World/SPlayerStart.h`
- `AI/SZombieAIController.h`, `AI/SZombieCharacter.h`
- `Mutators/SMutator.h`
- `Items/SWeapon.h`
- `SurvivalGame/STypes.h`, `SurvivalGame/SurvivalGame.h`

**SBaseCharacter.cpp** imports:
- `World/SGameMode.h` (calls `ModifyDamage`, `Killed`)
- `Components/SCharacterMovementComponent.h`
- `Items/SDamageType.h`

**SCharacter.cpp** imports:
- `Items/SUsableActor.h`, `Items/SWeapon.h`, `Items/SWeaponPickup.h`
- `Components/SCharacterMovementComponent.h`, `Components/SCarryObjectComponent.h`
- `Player/SBaseCharacter.h`, `Player/SPlayerController.h`

**SWeapon.cpp** imports:
- `Player/SCharacter.h`, `Player/SPlayerController.h`
- `Items/SWeaponPickup.h`
- `SurvivalGame/STypes.h`

**SWeaponInstant.cpp** imports:
- `Items/SImpactEffect.h`, `Items/SDamageType.h`
- `Player/SPlayerController.h`

**SZombieCharacter.cpp** imports:
- `AI/SZombieAIController.h`, `AI/SBotWaypoint.h`
- `Player/SCharacter.h`, `Player/SBaseCharacter.h`, `Player/SPlayerState.h`

**Call Graph (key chains):**
```
SGameMode::DefaultTimer (1s tick)
  → SGameState::GetAndUpdateIsNight()
  → SGameState::BroadcastGameMessage()
  → SGameMode::OnNightEnded()

ASBaseCharacter::TakeDamage
  → SGameMode::ModifyDamage() [friendly fire check]
  → ASBaseCharacter::Die()
    → SGameMode::Killed() [scoring]
    → ASBaseCharacter::OnDeath()

ASCharacter::Use()
  → ServerUse() [RPC]
    → ASUsableActor::OnUsed()

ASWeapon::StartFire()
  → ServerStartFire() [RPC]
    → ASWeapon::HandleFiring()
      → ASWeaponInstant::FireWeapon()
        → ProcessInstantHit()
          → ServerNotifyHit() [RPC]
            → DealDamage()
```

---

## 5. CONVENTIONS

### Naming Conventions (from sample_signatures)

| Rule | Pattern | Examples |
|---|---|---|
| **Prefix 'A' for Actors** | `A` prefix on all `AActor` subclasses | `ASBaseCharacter`, `ASGameMode`, `ASWeapon`, `ASBombActor` |
| **Prefix 'U' for UObject** | `U` prefix on all `UObject` subclasses | `USDamageType`, `USCharacterMovementComponent`, `USGameplayStatics` |
| **Prefix 'S' for project classes** | Project-specific prefix `S` after `A`/`U` | `ASBaseCharacter`, `ASZombieCharacter`, `USCharacterMovementComponent` |
| **Suffix 'Component' for components** | `*Component` suffix | `USCharacterMovementComponent`, `USCarryObjectComponent` |
| **Suffix 'Controller' for controllers** | `*Controller` suffix | `ASPlayerController`, `ASZombieAIController` |
| **Suffix 'Character' for characters** | `*Character` suffix | `ASBaseCharacter`, `ASZombieCharacter`, `ASCharacter` |
| **Suffix 'GameMode' for game modes** | `*GameMode` suffix | `ASGameMode`, `ASCoopGameMode`, `ASOpenWorldGameMode` |
| **Suffix 'State' for state classes** | `*State` suffix | `ASGameState`, `ASPlayerState` |
| **Suffix 'Actor' for items/objects** | `*Actor` suffix | `ASUsableActor`, `ASPickupActor`, `ASBombActor`, `ASConsumableActor` |
| **Suffix 'Weapon' for weapons** | `*Weapon` suffix | `ASWeapon`, `ASWeaponInstant`, `ASWeaponPickup` |
| **Prefix 'E' for enums** | `E` prefix on all enums | `EInventorySlot`, `EBotBehaviorType`, `EWeaponState`, `EHUDState` |
| **Prefix 'F' for structs** | `F` prefix on all structs | `FTakeHitInfo`, `FReplacementInfo` |
| **Prefix 'b' for booleans** | `b` prefix on bool properties | `bIsDying`, `bIsEquipped`, `bHasNewFocus`, `bAllowFriendlyFireDamage` |
| **Prefix 'On' for event callbacks** | `On*` for event/delegate handlers | `OnRep_LastTakeHitInfo`, `OnSeePlayer`, `OnHearNoise`, `OnDeath` |
| **Prefix 'Server' for RPCs** | `Server*` for server RPCs | `ServerSetSprinting`, `ServerStartFire`, `ServerSuicide` |
| **Prefix 'Client' for client RPCs** | `Client*` for client RPCs | `ClientHUDStateChanged`, `ClientReceiveChatMessage` |

### Architectural Patterns

- **Server-Authoritative RPC:** All state-changing functions use `UFUNCTION(Server, Reliable, WithValidation)` with `_Implementation` and `_Validate` stubs
- **ReplicatedUsing:** Properties use `ReplicatedUsing=OnRep_*` for client-side sync (e.g., `OnRep_LastTakeHitInfo`, `OnRep_BurstCounter`)
- **Abstract Base Classes:** Key hierarchies use `UCLASS(ABSTRACT)` or `UCLASS(Abstract)` — `ASBaseCharacter`, `ASWeapon`, `ASUsableActor`, `ASPickupActor`, `ASMutator`
- **BlueprintNativeEvent:** Game mode and mutator methods use `BlueprintNativeEvent` for BP extensibility (`CheckRelevance`, `InitGame`)
- **Constructor with FObjectInitializer:** All Actor constructors use `const class FObjectInitializer& ObjectInitializer` pattern
- **CreateDefaultSubobject:** Components created in constructors via `CreateDefaultSubobject<T>(TEXT("..."))`

### Style Conventions

- **Copyright header:** `// Copyright 1998-2015 Epic Games, Inc. All Rights Reserved.` on all files
- **Include order:** Own header first, then project headers, then engine headers
- **Pragma once:** All headers use `#pragma once`
- **GENERATED_BODY():** All UCLASS/USTRUCT/UENUM use generated body macros
- **UPROPERTY categories:** All properties use `Category = "..."` specifier
- **Virtual overrides:** All overrides marked `virtual` with `override` (C++11 style)

---

## 6. SIMILAR IMPLEMENTATIONS

| Base Class | Similar Implementations | File | Similarity Reason |
|---|---|---|---|
| **ASBaseCharacter** | `ASCharacter` | `Public/Player/SCharacter.h` | Extends ASBaseCharacter, same health/damage/death system |
| **ASBaseCharacter** | `ASZombieCharacter` | `Public/AI/SZombieCharacter.h` | Extends ASBaseCharacter, overrides IsSprinting(), PlayHit() |
| **ASWeapon** | `ASWeaponInstant` | `Public/Items/SWeaponInstant.h` | Extends ASWeapon, implements FireWeapon() for hitscan |
| **ASWeapon** | `ASFlashlight` | `Public/Items/SFlashlight.h` | Extends ASWeapon, overrides HandleFiring() for light toggle |
| **ASUsableActor** | `ASPickupActor` | `Public/Items/SPickupActor.h` | Extends ASUsableActor, adds respawn/replication |
| **ASPickupActor** | `ASConsumableActor` | `Public/Items/SConsumableActor.h` | Extends ASPickupActor, implements OnUsed() for consumables |
| **ASPickupActor** | `ASWeaponPickup` | `Public/Items/SWeaponPickup.h` | Extends ASPickupActor, implements OnUsed() for weapon pickup |
| **ASUsableActor** | `ASBombActor` | `Public/Items/SBombActor.h` | Extends ASUsableActor, adds explosion/TakeDamage |
| **ASGameMode** | `ASCoopGameMode` | `Public/World/SCoopGameMode.h` | Extends ASGameMode, adds match end/night respawn |
| **ASGameMode** | `ASOpenWorldGameMode` | `Public/World/SOpenWorldGameMode.h` | Extends ASGameMode, overrides CanSpectate |
| **ASMutator** | `ASMutator_WeaponReplacement` | `Public/Mutators/SMutator_WeaponReplacement.h` | Extends ASMutator, implements CheckRelevance/InitGame |
| **UBTTask_BlackboardBase** | `UBTTask_FindBotWaypoint` | `Public/AI/BTTask_FindBotWaypoint.h` | Extends UBTTask_BlackboardBase, implements ExecuteTask |
| **UBTTask_BlackboardBase** | `UBTTask_FindPatrolLocation` | `Public/AI/BTTask_FindPatrolLocation.h` | Extends UBTTask_BlackboardBase, implements ExecuteTask |

---

## 7. TASK CONTEXT

This is a **code review** of the EpicSurvivalGame project. The reviewer needs to analyze the architecture for:

**What to look at:**
1. **Character Hierarchy** (`SBaseCharacter` → `SCharacter` + `SZombieCharacter`): Check if the base class properly abstracts shared functionality (health, damage, death, movement modifiers) and if the subclasses correctly extend it without duplication.
2. **Weapon/Item Hierarchy** (`SUsableActor` → `SPickupActor` → `SConsumableActor`/`SWeaponPickup`; `SWeapon` → `SWeaponInstant`/`SFlashlight`): Evaluate the abstract base pattern, whether `FireWeapon()` as PURE_VIRTUAL is appropriate, and if the inventory system is clean.
3. **Game Mode Hierarchy** (`SGameMode` → `SCoopGameMode` + `SOpenWorldGameMode`): Check if the base game mode properly handles day/night cycle, bot spawning, and if subclasses add meaningful specialization.
4. **AI System** (`SZombieCharacter` + `SZombieAIController` + behavior tasks): Evaluate the sensing-based AI, patrol/passive behavior, and the separation between character and controller.
5. **Mutator Chain** (`SMutator` → `SMutator_WeaponReplacement`): Review the linked-list pattern for gameplay modification.
6. **Networking/Replication**: Check RPC patterns (Server/Client/NetMulticast), `ReplicatedUsing` properties, and authority checks.
7. **Day/Night Cycle**: Review the time-of-day system spanning `SGameState`, `SGameMode`, and `STimeOfDayManager`.

**Key files to read in full:** `SBaseCharacter.h/.cpp`, `SCharacter.h/.cpp`, `SGameMode.h/.cpp`, `SWeapon.h/.cpp`, `SWeaponInstant.h/.cpp`, `SZombieCharacter.h/.cpp`, `SZombieAIController.h/.cpp`, `SGameState.h/.cpp`, `SMutator.h/.cpp`, `SMutator_WeaponReplacement.h/.cpp`

**What to be careful about:**
- The project uses **old UE4 conventions** (pre-4.25) — no IInterface, no TSubclassOf in some places, old-style `APawn*` instead of `APawn*` in delegates
- The README explicitly states the project uses "very old standards and conventions" from 2015
- Some code has commented-out sections (e.g., `WakeAllBots()`/`PassifyAllBots()` in SGameMode.cpp)
- The `FTakeHitInfo` struct in STypes.h uses a manual replication pattern with `EnsureReplicationByte`
- Plugins (`ExtendedRifleMod`, `MyFlashlightMod`) are content-only with no C++ modules

---

## 8. RELEVANT CODE SNIPPETS

### Snippet 1: Abstract Base Character with Server-Authoritative RPC Pattern
**File:** `SurvivalGame/Source/SurvivalGame/Public/Player/SBaseCharacter.h` (lines ~30-50)
```cpp
UFUNCTION(Server, Reliable, WithValidation)
void ServerSetSprinting(bool NewSprinting);
void ServerSetSprinting_Implementation(bool NewSprinting);
bool ServerSetSprinting_Validate(bool NewSprinting);

UPROPERTY(Transient, Replicated)
uint32 bWantsToRun : 1;

virtual float TakeDamage(float Damage, struct FDamageEvent const& DamageEvent, 
    class AController* EventInstigator, class AActor* DamageCauser);
virtual bool Die(float KillingDamage, FDamageEvent const& DamageEvent, 
    AController* Killer, AActor* DamageCauser);
```
**Why relevant:** Shows the standard UE4 server-authoritative RPC pattern (`Server, Reliable, WithValidation` + `_Implementation` + `_Validate`) and the replicated property pattern used throughout the project.

### Snippet 2: GameMode as Central Orchestrator with Day/Night Cycle
**File:** `SurvivalGame/Source/SurvivalGame/Private/World/SGameMode.cpp` (lines 84-133)
```cpp
void ASGameMode::DefaultTimer()
{
    if (IsMatchInProgress()) {
        ASGameState* MyGameState = Cast<ASGameState>(GameState);
        if (MyGameState) {
            MyGameState->ElapsedGameMinutes += MyGameState->GetTimeOfDayIncrement();
            MyGameState->GetAndUpdateIsNight();
            bool CurrentIsNight = MyGameState->GetIsNight();
            if (CurrentIsNight != LastIsNight) {
                EHUDMessage MessageID = CurrentIsNight ? EHUDMessage::Game_SurviveStart : EHUDMessage::Game_SurviveEnded;
                MyGameState->BroadcastGameMessage(MessageID);
                if (!CurrentIsNight) { OnNightEnded(); }
            }
            LastIsNight = MyGameState->bIsNight;
        }
    }
}
```
**Why relevant:** Shows the game mode as the central orchestrator driving the day/night cycle via a 1-second timer, delegating state to `SGameState` and broadcasting messages.

### Snippet 3: Abstract Weapon with PURE_VIRTUAL Fire Pattern
**File:** `SurvivalGame/Source/SurvivalGame/Public/Items/SWeapon.h` (lines ~50-70)
```cpp
UCLASS(ABSTRACT, Blueprintable)
class SURVIVALGAME_API ASWeapon : public AActor
{
    virtual void FireWeapon() PURE_VIRTUAL(ASWeapon::FireWeapon, );
    
    UFUNCTION(Reliable, Server, WithValidation)
    void ServerStartFire();
    void ServerStartFire_Implementation();
    bool ServerStartFire_Validate();
    
    virtual void HandleFiring();
    void DetermineWeaponState();
};
```
**Why relevant:** Shows the abstract weapon pattern with `PURE_VIRTUAL` (UE4's alternative to pure virtual), server RPCs for firing, and the state machine approach (`DetermineWeaponState`).

### Snippet 4: Mutator Chain Pattern
**File:** `SurvivalGame/Source/SurvivalGame/Private/Mutators/SMutator.cpp` (lines 10-27)
```cpp
bool ASMutator::CheckRelevance_Implementation(AActor* Other)
{
    if (NextMutator) {
        return NextMutator->CheckRelevance(Other);
    }
    return true;
}

void ASMutator::InitGame_Implementation(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
    if (NextMutator) {
        NextMutator->InitGame(MapName, Options, ErrorMessage);
    }
}
```
**Why relevant:** Shows the linked-list mutator chain pattern. Each mutator calls `Super::CheckRelevance_Implementation()` to chain to the next mutator, allowing multiple gameplay modifications to stack.

### Snippet 5: Damage Pipeline with GameMode Integration
**File:** `SurvivalGame/Source/SurvivalGame/Private/Player/SBaseCharacter.cpp` (lines 56-101)
```cpp
float ASBaseCharacter::TakeDamage(float Damage, struct FDamageEvent const& DamageEvent, 
    class AController* EventInstigator, class AActor* DamageCauser)
{
    ASGameMode* MyGameMode = Cast<ASGameMode>(GetWorld()->GetAuthGameMode());
    Damage = MyGameMode ? MyGameMode->ModifyDamage(Damage, this, DamageEvent, EventInstigator, DamageCauser) : Damage;
    
    const float ActualDamage = Super::TakeDamage(Damage, DamageEvent, EventInstigator, DamageCauser);
    if (ActualDamage > 0.f) {
        Health -= ActualDamage;
        if (Health <= 0) {
            USDamageType* DmgType = Cast<USDamageType>(DamageEvent.DamageTypeClass->GetDefaultObject());
            bCanDie = (DmgType == nullptr || DmgType->GetCanDieFrom());
            if (bCanDie) { Die(ActualDamage, DamageEvent, EventInstigator, DamageCauser); }
            else { Health = 1.0f; }
        }
    }
}
```
**Why relevant:** Shows the complete damage pipeline: GameMode damage modification (friendly fire check), custom damage type with `GetCanDieFrom()`, and the death flow. This is the core gameplay loop integration.