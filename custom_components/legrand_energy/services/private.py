"""Private authentication service for Legrand Energy."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from http.cookies import Morsel
from urllib.parse import unquote

import aiohttp
from yarl import URL

from custom_components.legrand_energy.models.auth import PrivateSession

AUTH_BASE = "https://auth.netatmo.com"
HOME_DASHBOARD_URL = "https://home.netatmo.com/control/dashboard"

API_TIMEOUT = aiohttp.ClientTimeout(total=30)

USER_AGENT = (
    "Mozilla/5.0 "
    "(Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)

REFRESH_TOKEN_COOKIE = "authnetatmocomrefresh_token"
LARAVEL_SESSION_COOKIE = "authnetatmocomlaravel_session"
MAIL_COOKIE = "authnetatmocommail_cookie"
AUTHORIZE_STATE_COOKIE = "authnetatmocomauthorize_state"
XSRF_TOKEN_COOKIE = "XSRF-TOKEN"
LOCALE_COOKIE = "netatmocomlocale"
ACCESS_TOKEN_COOKIE = "netatmocomaccess_token"

REQUIRED_REFRESH_COOKIES: tuple[str, ...] = (
    REFRESH_TOKEN_COOKIE,
    LARAVEL_SESSION_COOKIE,
    MAIL_COOKIE,
    XSRF_TOKEN_COOKIE,
)

DEFAULT_REFRESH_COOKIES: dict[str, str] = {
    LOCALE_COOKIE: "fr-FR",
}


class PrivateAuthServiceError(Exception):
    """Base private authentication service error."""


class PrivateAuthServiceAuthenticationError(PrivateAuthServiceError):
    """Private authentication failed."""


class PrivateAuthServiceInvalidCredentialsError(PrivateAuthServiceAuthenticationError):
    """The Netatmo email address or password is invalid."""


class PrivateAuthServiceCsrfError(PrivateAuthServiceAuthenticationError):
    """The Netatmo CSRF token could not be retrieved."""


class PrivateAuthServiceSessionError(PrivateAuthServiceAuthenticationError):
    """The authenticated private Netatmo session could not be created."""


class PrivateAuthService:
    """Manage authentication against the private Netatmo API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the private authentication service."""
        self._session = session
        self._refresh_lock = asyncio.Lock()

    async def _get_csrf(self) -> str:
        """Retrieve the Netatmo CSRF token."""
        url = f"{AUTH_BASE}/access/csrf"

        try:
            async with self._session.get(
                url,
                timeout=API_TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                    "Referer": f"{AUTH_BASE}/access/login",
                },
            ) as response:
                if response.status != 200:
                    raise PrivateAuthServiceCsrfError(
                        f"Netatmo CSRF request failed with HTTP status "
                        f"{response.status}"
                    )

                try:
                    payload = await response.json()
                except (aiohttp.ContentTypeError, ValueError) as err:
                    raise PrivateAuthServiceCsrfError(
                        "Netatmo CSRF response is not valid JSON"
                    ) from err

        except PrivateAuthServiceError:
            raise

        except TimeoutError as err:
            raise PrivateAuthServiceCsrfError("Netatmo CSRF request timed out") from err

        except aiohttp.ClientError as err:
            raise PrivateAuthServiceCsrfError(
                f"Netatmo CSRF request failed: {err}"
            ) from err

        token = payload.get("token")

        if not isinstance(token, str) or not token.strip():
            raise PrivateAuthServiceCsrfError(
                "Netatmo CSRF response does not contain a valid token"
            )

        return token

    async def _post_login(
        self,
        username: str,
        password: str,
        csrf_token: str,
    ) -> str:
        """Submit the private Netatmo login form and return the redirect URL."""
        url = f"{AUTH_BASE}/access/postlogin"

        try:
            async with self._session.post(
                url,
                params={"next_url": HOME_DASHBOARD_URL},
                data={
                    "email": username,
                    "password": password,
                    "stay_logged": "on",
                    "_token": csrf_token,
                },
                allow_redirects=False,
                timeout=API_TIMEOUT,
                headers={
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "Origin": AUTH_BASE,
                    "Referer": f"{AUTH_BASE}/access/login",
                    "User-Agent": USER_AGENT,
                },
            ) as response:
                if response.status in {401, 403}:
                    raise PrivateAuthServiceInvalidCredentialsError(
                        "Netatmo rejected the private authentication credentials"
                    )

                if response.status == 200:
                    raise PrivateAuthServiceInvalidCredentialsError(
                        "Netatmo did not accept the private authentication credentials"
                    )

                if response.status not in {301, 302, 303, 307, 308}:
                    raise PrivateAuthServiceAuthenticationError(
                        "Netatmo private login failed with HTTP status "
                        f"{response.status}"
                    )

                location = response.headers.get("Location")

                if not location:
                    raise PrivateAuthServiceSessionError(
                        "Netatmo private login did not return a redirect URL"
                    )

                redirect_url = str(
                    URL(f"{AUTH_BASE}/access/postlogin").join(URL(location))
                )

                if "/access/keychain" not in redirect_url:
                    raise PrivateAuthServiceInvalidCredentialsError(
                        "Netatmo private login did not redirect to the keychain"
                    )

                return redirect_url

        except PrivateAuthServiceError:
            raise

        except TimeoutError as err:
            raise PrivateAuthServiceError(
                "Netatmo private login request timed out"
            ) from err

        except aiohttp.ClientError as err:
            raise PrivateAuthServiceError(
                f"Netatmo private login request failed: {err}"
            ) from err

    async def _complete_keychain(self, keychain_url: str) -> None:
        """Complete the Netatmo keychain authentication step."""
        try:
            async with self._session.get(
                keychain_url,
                allow_redirects=True,
                timeout=API_TIMEOUT,
                headers={
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "Referer": f"{AUTH_BASE}/access/login",
                    "User-Agent": USER_AGENT,
                },
            ) as response:
                if response.status != 200:
                    raise PrivateAuthServiceSessionError(
                        "Netatmo keychain request failed with HTTP status "
                        f"{response.status}"
                    )

                if "/access/keychain" not in response.url.path:
                    raise PrivateAuthServiceSessionError(
                        "Netatmo keychain request ended on an unexpected page"
                    )

        except PrivateAuthServiceError:
            raise

        except TimeoutError as err:
            raise PrivateAuthServiceSessionError(
                "Netatmo keychain request timed out"
            ) from err

        except aiohttp.ClientError as err:
            raise PrivateAuthServiceSessionError(
                f"Netatmo keychain request failed: {err}"
            ) from err

    def _extract_session_cookies(self) -> dict[str, str]:
        """Extract private authentication cookies from the session cookie jar."""
        cookies: dict[str, str] = {}

        for url in (
            URL(AUTH_BASE),
            URL("https://home.netatmo.com"),
            URL("https://app.netatmo.net"),
        ):
            for name, morsel in self._session.cookie_jar.filter_cookies(url).items():
                value = str(morsel.value)

                if value and value.casefold() != "deleted":
                    cookies[name] = value

        missing = [
            cookie_name
            for cookie_name in REQUIRED_REFRESH_COOKIES
            if not cookies.get(cookie_name)
        ]

        if missing:
            raise PrivateAuthServiceSessionError(
                "Netatmo private session is missing required authentication cookies: "
                + ", ".join(missing)
            )

        return cookies

    def _extract_web_token(self, cookies: Mapping[str, str]) -> str:
        """Extract and validate the private Netatmo web access token."""
        raw_token = cookies.get(ACCESS_TOKEN_COOKIE)

        if raw_token is None:
            home_cookies = self._session.cookie_jar.filter_cookies(
                URL("https://home.netatmo.com")
            )
            access_cookie = home_cookies.get(ACCESS_TOKEN_COOKIE)

            if access_cookie is not None:
                raw_token = str(access_cookie.value)

        if raw_token is None:
            app_cookies = self._session.cookie_jar.filter_cookies(
                URL("https://app.netatmo.net")
            )
            access_cookie = app_cookies.get(ACCESS_TOKEN_COOKIE)

            if access_cookie is not None:
                raw_token = str(access_cookie.value)

        if raw_token is None:
            raise PrivateAuthServiceSessionError(
                f"Netatmo private session does not contain {ACCESS_TOKEN_COOKIE}"
            )

        web_token = unquote(raw_token)

        if web_token.casefold() == "deleted" or len(web_token) < 20:
            raise PrivateAuthServiceSessionError(
                "Netatmo private session contains an invalid web access token"
            )

        return web_token

    async def login(
        self,
        username: str,
        password: str,
    ) -> PrivateSession:
        """Authenticate against the private Netatmo API."""
        csrf_token = await self._get_csrf()
        keychain_url = await self._post_login(
            username,
            password,
            csrf_token,
        )

        await self._complete_keychain(keychain_url)

        cookies = self._extract_session_cookies()
        web_token = self._extract_web_token(cookies)

        return PrivateSession(
            web_token=web_token,
            cookies=cookies,
        )

    async def refresh(
        self,
        session: PrivateSession,
    ) -> None:
        """Refresh an existing private Netatmo session."""
        async with self._refresh_lock:
            if not self._can_refresh(session):
                raise PrivateAuthServiceAuthenticationError(
                    "Netatmo private refresh credentials are incomplete"
                )

            cookies = self._build_refresh_cookies(session)

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
                    access_cookie = response.cookies.get(ACCESS_TOKEN_COOKIE)

                    if access_cookie is None:
                        home_cookies = self._session.cookie_jar.filter_cookies(
                            URL("https://home.netatmo.com")
                        )
                        access_cookie = home_cookies.get(ACCESS_TOKEN_COOKIE)

                    if access_cookie is None:
                        raise PrivateAuthServiceAuthenticationError(
                            f"Netatmo checklogin did not return {ACCESS_TOKEN_COOKIE}"
                        )

                    new_web_token = unquote(str(access_cookie.value))

                    if new_web_token.casefold() == "deleted" or len(new_web_token) < 20:
                        raise PrivateAuthServiceAuthenticationError(
                            "Netatmo did not return a valid web access token"
                        )

                    self._update_rotated_cookies(
                        session,
                        response.cookies,
                    )

            except PrivateAuthServiceError:
                raise

            except TimeoutError as err:
                raise PrivateAuthServiceError(
                    "Netatmo web-token refresh timed out"
                ) from err

            except aiohttp.ClientError as err:
                raise PrivateAuthServiceError(
                    f"Netatmo web-token refresh failed: {err}"
                ) from err

            session.web_token = new_web_token

    @staticmethod
    def _can_refresh(session: PrivateSession) -> bool:
        """Return whether the session contains all refresh cookies."""
        return all(
            bool(session.cookies.get(cookie_name))
            for cookie_name in REQUIRED_REFRESH_COOKIES
        )

    @staticmethod
    def _build_refresh_cookies(
        session: PrivateSession,
    ) -> dict[str, str]:
        """Build cookies required to refresh the private session."""
        cookies = {
            cookie_name: session.cookies[cookie_name]
            for cookie_name in REQUIRED_REFRESH_COOKIES
            if session.cookies.get(cookie_name)
        }

        cookies.update(DEFAULT_REFRESH_COOKIES)

        return cookies

    @staticmethod
    def _update_rotated_cookies(
        session: PrivateSession,
        response_cookies: Mapping[str, Morsel[str]],
    ) -> None:
        """Update private session cookies returned by Netatmo."""
        for cookie_name in REQUIRED_REFRESH_COOKIES:
            cookie = response_cookies.get(cookie_name)

            if cookie is None:
                continue

            value = str(cookie.value)

            if not value or value.casefold() == "deleted":
                continue

            session.cookies[cookie_name] = value
