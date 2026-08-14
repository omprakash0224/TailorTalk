from dotenv import load_dotenv
import os
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

load_dotenv()
client = QdrantClient(url=os.environ.get("QDRANT_URL"), api_key=os.environ.get("QDRANT_API_KEY"))
client.create_payload_index(collection_name="sarees", field_name="discounted_price", field_schema=PayloadSchemaType.FLOAT)
print("Index created successfully!")
