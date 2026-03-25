# Castor3 AIO Protocol Reference
# Gigabyte Aorus Waterforce X II 360
# VID=0x0414  PID=0x7a5e
# All commands confirmed from packet captures. No unknowns remain.

---

## Transport

- HID interface, report ID `0x99` prepended to all OUT packets (device strips it)
- OUT packets: 6143 bytes (zero-padded)
- IN packets: 255 bytes
- Command byte is always byte[0] after stripping report ID

---

## Sensor Streams (always running, unsolicited)

### 0xda — Pump / fan status
```
← da [fan_rpm_lo] [fan_rpm_hi] [00] [pump_rpm_lo] [pump_rpm_hi] ...
```
- bytes[1..2] LE uint16 = fan RPM
- bytes[4..5] LE uint16 = pump RPM
- Fan RPM may be noisy/jumpy when using a fan hub (e.g. Noctua NA-FH1)
  that shares a single tach signal across multiple fans.

### 0xe0 — System sensors
```
← e0 [b1] [b2] [cpu_temp_C] [b3] [b4] [b5] [b6] [coolant_temp_C] [b8] [b9] [tctl_C] ...
```
- byte[2]  = CPU temp °C (smoothed, what GCC displays)
- byte[7]  = coolant/housing temp °C (~45°C, near-constant)
- byte[10] = Tctl raw (AMD, spikes to 100+°C)
- **Prefer kernel for CPU temp**: `cat /sys/class/hwmon/hwmon*/temp1_input` (divide by 1000)

---

## Fan Control

### 0xdd — Fan controller status query
```
→ dd 00 00...
← dd 05 00...   (05 = preset mode active)
← dd 01 00...   (01 = customized mode active)
```

### 0xe5 — Fan preset select
```
→ e5 01 [preset_id] 00...   ← select preset
→ e5 02 00 00...             ← commit/apply
```
| ID   | Preset      |
|------|-------------|
| 0x00 | Zero RPM    |
| 0x01 | Customized  |
| 0x02 | Default     |
| 0x04 | Quiet       |
| 0x05 | Balanced    |
| 0x06 | Performance |
| 0x07 | Turbo       |

### 0xd9 — Query custom fan curve
```
→ d9 01 00...
← d9 01 01 00 [12 bytes curve data] 00...
```

### 0xe6 — Set custom fan curve
```
→ e6 00 01 00 [12 bytes curve data] 00...
```

**Curve data format — 4 control points × 3 bytes, then `00` terminator:**
```
[speed] [temp_start_C] [temp_end_C]   × 4
00
```
- `speed`: 0x00=0%, 0xFF=100% linear scale
- Segments define the fan response curve; device interpolates between points

Factory default (flat ~94%): `0a f0 1e  0a f0 2c  0a f0 50  0a f0 00`

Example sloped curve: `08 10 1d  08 eb 2b  0a 25 53  0a 6f 00`

**Recommended workflow — read-modify-write:**
```python
d9_resp = hid_query(b'\xd9\x01')
curve = bytearray(d9_resp[4:16])   # 12 bytes, 4 segments
# Modify: curve[i*3]=speed, curve[i*3+1]=start_temp, curve[i*3+2]=end_temp
hid_write(b'\xe6\x00\x01\x00' + bytes(curve) + b'\x00')
```

---

## Pump Control

### 0xfc — Query pump mode
```
→ fc 00 00...
← fc 05 [mode] 00...
```
- mode 0x01 = Balanced
- mode 0x02 = Turbo

### 0xfb — Set pump mode *(pump context — see also Carousel)*
```
→ fb 05 [mode] [sub] 00...
```
Used after `e7 09` + `fc` query. mode: 0x01=Balanced, 0x02=Turbo.

---

## LED Control

### 0xea — LED ring color (query / set)
```
Query: → ea [slot] 00...   ← ea [slot] [R][G][B] [R2][G2][B2] ...
Set:   → ea [slot] [R][G][B] 00...
```
- slot 1 = inner ring, slot 2 = outer ring
- slot number also matches Enthusiast display mode number (1–5) in that context

