"""Cloudinary storage integration for BrandSentinel AI."""

from pathlib import Path

import cloudinary
import cloudinary.uploader
import cloudinary.api
import httpx

from app.config import settings


def configure_cloudinary():
    """Configure Cloudinary using environment variables."""

    if not all([
        settings.cloudinary_cloud_name,
        settings.cloudinary_api_key,
        settings.cloudinary_api_secret,
    ]):
        raise RuntimeError("Cloudinary credentials are not configured.")

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def upload_document(file_path, public_id):
    """Upload a document as a raw Cloudinary resource."""

    configure_cloudinary()

    result = cloudinary.uploader.upload(
        str(file_path),
        resource_type="raw",
        public_id=public_id,
        folder="brandsentinel/documents",
        overwrite=False,
    )

    return {
        "public_id": result["public_id"],
        "secure_url": result["secure_url"],
    }


def download_document(public_id, destination_path):
    """Download a raw document from Cloudinary to a local path."""

    configure_cloudinary()

    resource = cloudinary.api.resource(
        public_id,
        resource_type="raw",
    )

    secure_url = resource["secure_url"]

    destination_path = Path(destination_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(
        follow_redirects=True,
        timeout=60.0
    ) as client:
        response = client.get(secure_url)
        response.raise_for_status()

        destination_path.write_bytes(response.content)

    return destination_path


def delete_document(public_id):
    """Delete a document from Cloudinary."""

    configure_cloudinary()

    return cloudinary.uploader.destroy(
        public_id,
        resource_type="raw",
    )