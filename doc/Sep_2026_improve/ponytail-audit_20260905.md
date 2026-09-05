# Ponytail Audit — ytb_summary_md (2026-09-05)

Scope: over-engineering only. 4 Python files (~1090 lines) + 208-line .gitignore + committed run artifacts. Correctness/security out of scope.

## Findings (biggest cut first)

delete fix_error_reports.py duplicates reorganize_reports.py (~200 lines: sanitize_*, generate_target_path, info-json, csv report, CLI loop). Import instead. [src/fix_error_reports.py]
delete Committed regenerable run outputs (*.db, migration/fix CSVs, analysis CSVs — incl. 1.1MB metadata_cache.db + 1.6MB migration_report.csv). git rm + .gitignore. [run_code/]
delete FILENAME_RE compiled but never used; parse_filename() uses split("_"). Remove it. [src/fix_error_reports.py:32-38]
delete Unused `import os` (only shutil + pathlib used). [organize_summary.py:2]
yagni MetadataCache class (42 lines) only delegates get/put/close for one caller. Plain functions. [src/reorganize_reports.py:171-212]
yagni 9-flag CLI (--cookie-browser/--batch-size/--limit/--output-dir/--log-file/--force/...) on a one-shot migration that's already done. Freeze defaults. [src/reorganize_reports.py:502-518]
yagni FixResult vs MigrationResult vs VideoMeta vs ReportInfo: four dataclasses sharing path/video_id/uploader/status/error. One suffices. [src/]
shrink 208-line stock Python .gitignore for a 4-script data repo. ~15 lines cover it. [.gitignore]
shrink parse_report_file repeats `m = RE.search; if m:` 5x. Loop over (regex, attr) pairs. [src/reorganize_reports.py:112-147]
shrink read_md_title + read_md_video_id each re-read the same file; inline re.search ignores module constants. Read once. [src/fix_error_reports.py:104-128]
shrink sanitize_channel_name re-applies `re.sub(r"\s+","_",…)` already done by sanitize_filename. Drop second pass. [src/reorganize_reports.py:314-317 + src/fix_error_reports.py:71-74]
shrink get_first_letter + get_target_folder fold into one mapping; CATEGORIES prebuild + mkdir loop is chatty. [organize_summary.py:10-37]
stdlib DaySummary.links=None + __post_init__ → field(default_factory=list). [run_code/get_error/summarize_logs.py:17-25]
stdlib parse_date/daterange hand-roll day iteration → range((end-start).days+1). [run_code/get_error/summarize_logs.py:66-76]

net: -~350 lines, -0 deps possible.
