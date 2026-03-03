# Changelog: acc_5

**Generated:** 2026-03-03T13:43:14.391320Z
**Version:** v1 → v2
**Summary:** 6 field(s) updated during onboarding

## Changes

### `after_hours_flow_summary`
- **Before:** `Contact field supervisor Dana Price for emergencies; if no answer try main dispatch; if still no answer take message and promise 2-hour callback for weather emergencies`
- **After:** `Contact field supervisor Dana Price for emergencies; if no answer try main dispatch; if still no answer take message and promise 4-hour callback for weather emergencies`
- **Type:** value_updated

### `business_hours.days`
- **Before:** `['Mon', 'Tue', 'Wed', 'Thu', 'Fri']`
- **After:** `['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']`
- **Type:** list_updated

### `call_transfer_rules.if_transfer_fails`
- **Before:** `promise callback within 2 hours for weather emergencies`
- **After:** `promise callback within 4 hours for weather emergencies`
- **Type:** value_updated

### `emergency_definition`
- **Before:** `['active water infiltration into a structure', 'structural damage from storm', 'fallen tree on roof', 'building unsafe']`
- **After:** `['active water infiltration into a structure', 'structural damage from storm', 'fallen tree on roof', 'building unsafe', 'hail damage assessment requests']`
- **Type:** list_updated

### `non_emergency_routing_rules.destination`
- **Before:** `Summit Roofing Group`
- **After:** `615-555-0050`
- **Type:** value_updated

### `notes`
- **Before:** `Saturday hours 8am-noon during busy season; storm damage is main emergency type`
- **After:** `Saturday hours 8am-noon year-round; storm damage is main emergency type`
- **Type:** value_updated

