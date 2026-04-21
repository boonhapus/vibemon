import niquests
import structlog

_LOGGER = structlog.get_logger(__name__)


class LoggingHook(niquests.AsyncLifeCycleHook):
    """Structured logging hook for an API client."""

    def __init__(self, provider: str) -> None:
        super().__init__()
        self.provider = provider

    async def pre_request(self, prepared_request: niquests.PreparedRequest, **kwargs) -> None:
        """
        The prepared request just got built. You may alter it prior to be sent through HTTP.

        Further reading:
          https://niquests.readthedocs.io/en/latest/user/advanced.html#niquests.hooks.AsyncLifeCycleHook.pre_request
        """
        await _LOGGER.adebug(
            f"{self.provider}.request",
            method=prepared_request.method,
            url=str(prepared_request.url),
            body=prepared_request.body,
        )

    async def response(self, response: niquests.Response, **kwargs) -> None:
        """
        The response generated from a Request. You may alter the response at will.

        Further reading:
          https://niquests.readthedocs.io/en/latest/user/advanced.html#niquests.hooks.AsyncLifeCycleHook.response
        """
        if response.request is None:
            return

        await _LOGGER.ainfo(
            f"{self.provider}.response",
            method=response.request.method,
            url=str(response.request.url),
            status_code=response.status_code,
            elapsed_s=round(response.elapsed.total_seconds(), 2),
        )
