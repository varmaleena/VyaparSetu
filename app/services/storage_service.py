"""Private, generation-guarded Cloud Storage writes for invoice images."""

from dataclasses import dataclass

from google.cloud.storage import Bucket

from app.models.invoice import InvoiceImage


@dataclass(frozen=True)
class StoredInvoice:
    name: str
    uri: str
    generation: int


class InvoiceStorage:
    def __init__(self, bucket: Bucket) -> None:
        self.bucket = bucket

    def upload(self, intake_id: str, image: InvoiceImage) -> StoredInvoice:
        blob = self.bucket.blob(f"intake/{intake_id}")
        blob.upload_from_string(
            image.content,
            content_type=image.media_type,
            if_generation_match=0,
            timeout=30,
        )
        if blob.generation is None:
            raise RuntimeError("Cloud Storage did not return an object generation")
        return StoredInvoice(
            blob.name, f"gs://{self.bucket.name}/{blob.name}", int(blob.generation)
        )

    def delete(self, stored: StoredInvoice) -> None:
        blob = self.bucket.blob(stored.name, generation=stored.generation)
        blob.delete(if_generation_match=stored.generation, timeout=15)
