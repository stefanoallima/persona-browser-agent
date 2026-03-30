# PB Feature Rubric v1.0

## Overview

This rubric defines how the **Visual Scorer** and **Text Scorer** evaluate pages in the persona-browser agent.

### Feature-Based Activation

There is **no page-type classification**. Instead, each feature category activates automatically based on what is detected on the page:

- Feature categories are activated when their trigger conditions are met (e.g., form fields visible, nav elements visible).
- Multiple categories can be active simultaneously on a single page.
- The `BASELINE` category **always applies** regardless of page content.

### Criterion Result Values

Each criterion produces one of:

| Value | Meaning |
|-------|---------|
| `PASS` | Criterion is satisfied |
| `FAIL` | Criterion is not satisfied |
| `UNKNOWN` | Cannot be determined (insufficient signal) |

### Deal-Breaker Confidence Rule

| Confidence | Effect |
|------------|--------|
| `high` | Instant FAIL — the entire feature score is failed regardless of other criteria |
| `medium` | -20 penalty applied to the feature score |

---

## Feature Categories

---

## 1. FORMS

**Activation:** Activates when form fields are visible on the page.

### Labels & Inputs

| ID | Criterion | Scorer |
|----|-----------|--------|
| `forms.labels_visible` | Every input field has a visible, associated label | Visual |
| `forms.required_marked` | Required fields are visually distinguished (e.g., asterisk or label text) | Visual |
| `forms.input_types_match` | Input types match expected data (e.g., email field uses email input, date uses date picker) | Text + Visual |
| `forms.tab_order` | Tab order follows logical reading order through the form | Text + Visual |

### Validation & Errors

| ID | Criterion | Scorer |
|----|-----------|--------|
| `forms.error_on_empty_submit` | Submitting an empty required field triggers a validation error | Text + Visual |
| `forms.error_on_invalid` | Submitting an invalid value (e.g., bad email format) triggers a validation error | Text + Visual |
| `forms.error_near_field` | Error messages appear in close proximity to the field that caused them | Visual |
| `forms.error_specific` | Error messages describe what is wrong, not just that something is wrong | Text |
| `forms.error_clears` | Error messages disappear once the user corrects the field | Text + Visual |
| `forms.data_preserved_on_error` | Previously entered valid data is preserved after a validation error | Text + Visual |

### Submission

| ID | Criterion | Scorer |
|----|-----------|--------|
| `forms.submit_visible` | The submit button is visible and clearly labeled | Visual |
| `forms.loading_state` | A loading/in-progress state is shown while the form is submitting | Visual |
| `forms.success_confirmation` | A clear success confirmation is shown after successful submission | Text + Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `forms.db_empty_submit` | Form submits successfully with all required fields empty | high |
| `forms.db_data_lost` | User-entered data is silently discarded on error or navigation | high |
| `forms.db_no_error_recovery` | After a submission error, the user has no path to correct and resubmit | high |

---

## 2. NAVIGATION

**Activation:** Activates when navigation elements (nav bars, menus, breadcrumbs, links) are visible.

### Criteria

| ID | Criterion | Scorer |
|----|-----------|--------|
| `nav.current_indicated` | The currently active page or section is visually indicated in the navigation | Visual |
| `nav.logo_links_home` | Clicking the site logo navigates the user to the home/root page | Text + Visual |
| `nav.no_dead_ends` | Every navigable page provides a path back or forward; no dead-end pages | Text + Visual |
| `nav.back_works` | The browser back button returns the user to the previous state without errors | Text + Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `nav.db_404` | A navigation link leads to a 404 or broken page | high |
| `nav.db_trapped` | The user reaches a page with no navigation out and no browser history to go back to | high |

---

## 3. CTA

**Activation:** Activates when call-to-action buttons are visible.

### Criteria

| ID | Criterion | Scorer |
|----|-----------|--------|
| `cta.prominent` | The primary CTA is visually prominent and stands out from surrounding content | Visual |
| `cta.text_clear` | The CTA label clearly communicates what will happen when clicked | Text |
| `cta.destination_correct` | The CTA navigates or triggers the expected action or destination | Text + Visual |
| `cta.no_competing` | There are no competing CTAs of equal weight that create choice paralysis | Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `cta.db_nonfunctional` | The primary CTA button does nothing when clicked | high |

---

## 4. DATA_DISPLAY

**Activation:** Activates when tables, cards, or lists are visible.

### Criteria

