import io
import logging
import statistics
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

import imagehash
import pillow_avif
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.models import ImageCache
from app.models.models import VisionIngredient, VisionResult

logger = logging.getLogger(__name__)


class ImageCacheService:

    def __init__(self, db: Session, hash_threshold: Optional[int] = None):
        self.db = db
        if hash_threshold is not None:
            self.hash_threshold = hash_threshold
        else:
            self.hash_threshold = get_settings().hash_threshold
        logger.debug(
            f"ImageCacheService initialized with threshold: {self.hash_threshold}"
        )

    def get(self, image_data: bytes) -> Tuple[Optional[VisionResult], bool]:
        if not get_settings().image_cache_enabled:
            return None, False

        hashes = self._generate_perceptual_hashes(image_data)
        if not hashes:
            logger.warning("Could not generate perceptual hash for the image.")
            return None, False

        similar_image, similarity = self._find_similar_image(hashes)

        if similar_image and similarity <= self.hash_threshold:
            logger.info(
                f"Found similar image (ID: {similar_image.id}) with similarity "
                f"{similarity} (threshold: {self.hash_threshold}). Returning from cache."
            )
            self._update_access_stats(similar_image)

            ingredients_data = similar_image.ingredients
            if ingredients_data is not None:
                if isinstance(ingredients_data, list):
                    ingredients = [VisionIngredient(**ing) for ing in ingredients_data]
                    result = VisionResult(ingredients=ingredients)
                    return result, True

        elif similar_image:
            logger.info(
                f"Found image with similarity {similarity}, but it is outside the "
                f"threshold of {self.hash_threshold}. Treating as a cache miss."
            )

        logger.info("No similar image found in cache. Analysis should proceed.")
        return None, False

    def set(
        self,
        image_data: bytes,
        image_format: str,
        analysis_result: VisionResult,
    ) -> Optional[ImageCache]:
        hashes = self._generate_perceptual_hashes(image_data)
        if not hashes:
            return None

        cache_entry_data = self._prepare_cache_data(
            hashes=hashes,
            image_data=image_data,
            analysis_result=analysis_result,
            image_format=image_format,
        )

        if not cache_entry_data:
            return None

        cache_entry = ImageCache(**cache_entry_data)
        self.db.add(cache_entry)
        self.db.flush()
        logger.info(
            f"Successfully staged new image analysis for caching. Cache ID will be {cache_entry.id}"
        )
        return cache_entry

    def _find_similar_image(self, hashes: dict) -> Tuple[Optional[ImageCache], int]:
        new_phash = hashes.get("perceptual_hash")
        if not new_phash:
            return None, self.hash_threshold + 1

        exact_match = (
            self.db.query(ImageCache)
            .filter(ImageCache.perceptual_hash == new_phash)
            .first()
        )
        if exact_match:
            return exact_match, 0

        all_hashes_query = select(ImageCache.id, ImageCache.perceptual_hash)
        streamed_hashes = self.db.execute(all_hashes_query)

        best_match_id = None
        best_similarity = self.hash_threshold + 1

        for img_id, cached_phash in streamed_hashes:
            similarity = self._calculate_hash_similarity(cached_phash, new_phash)
            if similarity < best_similarity:
                best_similarity = similarity
                best_match_id = img_id
                if best_similarity == 0:
                    break

        if best_match_id is not None:
            best_match_object = self.db.get(ImageCache, best_match_id)
            return best_match_object, best_similarity

        return None, best_similarity

    @staticmethod
    def _prepare_cache_data(
        hashes: dict,
        image_data: bytes,
        image_format: str,
        analysis_result: VisionResult,
    ) -> Optional[Dict]:
        try:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            image_dimensions = f"{width}x{height}"

            ingredients_json = (
                [ing.model_dump() for ing in analysis_result.ingredients]
                if analysis_result.ingredients
                else None
            )

            confidence = None
            if analysis_result.ingredients:
                confidences = [ing.confidence for ing in analysis_result.ingredients]
                if confidences:
                    confidence = statistics.mean(confidences)

            return {
                "perceptual_hash": hashes["perceptual_hash"],
                "image_size": image_dimensions,
                "image_format": image_format,
                "file_size": len(image_data),
                "ingredients": ingredients_json,
                "analysis_confidence": confidence,
                "access_count": 1,
            }
        except Exception as e:
            logger.error(f"Could not prepare image cache data: {e}", exc_info=True)
            return None

    @staticmethod
    def _generate_perceptual_hashes(image_data: bytes) -> Dict[str, str]:
        try:
            image = Image.open(io.BytesIO(image_data))
            perceptual_hash = str(imagehash.phash(image))
            return {"perceptual_hash": perceptual_hash}
        except Exception as e:
            logger.error(f"Error generating perceptual hash: {e}", exc_info=True)
            return {}

    @staticmethod
    def _calculate_hash_similarity(hash1: str, hash2: str) -> int:
        if len(hash1) != len(hash2):
            return 64
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except Exception as e:
            logger.error(
                f"Error calculating hash similarity between '{hash1}' and '{hash2}': {e}",
                exc_info=True,
            )
            return 64

    @staticmethod
    def _update_access_stats(cache_entry: ImageCache):
        cache_entry.last_accessed = datetime.now(timezone.utc)  # type: ignore
        cache_entry.access_count += 1  # type: ignore
        logger.debug(f"Staged access stat update for cache ID: {cache_entry.id}")
