# CSV Schemas

All three templates are downloadable pre-filled from the app itself
(`/api/templates/salary`, `/api/templates/projection`, `/api/templates/results`, or the
"Download template" link on the relevant page) so you always have an exact, current example to
start from.

## Column matching

Headers are matched case-insensitively and with punctuation/spacing normalized, plus a small
list of common aliases per column (e.g. `Sal` or `Salary` both match `salary`; `Own%` or `own`
both match `projected_ownership`). If a required column can't be matched, the import is
rejected up front with the exact list of missing columns — nothing is partially imported.
Unrecognized extra columns are ignored and reported, not silently dropped without notice.

## Row-level validation

Every row is validated independently. A row with an error is skipped and reported (row number
+ every problem found on that row); rows without errors are still imported even if other rows
in the same file failed. Duplicate rows (same primary key — `player_id` for salary/projection)
are deduplicated, keeping the first occurrence, and the count of removed duplicates is shown.

---

## A. Salary CSV

One salary CSV describes exactly one slate (all rows must share the same `slate_id`). Importing
it creates or updates that `Slate` and upserts every player in it.

| Column            | Required | Validation                                                        |
| ------------------ | -------- | -------------------------------------------------------------------- |
| `slate_id`         | yes      | Non-empty. Must be identical across every row in the file.            |
| `slate_name`       | yes      | Non-empty.                                                             |
| `sport`            | no       | Defaults to `NFL`.                                                     |
| `contest_date`     | yes      | Must parse as a date/time.                                             |
| `player_id`        | yes      | Non-empty, unique within the file (duplicates are removed).            |
| `player_name`      | yes      | Non-empty.                                                             |
| `team`              | yes      | Non-empty (upper-cased on import).                                     |
| `opponent`          | yes      | Non-empty (upper-cased on import).                                     |
| `position`          | yes      | One of `QB`, `RB`, `WR`, `TE`, `DST`.                                   |
| `roster_positions`  | no       | Free text (e.g. `RB/FLEX`); falls back to `position` if blank.         |
| `salary`            | yes      | Positive integer, ≤ 100,000.                                            |
| `game_info`         | no       | Free text, shown throughout the UI (e.g. `AAA@BBB 1:00PM`).            |
| `start_time`        | no       | Parsed as a date/time if present.                                       |
| `status`            | no       | Defaults to `ACTIVE` (e.g. `QUESTIONABLE`, `OUT`).                     |

## B. Projection CSV

Attaches to whichever slate is currently active in the app. Import the same slate's projection
CSV from multiple sources (label each import differently) to blend them in the Projection Lab.

| Column                       | Required | Validation                                                                 |
| ------------------------------ | -------- | ------------------------------------------------------------------------------ |
| `player_id`                    | yes      | Must match a `player_id` from that slate's salary import to take effect.        |
| `player_name`                  | yes      | Non-empty.                                                                      |
| `projected_points`              | yes      | Numeric, 0–100.                                                                  |
| `floor`                         | no       | Numeric, 0–120; **must not exceed `projected_points`** (flagged as an impossible value). |
| `ceiling`                       | no       | Numeric, 0–120; **must not be below `projected_points`** (flagged as an impossible value). |
| `standard_deviation`            | no       | Numeric, 0–60. Required (on at least one player) to use the Simulation Lab.       |
| `projected_ownership`           | no       | Numeric, 0–100 (percent).                                                        |
| `expected_minutes_or_snaps`     | no       | Numeric, 0–100. Informational.                                                    |
| `target_share_or_usage`        | no       | Numeric, 0–100. Informational.                                                    |
| `notes`                         | no       | Free text.                                                                       |
| `projection_source`             | no       | Free text label; defaults to `User Upload`.                                       |
| `last_updated`                  | no       | Parsed as a date/time if present.                                                |

## C. Results CSV

Rows reference a slate by its `slate_id` — import that slate's salary CSV first, or the row is
skipped with an explanation.

| Column                  | Required | Validation                                          |
| -------------------------- | -------- | ------------------------------------------------------ |
| `slate_id`                 | yes      | Must match a previously-imported slate's `slate_id`.     |
| `contest_name`             | yes      | Non-empty.                                              |
| `contest_type`             | yes      | Free text (e.g. `GPP`, `Cash`, `Double-Up`, `3-Max`).    |
| `field_size`               | no       | Numeric.                                                |
| `entry_fee`                | yes      | Numeric (dollars).                                      |
| `number_of_entries`        | yes      | Non-negative integer.                                    |
| `total_entry_fees`         | no       | Numeric; defaults to `entry_fee × number_of_entries`.     |
| `total_winnings`           | no       | Numeric; defaults to 0.                                  |
| `net_profit_loss`          | no       | Numeric; defaults to `total_winnings − total_entry_fees`. |
| `lineup_id`                | no       | Free text — your own reference, stored as-is.             |
| `final_rank`               | no       | Numeric.                                                |
| `lineup_points`            | no       | Numeric.                                                |
| `cash_line`                | no       | Numeric.                                                |
| `top_one_percent_line`     | no       | Numeric.                                                |
| `notes`                    | no       | Free text.                                              |

## Data provenance

Every import is recorded in an `ImportBatch` (kind, source label, file name, row/error counts,
timestamp) visible on the slate's data page, and in the account-wide audit log on the Settings
page — so you can always tell whether a number in the app came from a specific upload and when.
