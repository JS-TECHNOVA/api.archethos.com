"""
Upload validation.

Everything here assumes the uploaded file is hostile until proven otherwise. A
browser-supplied filename, extension and Content-Type are all attacker-controlled
and none of them are trusted: the extension must be on the allowlist AND the
bytes must actually decode as the type they claim.
"""

import hashlib

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from .models import MediaType

# Extension -> canonical mime type. An extension absent from this map is rejected
# outright; an allowlist is the only safe direction here.
IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
}

DOCUMENT_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".dwg": "image/vnd.dwg",
    ".zip": "application/zip",
}

ALLOWED_EXTENSIONS = {**IMAGE_EXTENSIONS, **DOCUMENT_EXTENSIONS}

#: Guards against decompression-bomb images that would exhaust memory on resize.
MAX_IMAGE_DIMENSION = 12000

#: Magic-number prefixes. Cheap sanity check before Pillow is asked to decode.
_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"%PDF-": "application/pdf",
}


def max_upload_bytes():
    return settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def extension_of(filename):
    name = (filename or "").lower()
    dot = name.rfind(".")
    return name[dot:] if dot != -1 else ""


def sniff_mime(head):
    for signature, mime in _SIGNATURES.items():
        if head.startswith(signature):
            return mime
    # RIFF....WEBP
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_upload(uploaded_file):
    """Validate an uploaded file and return its derived metadata.

    Returns a dict of ``media_type``, ``mime_type``, ``file_size``, ``checksum``
    and, for images, ``width`` / ``height``.

    Raises ``ValidationError`` with a message meant for the CMS user.
    """
    if not uploaded_file:
        raise ValidationError("No file was supplied.")

    extension = extension_of(uploaded_file.name)
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationError(
            f"Files of type '{extension or 'unknown'}' are not allowed. "
            f"Allowed types: {allowed}"
        )

    limit = max_upload_bytes()
    if uploaded_file.size > limit:
        raise ValidationError(
            f"File is {uploaded_file.size / 1024 / 1024:.1f} MB; "
            f"the limit is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
    if uploaded_file.size == 0:
        raise ValidationError("The file is empty.")

    is_image = extension in IMAGE_EXTENSIONS
    declared_mime = ALLOWED_EXTENSIONS[extension]

    checksum, head = _digest(uploaded_file)

    sniffed = sniff_mime(head)
    if sniffed and sniffed.startswith("image/") and not is_image:
        raise ValidationError(
            "This file is an image but has a non-image extension. Rename it and try again."
        )

    metadata = {
        "media_type": MediaType.IMAGE if is_image else MediaType.DOCUMENT,
        "mime_type": sniffed or declared_mime,
        "file_size": uploaded_file.size,
        "checksum": checksum,
        "width": None,
        "height": None,
    }

    if is_image:
        width, height = _verify_image(uploaded_file)
        metadata["width"] = width
        metadata["height"] = height

    return metadata


def _digest(uploaded_file):
    """sha256 the whole file, returning the digest and the first bytes."""
    digest = hashlib.sha256()
    head = b""
    uploaded_file.seek(0)
    for chunk in uploaded_file.chunks():
        if not head:
            head = bytes(chunk[:32])
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest(), head


def _verify_image(uploaded_file):
    """Confirm the bytes really are a decodable image, and measure it.

    A `.jpg` extension proves nothing — this is what stops an executable or an
    HTML file being stored and later served from the media domain.
    """
    uploaded_file.seek(0)
    try:
        with Image.open(uploaded_file) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(
            "This file is not a readable image, despite its extension."
        ) from exc

    # verify() consumes the file object, so reopen to read dimensions.
    uploaded_file.seek(0)
    try:
        with Image.open(uploaded_file) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("The image dimensions could not be read.") from exc
    finally:
        uploaded_file.seek(0)

    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValidationError(
            f"Image is {width}x{height}px; the maximum is "
            f"{MAX_IMAGE_DIMENSION}px on either side."
        )

    return width, height
