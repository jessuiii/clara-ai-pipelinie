# Changelog: acc_4

**Generated:** 2026-03-03T13:43:11.191822Z
**Version:** v1 → v2
**Summary:** 9 field(s) updated during onboarding

## Changes

### `after_hours_flow_summary`
- **Before:** `Emergency calls go to Kyle Ramos; if no answer in 45s, answering service pages him. Non-emergency: take message for next-day callback.`
- **After:** `Emergency calls go to Diane Foster; if no answer in 45s, answering service pages her. Non-emergency: take message for next-day callback.`
- **Type:** value_updated

### `business_hours.days`
- **Before:** `['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']`
- **After:** `['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']`
- **Type:** list_updated

### `call_transfer_rules.if_transfer_fails`
- **Before:** `answering service pages Kyle`
- **After:** `answering service pages Diane`
- **Type:** value_updated

### `emergency_routing_rules.fallback`
- **Before:** `answering service pages Kyle`
- **After:** `answering service pages Diane`
- **Type:** value_updated

### `emergency_routing_rules.primary_contact`
- **Before:** `Kyle Ramos 602-555-0850`
- **After:** `Diane Foster 602-555-0920`
- **Type:** value_updated

### `integration_constraints`
- **Before:** `['never add customers or create service orders in PestPac']`
- **After:** `['never add customers or create service orders in PestPac', 'never give out technician home addresses to callers']`
- **Type:** list_updated

### `notes`
- **Before:** `Closed Sundays; human approval required for all PestPac actions`
- **After:** `Closed Sundays except 9am-3pm for residential; human approval required for all PestPac actions; never give out technician home addresses`
- **Type:** value_updated

### `office_hours_flow_summary`
- **Before:** `Take message for next-day callback; no transfers or order creation in PestPac.`
- **After:** `Take message for next-day callback; no transfers or order creation in PestPac. Sunday 9am-3pm residential calls only.`
- **Type:** value_updated

### `services_supported`
- **Before:** `['commercial pest control', 'residential pest control', 'termite treatment', 'rodent exclusion', 'bed bug remediation']`
- **After:** `['commercial pest control', 'residential pest control', 'termite treatment', 'rodent exclusion', 'bed bug remediation', 'bird exclusion', 'bat exclusion']`
- **Type:** list_updated