### 0xab — LED effect query
```
→ ab 00 00...   ← ab 05 [speed] [brightness] 00...
```

---

## Display Mode Overview

| Display Mode   | e8 ID | e7 session | Primary commands            |
|----------------|-------|------------|-----------------------------|
| Enthusiast 01  | —     | `e7 01`    | `ac` + `e2` + `e4`          |
| Enthusiast 02  | —     | `e7 02`    | `ac` + `e2` + `ae` + `e4`   |
| Enthusiast 03  | —     | `e7 03`    | `ac` + `e2` + `e4`          |
| Enthusiast 04  | —     | `e7 04`    | `ac` + `e2` + `e4`          |
| Enthusiast 05  | —     | `e7 05`    | `ac` + `e2` + `e4`          |
| Custom Image   | 0x01  | `e7 06`    | `f1/f2/c0/c2` + `f0`        |
| Custom Gif     | 0x06  | `e7 07`    | `f1/f2/c0/c2` + `f0` + `ac` |
| Custom Video   | 0x07  | `e7 08`    | `f1/f2/c0/c2` + `f0` + `ac` |
| Carousel       | 0x08  | `e7 09`    | `fb` playlist + `ac`        |

### 0xe7 — Open display session
```
→ e7 [n] 00...
```
n = mode index (1–5 Enthusiast, 6–9 image/carousel). Also used as n=slot_count+5 for ROM slot queries.

### 0xe8 — Set / query display mode (image modes only)
```
Query: → e8 00 00...   ← e8 [mode_id] 00...
Set:   → e8 [mode_id] 00...
```
Enthusiast modes do not use `e8`; they use `ac` bracket instead.

### 0xac — Display edit session bracket
```
→ ac 01 00...   ← begin
→ ac 00 00...   ← end / commit
```
Used by all Enthusiast modes and Custom Gif/Video/Carousel. Wraps `e2`, `ae`, `e4`, `fb` changes.

### 0xe4 — Panel colors (Enthusiast modes)
```
→ e4 [mode] [R1][G1][B1] [R2][G2][B2] [R3][G3][B3] [R4][G4][B4] 00...
```
- `mode` = Enthusiast mode number (0x01–0x05)
- One RGB triple per panel/quadrant in panel order
- Enth01: 1 triple; Enth02: 2; Enth03: 3; Enth04: 4; Enth05: 2

---

## Enthusiast Mode Details

### Enthusiast 01 — Single gauge (e7 01)
Checkboxes: CPU Temp · CPU Clock · CPU Usage · CPU Power
```
e2 00 00 [Temp][Clock][Usage][Power] 00...
           [3]   [4]   [5]   [6]
```
Each byte: 0=off, 1=on. Color: `e4 01 [R][G][B]`
Session: `ac 01` → `e2` → `e4` → `ac 00`

### Enthusiast 02 — Arc gauge with model name (e7 02)
Checkboxes: CPU Temp · CPU Usage · CPU Clock. Radio: CPU Model Name
```
e2 00 00 [Temp][Usage][Clock] 00...
           [3]   [4]   [5]
ae [n]    ← 0x00=No Model Name, 0x01=Show Model Name
```
Colors: `e4 02 [R1][G1][B1] [R2][G2][B2]`
Session: `ac 01` → `e2` → `ae` → `e4` → `ac 00`

### Enthusiast 03 — Three-panel (e7 03)
Panel A (top-left): CPU Temp · CPU Clock
Panel B (bottom-left): Fan RPM · Pump RPM
Panel C (right): CPU Temp · CPU Clock · CPU Usage · CPU Power
```
e2 00 00
  [A_Temp][A_Clock][00][00]                bytes[3..6]
  [B_Fan][B_Pump][00][00]                  bytes[7..10]
  [00][00][00][00][01]                      bytes[11..15]  ← byte[15]=0x01 constant marker
  [C_Temp][C_Clock][C_Usage][C_Power]       bytes[16..19]
  00...
```
Colors: `e4 03 [R_A][G_A][B_A] [R_B][G_B][B_B] [R_C][G_C][B_C]`
Session: `ac 01` → `e2` → `e4` → `ac 00`

