import asyncio
import base64
import binascii
import imghdr
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from pydantic_ai import ImageUrl
from pydantic_ai.agent import Agent

from app.agents.prompts import VISION_AGENT_PROMPT
from app.agents.spec import AGENTS, AgentName, AgentSpec
from app.models.models import VisionResult, VisionResult_llm
from app.models.service_models import ImageInput
from app.services.image_cache_service import ImageCacheService
from app.services.ingredient_service import IngredientService


class VisionService:
    MAX_BYTES = 15 * 1024 * 1024  # 15 MB hard limit

    def __init__(
        self,
        image_cache_service: ImageCacheService,
        ingredient_service: IngredientService,
    ):
        self.image_cache_service = image_cache_service
        self.ingredient_service = ingredient_service
        self.logger = logging.getLogger(__name__)

    async def analyze_image(
        self, image_input: Optional[ImageInput], image_data: bytes, image_format: str
    ) -> VisionResult:
        """
        Analyzes an image, using the cache service first.
        """
        if image_input is None:
            return VisionResult(ingredients=None)

        # 1. Check cache first
        cached_result, is_cached = self.image_cache_service.get(image_data)
        if is_cached and cached_result:
            return cached_result

        # 2. If not in cache, perform analysis
        try:
            data_uri = await self._to_data_uri(image_input.url)
        except Exception as exc:
            raise HTTPException(400, f"Invalid image: {exc}") from exc

        try:
            # we need the taxonomy block here same as in for we did for recipe agent.
            taxonomy = await self.ingredient_service.list_parent_ingredients()
            taxonomy_block = self.ingredient_service.build_taxonomy_block(taxonomy)

            vision_agent_spec = AgentSpec[VisionResult_llm](
                name=AgentName.VISION.value,
                model="openai:gpt-5.2",  # Use the same model as the default
                system_prompt=VISION_AGENT_PROMPT
                + "\n\n"
                + taxonomy_block,  # Use the default prompt and add the taxonomy block
                output_model=VisionResult_llm,
                retries=3,
            )
            vision_agent = vision_agent_spec.build()

            agent_out = await vision_agent.run(
                [
                    "Analyze this image using the system prompt and return JSON.",
                    ImageUrl(url=data_uri),
                ]
            )
            analysis_result = agent_out.output.data

            # Temporarily disabled: create new parent ingredients from vision analysis
            # try:
            #     await self.ingredient_service.create_new_parent_ingredients(
            #         analysis_result
            #     )
            # except Exception:
            #     self.logger.exception("Failed while creating new parent ingredients")

            # Create a VisionResult object containing only the ingredients
            ingredient_list = analysis_result.ingredients

            clean_list_ingredients = await self.ingredient_service.verify_ingredients(
                ingredient_list
            )

            final_result = VisionResult(ingredients=clean_list_ingredients)

            # --- Step 4: Store the new result in the cache ---
            if analysis_result and analysis_result.ingredients:
                self.image_cache_service.set(image_data, image_format, final_result)

            return final_result

        except Exception as exc:
            raise HTTPException(502, "Vision analysis failed") from exc

    @staticmethod
    async def _to_data_uri(source: str) -> str:
        if urlparse(source).scheme in {"http", "https"}:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(source, follow_redirects=True)
                resp.raise_for_status()

                if len(resp.content) > VisionService.MAX_BYTES:
                    raise ValueError("image exceeds 15 MB limit")

                mime = resp.headers.get("Content-Type", "image/jpeg")
                b64 = await asyncio.to_thread(base64.b64encode, resp.content)
                return f"data:{mime};base64,{b64.decode()}"

        if source.startswith("data:image/"):
            return source

        try:
            decoded_data = base64.b64decode(source)
            mime_guess = imghdr.what(None, h=decoded_data)
            mime = f"image/{mime_guess or 'jpeg'}"
            return f"data:{mime};base64,{source}"
        except (binascii.Error, TypeError):
            raise ValueError("Invalid base64 string provided for image source.")
