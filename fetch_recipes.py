#!/usr/bin/env python3
"""
Recipe Fetcher Script
--------------------
A simple command line tool to fetch recipes from Spoonacular API
and store them in Firebase Firestore.

Usage:
  python fetch_recipes.py [--count COUNT]

Options:
  --count COUNT   Number of recipes to fetch (default: 30)
"""

import argparse
import os
import sys
from import_recipes import main as import_main

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Fetch recipes from Spoonacular API')
    parser.add_argument('--count', type=int, default=30,
                        help='Number of recipes to fetch (default: 30)')
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Set the recipe count environment variable
    os.environ['RECIPE_COUNT'] = str(args.count)
    
    print(f"Starting recipe import process. Requesting {args.count} recipes...")
    
    # Run the import process
    import_main()
    
    print("Recipe import process completed. Check recipe_import.log for details.")
    sys.exit(0) 