### Enthusiast 04 — Four quadrants (e7 04)
Each quadrant radio-selects one metric. Layout: Q1=top-left, Q2=bottom-left, Q3=top-right, Q4=bottom-right
```
e2 00
  [Q1_Fan][Q1_Pump][Q1_Temp][Q1_Clock][Q1_Usage][Q1_Power]   bytes[1..6]   ONE-HOT
  [Q2_Fan][Q2_Pump][Q2_Temp][Q2_Clock][Q2_Usage][Q2_Power]   bytes[7..12]  ONE-HOT
  [Q3_Fan][Q3_Pump][Q3_Temp][Q3_Clock][Q3_Usage][Q3_Power]   bytes[13..18] ONE-HOT
  [Q4_Fan][Q4_Pump][Q4_Temp][Q4_Clock][Q4_Usage][Q4_Power]   bytes[19..24] ONE-HOT
  00...
```
Exactly one byte per 6-byte group must be 1, rest 0.
Metric offsets: +0=Fan_RPM +1=Pump_RPM +2=CPU_Temp +3=CPU_Clock +4=CPU_Usage +5=CPU_Power

Colors: `e4 04 [R_Q1][G_Q1][B_Q1] [R_Q2][G_Q2][B_Q2] [R_Q3][G_Q3][B_Q3] [R_Q4][G_Q4][B_Q4]`
Session: `ac 01` → `e2` → `e4` → `ac 00`

### Enthusiast 05 — Ring gauge + value (e7 05)
Same one-hot 6-metric encoding as Enth04, two groups:
```
e2 00
  [G1_Fan][G1_Pump][G1_Temp][G1_Clock][G1_Usage][G1_Power]   bytes[1..6]  ONE-HOT (ring)
  [G2_Fan][G2_Pump][G2_Temp][G2_Clock][G2_Usage][G2_Power]   bytes[7..12] ONE-HOT (value)
  00...
```
Group1 = ring gauge (UI shows Fan/Pump only; all 6 wired)
Group2 = small value display (UI shows CPU metrics only; all 6 wired)
Colors: `e4 05 [R1][G1][B1] [R2][G2][B2]`
Session: `ac 01` → `e2` → `e4` → `ac 00`

---

## Custom Image / Gif / Video Modes

Session: `e7 06` (Image), `e7 07` (Gif), `e7 08` (Video)

### ROM slot listing
```
→ f3 [slot] 00...
→ f4 [slot] 00...   ← f4 [slot] [type] 00...   type: 01=JPEG/PNG, 02=MKV
→ f5 [slot] [page] 00...  ← f5 [slot] [page] [len] [filename...] 00...
→ fd [slot+5] 00...  ← fd [slot+5] 05 [order] [enabled] 00...
```

### ROM free space
```
→ fa 42 00...   ← fa 02 [lo] [hi] 00...   LE uint16 × 1KB blocks (~45MB total)
```

### File upload
```
→ f1 01 00 00 [size_hi][size_lo] [name_len] [filename\0...] 00...   ← start
→ f2 [chunk_idx] [252 bytes data...]                                 ← repeat per chunk
→ f1 03 00 00 [size_hi][size_lo] 00...                               ← end/commit
   (poll) → c2 00...  ← c2 [pct] ...  until pct=0x64
→ c0 01 00 00 00...                                                   ← commit to ROM
```
- chunk_idx: 0x00, 0x01, 0x02... (increments per chunk, wraps at 0xFF)
- size: big-endian uint16

### Text overlay
GCC renders text to a 320×320 RGBA PNG named `_txt_.png` and uploads via `f1`/`f2`.
The reserved filename triggers overlay compositing on device.

