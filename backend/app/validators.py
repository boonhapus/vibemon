import pydantic

from app import utils


ensure_between_5_255 = pydantic.AfterValidator(lambda v: utils.clamp(v, minimum=5, maximum=255))
