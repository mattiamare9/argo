import httpx

from app.core.config import Settings
from app.modules.identity.keycloak_adapter import KeycloakIdentityProvider
from app.modules.identity.ports import IdentityError, IdentityProvider


def build_identity_provider(settings: Settings, http: httpx.AsyncClient) -> IdentityProvider:
    """Unico punto che sceglie l'implementazione della porta (oggi Keycloak)."""
    secret = settings.keycloak_backend_client_secret
    if secret is None:
        raise IdentityError("ARGO_KEYCLOAK_BACKEND_CLIENT_SECRET non configurato")
    return KeycloakIdentityProvider(
        base_url=settings.keycloak_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_backend_client_id,
        client_secret=secret.get_secret_value(),
        http=http,
    )