Upload uses `f1 03` for end (not `f1 02` which is for image uploads):
```
→ f1 01 [size BE uint32] [name_len] _txt_.png\0 00...
→ f2 [chunk_idx] [data...]
→ f1 03 [size BE uint32] 00...            ← text overlay end (0x03, not 0x02)
→ c2 00 (poll until pct=0x64)
→ c0 01 00 00                              ← commit to ROM
```

### System Info overlay

**WARNING: Do NOT use f0 to control overlay items — it corrupts the ROM file table.
f0 is only used during initial GCC setup and should not be sent from Linux.**

Overlay mode and metrics are controlled entirely by c0 commits and bare e2:

**Enable System Info overlay:**
```
→ c0 00 00 01                              ← enables System Info mode
→ e2 [bare, no session/ac bracket]         ← selects metrics (immediate effect)
```

**Disable overlay (None mode):**
```
→ c0 00 00 00                              ← clears overlay, shows plain image
```

**e2 metric selection (image/gif/video overlay):**
```
→ e2 00 00 [M1=0] [M1=1] [M1=2] [M1=3] 00 00 [M2=0] [M2=1] [M2=2] [M2=3] 00...
           byte[3] byte[4] byte[5] byte[6]     byte[9] byte[10] byte[11] byte[12]
```
Each group is one-hot (exactly one byte = 0x01, rest = 0x00):

| Offset in group | Metric    |
|-----------------|-----------|
| +0              | CPU Clock |
| +1              | CPU Temp  |
| +2              | CPU Usage |
| +3              | CPU Power |

Metric group 1 = bytes[3-6], metric group 2 = bytes[9-12].
Sent bare (no e7 session open, no ac bracket). Takes effect immediately.

**Overlay item layout on display:**
1. CPU title (fixed, always shown in System Info mode)
2. Metric 1 (e2 group 1)
3. Metric 2 (e2 group 2)
4. Aorus Logo (persists from GCC f0 setup; toggled via e4 color visibility)

### Overlay text colors (e4 in image context)
Set colors for overlay items using bare e4 (no session/ac bracket):
```
→ e4 06 [R1][G1][B1] [R2][G2][B2] [R3][G3][B3] [R4][G4][B4]
→ c0 00 01 01                              ← commit color settings
```
One RGB triple per overlay slot: [CPU title] [metric 1] [metric 2] [logo].
Setting a color for the logo slot implicitly shows the logo.

### Commit command summary (c0)
```
c0 00 00 00 — commit slot/duration; clears overlay (None mode)
c0 00 00 01 — enable System Info overlay mode
c0 00 01 01 — commit overlay color changes (e4)
c0 01 00 00 — commit file upload to ROM (after f1/f2)
```

### Slot display duration (f6)
```
→ f6 [ch] [seconds] [slot_a] [slot_b] 00...
```
- ch: 0x06 for Custom Image, 0x07 for Gif/Video/Carousel
- seconds: 0x05=5s, 0x0a=10s, 0x0f=15s, 0x14=20s

---

## Carousel Mode

Carousel cycles through any combination of the other 8 display modes.
It is NOT a separate image slot system.

Session: `e7 09`

### Playlist definition (fb — carousel context)
```
→ ac 01 00...
→ fb [interval_s] [mode_id] [mode_id] ... 00...
→ ac 00 00...
```
- `interval_s`: seconds per mode, raw byte (5–60 in 5s increments: 0x05, 0x0a, 0x0f ... 0x3c)
- `mode_id`: which display modes to include, in order
- Entire playlist + interval defined in one `fb` packet; send updated packet each time user changes selection

| mode_id | Display Mode   |
|---------|----------------|
| 0x01    | Enthusiast 01  |
| 0x02    | Enthusiast 02  |
| 0x03    | Enthusiast 03  |
| 0x04    | Enthusiast 04  |
| 0x05    | Enthusiast 05  |
| 0x06    | Custom Image   |
| 0x07    | Custom Gif     |
| 0x08    | Custom Video   |

