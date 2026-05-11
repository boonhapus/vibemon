from app import schema, types

UNIVERSAL_MOVES = (
    schema.Move(
        name="Tackle",
        flavor_text="A basic physical strike that any Vibemon can perform.",
        type=types.VibemonTypeT.NORMAL,
        category=types.MoveCategoryT.PHYSICAL,
        power=40,
        accuracy=1.0,
        pp=35,
        level_requirement=1,
    ),
    schema.Move(
        name="Breaking Point",
        flavor_text="A desperate all-out strike used when no moves have PP remaining; the user takes minor recoil.",
        type=types.VibemonTypeT.NORMAL,
        category=types.MoveCategoryT.PHYSICAL,
        power=50,
        accuracy=1.0,
        pp=1,
        level_requirement=1,
        effects=(
            schema.EffectGroup(
                trigger="after_damage",
                effects=(schema.Recoil(ratio=0.25),),
            ),
        ),
    ),
    schema.Move(
        name="Snap Strike",
        flavor_text="A reflexive opening hit that lands before heavier attacks can start.",
        type=types.VibemonTypeT.NORMAL,
        category=types.MoveCategoryT.PHYSICAL,
        power=40,
        accuracy=1.0,
        pp=30,
        priority=1,
        level_requirement=1,
    ),
)
