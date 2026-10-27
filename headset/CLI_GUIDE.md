# Razer Barracuda X Chroma - Simple CLI Guide

This guide shows you how to use your headset commands on Linux. 

**Important first step:** Before running any of the commands below, you must be inside the project folder. Open your terminal and type this first:

    cd ~/Desktop/peripheral-toolkit/headset

---

## 1. Check Battery
Want to know how much charge you have left?

    python3 cli/barracuda.py battery
    
**What happens:** The terminal will print a number from 0 to 100, telling you the exact battery percentage.

---

## 2. Change Sound Mode (EQ)
Your headset has four different sound profiles. You can switch between them right from your keyboard.

    python3 cli/barracuda.py eq music

**What happens:** The headset instantly switches to the chosen sound mode. 
You can replace `music` with any of these four options:
- `game` (Focuses on footsteps and small sounds)
- `music` (Rich, balanced sound)
- `movie` (Heavy bass and cinematic sound)
- `custom` (Your own personal profile)

---

## 3. Turn Lights On or Off
You can toggle the glowing Chroma lights on the earcups.

**To turn lights off:**
    python3 cli/barracuda.py lights-off

**To turn lights on:**
    python3 cli/barracuda.py lights-on

**What happens:** The LEDs on the headset will immediately turn off or turn back on.

---

## 4. Listen to the Physical Button
If you ever want to test if the connection is working, or just see what mode you are switching to when you press the button on the headset, use this:

    python3 cli/barracuda.py listen

**What happens:** The terminal will wait and listen. When you physically press the sound button on your headset, the terminal will print a message (for example: `-> Headset physically changed EQ to: Movie`). 
*(Press `Ctrl+C` on your keyboard to stop listening).*

---

## Auto-Pilot Features (No Commands Needed)

You don't need to type commands for these two features. They are running silently in the background and work automatically:

1. **The Volume Wheel:** Just turn the wheel on your headset. It will change your computer's volume automatically.
2. **The Echo (Sidetone):** If you open a program that listens to your voice (like Discord or a web browser call), the headset will automatically turn on the echo so you can hear yourself. When you hang up, it turns the echo off.
