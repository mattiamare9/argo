from app.cli import bootstrap_admin
from app.modules.identity import IdentityUser


class RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def ensure_user(self, user: IdentityUser) -> None:
        self.calls.append(("ensure_user", user.employee_id, user.email))

    async def grant_role(self, employee_id: str, role: str) -> None:
        self.calls.append(("grant_role", employee_id, role))

    async def send_enrollment(self, employee_id: str) -> None:
        self.calls.append(("send_enrollment", employee_id))


async def test_bootstrap_admin_creates_user_grants_role_and_sends_passkey_email() -> None:
    provider = RecordingProvider()
    await bootstrap_admin(provider, IdentityUser("ADMIN", "dev@example.com", "Dev", "Argo"))
    assert provider.calls == [
        ("ensure_user", "ADMIN", "dev@example.com"),
        ("grant_role", "ADMIN", "iam-admin"),
        ("send_enrollment", "ADMIN"),
    ]


async def test_send_invites_reports_who_was_not_reached() -> None:
    from app.cli import send_invites
    from app.modules.identity import UserNotFound

    class Provider:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send_enrollment(self, employee_id: str) -> None:
            if employee_id == "E2":
                raise UserNotFound(employee_id)
            self.sent.append(employee_id)

    provider = Provider()
    assert await send_invites(provider, ["E1", "E2", "E3"]) == ["E2"]
    assert provider.sent == ["E1", "E3"]