Example — Enth01 + Custom Image at 10s each:
```
ac 01
fb 0a 01 06 00...
ac 00
```

Note: `ce` is the screen rotation command — the `ce [00..0b]` sequences seen during
mode switches in earlier captures were GCC resetting rotation state, not carousel ordering.

---

## Commit Commands (c0)

```
c0 00 00 00 00...  ← commit slot durations / clear overlay (None mode)
c0 00 00 01 00...  ← enable System Info overlay mode
c0 00 01 01 00...  ← commit overlay color settings          (after bare e4 06)
c0 01 00 00 00...  ← commit file upload to ROM slot         (after f1/f2/c2)
```

---

## Status / Progress Polling

### 0xc1 — Device busy status
```
→ c1 00 00...   ← c1 [busy] [sub] 00...   busy: 0=idle, 1=busy
```

### 0xc2 — Upload progress
```
→ c2 00 00...   ← c2 [pct] 00...   pct: 0x00=0%, 0x64=100%
```

---

## Miscellaneous

### 0xdf — Fan channel enable query
```
→ df 00 00...   ← df 00 00 [ch1] [ch2] [ch3] 00...
```

---

## Display Rotation

### 0xce — Screen rotation
```
→ ce [step] 00...
```
- 12 steps, 30° per step clockwise, range 0x00–0x0b
- Takes effect immediately — no session bracket or commit needed
- Persists across power cycles

| Step | Degrees | Step | Degrees |
|------|---------|------|---------|
| 0x00 |   0°    | 0x06 |  180°   |
| 0x01 |  30°    | 0x07 |  210°   |
| 0x02 |  60°    | 0x08 |  240°   |
| 0x03 |  90°    | 0x09 |  270°   |
| 0x04 | 120°    | 0x0a |  300°   |
| 0x05 | 150°    | 0x0b |  330°   |

Cardinal orientations: `ce 00`=0°, `ce 03`=90°, `ce 06`=180°, `ce 09`=270°

Formula: `step = degrees / 30`

**Note:** `ce` was previously misidentified as a carousel order command based on seeing
`ce [00..0b]` sequences during mode switches. Those are GCC resetting rotation state,
not defining carousel order. Carousel order is handled entirely by `fb`.

---

## Quick Reference — Common Sequences

### Switch to Enthusiast 04, Q1=CPU_Temp Q2=Fan_RPM, all cyan
```
e7 04
ac 01
e2 00 00 01 00 01 00 00 00 00 00 00 01 00 00 00 00 00 00 01 00 00 00 00 00...
         ^^^^^^^^^^^                ^^^^^^^^^^^                ^^^^^^^^^^^
         Q1=CPU_Temp (+2)          Q2=Fan_RPM (+0)           Q3=... Q4=...
e4 04  00 ff ff  00 ff ff  00 ff ff  00 ff ff  00...
ac 00
```

### Upload image, set 10s display
```
e7 06
f3 01 / f4 01 / f5 01 / fd 06     ← enumerate slots
fa 42                               ← check free space
f1 01 00 00 [sz_hi][sz_lo] 09 boot1.jpg\0 00...
f2 00 [252 bytes] ...               ← repeat all chunks
f1 03 00 00 [sz_hi][sz_lo] 00...
c2 00... (poll until c2 64)
c0 01 00 00
f6 06 0a 01 00...                   ← 10s for slot 1
c0 00 00 00
```

### Set custom fan curve
```
dd 00                               ← verify fan controller
e5 01 01 / e5 02                    ← select Customized preset
d9 01                               ← read current curve
e6 00 01 00 [modified 12 bytes] 00... ← write new curve
```

### Set Carousel — Enth01 + Custom Image, 10s each
```
e7 09
ac 01
fb 0a 01 06 00...
ac 00
```

### Set screen rotation to 90° clockwise
```
ce 03 00...
```
No session or commit needed. step = degrees / 30.
