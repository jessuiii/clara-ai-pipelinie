# Changelog: acc_demo_1

**Generated:** 2026-03-03T12:58:04.451979Z
**Version:** v1 → v2
**Summary:** 5 field(s) updated during onboarding

## Changes

### `business_hours.days`
- **Before:** `['Mon', 'Tue', 'Wed', 'Thu', 'Fri']`
- **After:** `['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']`
- **Type:** list_updated

### `emergency_definition`
- **Before:** `['burst pipe', 'no water pressure', 'sewage backup', 'flooding', 'gas smell near plumbing fixtures']`
- **After:** `['burst pipe', 'no water pressure', 'sewage backup', 'flooding', 'gas smell near plumbing fixtures', 'water heater failure']`
- **Type:** list_updated

### `emergency_routing_rules.primary_contact`
- **Before:** `Dave Kowalski 713-555-0192`
- **After:** `Lisa Nguyen 713-555-0288`
- **Type:** value_updated

### `emergency_routing_rules.secondary_contact`
- **Before:** `dispatch line 713-555-0100`
- **After:** `Dave Kowalski 713-555-0192`
- **Type:** value_updated

### `notes`
- **Before:** `Saturday morning hours are sometimes open but not guaranteed.`
- **After:** `Saturday hours 8am-2pm Central. Weeknight emergencies: Dave Kowalski first, Lisa Nguyen secondary. Weekend emergencies: Lisa Nguyen first, Dave Kowalski secondary. Agent must confirm caller's full address for any emergency.`
- **Type:** value_updated

