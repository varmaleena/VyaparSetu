"""Deterministic image checks for a merchant's invoice photo."""

import hashlib
from io import BytesIO

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from app.models.invoice import MAX_INVOICE_BYTES, InvoiceImage

FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MAX_PIXELS = 24_000_000
MIN_EDGE = 480


class InvoiceImageError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_invoice_image(content: bytes) -> InvoiceImage:
    if len(content) > MAX_INVOICE_BYTES:
        raise InvoiceImageError("FILE_TOO_LARGE", "Use an image no larger than 10 MiB.")
    try:
        with Image.open(BytesIO(content)) as source:
            media_type = FORMATS.get(source.format or "")
            if not media_type or getattr(source, "n_frames", 1) != 1:
                raise InvoiceImageError(
                    "UNSUPPORTED_IMAGE", "Upload a single JPEG, PNG, or WebP photo."
                )
            if source.width * source.height > MAX_PIXELS or min(source.size) < MIN_EDGE:
                raise InvoiceImageError(
                    "IMAGE_DIMENSIONS",
                    "Retake the photo with the bill filling the frame.",
                )
            source.verify()
        with Image.open(BytesIO(content)) as source:
            oriented = ImageOps.exif_transpose(source)
            width, height = oriented.size
            preview = oriented.convert("L")
            preview.thumbnail((1024, 1024))
            edges = preview.filter(ImageFilter.FIND_EDGES).crop(
                (1, 1, preview.width - 1, preview.height - 1)
            )
            if ImageStat.Stat(edges).var[0] < 12:
                raise InvoiceImageError(
                    "LOW_IMAGE_DETAIL", "Retake the bill photo in focus and good light."
                )
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
    ) as exc:
        raise InvoiceImageError(
            "UNREADABLE_IMAGE", "Upload a readable photo of the supplier bill."
        ) from exc
    return InvoiceImage(
        content=content,
        media_type=media_type,
        width=width,
        height=height,
        sha256=hashlib.sha256(content).hexdigest(),
    )
