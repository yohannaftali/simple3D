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

---

## Main Page — Calibration Tools card + QGL shortcut

- `#card-tools` (Calibration Tools) in `#col-right` between Movement and Macros; populated by `renderTools(objects, macros)`, called from `fetchMacros()`
- CLEAN_NOZZLE shown only if the macro exists; MANUAL_PROBE always; PROBE_ACCURACY / PROBE_CALIBRATE only if a probe object exists
- `PID_EXTRUDER_*` / `PID_HEATER_BED_*` macros listed dynamically (orange, `confirm()` before running)
- MANUAL_PROBE / PROBE_CALIBRATE call `startCalibrate()` and switch to the Calibrate page for TESTZ / ACCEPT
- `#btn-qgl` above Home All, visible only when `quad_gantry_level` is in the objects list
- `restoreCardOrder()` now keeps cards missing from a saved order at their default position (instead of jumping to the top of the column)

---

## Main Page — Resizable cards

- Bottom-left grip (`.resize-handle`, inline SVG) on every card in `CARD_IDS`; touch + mouse
- Drag changes the card body height (min 30px, body scrolls); double-tap / double-click resets
- Stored per orientation in `localStorage` (`ch_portrait_<id>`, `ch_landscape_<id>`), re-applied on `orientationchange`/`resize`
- CSS `resize` is not used — not supported for touch on iOS 10 Safari
- Width is not resizable (cards fill their column)

---

## Fix — Macros not loading on page open

- Klipper returns `null` (not missing) for fields an object doesn't have — e.g. `mcu.temperature`, `temperature_host.temperature` on this printer
- `updateTempsUI()` called `.toFixed()` on `null`, throwing inside the subscribe-response handler before `fetchMacros()` ran; the Refresh button worked because it calls `fetchMacros()` directly
- Temp/fan checks now use `typeof x === 'number'`; `fetchMacros()` / `fetchMiniConsole()` run before the UI updates in `handleWSMessage()`

---

## Fix — Landscape main page clipped / unused bottom space

- `#page-main` in landscape inherited `.page { padding-bottom: 54px }` on top of `height: calc(100vh - 44px)` → ~54px dead space above the nav bar; now `padding-bottom: 0`
- `#page-main .container` was `overflow: hidden`, so cards resized taller than the screen were cut off; now `overflow-y: auto` (scrolls only when content overflows)
- `fitMainPage()` sets `#page-main` height to `window.innerHeight - 44` in landscape (iOS Safari `100vh` includes the toolbar area); re-run on `resize` / `orientationchange`

---

## Fix — Double scrollbar on Console / Jobs

- Both pages had `.page { padding-bottom: 54px }` plus an inner wrapper with another `padding-bottom: 54px`, and fixed guesses `calc(100vh - 150px)` / `calc(100vh - 160px)` for the log/list → body scrolled as well as the list
- `#page-console` / `#page-jobs` now have exact height (`window.innerHeight - 44` via `fitMainPage()`), `padding-bottom: 0`, `overflow: hidden`
- `.fill-wrap` → `.fill-card` flex column; `#console-log` / `#jobs-list` take `flex: 1` of the remaining space and are the only scroll area
- Target these pages by id, not by an extra class: `showPage()` overwrites `className` with `'page active'`

---

## Fix — MCU / SoC temperatures always "--"

- `mcu` and `temperature_host` report `temperature: null` on this printer; the values live in `temperature_sensor MCU` and `temperature_sensor SoC`
- `WS_OBJECTS` and `updateTempsUI()` now use those names (hardcoded, like `heater_fan hotend_fan` / `fan_generic exhaust_fan`)

---

## Phase 7 — UI refresh (KlipperScreen / Bambu style)

