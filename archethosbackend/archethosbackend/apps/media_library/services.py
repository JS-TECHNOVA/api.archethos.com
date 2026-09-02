"""
Replacing an asset's file in place.

Swaps the bytes behind an existing asset while keeping its identity: same id,
same stored path, same descriptive fields. Every page referencing it keeps
working and nothing has to be repointed — which is the entire reason to have
this rather than "upload a new one and update 40 references".

Only the file and the metadata derived from it change:

    kept        id · path · title · alt_text · caption · description · tags
    replaced    the bytes on disk
    recomputed  file_size · mime_type · width · height · checksum · file_name
"""

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction

from .models import MediaAsset, SourceType
from .validators import extension_of, validate_upload


def replace_file(asset, uploaded_file):
    """Overwrite `asset`'s file with `uploaded_file`.

    Raises ``ValidationError`` with a message meant for the CMS user.
    """
    if asset.source_type != SourceType.UPLOAD:
        # A YouTube asset has no file to replace; its URL is the content.
        raise ValidationError(
            "This asset is an external video, not an uploaded file. "
            "Delete it and add the new video instead."
        )

    if not asset.file:
        raise ValidationError("This asset has no stored file to replace.")

    new_extension = extension_of(uploaded_file.name)
    if new_extension != asset.extension:
        # The path is being kept, so a .jpg written to a .png path would be
        # served under the wrong extension for the rest of its life. Refuse it
        # rather than quietly creating that.
        raise ValidationError(
            f"The replacement must be a {asset.extension} file to keep the same "
            f"path; this one is {new_extension or 'an unknown type'}. Upload it "
            "as a new asset if the format has changed."
        )

    # Same rules as a first upload: bytes are verified, not just the filename.
    metadata = validate_upload(uploaded_file)

    if metadata["media_type"] != asset.media_type:
        raise ValidationError(
            f"This asset is {asset.get_media_type_display().lower()}; the "
            f"replacement is not."
        )

    stored_name = asset.file.name

    with transaction.atomic():
        # Delete then save under the exact name. `save()` alone would find the
        # name taken and quietly append a suffix, leaving the original bytes in
        # place and the asset pointing at a file nobody replaced.
        if default_storage.exists(stored_name):
            default_storage.delete(stored_name)

        written_name = default_storage.save(stored_name, uploaded_file)
        if written_name != stored_name:
            # Storage refused the exact name. Undo rather than leave two files
            # and an asset row pointing at the stale one.
            default_storage.delete(written_name)
            raise ValidationError(
                "The file could not be written to its original path. "
                "Nothing was changed."
            )

        asset.file_name = uploaded_file.name[:255]
        asset.file_size = metadata["file_size"]
        asset.mime_type = metadata["mime_type"]
        asset.width = metadata["width"]
        asset.height = metadata["height"]
        asset.checksum = metadata["checksum"]
        asset.save(
            update_fields=[
                "file_name",
                "file_size",
                "mime_type",
                "width",
                "height",
                "checksum",
                "updated_at",
            ]
        )

    return asset


def normalise_tags(value, *, limit=25, max_length=50):
    """Lowercase, trim, de-duplicate, and keep the order they were given in.

    Case-folding here means "Villa" and "villa" are one tag rather than two that
    look identical in a filter list.
    """
    if not isinstance(value, list):
        raise ValidationError("Tags must be a list of words.")

    seen = set()
    tags = []
    for entry in value:
        if not isinstance(entry, str):
            raise ValidationError("Each tag must be text.")

        tag = " ".join(entry.strip().lower().split())
        if not tag:
            continue
        if len(tag) > max_length:
            raise ValidationError(f"'{tag[:20]}…' is too long for a tag.")
        if tag in seen:
            continue

        seen.add(tag)
        tags.append(tag)

    if len(tags) > limit:
        raise ValidationError(f"Too many tags (limit {limit}).")
    return tags
