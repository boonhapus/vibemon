import uuid

import pytest
from app import schema, types
from app.game_engine import (
    Phase,
    GameEngine,
    check_pre_action,
    resolve_turn_order,
    execute_attack,
    end_of_turn_maintenance,
    apply_status_damage,
    effective_speed,
    _accuracy_modifier,
    stat_stage_multiplier,
    resolve_speed_tie,
)


class TestPhaseEnum:
    def test_phase_enum_exists(self):
        assert hasattr(Phase, "ACTION_SORTING")
        assert hasattr(Phase, "PRE_ACTION_CHECKS")
        assert hasattr(Phase, "EXECUTE_STACK")
        assert hasattr(Phase, "END_OF_TURN")
        assert hasattr(Phase, "TURN_END")


class TestPriorityBrackets:
    def test_resolve_turn_order_priority_higher_first(self):
        a = schema.BattleVibemon(
            name="A",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=50,
            moves=[
                types.Move(
                    name="Tackle",
                    type=types.VibemonTypeT.NORMAL,
                    category=types.MoveCategoryT.PHYSICAL,
                    power=40,
                    priority=0,
                )
            ],
        )
        b = schema.BattleVibemon(
            name="B",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=50,
            moves=[
                types.Move(
                    name="Quick Attack",
                    type=types.VibemonTypeT.NORMAL,
                    category=types.MoveCategoryT.PHYSICAL,
                    power=40,
                    priority=1,
                )
            ],
        )
        aid = uuid.uuid4()
        bid = uuid.uuid4()
        action_a = types.Action(trainer_name=aid, action_type=types.ActionType.MOVE, value="Tackle")
        action_b = types.Action(trainer_name=bid, action_type=types.ActionType.MOVE, value="Quick Attack")

        order = resolve_turn_order(a, b, action_a, action_b)
        assert order[0][0].name == "B"


class TestSpeedTie:
    def test_resolve_speed_tie_random(self):
        a_speed, b_speed = 50, 50
        results = {"first_a": 0, "first_b": 0}
        for _ in range(100):
            order = resolve_speed_tie(a_speed, b_speed)
            if order[0] == 0:
                results["first_a"] += 1
            else:
                results["first_b"] += 1
        assert results["first_a"] > 0 and results["first_b"] > 0


class TestAccuracyModifiers:
    def test_accuracy_modifier_increases_with_positive_stages(self):
        mod = _accuracy_modifier(accuracy_stage=1, evasion_stage=0)
        assert mod > 1.0

    def test_accuracy_modifier_decreases_with_negative_stages(self):
        mod = _accuracy_modifier(accuracy_stage=0, evasion_stage=1)
        assert mod < 1.0


class TestConfusion33Percent:
    def test_confusion_block_chance_33_percent(self):
        blocked_count = 0
        for _ in range(300):
            v = schema.BattleVibemon(
                name="Test",
                base_hp=100,
                base_attack=100,
                base_defense=100,
                base_sp_attack=100,
                base_sp_defense=100,
                base_speed=100,
                is_confused=True,
                confusion_turns=5,
            )
            result = check_pre_action(v)
            if result.blocked:
                blocked_count += 1
        assert 0.25 < blocked_count / 300 < 0.40


class TestStatusTracking:
    def test_taunt_decrement(self):
        v = schema.BattleVibemon(
            name="Test",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            taunt_turns=3,
        )
        end_of_turn_maintenance(v)
        assert v.taunt_turns == 2

    def test_bound_decrement(self):
        v = schema.BattleVibemon(
            name="Test",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            bound_turns=3,
        )
        end_of_turn_maintenance(v)
        assert v.bound_turns == 2


