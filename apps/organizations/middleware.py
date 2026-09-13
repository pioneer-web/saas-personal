class CurrentOrganizationMiddleware:
    """Define request.organization com base na primeira associação ativa do usuário.

    Na Etapa 2 poderemos adicionar seletor de organização caso um usuário participe de mais de uma.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        if getattr(request, "user", None) and request.user.is_authenticated:
            membership = (
                request.user.memberships
                .filter(is_active=True, organization__is_active=True)
                .select_related("organization")
                .first()
            )
            if membership:
                request.organization = membership.organization
        return self.get_response(request)
