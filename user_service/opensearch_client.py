from django.conf import settings
from opensearchpy import OpenSearch

def get_opensearch_client():
    return OpenSearch(
        hosts=[settings.OPENSEARCH_URL],
        use_ssl=False,
        verify_certs=False, # True in prod
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )