# CHANGE_HISTORY.md — simple3D

Detailed implementation notes per phase. AGENTS.md holds the current reference state; this file holds the "what was built and why" history.

---

## Phase 0 — WebSocket Transport

- `connectWS()` / `disconnectWS()` open/close `ws://<ip>:<port>/websocket`
- `wsSubscribe()` sends `printer.objects.subscribe` (id=1) for `WS_OBJECTS`
- `handleWSMessage()` handles subscribe response, `notify_status_update`, `notify_klippy_ready`, `notify_klippy_disconnected`, `notify_klippy_shutdown`
- `mergeDeep()` accumulates partial state updates into `printerStatus`
- `scheduleReconnect()` retries after 3 seconds on close
- `refreshAll()` re-subscribes if connected, calls `connectWS()` if not
- Replaced all polling `setInterval` for temps/print-status — state is now pure WS push

---

## Phase 1 — Navigation System

- `#nav-bar` fixed at bottom, 5 equal-width buttons with Unicode icons
- All pages wrapped in `.page` divs, toggled via CSS class `.active`
- `showPage(name)` updates both page and nav button classes
- `currentPage` variable updated on each page switch
- Console fetch triggered on switch to console; jobs fetch triggered on switch to jobs
- `padding-bottom: 54px` on `.page` to clear nav bar

**Deviation from original spec:** `showPage()` uses `className` toggle instead of `style.display` — cleaner, CSS-driven approach.

---

## Phase 2 — Enhanced Print Status

- M117 message (`display_status.message`) — shown with yellow left-border highlight when non-empty; uses `String().trim()` for robustness
- Filename from `print_stats.filename`
- Filament length from metadata `filament_total` (converted mm → meters, shown as `X.Xm`)
- Elapsed time from `print_stats.print_duration` (formatted `HH:MM:SS`)
- Remaining time calculated as `estimated_time - print_duration` (formatted `HH:MM:SS`)
- Metadata fetched once per filename change, cached in `cachedMetaFile` / `cachedEstimatedTime` / `cachedFilamentTotal`
- Button state: `printing` → Pause+Cancel, `paused` → Resume+Cancel, `complete` → Reprint, other → all hidden
- `reprintLast()` uses `lastFilename` to POST to `/printer/print/start`
- `formatTime(seconds)` helper

**Known gap:** `cachedEstimatedTime` is used only to compute remaining time, not shown as a standalone "Est. total" field. Add `#print-est-total` to `.print-meta` if needed.

---

## Phase 3 — Console Page

- `#console-log` — dark monospace scrollable area, `height: calc(100vh - 150px)`
- GCode input with Enter key support (`onkeydown` checking `keyCode === 13`)
- Clear button resets `innerHTML` and `lastConsoleTime`
- `GET /server/gcode_store?count=100` — incremental append by comparing `entry.time > lastConsoleTime`
- Color: commands (blue `#a0c4ff`), responses (grey `#ccc`), errors (red `#e74c3c`)
- Auto-scroll unless user scrolled up (detected via scroll event listener)
- Dedicated 3-second `setInterval` started in `showPage('console')` and cleared on page leave

---

## Phase 4 — Z Calibration Page

- Two method cards: Voron Tap/Probe (`PROBE_CALIBRATE`) and Standard Endstop (`Z_ENDSTOP_CALIBRATE`)
- `#cal-adj-panel` hidden by default, shown after either button is pressed
- TESTZ buttons: `+1`, `+0.1`, `+0.025`, `-0.025`, `-0.1`, `-1`
- ACCEPT → shows `#cal-save-row`; ABORT → hides panel
- SAVE_CONFIG button with restart warning
- Note at top about custom macros

---

## Phase 5 — Jobs Page

- `GET /server/files/list?root=gcodes` — sorted by `modified` descending
- Filename from `f.path || f.filename` (actual API returns `path`)
- File size formatted as KB or MB
- Modified date formatted as `DD/MM/YY HH:MM`
- Print button with `confirm()` dialog → `POST /printer/print/start`
- Refresh button
- HTML-escaped filenames (XSS safe via `escHtml()`)
- `currentPrintingFile` updated alongside `lastFilename` — set to `ps.filename` when printing, cleared to `''` when idle; used to highlight active file in Jobs list

---

## Phase 6 — Filament Change Page

- Preset preheat buttons: PLA 200°C, PETG 235°C, ABS 250°C, TPU 220°C
- Custom temp input + Set + Off buttons
- Live hotend temp display (`#fil-hotend-temp`) updated via shared `filHotendTemp`/`filHotendTarget` vars from WebSocket state
- "Ready" indicator: green when within 3°C of target, orange when heating, grey when off
- Retract 50mm / 100mm (`G91\nG1 E-Xmm F300\nG90`)
- Load 50mm (`G91\nG1 E50 F300\nG90`)
- Purge 30mm and 50mm at slow speed F150
- Note about homing before load/unload

**Known gap:** No cold-retract guard on Unload buttons. To add: check `filHotendTemp >= 150` before allowing retract, or show a warning label.
