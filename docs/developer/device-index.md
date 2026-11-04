# Device index for repository tooling

The Linux udev generator and JSON exporter share the declaration readers in
`liquidctl._device_index`. These private helpers inspect loaded driver classes;
they do not scan buses, instantiate devices, or communicate with hardware.

From a Linux source checkout with liquidctl's runtime dependencies installed:

```sh
python extra/export-device-index.py > device-index.json
python extra/linux/generate-uaccess-udev-rules.py > extra/linux/71-liquidctl.rules
```

The exporter reads this checkout's README by default. `--readme PATH` selects
another README. The JSON has a versioned, experimental format for review:

- `usb_matches`: one entry per declared driver match, with integer VID/PID,
  driver class, the original description and constructor parameters. Keep
  separate entries when identifiers are shared; a description can name a
  family rather than a unique product. Driver-specific probe logic can impose
  additional requirements beyond these declarations.
- `nvidia_i2c_matches`: PCI vendor/device and subsystem identifiers, I2C
  addresses, driver class and description. These require the NVIDIA kernel
  driver and the `NVIDIA i2c adapter 1 ` adapter-name prefix as well.
- `readme`: the supported-family table, including documentation links,
  maintainer-owned minimum **recommended** versions, support notes, the note
  legend and Markdown references. Names and notes are preserved verbatim.

The driver declarations remain authoritative for identifiers; the README
remains authoritative for its family-level support notes and MRLVs. Neither is
duplicated in a separately maintained catalogue. In particular, the exporter
does **not** automatically assign a family's MRLV or notes to a match based on
a guessed name similarity. Consumers need an explicit, reviewed association
before joining the two. Some README families, such as generic DDR4 devices,
are not enumerated by the declaration readers used for udev rules.

Generated metadata is not evidence of a new hardware test. Preserve grouped
models, matching constraints, source revision and upstream documentation when
building a downstream index. This tool does not change the CLI, driver probe
logic, or the udev rules' access policy.
