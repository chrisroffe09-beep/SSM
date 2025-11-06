#!/usr/bin/env python3
import psutil
import time

print("Searching for Rhythmbox process...")
found = False
for proc in psutil.process_iter(['pid', 'name']):
    if 'rhythmbox' in proc.info['name'].lower():
        print(f"Found: {proc.info['name']} (PID {proc.info['pid']})")
        found = True
        try:
            print("Sending terminate()...")
            proc.terminate()
            time.sleep(2)
            if proc.is_running():
                print("Still running — sending kill()...")
                proc.kill()
            else:
                print("Terminated successfully.")
        except psutil.AccessDenied:
            print("Access denied. Try running with sudo.")
        except psutil.NoSuchProcess:
            print("Process already exited.")
        break

if not found:
    print("Rhythmbox not found.")
