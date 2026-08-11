from rest_framework.authentication import SessionAuthentication


class StrictSessionAuthentication(SessionAuthentication):
    """Require CSRF for every unsafe session-oriented request, including login."""

    def authenticate(self, request):
        authenticated = super().authenticate(request)
        if request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"} and authenticated is None:
            self.enforce_csrf(request)
        return authenticated
