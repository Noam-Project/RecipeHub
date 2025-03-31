import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recipe_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("recipe_importer")

# Load environment variables
load_dotenv()

# Initialize Firebase if not already initialized
try:
    app = firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')

if not SPOONACULAR_API_KEY:
    logger.error("Spoonacular API key not found in environment variables")
    raise ValueError("API key not found. Please set SPOONACULAR_API_KEY in .env")

def fetch_recipe_ids(count=30):
    """Fetch recipe IDs from Spoonacular"""
    logger.info(f"Fetching {count} recipe IDs from Spoonacular API")
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "number": count,
        "addRecipeInformation": True,
        "fillIngredients": True,
        "instructionsRequired": True,
        "sort": "random"  # Get random recipes each time
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])
        logger.info(f"Successfully fetched {len(results)} recipe IDs")
        return [recipe['id'] for recipe in results]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching recipe IDs: {str(e)}")
        return []

def fetch_recipe_details(recipe_ids):
    """Fetch bulk recipe details"""
    if not recipe_ids:
        logger.warning("No recipe IDs provided to fetch details")
        return []
        
    logger.info(f"Fetching details for {len(recipe_ids)} recipes")
    url = "https://api.spoonacular.com/recipes/informationBulk"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "ids": ",".join(map(str, recipe_ids)),
        "includeNutrition": True
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        recipes = response.json()
        logger.info(f"Successfully fetched details for {len(recipes)} recipes")
        return recipes
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching recipe details: {str(e)}")
        return []

def sanitize_recipe(recipe):
    """Convert Spoonacular data to Firestore-friendly format"""
    try:
        # Extract nutrition information
        nutrition = None
        if 'nutrition' in recipe:
            nutrients = recipe['nutrition'].get('nutrients', [])
            nutrition = {
                'calories': next((n['amount'] for n in nutrients if n['name'] == 'Calories'), 'N/A'),
                'protein': next((n['amount'] for n in nutrients if n['name'] == 'Protein'), 'N/A'),
                'carbs': next((n['amount'] for n in nutrients if n['name'] == 'Carbohydrates'), 'N/A'),
                'fat': next((n['amount'] for n in nutrients if n['name'] == 'Fat'), 'N/A')
            }
        
        # Process the ingredients
        ingredients = []
        for ingredient in recipe.get('extendedIngredients', []):
            ingredients.append({
                'id': ingredient.get('id', 0),
                'name': ingredient.get('name', ''),
                'amount': ingredient.get('amount', 0),
                'unit': ingredient.get('unit', '')
            })
        
        return {
            'id': str(recipe['id']),
            'title': recipe.get('title', 'Untitled Recipe'),
            'image': recipe.get('image', ''),
            'readyInMinutes': recipe.get('readyInMinutes', 0),
            'servings': recipe.get('servings', 1),
            'summary': recipe.get('summary', ''),
            'instructions': recipe.get('instructions', 'No instructions available'),
            'vegetarian': recipe.get('vegetarian', False),
            'vegan': recipe.get('vegan', False),
            'glutenFree': recipe.get('glutenFree', False),
            'dairyFree': recipe.get('dairyFree', False),
            'dishTypes': recipe.get('dishTypes', []),
            'ingredients': ingredients,
            'nutrition': nutrition,
            'importedAt': firestore.SERVER_TIMESTAMP
        }
    except Exception as e:
        logger.error(f"Error sanitizing recipe {recipe.get('id')}: {str(e)}")
        # Return a minimal valid recipe object if there's an error
        return {
            'id': str(recipe.get('id', 'unknown')),
            'title': recipe.get('title', 'Error processing recipe'),
            'importedAt': firestore.SERVER_TIMESTAMP
        }

def store_recipes(recipes):
    """Store recipes in Firestore with duplicate check"""
    if not recipes:
        logger.warning("No recipes provided to store")
        return
        
    logger.info(f"Preparing to store {len(recipes)} recipes")
    batch = db.batch()
    recipes_ref = db.collection('recipes')
    
    # Track stored and skipped counts
    stored_count = 0
    skipped_count = 0
    
    for recipe in recipes:
        try:
            recipe_id = str(recipe['id'])
            # Check if recipe exists
            existing_doc = recipes_ref.document(recipe_id).get()
            
            if not existing_doc.exists:
                sanitized = sanitize_recipe(recipe)
                batch.set(recipes_ref.document(recipe_id), sanitized)
                stored_count += 1
            else:
                skipped_count += 1
                logger.debug(f"Skipping duplicate recipe: {recipe_id}")
        except Exception as e:
            logger.error(f"Error processing recipe {recipe.get('id', 'unknown')}: {str(e)}")
    
    try:
        if stored_count > 0:
            batch.commit()
            logger.info(f"Successfully stored {stored_count} recipes (skipped {skipped_count} duplicates)")
        else:
            logger.info(f"No new recipes to store (skipped {skipped_count} duplicates)")
    except Exception as e:
        logger.error(f"Error storing recipes in Firestore: {str(e)}")

def main():
    """Main function to run the recipe import process"""
    start_time = datetime.now()
    
    # Get recipe count from environment variable or use default
    recipe_count = int(os.environ.get('RECIPE_COUNT', 30))
    
    logger.info(f"Starting recipe import process at {start_time} for {recipe_count} recipes")
    
    try:
        # Fetch and store recipes
        recipe_ids = fetch_recipe_ids(recipe_count)
        if recipe_ids:
            # Add a delay to respect rate limits
            time.sleep(1)  # Spoonacular free tier rate limiting
            
            recipes_data = fetch_recipe_details(recipe_ids)
            if recipes_data:
                store_recipes(recipes_data)
            else:
                logger.warning("No recipe details were retrieved")
        else:
            logger.warning("No recipe IDs were retrieved")
    except Exception as e:
        logger.error(f"Unhandled exception in main process: {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Recipe import process completed at {end_time}. Duration: {duration:.2f} seconds")

if __name__ == "__main__":
    main() 