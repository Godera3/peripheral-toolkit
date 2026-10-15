# Bugs / Known Issues

## Color/brightness/colorful are wireless-only
- Commands `color`, `brightness`, `colorful` currently require the wireless dongle and will fail with "Wireless AULA dongle not found." when using wired connection.
- This matches the current implementation (they use wireless-specific parameter sequences), but may not reflect actual hardware capability.
- To fix: investigate if these adjustments work over wired path; if yes, extend support in `aula_f75/core.py` and CLI.
