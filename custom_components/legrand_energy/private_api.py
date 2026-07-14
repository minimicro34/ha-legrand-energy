"""Private API client for Legrand Energy."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from http.cookies import Morsel
from typing import Any, cast
from urllib.parse import unquote

import aiohttp

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"
AUTH_BASE = "https://auth.netatmo.com"

API_TIMEOUT = aiohttp.ClientTimeout(total=30)

USER_AGENT = (
    "Mozilla/5.0 "
    "(Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)

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

PrivateAuthUpdateCallback = Callable[[dict[str, str]], Awaitable[None]]


class LegrandPrivateApiError(Exception):
    """Base private API error."""


class LegrandPrivateApiAuthenticationError(LegrandPrivateApiError):
    """Private API authentication error."""


class LegrandPrivateApiRateLimitError(LegrandPrivateApiError):
    """Private API rate limit exceeded."""


class LegrandPrivateApi:
    """Client for the private Netatmo API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        web_token: str,
        *,
        refresh_token: str | None = None,
        laravel_session: str | None = None,
        mail_cookie: str | None = None,
        authorize_state: str | None = None,
        state_cookie: str | None = None,
        xsrf_token: str | None = None,
        auth_update_callback: PrivateAuthUpdateCallback | None = None,
    ) -> None:
        """Initialize the private API client."""
        self._session = session
        self._web_token = web_token

        self._refresh_token = refresh_token
        self._laravel_session = laravel_session
        self._mail_cookie = mail_cookie
        self._authorize_state = authorize_state
        self._state_cookie = state_cookie
        self._xsrf_token = xsrf_token

        self._auth_update_callback = auth_update_callback
        self._refresh_lock = asyncio.Lock()

    @property
    def web_token(self) -> str:
        """Return the current private web token."""
        return self._web_token

    def set_web_token(self, web_token: str) -> None:
        """Replace the private web token in memory."""
        self._web_token = web_token

    def _headers(self) -> dict[str, str]:
        """Return private API request headers."""
        return {
            "Authorization": f"Bearer {self._web_token}",
            "Accept": "application/json",
        }

    def _can_refresh(self) -> bool:
        """Return whether enough private authentication data is available."""
        return all(
            (
                self._refresh_token,
                self._laravel_session,
                self._mail_cookie,
                self._authorize_state,
                self._state_cookie,
                self._xsrf_token,
            )
        )

    async def _get(
        self,
        base_url: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        retry_auth: bool = True,
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
                    if retry_auth and self._can_refresh():
                        await self.refresh_web_token()

                        return await self._get(
                            base_url,
                            endpoint,
                            params,
                            retry_auth=False,
                        )

                    raise LegrandPrivateApiAuthenticationError(
                        f"Private API request to {endpoint} "
                        f"failed with HTTP status {response.status}"
                    )

                if response.status == 429:
                    response_text = await response.text()

                    raise LegrandPrivateApiRateLimitError(
                        f"Private API rate limit exceeded for {endpoint}: "
                        f"{response_text[:300]}"
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

        if data.get("status") == "error":
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} "
                f"returned an API error: {data.get('error')}"
            )

        return cast(dict[str, Any], data)

    async def homestatus(self, home_id: str) -> dict[str, Any]:
        """Return the current private home status."""
        return await self._get(
            APP_API_BASE,
            "homestatus",
            {"home_id": home_id},
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
            "modules": [module_payload],
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

    async def getcontracts(self, home_id: str) -> dict[str, Any]:
        """Return the electricity contract."""
        return await self._get(
            APP_API_BASE,
            "getcontracts",
            {"home_id": home_id},
        )

    async def test_keychain(self) -> None:
        """Test Netatmo keychain flow without changing current auth data."""
        if not self._can_refresh():
            raise LegrandPrivateApiAuthenticationError(
                "Netatmo keychain test credentials are incomplete"
            )

        assert self._refresh_token is not None
        assert self._laravel_session is not None
        assert self._mail_cookie is not None
        assert self._authorize_state is not None
        assert self._state_cookie is not None
        assert self._xsrf_token is not None

        cookies = {
            "authnetatmocomrefresh_token": self._refresh_token,
            "authnetatmocomlaravel_session": self._laravel_session,
            "authnetatmocommail_cookie": self._mail_cookie,
            "authnetatmocomauthorize_state": self._authorize_state,
            "authnetatmocomstate": self._state_cookie,
            "XSRF-TOKEN": self._xsrf_token,
            "netatmocomlocale": "fr-FR",
        }

        url = f"{AUTH_BASE}/access/keychain?next_url=https%3A%2F%2Fhome.netatmo.com"

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
                    "User-Agent": USER_AGENT,
                },
            ) as response:
                _LOGGER.warning(
                    "KEYCHAIN status=%s location=%s cookies=%s",
                    response.status,
                    response.headers.get("Location"),
                    list(response.cookies.keys()),
                )

        except TimeoutError as err:
            raise LegrandPrivateApiError("Netatmo keychain test timed out") from err

        except aiohttp.ClientError as err:
            raise LegrandPrivateApiError(
                f"Netatmo keychain test failed: {err}"
            ) from err

    async def refresh_web_token(self) -> str:
        """Refresh the Netatmo private web access token."""
        async with self._refresh_lock:
            if not self._can_refresh():
                raise LegrandPrivateApiAuthenticationError(
                    "Netatmo private refresh credentials are incomplete"
                )

            assert self._refresh_token is not None
            assert self._laravel_session is not None
            assert self._mail_cookie is not None
            assert self._authorize_state is not None
            assert self._state_cookie is not None
            assert self._xsrf_token is not None

            cookies = {
                "authnetatmocomrefresh_token": self._refresh_token,
                "authnetatmocomlaravel_session": self._laravel_session,
                "authnetatmocommail_cookie": self._mail_cookie,
                "authnetatmocomauthorize_state": self._authorize_state,
                "authnetatmocomstate": self._state_cookie,
                "XSRF-TOKEN": self._xsrf_token,
                "netatmocomlocale": "fr-FR",
            }

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
                        "User-Agent": USER_AGENT,
                    },
                ) as response:
                    access_cookie = response.cookies.get("netatmocomaccess_token")

                    _LOGGER.warning(
                        "checklogin HTTP=%s Location=%s",
                        response.status,
                        response.headers.get("Location"),
                    )

                    if access_cookie is None:
                        raise LegrandPrivateApiAuthenticationError(
                            "Netatmo checklogin did not return netatmocomaccess_token"
                        )

                    new_web_token = unquote(str(access_cookie.value))

                    _LOGGER.warning(
                        "Netatmo refresh diagnostics: "
                        "length=%s deleted=%s prefix=%s suffix=%s",
                        len(new_web_token),
                        new_web_token.casefold() == "deleted",
                        new_web_token[:6],
                        new_web_token[-4:],
                    )

                    if new_web_token.casefold() == "deleted" or len(new_web_token) < 20:
                        raise LegrandPrivateApiAuthenticationError(
                            "Netatmo did not return a valid web access token"
                        )

                    self._update_rotated_cookies(response.cookies)

            except LegrandPrivateApiError:
                raise

            except TimeoutError as err:
                raise LegrandPrivateApiError(
                    "Netatmo web-token refresh timed out"
                ) from err

            except aiohttp.ClientError as err:
                raise LegrandPrivateApiError(
                    f"Netatmo web-token refresh failed: {err}"
                ) from err

            self.set_web_token(new_web_token)
            await self._persist_private_auth()

            _LOGGER.info("Netatmo private web token refreshed successfully")

            return new_web_token

    def _update_rotated_cookies(
        self,
        response_cookies: Mapping[str, Morsel[str]],
    ) -> None:
        """Update private session cookies returned by Netatmo."""
        cookie_mapping = {
            "authnetatmocomrefresh_token": "_refresh_token",
            "authnetatmocomlaravel_session": "_laravel_session",
            "authnetatmocommail_cookie": "_mail_cookie",
            "authnetatmocomauthorize_state": "_authorize_state",
            "authnetatmocomstate": "_state_cookie",
            "XSRF-TOKEN": "_xsrf_token",
        }

        for cookie_name, attribute_name in cookie_mapping.items():
            cookie = response_cookies.get(cookie_name)

            if cookie is None:
                continue

            value = str(cookie.value)

            if not value or value.casefold() == "deleted":
                continue

            setattr(self, attribute_name, value)

    async def _persist_private_auth(self) -> None:
        """Persist the current private authentication state."""
        if self._auth_update_callback is None:
            return

        auth_data = {"web_token": self._web_token}

        optional_values = {
            "refresh_token_web": self._refresh_token,
            "laravel_session": self._laravel_session,
            "mail_cookie": self._mail_cookie,
            "authorize_state": self._authorize_state,
            "state_cookie": self._state_cookie,
            "xsrf_token": self._xsrf_token,
        }

        auth_data.update(
            {key: value for key, value in optional_values.items() if value is not None}
        )

        await self._auth_update_callback(auth_data)
