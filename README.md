RecipeHub
📖 Project Overview
RecipeHub is a comprehensive recipe management platform that allows users to discover, save, and review culinary creations from around the world. Built with modern web technologies, this platform provides a seamless experience for food enthusiasts to find inspiration for their next meal.
!RecipeHub Banner

✨ Features
User Experience
Recipe Discovery: Browse through a vast collection of recipes with detailed instructions, ingredients, and nutritional information
Advanced Search: Filter recipes by cuisine, dietary restrictions, ingredients, or meal type
Personalized Accounts: Create and maintain a profile to track your culinary journey
Recipe Saving: Bookmark favorite recipes for quick access later
Rating & Reviews: Share your cooking experience and read insights from others
Responsive Design: Enjoy a seamless experience across desktop, tablet, and mobile devices
Technical Features
Secure Authentication: Email-based user authentication system
Cloud Storage: Firebase integration for reliable data storage and retrieval
API Integration: Connects with Spoonacular API for extensive recipe data
Admin Dashboard: Comprehensive tools for content management and user oversight
Scalable Architecture: Designed to handle growing user base and content library

🛠️ Technology Stack
Frontend
HTML5, CSS3, JavaScript
Bootstrap 5 for responsive design
Font Awesome icons
Backend
Python with Flask framework
Jinja2 templating engine
Database & Storage
Firebase Firestore for NoSQL database
Firebase Storage for image management
Authentication
Firebase Authentication
External APIs
Spoonacular Recipe API

🖼️ User Interface
RecipeHub features an intuitive, clean interface designed for both usability and aesthetic appeal:
Homepage: Showcases featured recipes and provides quick navigation
Recipe Detail Pages: Comprehensive display of recipe information with ratings and reviews
User Profiles: Personal space to manage saved recipes and past reviews
Search Results: Clean grid layout with filtering options
Admin Dashboard: Data visualization and management tools

💻 Installation & Setup
Prerequisites
Python 3.8 or higher
Git
Firebase account
Spoonacular API key
Setup Instructions
Clone the repository
Apply to account.html
Install dependencies
Apply to account.html
Configure Firebase
Create a project in Firebase Console
Enable Authentication, Firestore, and Storage
Download the service account key and save as firebase-key.json in the project root
Set up environment variables
Create a .env file in the project root
Add the following variables:
Apply to account.html
Run the application
Apply to account.html
Access the application at http://localhost:5000

📁 Project Structure
RecipeHub/
├── app.py                 # Main Flask application
├── static/                # Static assets
│   ├── css/               # Stylesheets
│   ├── js/                # JavaScript files
│   └── img/               # Images and icons
├── templates/             # HTML templates
│   ├── base.html          # Base template with common elements
│   ├── index.html         # Homepage
│   ├── recipe_detail.html # Recipe detail page
│   ├── login.html         # Authentication pages
│   └── admin.html         # Admin dashboard
├── scripts/               # Utility scripts
│   └── fetch_recipes.py   # Script to import recipes from API
└── requirements.txt       # Python dependencies

Apply to account.html

🔒 Security Features
Secure user authentication with Firebase
Protected admin routes with role-based access control
Secure handling of API keys and sensitive information
Input validation and sanitization to prevent common vulnerabilities

📊 Admin Capabilities
The Admin Dashboard provides powerful tools for site management:
User management
Content moderation
Analytics and statistics
Bulk recipe imports
Review monitoring

🔍 Future Enhancements
We're continuously improving RecipeHub with plans for:
Meal planning calendar
Nutritional tracking
Shopping list generation
Recipe recommendation engine
Social sharing capabilities
