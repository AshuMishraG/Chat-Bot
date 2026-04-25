import asyncio
import logging

from app.core.db import SessionLocal
from app.core.db.models import MixlistEmbeddings, RecipeEmbeddings
from app.services.embedding_service import EmbeddingService
from app.services.embedding_service_mixlists import MixlistEmbeddingService

logger = logging.getLogger(__name__)


async def cleanup_embeddings():
    with SessionLocal() as db:
        recipe_embedding_service = EmbeddingService(db)
        mixlist_embedding_service = MixlistEmbeddingService(db)

        logger.info("Fetching all valid recipe IDs from the external API...")
        try:
            all_recipes_data = await recipe_embedding_service._fetch_all_recipes()
        except Exception:
            logger.exception(
                "Failed to fetch recipes; skipping recipe embeddings cleanup to avoid accidental deletion."
            )
            all_recipes_data = None

        if not all_recipes_data:
            logger.error(
                "No valid recipe data returned; skipping recipe embeddings cleanup to avoid accidental mass deletion."
            )
            valid_recipe_ids = set()
            skip_recipe_cleanup = True
        else:
            valid_recipe_ids = {recipe["id"] for recipe in all_recipes_data}
            logger.info(f"Found {len(valid_recipe_ids)} valid recipe IDs.")
            skip_recipe_cleanup = False

        logger.info("Fetching all valid mixlist IDs from the external API...")
        try:
            all_mixlists_data = await mixlist_embedding_service._fetch_all_mixlists()
        except Exception:
            logger.exception(
                "Failed to fetch mixlists; skipping mixlist embeddings cleanup to avoid accidental deletion."
            )
            all_mixlists_data = None

        if not all_mixlists_data:
            logger.error(
                "No valid mixlist data returned; skipping mixlist embeddings cleanup to avoid accidental mass deletion."
            )
            valid_mixlist_ids = set()
            skip_mixlist_cleanup = True
        else:
            valid_mixlist_ids = {mixlist["id"] for mixlist in all_mixlists_data}
            logger.info(f"Found {len(valid_mixlist_ids)} valid mixlist IDs.")
            skip_mixlist_cleanup = False

        if not skip_recipe_cleanup:
            # Fetch all existing recipe embedding IDs from the database
            logger.info("Fetching existing recipe embedding IDs from the database...")
            existing_recipe_embedding_ids = (
                recipe_embedding_service._get_existing_embedding_ids()
            )
            logger.info(
                f"Found {len(existing_recipe_embedding_ids)} existing recipe embeddings in DB."
            )

            # Identify obsolete recipe embedding IDs
            obsolete_recipe_embedding_ids = (
                existing_recipe_embedding_ids - valid_recipe_ids
            )
            logger.info(
                f"Identified {len(obsolete_recipe_embedding_ids)} obsolete recipe embeddings."
            )

            # Delete obsolete recipe embeddings
            if obsolete_recipe_embedding_ids:
                logger.info("Deleting obsolete recipe embeddings...")
                recipe_embedding_service.db.query(RecipeEmbeddings).filter(
                    RecipeEmbeddings.recipe_id.in_(obsolete_recipe_embedding_ids)
                ).delete(synchronize_session=False)
                recipe_embedding_service.db.commit()
                logger.info("Obsolete recipe embeddings deleted successfully.")
            else:
                logger.info("No obsolete recipe embeddings to delete.")
        else:
            logger.info("Skipped recipe embeddings cleanup.")

        if not skip_mixlist_cleanup:
            # Fetch all existing mixlist embedding IDs from the database
            logger.info("Fetching existing mixlist embedding IDs from the database...")
            existing_mixlist_embedding_ids = (
                mixlist_embedding_service._get_existing_embedding_ids()
            )
            logger.info(
                f"Found {len(existing_mixlist_embedding_ids)} existing mixlist embeddings in DB."
            )

            # Identify obsolete mixlist embedding IDs
            obsolete_mixlist_embedding_ids = (
                existing_mixlist_embedding_ids - valid_mixlist_ids
            )
            logger.info(
                f"Identified {len(obsolete_mixlist_embedding_ids)} obsolete mixlist embeddings."
            )

            # Delete obsolete mixlist embeddings
            if obsolete_mixlist_embedding_ids:
                logger.info("Deleting obsolete mixlist embeddings...")
                mixlist_embedding_service.db.query(MixlistEmbeddings).filter(
                    MixlistEmbeddings.mixlist_id.in_(obsolete_mixlist_embedding_ids)
                ).delete(synchronize_session=False)
                mixlist_embedding_service.db.commit()
                logger.info("Obsolete mixlist embeddings deleted successfully.")
            else:
                logger.info("No obsolete mixlist embeddings to delete.")
        else:
            logger.info("Skipped mixlist embeddings cleanup.")

        logger.info("Embedding cleanup process completed.")


if __name__ == "__main__":
    asyncio.run(cleanup_embeddings())