| ID | Criterion | Scorer |
|----|-----------|--------|
| `data.above_fold` | Key data or the primary data container is visible without scrolling | Visual |
| `data.grouped_logically` | Related data items are visually grouped together | Visual |
| `data.empty_states` | Empty states (no data) are handled with a meaningful message rather than a blank area | Text + Visual |
| `data.loading_indicator` | A loading indicator is shown while data is being fetched | Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `data.db_wrong` | Data displayed is factually incorrect or does not match the source of truth | high |
| `data.db_unreachable` | The data container is present but permanently empty or inaccessible due to an error | high |

---

## 5. ERROR_STATES

**Activation:** Activates when error messages are visible on the page.

### Criteria

| ID | Criterion | Scorer |
|----|-----------|--------|
| `error.plain_language` | Error messages are written in plain language the user can understand | Text |
| `error.recovery_path` | Each error message provides or implies a clear path to recovery | Text |
| `error.no_jargon` | Error messages contain no technical jargon, stack traces, or internal codes visible to the user | Text |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `error.db_blank` | An error condition occurs but no error message is shown to the user | high |
| `error.db_no_recovery` | An error state is shown but there is no way for the user to recover or retry | high |

---

## 6. BASELINE

**Activation:** ALWAYS applies — this category is active on every page regardless of other detected features.

### Criteria

| ID | Criterion | Scorer |
|----|-----------|--------|
| `baseline.no_errors` | No unhandled JavaScript errors or crash states are present | Text + Visual |
| `baseline.readable` | All text content is legible (sufficient contrast, no truncation of key content) | Visual |
| `baseline.no_broken_assets` | No broken images, missing icons, or failed CSS assets are visible | Visual |
| `baseline.responsive` | The layout is not broken at the current viewport size | Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `baseline.db_blank` | The page is completely blank or fails to render any meaningful content | high |
| `baseline.db_console_errors` | Unhandled errors in the console indicate a critical runtime failure affecting the user experience | high |

---

## 7. TASK_COMPLETION

**Activation:** Activates when `network_log` contains API calls **AND** `codeintel` has `api_endpoints`.

### End-to-End

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.backend_outcome` | The intended backend operation (create, update, delete, fetch) completed successfully | Network Verifier |
| `task.data_on_next_page` | Data submitted or created appears correctly on the subsequent page or state | Text + Visual |
| `task.api_status_correct` | API responses return the expected HTTP status codes for each operation | Network Verifier |
| `task.no_network_errors` | No network-level errors (5xx, timeouts, CORS failures) occurred during the task | Network Verifier |

### Data Persistence

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.survives_refresh` | Data created or modified persists correctly after a page refresh | Text + Visual |
| `task.data_consistent` | The same data appears consistently across all views that display it | Text + Visual |
| `task.loading_resolves` | Loading states eventually resolve to data or a meaningful empty/error state | Visual |

### Auth

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.auth_access` | Authenticated users can access all content and actions they are authorized for | Text + Visual |
| `task.auth_persists_nav` | Authentication state is maintained when navigating between pages | Text + Visual |
| `task.auth_persists_refresh` | Authentication state is maintained after a page refresh | Text + Visual |
| `task.unauth_redirect` | Unauthenticated users are redirected to the login page when accessing protected routes | Text + Visual |

### Backend-Frontend Integration

| ID | Criterion | Scorer |
|----|-----------|--------|
| `task.data_matches_api` | Data displayed in the UI matches the data returned by the API | Network Verifier + Text |
| `task.error_matches_api` | Error messages shown to the user correspond to actual error responses from the API | Network Verifier + Text |
| `task.loading_during_async` | A loading state is shown for the entire duration of any async API call | Visual |
| `task.graceful_error_handling` | API errors are caught and displayed as user-friendly messages, not raw error objects | Text + Visual |

### Deal-Breakers

| ID | Criterion | Confidence Required |
|----|-----------|---------------------|
| `task.db_silent_fail` | An operation appears to succeed in the UI but fails silently on the backend | high |
| `task.db_data_lost` | Data submitted by the user is not persisted and is permanently lost | high |
| `task.db_wrong_auth` | A user gains access to resources or actions they are not authorized for | high |
| `task.db_no_result` | A task that should produce a visible result produces nothing, with no error shown | high |
| `task.db_500` | A backend 500 error occurs and is not gracefully handled | high |
| `task.db_success_but_fail` | The UI reports success but the intended outcome is not reflected in the system state | high |
