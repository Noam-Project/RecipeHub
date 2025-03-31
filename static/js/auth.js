// Firebase Authentication utilities

// Sign up with email/password
async function signUp(email, password, displayName) {
  console.log("Attempting signup for:", email);
  try {
    const userCredential = await firebase.auth().createUserWithEmailAndPassword(email, password);
    
    // Update profile with display name
    await userCredential.user.updateProfile({
      displayName: displayName
    });
    
    // Create user document in Firestore
    await createUserDocument(userCredential.user.uid, email, displayName);
    
    console.log("User created successfully:", userCredential.user.uid);
    
    // Show success message
    const errorElement = document.getElementById('signupError');
    if (errorElement) {
      errorElement.textContent = "Account created successfully! Redirecting...";
      errorElement.classList.remove('d-none', 'alert-danger');
      errorElement.classList.add('alert-success');
    }
    
    // The redirect will be handled by onAuthStateChanged
    return userCredential;
  } catch (error) {
    console.error("Signup error:", error);
    throw error;
  }
}

// Create user document in Firestore
async function createUserDocument(uid, email, displayName) {
  console.log("Creating user document for:", uid);
  try {
    await firebase.firestore().collection('users').doc(uid).set({
      email: email,
      display_name: displayName,
      created_at: firebase.firestore.FieldValue.serverTimestamp(),
      is_admin: false
    });
    console.log("User document created successfully");
  } catch (error) {
    console.error("Error creating user document:", error);
    throw error;
  }
}

// Sign in with email/password
async function signIn(email, password) {
  console.log("Attempting login for:", email);
  try {
    const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
    console.log("Login successful for:", email);
    
    // Show success message
    const errorElement = document.getElementById('loginError');
    if (errorElement) {
      errorElement.textContent = "Login successful! Redirecting...";
      errorElement.classList.remove('d-none', 'alert-danger');
      errorElement.classList.add('alert-success');
    }
    
    return userCredential;
  } catch (error) {
    console.error("Login error:", error);
    throw error;
  }
}

// Sign out
async function signOut() {
  try {
    // First clear the session on the server
    await fetch('/api/logout', {
      method: 'POST',
    });
    
    // Then sign out from Firebase
    await firebase.auth().signOut();
    
    // Redirect to home
    window.location.href = '/';
  } catch (error) {
    console.error("Logout error:", error);
    throw error;
  }
}

// Auth state observer
firebase.auth().onAuthStateChanged((user) => {
  console.log("Auth state changed. User:", user ? user.uid : "signed out");
  
  if (user) {
    // User is signed in
    
    // Check if we need to create a session on server
    if (!sessionStorage.getItem('authStatus')) {
      console.log("Creating server session for user:", user.uid);
      
      // Get the ID token
      user.getIdToken().then((idToken) => {
        // Send the token to your server
        fetch('/api/create-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ idToken: idToken }),
        })
        .then(response => response.json())
        .then(data => {
          console.log('Session created:', data);
          sessionStorage.setItem('authStatus', 'authenticated');
          
          // Check if we're on login or signup page and redirect to home
          const currentPath = window.location.pathname;
          if (currentPath === '/login' || currentPath === '/signup') {
            console.log("Redirecting to homepage after authentication");
            window.location.href = '/';
          } else {
            // Otherwise, just reload to update UI based on auth state
            window.location.reload();
          }
        })
        .catch(error => {
          console.error('Error creating session:', error);
          
          // Still try to redirect if on login/signup pages
          const currentPath = window.location.pathname;
          if (currentPath === '/login' || currentPath === '/signup') {
            window.location.href = '/';
          }
        });
      });
    }
  } else {
    // User is signed out
    console.log('User is signed out');
    sessionStorage.removeItem('authStatus');
  }
});

