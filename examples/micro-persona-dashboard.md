# Micro-Persona: T05 — Dashboard Consumer

## Identity
- **Consumer**: Logged-in user checking their account status
- **Task**: T05 — Implement user dashboard
- **Expectation**: See an overview of account activity, navigate to key sections

## Contract
The dashboard MUST:
- Show: user name/avatar, key metrics (orders, notifications, recent activity)
- Navigation: quick links to profile, orders, settings
- Data: real content (not placeholder "Lorem ipsum" or empty states with no guidance)
- Responsive: works on desktop and tablet widths

## Deal-Breakers
- Dashboard shows no data and no explanation (blank page)
- Navigation leads to 404 pages
- User can't tell which section they're in

## Verification Rubric

### CONTRACT (must ALL pass)
- [ ] User name displayed
- [ ] At least 2 key metrics visible
- [ ] Navigation to profile works
- [ ] Navigation to orders works
- [ ] Navigation to settings works

### ERROR HANDLING (must ALL pass)
- [ ] Empty state for new users shows helpful guidance
- [ ] Failed data load shows error message (not blank)

### EDGE CASES (must ALL pass)
- [ ] Very long username doesn't overflow layout
- [ ] Dashboard with 0 orders shows empty state
- [ ] Dashboard with 100+ notifications doesn't break

### BEHAVIORAL (95%+ must pass)
- [ ] Current section highlighted in navigation
- [ ] Page loads within 2 seconds
- [ ] Responsive layout at 768px width
- [ ] Interactive elements have hover/focus states
