# Changelog: bens_electric

**Generated:** 2026-03-03T16:07:32.434454Z
**Version:** v1 → v2
**Summary:** 8 field(s) updated during onboarding

## Changes

### `after_hours_flow_summary`
- **Before:** `Ben is on call and may answer or defer to another service`
- **After:** `Clara answers, patches through to Ben if caller is from G and M pressure washing`
- **Type:** value_updated

### `business_hours.end`
- **Before:** `None`
- **After:** `4:30`
- **Type:** added

### `business_hours.start`
- **Before:** `None`
- **After:** `8:00`
- **Type:** added

### `emergency_definition`
- **Before:** `['emergency calls from regular property managers and general contractors']`
- **After:** `['emergency calls from regular property managers and general contractors', 'emergency calls from G and M pressure washing (for properties they manage, e.g. Chevron gas stations)']`
- **Type:** list_updated

### `emergency_routing_rules.fallback`
- **Before:** `defer to another service`
- **After:** `patch through to Ben if caller is from G and M pressure washing`
- **Type:** value_updated

### `notes`
- **Before:** `Ben has 30 years of experience as an electrician and has been running his own business for 8 years. He has a team of 3 full-time electricians and 1 apprentice, and uses Jobber as his CRM.`
- **After:** `Ben has a service call fee of $115, and an hourly charge of $98. Ben wants Clara to mention the service call fee if the caller inquires about it.`
- **Type:** value_updated

### `office_hours_flow_summary`
- **Before:** `Ben manages operations and answers calls`
- **After:** `Ben manages operations and answers calls, Clara answers and transfers to Ben if necessary`
- **Type:** value_updated

### `questions_or_unknowns`
- **Before:** `['What is the exact business hours and timezone?', 'What is the office address?']`
- **After:** `['What is the exact business hours and timezone?', 'What is the office address?', 'What is the exact timezone?']`
- **Type:** list_updated