- **Sidebar navigation:** bottom `#nav-bar` replaced by a fixed left `#sidebar` (84px, 60px under 520px wide). Each item has an SVG icon and a label. Live nozzle/bed temps and a connection dot sit at the bottom, plus an **E-Stop** (`POST /printer/emergency_stop`, with confirm). `.page` got a `margin-left`, and `fitMainPage()` no longer subtracts 44px.
- **Icons:** inline SVG `ICONS` map + `ic()` / `renderIcons()`. They're used in card titles, temp/fan rows, buttons, and nav. Icon-over-text buttons use block `<i>`/`<svg>` (no flexbox inside `<button>`, unreliable before Safari 11).
- **Print status:** Bambu-style layout with a part thumbnail taken from the file metadata `thumbnails` (largest one). Shows big %, remaining time, layer `current/total` from `print_stats.info`, and filament. The metadata fetch is de-duplicated with `metaPendingFile`, and a failed or empty result no longer refetches on every WS push.
- **Movement:** joystick-style XY ring (SVG background, 4 direction buttons, home XY in the center) plus a Z column (Z+ / home Z / Z−). The step `<select>` became a segmented control (0.1/1/10/25/50, remembered). Live X/Y/Z readout from `toolhead.position` turns green when the axis is homed. Actions: Home All, QGL (if `quad_gantry_level`), Z Tilt (if `z_tilt`), Motors Off (M84).
- **Filament page (Bambu style):** Nozzle card has a big temp readout, −/+ target, Heat/Off, and material chips (PLA/PETG/ABS/ASA/TPU/PA). Extruder card has Retract ▲ / Extrude ▼ around a nozzle graphic, plus distance (5–100mm) and speed (1–10mm/s) selectors. Load/Unload use `LOAD_FILAMENT` / `UNLOAD_FILAMENT` macros if defined, otherwise a G-code fallback. A cold-nozzle confirm appears below 170°C.
- **Jobs:** thumbnails plus estimated time and filament per file. Metadata is fetched one request at a time (first 60 files) and cached by `path|modified`.
- **Calibrate:** BED_MESH_CALIBRATE and Z_TILT_ADJUST are added to Calibration Tools when the printer has them.
- **Connection card:** FW Restart button (`POST /printer/firmware_restart`).
- `apiGet()` gained an optional `errCb` (non-200 / timeout / bad JSON).
- Fix: the Jobs "Print" button now escapes for JS before HTML. Before, filenames with `'` broke the onclick.

---

## Phase 8: Page-based layout for 7" screens

Requested: "style with page rather than many sections, it is for only 7 inch screen", and "one page can be split into many pages like in Bambu Lab UI".

- Replaced the scrolling Main page of collapsible / draggable / resizable cards with one-screen pages. Card collapse, drag, resize, `CARD_IDS`, `fitMainPage()`, mini console, and the Custom GCode card are removed; the Console page covers GCode.
- **Sidebar:** Home, Control, Filament, Files, Tools, Console, Settings (with connection dot), plus E-Stop.
- **Tabs (sub-pages):** generic `TABS` / `showTab()` / `initTabs()`. Control = Move | Temperature, Tools = Macros | Calibrate | Z Offset, Settings = Connection | System. The last tab per page is remembered.
- **Home:** large thumbnail, big %, progress, time/layer/filament, Pause/Resume/Cancel (Cancel now confirms), Reprint, and a Files shortcut when idle. 2x3 status tiles; tapping Nozzle/Bed/Fan/Speed opens the keypad for that value.
- **Temperature keypad:** pick Nozzle / Bed / Part Fan / Speed, then use presets or a 0-9 keypad. No on-screen keyboard is needed.
- **Z Offset tab:** live baby-stepping (`SET_GCODE_OFFSET Z_ADJUST=.. MOVE=1`) with a 0.005-0.05 step, Reset, and Save (`Z_OFFSET_APPLY_PROBE`/`_ENDSTOP` + `SAVE_CONFIG`, blocked while printing). The paper-test calibration (TESTZ) moved here, with a Done button after ACCEPT.
- **Print lock** now disables the controls in `.lockable` panels (Move, Extruder, Macros, Calibrate, paper test) and shows a `.lock-msg`, instead of collapsing cards.
- Filament target is a -/+ stepper (`filSetTemp`) instead of a number input.
- `jsAttr()` helper for JS-in-attribute escaping (macro, tool, and file buttons).
- Settings > System adds Restart Klipper (`POST /printer/restart`) and Reload UI. On first run with no IP saved, the app opens Settings.

### Phase 8.1: Control > Move additions

