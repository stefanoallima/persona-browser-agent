# Consumer Rubric: poc-test-app-signup-dashboard

Generated from: specs.md, design.md, codebase analysis
Change scope: User registration flow and authenticated dashboard for the poc/test_app signup+dashboard application

## Registration Page
Identified by: Page with a "Create Account" heading and a registration form containing Full Name, Email Address, and Password fields

### Must Pass
- The page renders a form with exactly three visible input fields: Full Name (text), Email Address (email), and Password (password)
  (codeintel: pages[0].elements.forms[0].fields)
- Submitting the form with a valid unique name, email address, and password of at least 8 characters results in the browser navigating to /dashboard
  (codeintel: pages[0].elements.forms[0].on_success.redirect)
- Submitting the form with a password shorter than 8 characters shows an error message — the user stays on the registration page
  (codeintel: api_endpoints[0].responses.400 — "Password must be at least 8 characters long")
- Submitting the form with any required field left blank shows an error message — the user stays on the registration page
  (codeintel: api_endpoints[0].responses.400 — "Missing required fields: name, email, password")
- Submitting the form with an email address that was already registered shows an error message indicating the email is taken
  (codeintel: api_endpoints[0].responses.409 — "Email already registered")

### Should Pass
- After a validation error, previously entered values remain in the Name and Email fields so the user does not have to retype them
- The error message area is not visible on initial page load; it only appears after a failed submission attempt
- The submit button is labelled "Register"
  (codeintel: pages[0].elements.forms[0].submit_button.text)

### Deal-Breakers
- The form submits successfully (navigates away or shows success) when any required field (name, email, or password) is empty
- User data entered during registration is silently discarded — a subsequent visit to /dashboard shows no name or email
  (codeintel: data_flows[0])

## Dashboard Page
Identified by: Page with a "Welcome!" heading that displays the authenticated user's name and email address

### Must Pass
- The page displays the user's full name exactly as entered during registration, visible in the user info section
  (codeintel: api_endpoints[1].responses.200.body — name field)
- The page displays the user's email address exactly as entered during registration, visible in the user info section
  (codeintel: api_endpoints[1].responses.200.body — email field)
- A logout or navigation control (button labelled "Logout") is present on the page
  (codeintel: pages[1].elements.navigation.links[0])
- The page heading "Welcome!" is visible

### Should Pass
- The dashboard loads user data without the user seeing a persistent "Loading user data..." spinner — the name and email replace the loading state within a reasonable time
- The Name and Email labels are visually distinct from their values (e.g. bold labels followed by plain text values)

### Deal-Breakers
- The dashboard renders completely blank or shows only the loading text after a successful registration and redirect
- The name displayed on the dashboard does not match the name that was entered during registration
  (codeintel: data_flows[0].verification)
- An unauthenticated visitor (no session cookie) who navigates directly to /dashboard sees any dashboard content instead of being redirected to the registration page
  (codeintel: auth.protected_routes.frontend, auth.redirect_on_unauth)