// DOM event listeners for authentication
document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM loaded, setting up auth event listeners");
  
  // Logout functionality
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function(e) {
      e.preventDefault();
      signOut();
    });
  }
  
  // Connect signup form if it exists
  const signupForm = document.getElementById('signupForm');
  if (signupForm) {
    console.log("Signup form found, attaching event listener");
    
    signupForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const displayName = document.getElementById('displayName').value;
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      const confirmPassword = document.getElementById('confirmPassword').value;
      const errorElement = document.getElementById('signupError');
      
      // Hide any previous errors
      if (errorElement) {
        errorElement.textContent = "";
        errorElement.classList.add('d-none');
      }
      
      // Validate form fields
      if (!displayName || !email || !password || !confirmPassword) {
        if (errorElement) {
          errorElement.textContent = "All fields are required";
          errorElement.classList.remove('d-none');
          errorElement.classList.add('alert-danger');
        }
        return;
      }
      
      // Validate passwords match
      if (password !== confirmPassword) {
        if (errorElement) {
          errorElement.textContent = "Passwords don't match";
          errorElement.classList.remove('d-none');
          errorElement.classList.add('alert-danger');
        }
        return;
      }
      
      // Validate password length
      if (password.length < 6) {
        if (errorElement) {
          errorElement.textContent = "Password must be at least 6 characters long";
          errorElement.classList.remove('d-none');
          errorElement.classList.add('alert-danger');
        }
        return;
      }
      
      // Show loading state
      const submitBtn = signupForm.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating account...';
      }
      
      // Sign up with email and password
      signUp(email, password, displayName)
        .then(() => {
          console.log("Signup successful, waiting for redirect from onAuthStateChanged");
          // Redirect will be handled by onAuthStateChanged
        })
        .catch((error) => {
          // Re-enable button
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Create Account';
          }
          
          // Show error message
          if (errorElement) {
            errorElement.textContent = error.message;
            errorElement.classList.remove('d-none', 'alert-success');
            errorElement.classList.add('alert-danger');
          }
        });
    });
  }
  
  // Connect login form if it exists
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    console.log("Login form found, attaching event listener");
    
    loginForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      const errorElement = document.getElementById('loginError');
      
      // Hide any previous errors
      if (errorElement) {
        errorElement.textContent = "";
        errorElement.classList.add('d-none');
      }
      
      // Validate form fields
      if (!email || !password) {
        if (errorElement) {
          errorElement.textContent = "Email and password are required";
          errorElement.classList.remove('d-none');
          errorElement.classList.add('alert-danger');
        }
        return;
      }
      
      // Show loading state
      const submitBtn = loginForm.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Logging in...';
      }
      
      // Sign in with email and password
      signIn(email, password)
        .then(() => {
          console.log("Login successful, waiting for redirect from onAuthStateChanged");
          // Redirect is handled by onAuthStateChanged
        })
        .catch((error) => {
          // Re-enable button
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Login';
          }
          
          // Show error message
          if (errorElement) {
            errorElement.textContent = error.message;
            errorElement.classList.remove('d-none', 'alert-success');
            errorElement.classList.add('alert-danger');
          }
        });
    });
  }
  
  // Connect Google login/signup buttons
  const googleLoginBtn = document.getElementById('googleLogin');
  if (googleLoginBtn) {
    googleLoginBtn.addEventListener('click', function() {
      const errorElement = document.getElementById('loginError');
      if (errorElement) {
        errorElement.classList.add('d-none');
      }
      
      // Show loading state
      googleLoginBtn.disabled = true;
      googleLoginBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Connecting to Google...';
      
      signInWithGoogle()
        .then(() => {
          // Redirect is handled by onAuthStateChanged
        })
        .catch((error) => {
          // Re-enable button
          googleLoginBtn.disabled = false;
          googleLoginBtn.innerHTML = '<i class="fab fa-google me-2"></i>Sign in with Google';
          
          // Show error message
          if (errorElement) {
            errorElement.textContent = error.message;
            errorElement.classList.remove('d-none');
          }
        });
    });
  }
  
  const googleSignupBtn = document.getElementById('googleSignup');
  if (googleSignupBtn) {
    googleSignupBtn.addEventListener('click', function() {
      const errorElement = document.getElementById('signupError');
      if (errorElement) {
        errorElement.classList.add('d-none');
      }
      
      // Show loading state
      googleSignupBtn.disabled = true;
      googleSignupBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Connecting to Google...';
      
      signInWithGoogle()
        .then(() => {
          // Redirect is handled by onAuthStateChanged
        })
        .catch((error) => {
          // Re-enable button
          googleSignupBtn.disabled = false;
          googleSignupBtn.innerHTML = '<i class="fab fa-google me-2"></i>Sign up with Google';
          
          // Show error message
          if (errorElement) {
            errorElement.textContent = error.message;
            errorElement.classList.remove('d-none');
          }
        });
    });
  }
  
  // Connect reset password functionality
  const resetPasswordBtn = document.getElementById('resetPassword');
  if (resetPasswordBtn) {
    resetPasswordBtn.addEventListener('click', function(e) {
      e.preventDefault();
      
      const email = document.getElementById('email').value;
      if (!email) {
        alert('Please enter your email address');
        return;
      }
      
      firebase.auth().sendPasswordResetEmail(email)
        .then(() => {
          alert('Password reset email sent. Check your inbox.');
        })
        .catch((error) => {
          alert('Error: ' + error.message);
        });
    });
  }
});