- The Quad Gantry Level button is always visible, under Home All / Motors Off. `runQgl()` offers `G28` -> `QUAD_GANTRY_LEVEL` -> `G28 Z` when not homed, and warns if the config has no `[quad_gantry_level]`.
- Z Offset button (shows the current offset) jumps to Tools > Z Offset. It is `.nolock`, so it works while printing.
- The position readout is now an Actual / Target table like Mainsail/Fluidd. Actual = `motion_report.live_position`, Target = `gcode_move.gcode_position`, and the axis letter turns green when homed. WS subscription adds `motion_report` and `gcode_move.gcode_position`.

### Phase 8.2: Self-update and Console macro picker

- **Settings › System › simple3D Update:** shows installed vs latest version and the commits behind. Check (`/machine/update/refresh`), Update from main (`/machine/update/upgrade`, with `/client` as a fallback), and Reset to main (`/machine/update/recover?hard=true`), which appears only when the repo is dirty or invalid. Progress comes from `notify_update_response`; the page reloads after updating. This needs `[update_manager simple3d]` in moonraker.conf (see README).
- `apiPost()` gained `errCb(status, message)` (Moonraker error message) and `timeoutMs`.
- **Console › Macros:** a full-page picker listing all visible macros, with descriptions from `/printer/gcode/help` and a filter box. Insert puts `NAME ` in the input for parameters; Run sends it and goes back to the log.

### Phase 8.3: Update tab (Klipper / Moonraker / System / simple3D)

- New tab **Settings › Update** replaces the simple3D-only panel. It lists every Moonraker update_manager entry with a badge, an Update button and expandable commits/packages, plus Check (`/machine/update/refresh`) and Update all (`/machine/update/upgrade` with no name). Repair (`recover?hard=true`) appears for dirty or invalid repos.
- Legacy endpoint fallback on 404. A dropped connection during a Moonraker/system update is treated as a restart, and the status is re-checked after 10s.
- All update actions are disabled while printing; the list re-renders when the print lock changes.
- Tested against the CB1's real `/machine/update/status` (Moonraker v0.11 reports the key `System` capitalised).
- Printer: `~/simple3D` converted to a git clone of `main` (backup `~/simple3D.bak-20261101`).

### Phase 8.4: Home header + console preview

- Home header: printer name (Fluidd instanceName, then Mainsail printername, then `/printer/info` hostname) and network (`/machine/system_info`: first IPv4 on wlan, then eth; Wi-Fi or LAN icon). Moonraker doesn't report the SSID.
- Home console preview `#home-log`: fills the space between the print info and the buttons and shows the last 40 gcode_store lines, colour-coded. It polls every 3s only while Home is visible, auto-scrolls (re-scrolled after layout via `homeLogScroll()`), and tapping it opens the Console page.
- New `lan` icon.

### Phase 8.5: server.py self-update (no moonraker.conf needed)

- New `server.py` replaces `python3 -m http.server`. It is standard-library only and:
  - serves the static files, blocks dot-paths (the `.git` folder was publicly readable with http.server once `~/simple3D` became a git clone), and sends no-cache for the page;
  - `GET /api/self/status[?fetch=1]` returns local/remote commit, commits behind (max 30), ahead, dirty, and fetch_error;
  - `POST /api/self/update[?force=1]` does a ff-only merge of origin/main (force: hard reset). It returns 409 when dirty and not forced. If `server.py` changed, it exits with code 75 and systemd (`Restart=always`) starts the new version.
- The simple3D row in Settings > Update now uses server.py and is allowed while printing; Moonraker rows stay locked. A Moonraker `simple3d` entry is hidden when server.py answers.
- `simple3d.service`: ExecStart is server.py, `Restart=always`, `RestartSec=2`. `install_service.sh` now restarts (not just starts) and is safe to re-run.
- Tested end-to-end against a local bare repo: behind=1 shown in the UI, ff update, and a self-restart on a server.py change (exit 75).

### Phase 8.6: Full screen

- Settings > System > Display: a Full screen / Exit full screen button (Fullscreen API including the webkit/moz/ms prefixes; `p['catch']` so old engines parse it), and "Start in full screen" (`fs_auto`), which enters full screen on the first tap after load, because browsers block it without a gesture.
- The hint adapts: already running as an app, iOS without the Fullscreen API (use Add to Home Screen), or install suggestion.
- App mode: `manifest.webmanifest` (display fullscreen, landscape) + icons 180/192/512 + Apple/Android meta tags; the title is now "simple3D". server.py maps `.webmanifest` to `application/manifest+json`.
