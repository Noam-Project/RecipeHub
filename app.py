from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from functools import wraps
import requests
from datetime import datetime
import json
import logging
from google.cloud import storage

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize Firebase
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# User class
class User:
    def __init__(self, uid, email, display_name=None):
        self.uid = uid
        self.email = email
        self.display_name = display_name
        
    def get_saved_recipes(self):
        """Get saved recipes with full recipe data"""
        saved_refs = db.collection('users').document(self.uid).collection('saved_recipes').stream()
        saved_recipes = []
        
        for doc in saved_refs:
            saved_data = doc.to_dict()
            saved_data['id'] = doc.id  # Add document ID
            
            # Only proceed if recipe_id exists
            if 'recipe_id' in saved_data:
                # Fetch the actual recipe data
                recipe_ref = db.collection('recipes').document(saved_data['recipe_id']).get()
                if recipe_ref.exists:
                    # Create a nested structure with both saved info and recipe data
                    complete_data = {
                        'id': doc.id,
                        'saved_at': saved_data.get('saved_at'),
                        'recipe': recipe_ref.to_dict()
                    }
                    saved_recipes.append(complete_data)
                else:
                    # If recipe doesn't exist, still include minimal data
                    logger.warning(f"Recipe {saved_data['recipe_id']} referenced in saved_recipes does not exist")
                    complete_data = {
                        'id': doc.id,
                        'saved_at': saved_data.get('saved_at'),
                        'recipe': {
                            'id': saved_data['recipe_id'],
                            'title': 'Unknown Recipe',
                            'image': '',
                            'readyInMinutes': 0
                        }
                    }
                    saved_recipes.append(complete_data)
            
        return saved_recipes
    
    def get_reviews(self):
        reviews_ref = db.collection('reviews').where('user_id', '==', self.uid).stream()
        reviews_list = []
        
        for doc in reviews_ref:
            review_data = doc.to_dict()
            review_data['id'] = doc.id  # Add the document ID
            
            # Try to fetch the recipe data for each review
            if 'recipe_id' in review_data:
                recipe_ref = db.collection('recipes').document(review_data['recipe_id']).get()
                if recipe_ref.exists:
                    review_data['recipe'] = recipe_ref.to_dict()
                else:
                    review_data['recipe'] = {
                        'id': review_data['recipe_id'],
                        'title': 'Unknown Recipe',
                        'image': ''
                    }
            
            reviews_list.append(review_data)
            
        return reviews_list

