import pydantic


class VibemonSound(pydantic.BaseModel):
    description: str = pydantic.Field(description="Cinematic sound effect description.")
    duration: float = pydantic.Field(ge=0.5, le=4.0)
