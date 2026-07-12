"""Private API client for Legrand Energy."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import aiohttp

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"
SYNC_API_BASE = "https://app.netatmo.net/syncapi/v1"
AUTH_BASE = "https://auth.netatmo.com"

API_TIMEOUT = aiohttp.ClientTimeout(total=30)

PRIVATE_MEASURE_TYPE_ELECTRICITY = (
    "sum_energy_elec,"
    "sum_energy_elec$0,"
    "sum_energy_elec$1,"
    "sum_energy_elec$2,"
    "sum_energy_price$0,"
    "sum_energy_price$1,"
    "sum_energy_price$2"
)

PRIVATE_MEASURE_TYPE_FLUID = "sum_fluid_consumption$0,sum_fluid_price$0"


class LegrandPrivateApiError(Exception):
    """Base private API error."""


class LegrandPrivateApiAuthenticationError(LegrandPrivateApiError):
    """Private API authentication error."""


class LegrandPrivateApi:
    """Client for the private Netatmo API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        web_token: str,
    ) -> None:
        """Initialize the private API client."""
        self._session = session
        self._web_token = web_token

    @property
    def web_token(self) -> str:
        """Return the current private web token."""
        return self._web_token

    def set_web_token(
        self,
        web_token: str,
    ) -> None:
        """Replace the private web token in memory."""
        self._web_token = web_token

    def _headers(self) -> dict[str, str]:
        """Return private API request headers."""
        return {
            "Authorization": f"Bearer {self._web_token}",
            "Accept": "application/json",
        }

    async def _get(
        self,
        base_url: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a private API GET request."""
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=API_TIMEOUT,
            ) as response:
                if response.status in (401, 403):
                    raise LegrandPrivateApiAuthenticationError(
                        f"Private API request to {endpoint} "
                        f"failed with HTTP status {response.status}"
                    )

                if response.status >= 400:
                    response_text = await response.text()

                    raise LegrandPrivateApiError(
                        f"Private API request to {endpoint} "
                        f"failed with HTTP status {response.status}: "
                        f"{response_text[:300]}"
                    )

                try:
                    data = await response.json(content_type=None)
                except (
                    aiohttp.ContentTypeError,
                    json.JSONDecodeError,
                ) as err:
                    raise LegrandPrivateApiError(
                        f"Private API request to {endpoint} returned invalid JSON"
                    ) from err

        except LegrandPrivateApiError:
            raise

        except TimeoutError as err:
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} timed out"
            ) from err

        except aiohttp.ClientError as err:
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} failed: {err}"
            ) from err

        if not isinstance(data, dict):
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} returned an unexpected response"
            )

        api_status = data.get("status")

        if api_status == "error":
            error = data.get("error")

            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} returned an API error: {error}"
            )

        return cast(dict[str, Any], data)

    async def homestatus(
        self,
        home_id: str,
    ) -> dict[str, Any]:
        """Return the current private home status."""
        return await self._get(
            APP_API_BASE,
            "homestatus",
            {
                "home_id": home_id,
            },
        )

    async def get_measure(
        self,
        home_id: str,
        module_id: str,
        measure_type: str,
        bridge: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a raw private measure for testing."""
        module_payload: dict[str, Any] = {
            "id": module_id,
            "type": measure_type,
        }

        if bridge is not None:
            module_payload["bridge"] = bridge

        home_payload = {
            "id": home_id,
            "modules": [
                module_payload,
            ],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": "max",
                "date_end": "last",
            },
        )

    async def get_electricity_measure(
        self,
        home_id: str,
        module_id: str,
        bridge: str,
        date_begin: int,
        date_end: int,
    ) -> dict[str, Any]:
        """Return electricity measurements for one module."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": PRIVATE_MEASURE_TYPE_ELECTRICITY,
                },
            ],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def get_electricity_measures(
        self,
        home_id: str,
        modules: list[tuple[str, str]],
        date_begin: int,
        date_end: int,
    ) -> dict[str, Any]:
        """Return electricity measurements for multiple modules."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": PRIVATE_MEASURE_TYPE_ELECTRICITY,
                }
                for module_id, bridge in modules
            ],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def get_fluid_measure(
        self,
        home_id: str,
        module_id: str,
        bridge: str,
        date_begin: int,
        date_end: int,
    ) -> dict[str, Any]:
        """Return fluid measurements for one module."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": PRIVATE_MEASURE_TYPE_FLUID,
                },
            ],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def getcontracts(
        self,
        home_id: str,
    ) -> dict[str, Any]:
        """Return the electricity contract."""
        return await self._get(
            SYNC_API_BASE,
            "getcontracts",
            {
                "home_id": home_id,
            },
        )

    async def refresh_web_token(
        self,
        *,
        refresh_token: str,
        laravel_session: str | None = None,
        mail_cookie: str | None = None,
        authorize_state: str | None = None,
        locale: str = "fr-FR",
    ) -> str:
        """Test refreshing the Netatmo private web token.

        This method calls the private authentication endpoint identified
        through the Netatmo web application.

        It updates the token in memory but does not yet save it in the
        Home Assistant ConfigEntry.
        """
        cookies: dict[str, str] = {
            "authnetatmocomrefresh_token": refresh_token,
            "netatmocomlocale": locale,
        }

        if laravel_session:
            cookies["authnetatmocomlaravel_session"] = laravel_session

        if mail_cookie:
            cookies["authnetatmocommail_cookie"] = mail_cookie

        if authorize_state:
            cookies["authnetatmocomauthorize_state"] = authorize_state

        url = (
            f"{AUTH_BASE}/access/checklogin"
            "?next_url="
            "https%3A%2F%2Fhome.netatmo.com"
            "%2Fcontrol%2Fdashboard"
        )

        try:
            async with self._session.get(
                url,
                cookies=cookies,
                allow_redirects=False,
                timeout=API_TIMEOUT,
                headers={
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/150.0.0.0 Safari/537.36"
                    ),
                },
            ) as response:
                _LOGGER.warning(
                    "Netatmo refresh test returned HTTP %s with location %s",
                    response.status,
                    response.headers.get("Location"),
                )

                access_cookie = response.cookies.get("netatmocomaccess_token")

                if access_cookie is None:
                    set_cookie_headers = response.headers.getall(
                        "Set-Cookie",
                        [],
                    )

                    cookie_names = [
                        header.split("=", 1)[0]
                        for header in set_cookie_headers
                        if "=" in header
                    ]

                    _LOGGER.warning(
                        "Netatmo refresh test returned cookies: %s",
                        cookie_names,
                    )

                    raise LegrandPrivateApiAuthenticationError(
                        "Netatmo checklogin did not return netatmocomaccess_token"
                    )

                new_web_token = access_cookie.value

        except LegrandPrivateApiError:
            raise

        except TimeoutError as err:
            raise LegrandPrivateApiError("Netatmo web-token refresh timed out") from err

        except aiohttp.ClientError as err:
            raise LegrandPrivateApiError(
                f"Netatmo web-token refresh failed: {err}"
            ) from err

        if not new_web_token:
            raise LegrandPrivateApiAuthenticationError(
                "Netatmo returned an empty web token"
            )

        self.set_web_token(new_web_token)

        _LOGGER.warning(
            "Netatmo web token refreshed successfully: %s...%s",
            new_web_token[:6],
            new_web_token[-4:],
        )

        return new_web_token
