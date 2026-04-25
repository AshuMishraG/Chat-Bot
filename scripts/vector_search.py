# Search the database for the most similar recipes to the query
# Returns the recipe ID, recipe Name, Embedding String and Similarity Score.
# this file is For the direct testing endpoint api/vector-search

import sys

from openai import AsyncOpenAI
from app.core.db import SessionLocal

from app.core.db.models import RecipeEmbeddings

aclient = AsyncOpenAI()


async def vector_search_logic(query: str):
    """
    Performs a vector search for recipes based on a query string.
    This function handles its own database session.
    """
    if not query:
        print("Search query is empty.")
        return None

    print(f"Searching for recipes similar to: '{query}'")
    db = SessionLocal()
    try:
        # 1. Get the embedding for the user's query
        embedding_response = await aclient.embeddings.create(
            input=query, model="text-embedding-3-small", dimensions=768
        )
        query_embedding = embedding_response.data[0].embedding

        # 2. Search by the embeddings for most similar recipes
        # The HNSW index on the table is configured for cosine distance, to search by cosine distance
        similar_recipes = (
            db.query(
                RecipeEmbeddings,
                RecipeEmbeddings.embedding.cosine_distance(query_embedding).label(
                    "distance"
                ),
            )
            .order_by("distance")
            .limit(3)
            .all()
        )

        if similar_recipes:
            print(f"Found {len(similar_recipes)} similar recipes:")
            for recipe, distance in similar_recipes:
                similarity = 1 - distance
                print(
                    f"  ID: {recipe.recipe_id}, Distance: {distance:.4f}, Similarity: {similarity:.4f}"
                )
        else:
            print("No similar recipes found in the database.")

        return similar_recipes

    except Exception as e:
        print(f"An error occurred during vector search: {e}", file=sys.stderr)
        return []
    finally:
        db.close()
