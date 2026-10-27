# Bugs / Known Issues

## Missing Voice Prompt on USB Write
- **Symptom:** Changing EQ via physical button plays a woman's voice announcing the mode. Changing EQ via CLI (`set_eq()`) switches the mode but does not play the voice prompt.
- **Cause:** Likely a secondary "Play Voice Prompt" command sent by Synapse, or a specific flag in the payload that we haven't isolated yet. 
- **Fix:** Analyze `/tmp/all_out.txt` from the Synapse capture for commands immediately following the EQ `SET` (0x13).
