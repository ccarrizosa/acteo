Acteo Settings
===============

This document explains the purpose of each setting in the `Settings` dataclass.

Folders
-------
- input_folder
  Path to the folder containing images to process. Can be `null` until the
  user opens a folder from the UI.

- output_folder
  Destination for classified sequences. When a sequence is assigned a category
  and processed, files will be moved or copied here based on `move_mode`.

- discard_folder
  Destination for discarded sequences. When `safe_delete` is enabled, discard
  operations move files here instead of permanent deletion.

Grouping
--------
- grouping_mode
  Controls how images are grouped into sequences. Supported values:
  - `timestamp_gap`: images with timestamps within `timestamp_gap_seconds` are
    grouped together (recommended for trail cams).
  - `fixed_size`: images are grouped into consecutive batches of
    `fixed_group_size` images.

- timestamp_gap_seconds
  The maximum allowed time difference (in seconds) for two images to be
  considered part of the same sequence when `grouping_mode` is
  `timestamp_gap`. Typical values are 5–30 for burst images; larger values
  combine images taken farther apart in time.

- fixed_group_size
  Number of images per sequence when `grouping_mode` is `fixed_size`.

Presentation
------------
- images_per_sequence
  Number of images to display for each sequence in the UI grid. The UI will
  handle sequences shorter than this number gracefully.

File operations
---------------
- move_mode
  `move` (default): relocate original files to the `output_folder` after
  classification.
  `copy`: copy files to `output_folder` and keep originals in-place.

- preserve_folder_structure
  If true, the tool will recreate the subfolder hierarchy from the
  `input_folder` inside the `output_folder` when moving/copying files.

- safe_delete
  When true, discard actions move files to `discard_folder` instead of
  permanently deleting them. When false, discard may delete files (use with
  caution).

Auxiliary paths
---------------
- category_file_path
  File where user-defined categories are stored (JSON). Editable via the UI.

- metadata_file_path
  CSV file where each classified sequence is appended with details (sequence
  id, image paths, category, operator, timestamp, operation).

- thumbnails_cache_dir
  Folder used to store generated thumbnails to speed up UI browsing and
  reduce repeated image decoding.

IO & behavior
-------------
- concurrency
  Number of concurrent workers for IO-bound tasks (thumbnailing, move/copy).

- autoplay_interval_seconds
  Number of seconds between automatic image changes while previewing a
  sequence in the viewer.

- exif_priority
  If true, use EXIF DateTimeOriginal for image timestamps when available.
  Otherwise, fall back to filesystem modification time (mtime).

- file_patterns
  Glob patterns used to discover image files in the `input_folder`.

Operator & Misc
---------------
- operator_name
  Optional human-readable name of the operator; recorded in metadata.

- last_scanned
  ISO timestamp set to the last successful scan of the `input_folder`.

Notes
-----
- All path settings accept `~` and will be expanded to absolute paths by the
  application.
- The `settings.schema.json` in `/schemas` can be used to validate settings
  files before loading.
