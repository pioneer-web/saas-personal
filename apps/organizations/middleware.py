class CurrentOrganizationMiddleware:
    """Define request.organization e request.membership."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.membership = None

        if getattr(request, "user", None) and request.user.is_authenticated:
            membership = (
                request.user.memberships
                .filter(is_active=True, organization__is_active=True)
                .select_related("organization")
                .order_by("created_at")
                .first()
            )

            if membership:
                request.membership = membership
                request.organization = membership.organization

        return self.get_response(request)
