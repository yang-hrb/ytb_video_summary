
## Upstream Saving Process Instructions

### 1. How to Save Summary Files to the Correct Category Folder

When saving a new summary file, follow this path structure:

```
summary/{CATEGORY_FOLDER}/{CHANNEL_NAME}/{YYYY_MM}/{FILENAME}.md
```

**Step 1: Determine the Category Folder**

Based on the **first character** of the channel name:

| First Character | Category Folder |
|-----------------|-----------------|
| 0-9 (digit)     | `00_number`     |
| A or a          | `01_A_letter`   |
| B or b          | `02_B_letter`   |
| C or c          | `03_C_letter`   |
| D or d          | `04_D_letter`   |
| E or e          | `05_E_letter`   |
| F or f          | `06_F_letter`   |
| G or g          | `07_G_letter`   |
| H or h          | `08_H_letter`   |
| I or i          | `09_I_letter`   |
| J or j          | `10_J_letter`   |
| K or k          | `11_K_letter`   |
| L or l          | `12_L_letter`   |
| M or m          | `13_M_letter`   |
| N or n          | `14_N_letter`   |
| O or o          | `15_O_letter`   |
| P or p          | `16_P_letter`   |
| Q or q          | `17_Q_letter`   |
| R or r          | `18_R_letter`   |
| S or s          | `19_S_letter`   |
| T or t          | `20_T_letter`   |
| U or u          | `21_U_letter`   |
| V or v          | `22_V_letter`   |
| W or w          | `23_W_letter`   |
| X or x          | `24_X_letter`   |
| Y or y          | `25_Y_letter`   |
| Z or z          | `26_Z_letter`   |

**For Chinese/Unicode characters**: Use the first character's pinyin initial letter.
- Example: `立党 lidang` → starts with 'L' → `12_L_letter`
- Example: `七哥论国际` → starts with 'Q' (七) → `17_Q_letter`
- Example: `向陽說` → starts with 'X' (向) → `24_X_letter`

**Step 2: Create Folder Structure (if not exists)**

```bash
# Example: Saving a file for channel "Alex_Finn" in March 2026
mkdir -p summary/01_A_letter/Alex_Finn/2026_03
```

**Step 3: Save the File**

```bash
# File naming pattern: {YYYYMMDD}_{CHANNEL_PREFIX}_{TITLE_PREFIX}.md
# Example:
cp new_summary.md summary/01_A_letter/Alex_Finn/2026_03/20260326_Alex_Finn_Why_you_need_AI.md
```

**Complete Example**:
```
Channel: "Matt_Wolfe"
First letter: M (uppercase or lowercase both map to 13)
Category: 13_M_letter
Full path: summary/13_M_letter/Matt_Wolfe/2026_03/20260326_Matt_Wolfe_AI_News_update.md
```

---

### 2. How to Create daily_digest with Correct Table Alignment

**File Location**: `daily_digest/{YYYY_MM}/{YYYY-MM-DD-HH_MM}.md`

**File Template**:

```markdown
# Daily Summary for {YYYY-MM-DD}

## Statistics
- Total Processed: {COUNT}
- Total Audio Duration: {DURATION}

## Processed Content
| Uploader / Name | Title | Source / Model | Report Link |
| --- | --- | --- | --- |
| {CHANNEL} | {TITLE} | {MODEL} | [Report]({URL}) |
```

**CRITICAL: Table Alignment Rules**

1. **Always 4 columns**: Each row MUST have exactly 4 columns matching the header
2. **Use `|` as separator**: Each cell separated by ` | ` (space-pipe-space)
3. **No extra `|` in cells**: Do NOT put extra `|` characters inside cell content
4. **Empty cells**: Use empty string, not omit the cell: `| text | | text |` is OK

**Column Format**:

| Column | Content | Example |
|--------|---------|---------|
| 1 - Uploader / Name | Channel display name (may be truncated) | `Alex Finn` |
| 2 - Title | Video title (may include subtitle) | `Why you NEED AI` |
| 3 - Source / Model | AI model used | `nvidia/nemotron-3-super-120b-a12b:free` |
| 4 - Report Link | GitHub link to summary file | `[Report](https://github.com/yang-hrb/ytb_summary_md/blob/main/summary/01_A_letter/Alex_Finn/2026_03/file.md)` |

**Reference Link Format (CRITICAL)**:

The Report Link MUST include the category folder in the path:

```
https://github.com/yang-hrb/ytb_summary_md/blob/main/summary/{CATEGORY_FOLDER}/{CHANNEL_NAME}/{YYYY_MM}/{FILENAME}.md
```

**Examples**:

```markdown
| Alex Finn | Why you NEED AI | nvidia/nemotron-3-super-120b-a12b:free | [Report](https://github.com/yang-hrb/ytb_summary_md/blob/main/summary/01_A_letter/Alex_Finn/2026_03/20260326_Alex_Finn_Why_you_need_AI.md) |
| Tucker Carlson | The Great Scam | nvidia/nemotron-3-super-120b-a12b:free | [Report](https://github.com/yang-hrb/ytb_summary_md/blob/main/summary/20_T_letter/Tucker_Carlson/2026_03/20260326_Tucker_Carlson_The_Great_Scam.md) |
| 七哥论国际 | 2026年3月26日 | nvidia/nemotron-3-super-120b-a12b:free | [Report](https://github.com/yang-hrb/ytb_summary_md/blob/main/summary/17_Q_letter/七哥论国际/2026_03/20260326_七哥论国际_2026年3月26日.md) |
```