class TestStackCancellation:
    def test_faint_cancels_second_actor(self):
        aid = uuid.uuid4()
        bid = uuid.uuid4()
        a = schema.BattleVibemon(
            name="A",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            current_hp=100,
            moves=[
                types.Move(name="Hit", type=types.VibemonTypeT.NORMAL, category=types.MoveCategoryT.PHYSICAL, power=40)
            ],
        )
        b = schema.BattleVibemon(
            name="B",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=50,
            current_hp=1,
            moves=[
                types.Move(name="Hit", type=types.VibemonTypeT.NORMAL, category=types.MoveCategoryT.PHYSICAL, power=10)
            ],
        )
        engine = GameEngine(
            trainer_a=schema.Trainer(id=aid, name="TrainerA", team=[a]),
            trainer_b=schema.Trainer(id=bid, name="TrainerB", team=[b]),
        )
        action_a = types.Action(trainer_name=aid, action_type=types.ActionType.MOVE, value="Hit")
        action_b = types.Action(trainer_name=bid, action_type=types.ActionType.MOVE, value="Hit")

        engine.submit(action_a, action_b)
        assert b.is_fainted


class TestEndToEnd:
    def test_battle_runs_to_completion(self):
        pikachu = schema.BattleVibemon(
            name="Pikachu",
            elements=[types.VibemonTypeT.ELECTRIC],
            base_hp=111,
            base_attack=55,
            base_defense=40,
            base_sp_attack=50,
            base_sp_defense=50,
            base_speed=90,
            moves=[
                types.Move(
                    name="Thunderbolt",
                    type=types.VibemonTypeT.ELECTRIC,
                    category=types.MoveCategoryT.SPECIAL,
                    power=90,
                    accuracy=1.0,
                    pp=15,
                    pp_current=15,
                ),
            ],
        )
        charizard = schema.BattleVibemon(
            name="Charizard",
            base_hp=148,
            base_attack=84,
            base_defense=78,
            base_sp_attack=109,
            base_sp_defense=85,
            base_speed=100,
            elements=[types.VibemonTypeT.FIRE, types.VibemonTypeT.FLYING],
            moves=[
                types.Move(
                    name="Flamethrower",
                    type=types.VibemonTypeT.FIRE,
                    category=types.MoveCategoryT.SPECIAL,
                    power=90,
                    accuracy=1.0,
                    pp=15,
                    pp_current=15,
                ),
            ],
        )
        import uuid

        engine = GameEngine(
            trainer_a=schema.Trainer(id=uuid.uuid4(), name="Red", team=[pikachu]),
            trainer_b=schema.Trainer(id=uuid.uuid4(), name="Blue", team=[charizard]),
        )
        action_a = types.Action(
            trainer_name=engine.battle.trainer_a.id,
            action_type=types.ActionType.MOVE,
            value="Thunderbolt",
        )
        action_b = types.Action(
            trainer_name=engine.battle.trainer_b.id,
            action_type=types.ActionType.MOVE,
            value="Flamethrower",
        )
        while not engine.battle.is_over:
            engine.submit(action_a, action_b)

        assert engine.battle.is_over
        assert engine.battle.winner is not None


class TestStatStageModifier:
    def test_stage_zero_is_neutral(self):
        assert stat_stage_multiplier(0) == 1.0

    def test_positive_stages(self):
        assert stat_stage_multiplier(1) == pytest.approx(1.5)
        assert stat_stage_multiplier(2) == pytest.approx(2.0)
        assert stat_stage_multiplier(6) == pytest.approx(4.0)

    def test_negative_stages(self):
        assert stat_stage_multiplier(-1) == pytest.approx(2 / 3)
        assert stat_stage_multiplier(-2) == pytest.approx(0.5)
        assert stat_stage_multiplier(-6) == pytest.approx(0.25)

    def test_clamped_beyond_bounds(self):
        assert stat_stage_multiplier(10) == stat_stage_multiplier(6)
        assert stat_stage_multiplier(-10) == stat_stage_multiplier(-6)


class TestAccuracyModifierValues:
    def test_stage_zero_neutral(self):
        assert _accuracy_modifier(0, 0) == pytest.approx(1.0)

    def test_max_accuracy_stage(self):
        assert _accuracy_modifier(6, 0) == pytest.approx(3.0)

    def test_max_evasion_stage(self):
        assert _accuracy_modifier(0, 6) == pytest.approx(1 / 3)

    def test_symmetric_cancels_out(self):
        assert _accuracy_modifier(3, 3) == pytest.approx(1.0)


