const express = require('express');
const cookieParser = require('cookie-parser');

const app = express();
const PORT = process.env.PORT || 3333;

// In-memory stores
const users = {}; // { email: { user_id, name, password } }
const sessions = {}; // { sessionId: email }

// Middleware
app.use(express.json());
app.use(cookieParser());

// Helper: Generate unique ID
function generateId() {
  return 'user_' + Math.random().toString(36).substr(2, 9);
}

// Helper: Generate session ID
function generateSessionId() {
  return 'session_' + Math.random().toString(36).substr(2, 16);
}

// Helper: Get user from session cookie
function getUserFromSession(req) {
  const sessionId = req.cookies.session;
  if (!sessionId || !sessions[sessionId]) {
    return null;
  }
  const email = sessions[sessionId];
  return users[email] || null;
}

// GET / - Redirect to /register
app.get('/', (req, res) => {
  res.redirect('/register');
});

// GET /register - HTML signup form
app.get('/register', (req, res) => {
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Register</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
      padding: 40px;
      width: 100%;
      max-width: 400px;
    }
    h1 {
      font-size: 28px;
      margin-bottom: 30px;
      color: #333;
      text-align: center;
    }
    .form-group {
      margin-bottom: 20px;
    }
    label {
      display: block;
      margin-bottom: 8px;
      color: #555;
      font-weight: 500;
    }
    input {
      width: 100%;
      padding: 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      transition: border-color 0.3s;
    }
    input:focus {
      outline: none;
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    button {
      width: 100%;
      padding: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    button:hover {
      transform: translateY(-2px);
      box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    button:active {
      transform: translateY(0);
    }
    .error {
      color: #e74c3c;
      font-size: 14px;
      margin-top: 10px;
      padding: 10px;
      background: #fadbd8;
      border-radius: 4px;
      border-left: 4px solid #e74c3c;
      display: none;
    }
    .error.show {
      display: block;
    }
    .loading {
      display: none;
      text-align: center;
      color: #667eea;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Create Account</h1>
    <form id="registerForm">
      <div class="form-group">
        <label for="name">Full Name</label>
        <input type="text" id="name" name="name" required>
      </div>
      <div class="form-group">
        <label for="email">Email Address</label>
        <input type="email" id="email" name="email" required>
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" required minlength="8">
      </div>
      <div id="error" class="error"></div>
      <div id="loading" class="loading">Registering...</div>
      <button type="submit">Register</button>
    </form>
  </div>
  <script>
    const form = document.getElementById('registerForm');
    const errorDiv = document.getElementById('error');
    const loadingDiv = document.getElementById('loading');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const name = document.getElementById('name').value;
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;

      errorDiv.classList.remove('show');
      loadingDiv.style.display = 'block';

      try {
        const response = await fetch('/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (response.ok) {
          window.location.href = '/dashboard';
        } else {
          throw new Error(data.message || 'Registration failed');
        }
      } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.classList.add('show');
        loadingDiv.style.display = 'none';
      }
    });
  </script>
</body>
</html>
  `;
  res.send(html);
});

// POST /api/auth/register - Register user
app.post('/api/auth/register', (req, res) => {
  const { name, email, password } = req.body;

  // Validate required fields
  if (!name || !email || !password) {
    return res.status(400).json({
      message: 'Missing required fields: name, email, password'
    });
  }

  // Validate password length
  if (password.length < 8) {
    return res.status(400).json({
      message: 'Password must be at least 8 characters long'
    });
  }

  // Check for duplicate email
  if (users[email]) {
    return res.status(409).json({
      message: 'Email already registered'
    });
  }

  // Create user
  const user_id = generateId();
  users[email] = {
    user_id,
    name,
    email,
    password // In production, this would be hashed
  };

  // Create session
  const sessionId = generateSessionId();
  sessions[sessionId] = email;

  // Set httpOnly cookie
  res.cookie('session', sessionId, {
    httpOnly: true,
    secure: false, // Set to true in production with HTTPS
    sameSite: 'strict',
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  });

  res.status(201).json({ user_id });
});

// GET /api/user/me - Get current user
app.get('/api/user/me', (req, res) => {
  const user = getUserFromSession(req);

  if (!user) {
    return res.status(401).json({
      message: 'Not authenticated'
    });
  }

  res.json({
    name: user.name,
    email: user.email
  });
});

// GET /dashboard - Dashboard page
app.get('/dashboard', (req, res) => {
  const user = getUserFromSession(req);

  if (!user) {
    return res.redirect('/register');
  }

  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }
    .card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
      padding: 40px;
      width: 100%;
      max-width: 500px;
      text-align: center;
    }
    h1 {
      font-size: 28px;
      margin-bottom: 20px;
      color: #333;
    }
    .user-info {
      background: #f8f9fa;
      padding: 20px;
      border-radius: 4px;
      margin: 20px 0;
      text-align: left;
    }
    .info-row {
      margin: 10px 0;
      color: #555;
    }
    .label {
      font-weight: 600;
      color: #333;
    }
    .loading {
      color: #667eea;
      font-size: 16px;
    }
    .error {
      color: #e74c3c;
      padding: 10px;
      background: #fadbd8;
      border-radius: 4px;
      border-left: 4px solid #e74c3c;
      margin: 10px 0;
    }
    button {
      margin-top: 20px;
      padding: 12px 30px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    button:hover {
      transform: translateY(-2px);
      box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Welcome!</h1>
    <div class="user-info">
      <div id="content" class="loading">Loading user data...</div>
      <div id="error" class="error" style="display: none;"></div>
    </div>
    <button onclick="logout()">Logout</button>
  </div>
  <script>
    async function loadUserData() {
      try {
        const response = await fetch('/api/user/me');

        if (response.ok) {
          const data = await response.json();
          document.getElementById('content').innerHTML = \`
            <div class="info-row">
              <span class="label">Name:</span> \${data.name}
            </div>
            <div class="info-row">
              <span class="label">Email:</span> \${data.email}
            </div>
          \`;
        } else {
          throw new Error('Failed to load user data');
        }
      } catch (err) {
        const errorDiv = document.getElementById('error');
        errorDiv.textContent = err.message;
        errorDiv.style.display = 'block';
        document.getElementById('content').style.display = 'none';
      }
    }

    function logout() {
      window.location.href = '/register';
    }

    loadUserData();
  </script>
</body>
</html>
  `;
  res.send(html);
});

// Start server
app.listen(PORT, () => {
  console.log(`Test app listening on http://localhost:${PORT}`);
});
