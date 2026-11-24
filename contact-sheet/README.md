# Contact sheet

Interactive contact sheet for editing photo series: drag to reorder, move photos between series, rename series and write notes.

- `data.json` holds the photo list and the suggested starting series.
- Edits are saved in the browser you use (localStorage). Use **Export** to download your layout as JSON, and **Import** to load it on another device.
- `img/full` = 1400 px web copies, `img/thumb` = 480 px thumbnails. Originals are not stored here, and photo metadata (EXIF) is stripped.
