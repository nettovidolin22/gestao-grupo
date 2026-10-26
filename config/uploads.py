from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class LimiteUpload(FileUploadHandler):
    """Para de receber o envio quando passa do limite.

    O middleware LimiteTamanhoRequisicao barra pelo tamanho declarado; este cobre
    envios sem tamanho declarado (transferência em partes), que encheriam o disco.
    """

    def __init__(self, request=None):
        super().__init__(request)
        self.recebido = 0

    def receive_data_chunk(self, raw_data, start):
        self.recebido += len(raw_data)
        if self.recebido > settings.TAMANHO_MAXIMO_REQUISICAO:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None
