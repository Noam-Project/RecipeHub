// Firebase configuration for RecipeHub
const firebaseConfig = {
  apiKey: "AIzaSyBG95SxEi8jVQOG4RGKSKuYqpo7yokkYF8",
  authDomain: "recipehub-36272.firebaseapp.com",
  databaseURL: "https://recipehub-36272-default-rtdb.firebaseio.com",
  projectId: "recipehub-36272",
  storageBucket: "recipehub-36272.firebasestorage.app",
  messagingSenderId: "1064891871096",
  appId: "1:1064891871096:web:f2475e3f6b980dcd86628d",
  measurementId: "G-M7KQVP9Y2Q"
};

// Initialize Firebase using compat API
firebase.initializeApp(firebaseConfig);

// Initialize Firestore
const db = firebase.firestore();

// Initialize Storage
const storage = firebase.storage();

// Initialize Analytics if available
if (firebase.analytics) {
  const analytics = firebase.analytics();
} 