**Common Mistakes to AVOID**:

```markdown
# WRONG: Extra | in title cell splits into 5 columns
| StockTalk | Title Part 1 | Title Part 2 | model | [Report](...) |

# CORRECT: Merge title parts, keep 4 columns
| StockTalk | Title Part 1 Title Part 2 | model | [Report](...) |

# WRONG: Missing model column (only 3 columns)
| Unknown | N/A | [Report](...) |

# CORRECT: Include empty model column, keep 4 columns
| Unknown | N/A | N/A | [Report](...) |
```

**Pseudo-code for Category Folder Lookup**:

```python
def get_category_folder(channel_name: str) -> str:
    first_char = channel_name[0]
    
    if first_char.isdigit():
        return "00_number"
    
    # Convert to uppercase for comparison
    upper_char = first_char.upper()
    
    if upper_char.isalpha():
        # A=1, B=2, ..., Z=26
        num = ord(upper_char) - ord('A') + 1
        return f"{num:02d}_{upper_char}_letter"
    
    # For Chinese/Unicode: use pinyin initial
    # You may need a pinyin library or manual mapping
    pinyin_initial = get_pinyin_initial(channel_name)
    num = ord(pinyin_initial.upper()) - ord('A') + 1
    return f"{num:02d}_{pinyin_initial.upper()}_letter"
```

============================

## Implementation Details (2026-03-26)

### Overview

Three source files were modified and one dependency was added to satisfy the requirements above.

---

### Files Changed

#### 1. `src/utils.py` — Added `get_category_folder()`

New public function placed after `sanitize_filename()`.

**Logic:**
- First character is a digit → `00_number`
- First character is ASCII letter (A–Z, case-insensitive) → `NN_X_letter`
  - Formula: `num = ord(upper_char) - ord('A') + 1`, zero-padded to 2 digits
- First character is Chinese/CJK:
  1. Try `pypinyin` (if installed) to get the pinyin initial letter
  2. Fall back to a hardcoded table of common CJK channel-name starters (七→Q, 向→X, 立→L, etc.)
  3. Last resort: `00_number` with a warning log

```python
# Examples:
# get_category_folder("Matt_Wolfe")     → "13_M_letter"
# get_category_folder("Alex_Finn")      → "01_A_letter"
# get_category_folder("Tucker Carlson") → "20_T_letter"
# get_category_folder("123chan")        → "00_number"
# get_category_folder("七哥论国际")     → "17_Q_letter"
```

---

#### 2. `src/github_handler.py` — Updated `upload_to_github()`

Added optional `use_category_folder: bool = False` parameter.

**Before (remote path built):**
```
summary/{CHANNEL}/{YYYY_MM}/file.md
```

**After (when `use_category_folder=True`):**
```
summary/{CATEGORY_FOLDER}/{CHANNEL}/{YYYY_MM}/file.md
```

The category folder is obtained by calling `get_category_folder(uploader)`.
The default is `False` so existing callers (e.g. `_upload_info_json`) are unaffected.

---

#### 3. `src/pipeline.py` — `_upload_report()` enables category folder

```python
# Before
github_url = upload_to_github(report_file, uploader=uploader)

# After
github_url = upload_to_github(report_file, uploader=uploader, use_category_folder=True)
```

All three pipeline types (YouTube, local MP3, podcast) use `_upload_report()`,
so the fix applies uniformly.

---

#### 4. `src/daily_summary.py` — Fixed daily digest upload path

**Before:** called `upload_to_github(remote_folder="daily_digest", use_month_folder=True)`
with no uploader, which routed to `daily_digest/misc/{YYYY_MM}/file.md`.

**After:** calls `GitHubHandler.upload_file()` directly with an explicit remote path:

```python
remote_path = f"daily_digest/{year_month}/{report_file.name}"
# e.g. daily_digest/2026_03/2026-03-26-23_13.md
```

This matches the required structure:
```
daily_digest/2026_03/2026-03-20-23_31.md
```

---

### Dependency Added

| Package | Version | Purpose |
|---------|---------|---------|
| `pypinyin` | `>=0.51.0` | Convert Chinese channel-name first character to its pinyin initial letter for category folder mapping |

Added to `requirements.txt` under the **Utilities** section.
Already present in the active conda environment (`pypinyin==0.55.0`).

---

### Test Results

```
Ran 40 tests in 1.160s
OK
```

All 40 pre-existing unit tests pass with no regressions.

**Smoke-test of `get_category_folder()`:**

| Input | Expected | Result |
|-------|----------|--------|
| `Matt_Wolfe` | `13_M_letter` | ✓ |
| `Alex_Finn` | `01_A_letter` | ✓ |
| `Tucker Carlson` | `20_T_letter` | ✓ |
| `123chan` | `00_number` | ✓ |

