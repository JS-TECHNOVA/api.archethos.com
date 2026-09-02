"""
Login by email *or* username, through one input field.

The CMS login form has a single "Email or username" box. Rather than trying both
columns and hoping, the identifier is inspected first: if it looks like an email
address it is matched against `email`, otherwise against `username`.

Deciding up front matters for more than tidiness. Falling through both columns
means a user whose *username* happens to be "someone@example.com" could shadow a
different account's *email* — the regex removes that ambiguity entirely.
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()

#: Deliberately permissive. This only decides *which column to query* — it is not
#: an address validator, and rejecting an unusual-but-real address here would
#: lock someone out. Real validation happens when the account is created.
EMAIL_SHAPED = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def looks_like_email(identifier):
    return bool(EMAIL_SHAPED.match((identifier or "").strip()))


class EmailOrUsernameBackend(ModelBackend):
    """Resolve one identifier to a user, by email or by username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # The login serializer sends the value as `username`; Django Admin and
        # `createsuperuser` also use `username`. `email` is accepted so an older
        # caller passing that key keeps working.
        identifier = (kwargs.get("email") or username or "").strip()
        if not identifier or not password:
            return None

        lookup = "email__iexact" if looks_like_email(identifier) else "username__iexact"

        try:
            user = UserModel._default_manager.get(**{lookup: identifier})
        except UserModel.DoesNotExist:
            # Hash anyway so a missing account and a wrong password take the same
            # time — otherwise the response time reveals which accounts exist.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Should be unreachable: username is unique, and email has a
            # case-insensitive unique index. Never guess which account was meant.
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
