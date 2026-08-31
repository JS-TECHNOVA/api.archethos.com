"""
Email authentication for Django's built-in User.

auth.User keys on `username`, but the CMS logs in with an email address. This
backend resolves the email to a user; a case-insensitive unique index on
auth_user.email (accounts/migrations/0001) guarantees that resolution is
unambiguous.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if not email or not password:
            return None

        try:
            user = UserModel._default_manager.get(email__iexact=email)
        except UserModel.DoesNotExist:
            # Run the hasher anyway so a missing account and a wrong password
            # take the same amount of time (no user enumeration by timing).
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Should be impossible given the unique index, but never guess which
            # account was meant.
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
