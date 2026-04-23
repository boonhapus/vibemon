from typing import Any
import os

import niquests

from app.settings import settings
from app.plugins import api_hooks
from app import __project__


class WeatherAPIClient(niquests.AsyncSession):
    """
    Fetches current weather conditions from WeatherAPI.

    If `api_key` is not provided, will attempt to load from the environment
    variable called `WAETHER_API_KEY`.

    Further reading:
      https://www.weatherapi.com/docs/
    """

    def __init__(self, api_key: str = "", **session_opts) -> None:
        if not (api_key := api_key or settings.weather_api_key.get_secret_value()):
            raise TypeError("WeatherAPIClient missing 1 required positional argument: 'api_key'")

        self._api_key = api_key

        super().__init__(
            base_url="http://api.weatherapi.com/v1",
            hooks=api_hooks.LoggingHook(provider="climate.weather_api"),
            **session_opts,
        )

        self.headers.update(
            {
                "user-agent": f"{__project__.__name__} v{__project__.__version__} (+github/{__project__.__slug__})",
                "content-type": "application/json",
                "accept": "application/json",
            }
        )

    async def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> niquests.Response:  # type: ignore
        """Inject the API key."""

        match method:
            case "GET":
                kwargs.setdefault("params", {})["key"] = self._api_key
            case _:
                pass

        return await super().request(method, url, *args, **kwargs)

    async def current_weather(self, latitude: float, longitude: float) -> niquests.Response:
        """
        Find the current weather at a given coordinate.

        Further reading:
          https://www.weatherapi.com/docs/#intro-request
        """
        u = "/current.json"
        p = {"q": f"{latitude},{longitude}"}
        r = await self.get(u, params=p)
        return r
