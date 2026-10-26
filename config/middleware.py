from django.conf import settings
from django.http import HttpResponse


class LimiteTamanhoRequisicao:
    """Recusa envios gigantes logo na entrada, antes de o Django gravar o arquivo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            tamanho = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            tamanho = 0
        if tamanho > settings.TAMANHO_MAXIMO_REQUISICAO:
            limite = settings.TAMANHO_MAXIMO_ANEXO // (1024 * 1024)
            return HttpResponse(f"Arquivo grande demais. O limite é {limite} MB.", status=413)
        return self.get_response(request)
