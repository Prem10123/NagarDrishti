from io import BytesIO

from fastapi import UploadFile
from PIL import Image, ImageFile, UnidentifiedImageError

from .. import config

ImageFile.LOAD_TRUNCATED_IMAGES = False
Image.MAX_IMAGE_PIXELS = 20_000_000
_ALLOWED = {"JPEG", "PNG", "WEBP"}


class ImageRejected(ValueError):
    pass


def compress_upload(upload: UploadFile) -> bytes:
    raw = upload.file.read(config.MAX_UPLOAD_BYTES + 1)
    if not raw:
        raise ImageRejected("Please attach a photo.")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise ImageRejected("Photo is too large. Use an image under 8 MB.")
    try:
        with Image.open(BytesIO(raw)) as probe:
            probe.verify()
            fmt = probe.format
        with Image.open(BytesIO(raw)) as img:
            if fmt not in _ALLOWED and img.format not in _ALLOWED:
                raise ImageRejected("Use a JPEG, PNG, or WebP photo.")
            img = img.convert("RGB")
            img.thumbnail((1280, 1280))
            out = BytesIO()
            img.save(out, format="JPEG", quality=80, optimize=True)
            return out.getvalue()
    except ImageRejected:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise ImageRejected("That file is not a valid photo.")
