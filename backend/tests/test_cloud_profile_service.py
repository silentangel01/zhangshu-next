"""Tests for ``CloudProfileService`` — service layer orchestration.

Covers ``change_password()`` logout semantics:
- Success: ``auth.change_password`` called, then ``auth.logout`` called.
- Failure: ``auth.change_password`` raises, ``auth.logout`` NOT called.

Also covers simple pass-through methods (``get_profile``, ``update_profile``).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cloud_auth_service import CloudAuthError  # noqa: E402
from app.services.cloud_profile_service import CloudProfileService  # noqa: E402


@pytest.fixture
def mock_auth():
    return MagicMock()


@pytest.fixture
def service(mock_auth):
    return CloudProfileService(mock_auth)


# ── change_password ─────────────────────────────────────────────────


class TestChangePassword:
    def test_success_calls_logout(self, service, mock_auth):
        """After successful password change, local tokens are cleared."""
        mock_auth.change_password.return_value = {"ok": True}

        result = service.change_password("old_pass", "new_pass")

        assert result == {"ok": True}
        mock_auth.change_password.assert_called_once_with("old_pass", "new_pass")
        mock_auth.logout.assert_called_once()

    def test_failure_does_not_logout(self, service, mock_auth):
        """If password change fails, tokens are NOT cleared."""
        mock_auth.change_password.side_effect = CloudAuthError("Wrong password")

        with pytest.raises(CloudAuthError, match="Wrong password"):
            service.change_password("wrong", "new_pass")

        mock_auth.change_password.assert_called_once_with("wrong", "new_pass")
        mock_auth.logout.assert_not_called()

    def test_return_value_passthrough(self, service, mock_auth):
        """Return value from auth service is passed through unchanged."""
        expected = {"changed": True, "message": "密码已更改"}
        mock_auth.change_password.return_value = expected

        result = service.change_password("old", "new")

        assert result is expected


# ── get_profile ──────────────────────────────────────────────────────


class TestGetProfile:
    def test_delegates_to_auth(self, service, mock_auth):
        expected = {"id": "u1", "email": "a@b.com", "display_name": "Test"}
        mock_auth.get_account_profile.return_value = expected

        result = service.get_profile()

        assert result == expected
        mock_auth.get_account_profile.assert_called_once()


# ── update_profile ───────────────────────────────────────────────────


class TestUpdateProfile:
    def test_delegates_with_kwargs(self, service, mock_auth):
        expected = {"id": "u1", "display_name": "New", "signature": "Hi"}
        mock_auth.update_account_profile.return_value = expected

        result = service.update_profile(display_name="New", signature="Hi")

        assert result == expected
        mock_auth.update_account_profile.assert_called_once_with(
            display_name="New", signature="Hi"
        )

    def test_partial_update(self, service, mock_auth):
        mock_auth.update_account_profile.return_value = {"display_name": "Only"}

        service.update_profile(display_name="Only")

        mock_auth.update_account_profile.assert_called_once_with(
            display_name="Only", signature=None
        )


# ── delete_avatar ────────────────────────────────────────────────────


class TestDeleteAvatar:
    def test_delegates_to_auth(self, service, mock_auth):
        mock_auth.delete_avatar.return_value = {"ok": True}

        result = service.delete_avatar()

        assert result == {"ok": True}
        mock_auth.delete_avatar.assert_called_once()