# Admin User class (inherits from User)
class AdminUser(User):
    def delete_recipe(self, recipe_id):
        db.collection('recipes').document(recipe_id).delete()
        
    def delete_review(self, review_id):
        db.collection('reviews').document(review_id).delete()
    
    def set_user_claims(self, uid, claims):
        auth.set_custom_user_claims(uid, claims)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'is_admin' not in session or not session['is_admin']:
            flash('Admin privileges required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    # Get featured recipes
    recipes_ref = db.collection('recipes').limit(8).stream()
    recipes = [doc.to_dict() for doc in recipes_ref]
    return render_template('index.html', recipes=recipes)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle login via Firebase Authentication (client-side)
        return render_template('login.html')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Handle signup via Firebase Authentication (client-side)
        return render_template('signup.html')
    return render_template('signup.html')

@app.route('/recipes')
def recipes():
    # Get all recipes
    recipes_ref = db.collection('recipes').stream()
    recipes = [doc.to_dict() for doc in recipes_ref]
    return render_template('recipes.html', recipes=recipes)

@app.route('/recipe/<recipe_id>')
def recipe_detail(recipe_id):
    # Get recipe details
    recipe = db.collection('recipes').document(recipe_id).get().to_dict()
    
    # Get reviews for this recipe
    reviews_ref = db.collection('reviews').where('recipe_id', '==', recipe_id).stream()
    reviews = [doc.to_dict() for doc in reviews_ref]
    
    return render_template('recipe_detail.html', recipe=recipe, reviews=reviews)

@app.route('/account')
@login_required
def account():
    # Get user info
    user_id = session['user_id']
    user_doc = db.collection('users').document(user_id).get()
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
        if session.get('is_admin', False):
            user = AdminUser(user_id, user_data.get('email'), user_data.get('display_name'))
        else:
            user = User(user_id, user_data.get('email'), user_data.get('display_name'))
        
        saved_recipes = user.get_saved_recipes()
        reviews = user.get_reviews()
        
        return render_template('account.html', user=user_data, saved_recipes=saved_recipes, reviews=reviews)
    
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin.html')

# API routes for AJAX calls
@app.route('/api/save-recipe', methods=['POST'])
@login_required
def save_recipe():
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    user_id = session['user_id']
    
    # Use recipe_id as document ID to prevent duplicates
    saved_recipe_ref = db.collection('users').document(user_id).collection('saved_recipes').document(recipe_id)
    
    # Check if already exists
    if saved_recipe_ref.get().exists:
        return jsonify({'success': True, 'message': 'Recipe already saved'})
    
    # Add new save
    saved_recipe = {
        'recipe_id': recipe_id,
        'saved_at': firestore.SERVER_TIMESTAMP,
        'user_id': user_id
    }
    
    saved_recipe_ref.set(saved_recipe)
    return jsonify({'success': True, 'message': 'Recipe saved successfully'})

@app.route('/api/is-recipe-saved/<recipe_id>', methods=['GET'])
@login_required
def is_recipe_saved(recipe_id):
    user_id = session['user_id']
    saved_recipe_ref = db.collection('users').document(user_id).collection('saved_recipes').document(recipe_id)
    return jsonify({
        'is_saved': saved_recipe_ref.get().exists
    })

@app.route('/api/add-review', methods=['POST'])
@login_required
def add_review():
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    rating = data.get('rating')
    comment = data.get('comment')
    photo_url = data.get('photo_url')
    storage_path = data.get('storage_path')
    user_id = session['user_id']
    
    # Get user info to include in review
    user_doc = db.collection('users').document(user_id).get()
    user_data = user_doc.to_dict()
    user_name = user_data.get('display_name', 'Anonymous')
    
    # Create review object
    review = {
        'recipe_id': recipe_id,
        'user_id': user_id,
        'user_name': user_name,
        'rating': rating,
        'comment': comment,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    
    # Add photo URL and storage path if provided
    if photo_url:
        review['photo_url'] = photo_url
        if storage_path:
            review['storage_path'] = storage_path
    
    # Add review to Firestore
    db.collection('reviews').add(review)
    
    return jsonify({'success': True})

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    user_id = session['user_id']
    
    # Update user document in Firestore
    update_data = {}
    
    if 'display_name' in data:
        update_data['display_name'] = data['display_name']
    
    if 'photo_url' in data:
        update_data['photo_url'] = data['photo_url']
        
    if 'storage_path' in data:
        update_data['storage_path'] = data['storage_path']
    
    if update_data:
        db.collection('users').document(user_id).update(update_data)
        
    return jsonify({'success': True})

# Add a session check endpoint
@app.route('/api/check-session', methods=['GET'])
def check_session():
    """Check if user has an active session"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True, 
            'user_id': session['user_id'],
            'is_admin': session.get('is_admin', False)
        })
    else:
        return jsonify({'authenticated': False})

# Authentication API endpoints
@app.route('/api/create-session', methods=['POST'])
def create_session():
    id_token = request.json.get('idToken')
    
    if not id_token:
        logger.error("No ID token provided in request")
        return jsonify({'success': False, 'error': 'No ID token provided'}), 400
    
    try:
        # Verify the ID token
        logger.info("Verifying ID token")
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        
        logger.info(f"Token verified for user: {user_id}")
        
        # Create session
        session['user_id'] = user_id
        session['email'] = decoded_token.get('email', '')
        
        # Check if user is admin
        user_record = auth.get_user(user_id)
        
        # Check custom claims for admin status
        if user_record.custom_claims and user_record.custom_claims.get('admin'):
            session['is_admin'] = True
            logger.info(f"User {user_id} is an admin (from custom claims)")
        else:
            # Also check Firestore document for admin status
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists and user_doc.to_dict().get('is_admin', False):
                session['is_admin'] = True
                
                # If admin in Firestore but not in custom claims, update custom claims
                if not (user_record.custom_claims and user_record.custom_claims.get('admin')):
                    auth.set_custom_user_claims(user_id, {'admin': True})
                logger.info(f"User {user_id} is an admin (from Firestore)")
            else:
                session['is_admin'] = False
                logger.info(f"User {user_id} is not an admin")
        
        logger.info(f"Session created for user {user_id}, is_admin: {session.get('is_admin', False)}")
        # Set a long session expiration time
        session.permanent = True
        
        return jsonify({'success': True, 'user_id': user_id, 'is_admin': session.get('is_admin', False)})
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    # Clear session
    logger.info(f"Logging out user: {session.get('user_id', 'unknown')}")
    session.clear()
    return jsonify({'success': True})

@app.route('/api/fetch-recipes', methods=['GET'])
def fetch_recipes_from_api():
    # This endpoint will fetch recipes from Spoonacular API and store them in Firestore
    # This would typically be called by an admin or a scheduled task
    
    if 'user_id' not in session or not session.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    api_key = os.environ.get('SPOONACULAR_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'API key not configured'}), 500
    
    try:
        # Make request to Spoonacular API
        url = f"https://api.spoonacular.com/recipes/random?number=30&apiKey={api_key}"
        response = requests.get(url)
        data = response.json()
        
        # Store recipes in Firestore
        recipes_batch = db.batch()
        
        for recipe_data in data.get('recipes', []):
            recipe_ref = db.collection('recipes').document(str(recipe_data['id']))
            
            # Extract the relevant information
            recipe = {
                'id': str(recipe_data['id']),
                'title': recipe_data['title'],
                'image': recipe_data.get('image', ''),
                'readyInMinutes': recipe_data.get('readyInMinutes', 0),
                'servings': recipe_data.get('servings', 1),
                'summary': recipe_data.get('summary', ''),
                'instructions': recipe_data.get('instructions', ''),
                'vegetarian': recipe_data.get('vegetarian', False),
                'vegan': recipe_data.get('vegan', False),
                'glutenFree': recipe_data.get('glutenFree', False),
                'dairyFree': recipe_data.get('dairyFree', False),
                'dishTypes': recipe_data.get('dishTypes', []),
                'ingredients': [
                    {
                        'id': ingredient.get('id', 0),
                        'name': ingredient.get('name', ''),
                        'amount': ingredient.get('amount', 0),
                        'unit': ingredient.get('unit', '')
                    }
                    for ingredient in recipe_data.get('extendedIngredients', [])
                ],
                'importedAt': firestore.SERVER_TIMESTAMP
            }
            
            recipes_batch.set(recipe_ref, recipe)
        
        # Commit the batch
        recipes_batch.commit()
        
        return jsonify({'success': True, 'recipes_imported': len(data.get('recipes', []))})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API routes for admin actions
@app.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def get_admin_stats():
    # Get admin dashboard statistics
    try:
        users_count = len(list(db.collection('users').stream()))
        recipes_count = len(list(db.collection('recipes').stream()))
        reviews_count = len(list(db.collection('reviews').stream()))
        
        stats = {
            'total_users': users_count,
            'total_recipes': recipes_count,
            'total_reviews': reviews_count
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/set-admin-claim', methods=['POST'])
@login_required
@admin_required
def set_admin_claim():
    data = request.get_json()
    user_id = data.get('user_id')
    is_admin = data.get('is_admin', False)
    
    try:
        # Set custom claims
        auth.set_custom_user_claims(user_id, {'admin': is_admin})
        
        # Update user document in Firestore
        db.collection('users').document(user_id).update({
            'is_admin': is_admin
        })
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reviews/<review_id>', methods=['DELETE'])
@login_required
def delete_review(review_id):
    user_id = session['user_id']
    is_admin = session.get('is_admin', False)
    
    try:
        review_ref = db.collection('reviews').document(review_id)
        review = review_ref.get()
        
        if not review.exists:
            return jsonify({'success': False, 'error': 'Review not found'}), 404
            
        review_data = review.to_dict()
        
        # Check if user is the review author or an admin
        if review_data.get('user_id') == user_id or is_admin:
            review_ref.delete()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Not authorized to delete this review'}), 403
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/saved-recipes/<saved_id>', methods=['DELETE'])
@login_required
def delete_saved_recipe(saved_id):
    user_id = session['user_id']
    
    try:
        # Delete the saved recipe
        db.collection('users').document(user_id).collection('saved_recipes').document(saved_id).delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/top-recipes')
def get_top_recipes():
    try:
        recipes_ref = db.collection('recipes')
        top_recipes = []

        # Get all recipes with reviews
        for recipe_doc in recipes_ref.stream():
            recipe = recipe_doc.to_dict()
            reviews_ref = db.collection('reviews').where('recipe_id', '==', recipe_doc.id)
            reviews = [r.to_dict() for r in reviews_ref.stream()]
            
            if reviews:
                avg_rating = sum(r['rating'] for r in reviews) / len(reviews)
                top_recipes.append({
                    'id': recipe_doc.id,
                    'title': recipe.get('title'),
                    'avg_rating': round(avg_rating, 1),
                    'review_count': len(reviews)
                })

        # Sort by rating descending
        top_recipes.sort(key=lambda x: x['avg_rating'], reverse=True)
        return jsonify({'success': True, 'recipes': top_recipes[:10]})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/delete-recipe-reviews/<recipe_id>', methods=['DELETE'])
def delete_recipe_reviews(recipe_id):
    try:
        # Verify admin
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Delete all reviews for this recipe
        reviews_ref = db.collection('reviews').where('recipe_id', '==', recipe_id)
        for review in reviews_ref.stream():
            # Delete any associated photos
            if review.to_dict().get('storage_path'):
                bucket = storage.bucket()
                bucket.blob(review.to_dict()['storage_path']).delete()
            review.reference.delete()

        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)