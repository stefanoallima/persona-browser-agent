# Micro-Persona: T03 — Signup Form Consumer

## Identity
- **Consumer**: First-time visitor trying to create an account
- **Task**: T03 — Implement user registration page
- **Expectation**: Fill out a signup form and get confirmed as registered

## Contract
The registration page MUST:
- Accept: name, email, password, confirm password
- Validate: email format, password strength (8+ chars, 1 uppercase, 1 number)
- Show: clear error messages per field (not a single generic error)
- On success: redirect to dashboard or show welcome message
- On duplicate email: show "Email already registered" with link to login

## Deal-Breakers
- Form submits with empty required fields
- Password stored/shown in plain text
- No feedback after clicking "Register" (spinner or redirect)
- Broken on mobile viewport

## Verification Rubric

### CONTRACT (must ALL pass)
- [ ] Name field accepts text input
- [ ] Email field validates format
- [ ] Password field has strength requirements shown
- [ ] Confirm password must match password
- [ ] Submit button triggers validation
- [ ] Success state shows confirmation

### ERROR HANDLING (must ALL pass)
- [ ] Empty fields show "required" message
- [ ] Invalid email shows format hint
- [ ] Weak password shows specific requirement
- [ ] Mismatched passwords show clear error
- [ ] Duplicate email shows helpful message

### EDGE CASES (must ALL pass)
- [ ] Very long name (50+ chars) doesn't break layout
- [ ] Email with special chars (user+tag@domain.com) accepted
- [ ] Paste into password field works
- [ ] Form works with browser autofill

### BEHAVIORAL (95%+ must pass)
- [ ] Tab order follows visual layout
- [ ] Enter key submits form
- [ ] Error messages disappear when field is corrected
- [ ] Loading state shown during submission
- [ ] Form preserves input on validation error (doesn't clear fields)

## Form Data
```
name: Jordan Rivera
email: jordan.rivera@example.com
password: SecurePass123!
confirm_password: SecurePass123!
```