class TestBurnDamage:
    def test_burn_deals_one_sixteenth(self):
        v = schema.BattleVibemon(
            name="Test",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            status=types.StatusConditionT.BURN,
        )
        max_hp = v.max_hp
        dmg = apply_status_damage(v)
        assert dmg == max_hp // 16


class TestFlinchBeforeParalysis:
    def test_flinch_blocks_before_paralysis_roll(self):
        blocked_by_flinch = 0
        for _ in range(100):
            v = schema.BattleVibemon(
                name="Test",
                base_hp=100,
                base_attack=100,
                base_defense=100,
                base_sp_attack=100,
                base_sp_defense=100,
                base_speed=100,
                is_flinched=True,
                status=types.StatusConditionT.PARALYSIS,
            )
            result = check_pre_action(v)
            assert result.blocked
            if result.events and "flinched" in result.events[0].description:
                blocked_by_flinch += 1
        assert blocked_by_flinch == 100


class TestFaintGuard:
    def test_fainted_mon_blocked(self):
        v = schema.BattleVibemon(
            name="Test",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            current_hp=0,
        )
        result = check_pre_action(v)
        assert result.blocked


class TestEffectiveSpeed:
    def test_speed_stage_affects_turn_order(self):
        a = schema.BattleVibemon(
            name="Slow",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=50,
        )
        b = schema.BattleVibemon(
            name="Fast",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=80,
            moves=[
                types.Move(
                    name="Tackle", type=types.VibemonTypeT.NORMAL, category=types.MoveCategoryT.PHYSICAL, power=40
                )
            ],
        )
        a.stat_stages.speed = 6
        a.moves = [
            types.Move(name="Tackle", type=types.VibemonTypeT.NORMAL, category=types.MoveCategoryT.PHYSICAL, power=40)
        ]
        assert effective_speed(a) > effective_speed(b)

        aid, bid = uuid.uuid4(), uuid.uuid4()
        action_a = types.Action(trainer_name=aid, action_type=types.ActionType.MOVE, value="Tackle")
        action_b = types.Action(trainer_name=bid, action_type=types.ActionType.MOVE, value="Tackle")
        order = resolve_turn_order(a, b, action_a, action_b)
        assert order[0][0].name == "Slow"


class TestConfusionEndOfTurnDecrement:
    def test_confusion_decrements_at_end_of_turn(self):
        v = schema.BattleVibemon(
            name="Test",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            is_confused=True,
            confusion_turns=3,
        )
        end_of_turn_maintenance(v)
        assert v.confusion_turns == 2
        assert v.is_confused

    def test_confusion_clears_at_zero(self):
        v = schema.BattleVibemon(
            name="Test",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            is_confused=True,
            confusion_turns=1,
        )
        events = end_of_turn_maintenance(v)
        assert v.confusion_turns == 0
        assert not v.is_confused
        assert any("confusion" in e.description for e in events)


class TestStatusMoveEvent:
    def test_status_move_no_damage_text(self):
        attacker = schema.BattleVibemon(
            name="A",
            elements=[types.VibemonTypeT.ELECTRIC],
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
            moves=[
                types.Move(
                    name="Thunder Wave",
                    type=types.VibemonTypeT.ELECTRIC,
                    category=types.MoveCategoryT.STATUS,
                    accuracy=1.0,
                    pp=20,
                    pp_current=20,
                    effect=types.MoveEffect(status_inflict=types.StatusConditionT.PARALYSIS, chance=1.0),
                )
            ],
        )
        defender = schema.BattleVibemon(
            name="B",
            base_hp=100,
            base_attack=100,
            base_defense=100,
            base_sp_attack=100,
            base_sp_defense=100,
            base_speed=100,
        )
        move = attacker.moves[0]
        events = execute_attack(attacker, defender, move)
        damage_events = [e for e in events if e.hp_delta is not None]
        assert len(damage_events) == 0
        assert any("used Thunder Wave" in e.description for e in events)
