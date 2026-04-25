import pydantic

from app import utils


ensure_between_5_255 = pydantic.AfterValidator(lambda v: utils.clamp(v, minimum=5, maximum=255))
ensure_between_abs_7 = pydantic.AfterValidator(lambda v: utils.clamp(v, minimum=-7, maximum=7))
