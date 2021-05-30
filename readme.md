# picam-timelapse

A project to automate capturing timelapse sequences with the Raspberry Pi Camera Module.

## Features

- Store captured photographs on a USB drive
- Camera and timelapse settings can be configured by placing a yaml file on the USB drive (default config included)
- Use onboard LED to indicate read/write activity
- The Pi's MicroSD card should be a readonly file system, to alleviate data corruption problems related to plugging and unplugging power (this is not implemented yet)