from rest_framework import serializers

from apps.media_library.models import MediaAsset


class PublicMediaSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = ["id", "source", "thumbnail_url", "media_type", "title", "alt_text"]

    def _url(self, value):
        if not value:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(value) if request else value

    def get_source(self, asset: MediaAsset) -> str | None:
        return self._url(asset.external_url or (asset.file.url if asset.file else None))

    def get_thumbnail_url(self, asset: MediaAsset) -> str | None:
        return self._url(asset.thumbnail_url or (asset.thumbnail_file.url if asset.thumbnail_file else None))
