from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

from .audit import audit_actor


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_NAME)
        if raw_token:
            validated_token = self.get_validated_token(raw_token)
            result = self.get_user(validated_token), validated_token
        else:
            result = super().authenticate(request)

        if result and request.method in {"POST", "PUT", "PATCH", "DELETE"} and result[0].is_staff:
            audit_actor.set(result[0])
        return result
