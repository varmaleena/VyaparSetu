"""Storage writes for invoice images with Cloud Storage and local demo fallback."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.invoice import InvoiceImage


@dataclass(frozen=True)
class StoredInvoice:
    name: str
    uri: str
    generation: int


class InvoiceStorage:
    def __init__(self, bucket: Any = None, local_dir: str = "./data/invoices") -> None:
        self.bucket = bucket
        self.local_dir = Path(local_dir)
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, intake_id: str, image: InvoiceImage) -> StoredInvoice:
        if self.bucket is not None:
            try:
                blob = self.bucket.blob(f"intake/{intake_id}")
                blob.upload_from_string(
                    image.content,
                    content_type=image.media_type,
                    if_generation_match=0,
                    timeout=30,
                )
                if blob.generation is not None:
                    return StoredInvoice(
                        blob.name,
                        f"gs://{self.bucket.name}/{blob.name}",
                        int(blob.generation),
                    )
            except Exception:
                pass  # Fall back to local storage seamlessly

        # Local storage fallback
        file_path = self.local_dir / f"{intake_id}.bin"
        file_path.write_bytes(image.content)
        return StoredInvoice(
            name=f"local/{intake_id}",
            uri=f"file://{file_path.resolve()}",
            generation=1,
        )

    def delete(self, stored: StoredInvoice) -> None:
        if self.bucket is not None and not stored.uri.startswith("file://"):
            try:
                blob = self.bucket.blob(stored.name, generation=stored.generation)
                blob.delete(if_generation_match=stored.generation, timeout=15)
                return
            except Exception:
                pass
        local_path = self.local_dir / f"{stored.name.split('/')[-1]}.bin"
        if local_path.exists():
            local_path.unlink()

