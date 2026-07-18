from django.core.management.base import BaseCommand
from opensearch_client import get_opensearch_client

class Command(BaseCommand):
    help = "Initializes Opensearch indices"
    
    def handle(self, *args, **options):
        client = get_opensearch_client()
        index_name = "jobs"
        
        index_body = {
            "settings": {
                "index": {"number_of_shards": 1, "number_of_replicas": 1}
            },
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "text", "analyzer": "standard"},
                    "description": {"type": "text", "analyzer": "standard"},
                    "department": {"type": "keyword"},
                    "is_active": {"type": "boolean"},  # e.g., True, False
                    "created_at": {"type": "date"}
                }
            }
        }
        
        if not client.indices.exists(index=index_name):
            client.indices.create(index=index_name, body=index_body)
            self.stdout.write(self.style.SUCCESS(f"Index '{index_name}' created successfully."))
        else:
            self.stdout.write(f"Index '{index_name}' already exists.")