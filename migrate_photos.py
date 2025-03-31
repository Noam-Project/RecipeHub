#!/usr/bin/env python3
"""
RecipeHub Photo Migration Script
--------------------------------
This script migrates all photos in the RecipeHub application from external URLs
to Firebase Storage. It handles:
1. Recipe images from Spoonacular API
2. Review photos uploaded by users
3. User profile photos

Usage:
    python migrate_photos.py

Requirements:
    pip install firebase-admin requests tqdm
"""

import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore, storage
from urllib.parse import urlparse
import time
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("photo_migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("photo_migration")

# Initialize Firebase
try:
    firebase_admin.get_app()
except ValueError:
    # Use your project ID here
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'recipehub-36272.firebasestorage.app'  # Updated bucket name
    })

db = firestore.client()
bucket = storage.bucket()

def is_firebase_storage_url(url):
    """Check if URL is already from Firebase Storage"""
    if not url:
        return False
    parsed = urlparse(url)
    return 'firebasestorage.googleapis.com' in parsed.netloc

def download_image(url):
    """Download image from URL"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return response.content, response.headers.get('content-type', 'image/jpeg')
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {str(e)}")
        return None, None

def migrate_recipe_photos():
    """Migrate recipe photos from external URLs to Firebase Storage"""
    logger.info("Starting recipe photo migration...")
    
    # Get all recipes with image URLs
    recipes_ref = db.collection('recipes').stream()
    recipes = list(recipes_ref)  # Convert to list for progress bar
    
    migrated = 0
    skipped = 0
    failed = 0
    
    for doc in tqdm(recipes, desc="Migrating recipe photos"):
        recipe = doc.to_dict()
        recipe_id = recipe.get('id')
        image_url = recipe.get('image')
        
        if not image_url or not recipe_id:
            skipped += 1
            continue
            
        # Skip if already a Firebase Storage URL
        if is_firebase_storage_url(image_url):
            logger.info(f"Recipe {recipe_id} already using Firebase Storage, skipping")
            skipped += 1
            continue
        
        # Download the image
        image_data, content_type = download_image(image_url)
        if not image_data:
            failed += 1
            continue
        
        try:
            # Upload to Firebase Storage
            storage_path = f"recipe_images/{recipe_id}.jpg"
            blob = bucket.blob(storage_path)
            blob.upload_from_string(image_data, content_type=content_type)
            
            # Make it publicly accessible
            blob.make_public()
            new_url = blob.public_url
            
            # Update Firestore document
            db.collection('recipes').document(recipe_id).update({
                'image': new_url,
                'storage_path': storage_path  # Store the storage path for future reference
            })
            
            logger.info(f"Successfully migrated image for recipe {recipe_id}")
            migrated += 1
            
            # Respect API rate limits with a small delay
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Failed to migrate image for recipe {recipe_id}: {str(e)}")
            failed += 1
    
    logger.info(f"Recipe photo migration complete. Migrated: {migrated}, Skipped: {skipped}, Failed: {failed}")
    return migrated, skipped, failed

def migrate_review_photos():
    """Migrate review photos uploaded by users"""
    logger.info("Starting review photo migration...")
    
    # Get all reviews with photo URLs
    reviews_ref = db.collection('reviews').stream()
    reviews = list(reviews_ref)
    
    migrated = 0
    skipped = 0
    failed = 0
    
    for doc in tqdm(reviews, desc="Migrating review photos"):
        review_data = doc.to_dict()
        review_id = doc.id
        photo_url = review_data.get('photo_url')
        
        if not photo_url:
            skipped += 1
            continue
            
        # Skip if already a Firebase Storage URL
        if is_firebase_storage_url(photo_url):
            logger.info(f"Review {review_id} photo already using Firebase Storage, skipping")
            skipped += 1
            continue
        
        # Download the image
        image_data, content_type = download_image(photo_url)
        if not image_data:
            failed += 1
            continue
        
        try:
            # Upload to Firebase Storage
            storage_path = f"review_photos/{review_id}.jpg"
            blob = bucket.blob(storage_path)
            blob.upload_from_string(image_data, content_type=content_type)
            
            # Make it publicly accessible
            blob.make_public()
            new_url = blob.public_url
            
            # Update Firestore document
            db.collection('reviews').document(review_id).update({
                'photo_url': new_url,
                'storage_path': storage_path
            })
            
            logger.info(f"Successfully migrated photo for review {review_id}")
            migrated += 1
            
            # Respect API rate limits
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Failed to migrate photo for review {review_id}: {str(e)}")
            failed += 1
    
    logger.info(f"Review photo migration complete. Migrated: {migrated}, Skipped: {skipped}, Failed: {failed}")
    return migrated, skipped, failed

def migrate_user_profile_photos():
    """Migrate user profile photos"""
    logger.info("Starting user profile photo migration...")
    
    # Get all users with profile photos
    users_ref = db.collection('users').stream()
    users = list(users_ref)
    
    migrated = 0
    skipped = 0
    failed = 0
    
    for doc in tqdm(users, desc="Migrating profile photos"):
        user_data = doc.to_dict()
        user_id = doc.id
        photo_url = user_data.get('photo_url')
        
        if not photo_url:
            skipped += 1
            continue
            
        # Skip if already a Firebase Storage URL
        if is_firebase_storage_url(photo_url):
            logger.info(f"User {user_id} profile photo already using Firebase Storage, skipping")
            skipped += 1
            continue
        
        # Download the image
        image_data, content_type = download_image(photo_url)
        if not image_data:
            failed += 1
            continue
        
        try:
            # Upload to Firebase Storage
            storage_path = f"profile_photos/{user_id}.jpg"
            blob = bucket.blob(storage_path)
            blob.upload_from_string(image_data, content_type=content_type)
            
            # Make it publicly accessible
            blob.make_public()
            new_url = blob.public_url
            
            # Update Firestore document
            db.collection('users').document(user_id).update({
                'photo_url': new_url,
                'storage_path': storage_path
            })
            
            logger.info(f"Successfully migrated photo for user {user_id}")
            migrated += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate photo for user {user_id}: {str(e)}")
            failed += 1
    
    logger.info(f"User profile photo migration complete. Migrated: {migrated}, Skipped: {skipped}, Failed: {failed}")
    return migrated, skipped, failed

def main():
    """Run all migration functions"""
    start_time = time.time()
    logger.info("Starting photo migration process...")
    
    # Migrate recipe photos
    recipe_migrated, recipe_skipped, recipe_failed = migrate_recipe_photos()
    
    # Migrate review photos
    review_migrated, review_skipped, review_failed = migrate_review_photos()
    
    # Migrate user profile photos
    profile_migrated, profile_skipped, profile_failed = migrate_user_profile_photos()
    
    # Print summary
    total_migrated = recipe_migrated + review_migrated + profile_migrated
    total_skipped = recipe_skipped + review_skipped + profile_skipped
    total_failed = recipe_failed + review_failed + profile_failed
    
    logger.info("Migration complete!")
    logger.info(f"Total migrated: {total_migrated}")
    logger.info(f"Total skipped: {total_skipped}")
    logger.info(f"Total failed: {total_failed}")
    logger.info(f"Time taken: {time.time() - start_time:.2f} seconds")
    
    print("\n======= MIGRATION SUMMARY =======")
    print(f"Recipe photos: {recipe_migrated} migrated, {recipe_skipped} skipped, {recipe_failed} failed")
    print(f"Review photos: {review_migrated} migrated, {review_skipped} skipped, {review_failed} failed")
    print(f"Profile photos: {profile_migrated} migrated, {profile_skipped} skipped, {profile_failed} failed")
    print(f"Total: {total_migrated} migrated, {total_skipped} skipped, {total_failed} failed")
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    print("=================================")

if __name__ == "__main__":
    main() 