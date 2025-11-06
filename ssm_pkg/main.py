#!/usr/bin/env python3
import psutil
import shutil
import os
import time
import threading
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Group
from rich import box

refresh_paused = False

def get_network_speed():
    old = psutil.net_io_counters()
    time.sleep(1)
    new = psutil.net_io_counters()
    upload = (new.bytes_sent - old.bytes_sent) / 1024
    download = (new.bytes_recv - old.bytes_recv) / 1024
    return upload, download

def make_table_processes():
    table = Table(title="Active Processes", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("PID", style="green")
    table.add_column("CPU%", style="red")
    table.add_column("Memory%", style="yellow")

    processes = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append((p.info['name'], p.info['pid'], p.info['cpu_percent'], p.info['memory_percent']))
        except psutil.NoSuchProcess:
            pass
    processes = sorted(processes, key=lambda x: x[2], reverse=True)[:9]

    for i, (name, pid, cpu, mem) in enumerate(processes, start=1):
        table.add_row(str(i), name or "?", str(pid), f"{cpu:.1f}", f"{mem:.1f}")
    return table, processes

def make_table_disks():
    table = Table(title="Disk Usage", box=box.SIMPLE)
    table.add_column("Device", justify="left", style="cyan")
    table.add_column("Mount", justify="left", style="magenta")
    table.add_column("Used", justify="right", style="yellow")
    table.add_column("Free", justify="right", style="green")
    table.add_column("Total", justify="right", style="blue")
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            table.add_row(part.device, part.mountpoint,
                          f"{usage.used // (1024**3)}G",
                          f"{usage.free // (1024**3)}G",
                          f"{usage.total // (1024**3)}G")
        except PermissionError:
            continue
    return table

def make_system_stats():
    upload, download = get_network_speed()
    stats = Table(title="System Stats", box=box.SIMPLE)
    stats.add_column("CPU%", style="red")
    stats.add_column("RAM%", style="yellow")
    stats.add_column("Upload (KB/s)", style="cyan")
    stats.add_column("Download (KB/s)", style="green")
    stats.add_row(f"{psutil.cpu_percent():.1f}", f"{psutil.virtual_memory().percent:.1f}",
                  f"{upload:.1f}", f"{download:.1f}")
    return stats

def build_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="upper", ratio=6),
        Layout(name="lower", ratio=4)
    )
    layout["upper"].split_row(
        Layout(name="processes", ratio=6),
        Layout(name="disks", ratio=4)
    )
    layout["lower"].split_row(
        Layout(name="stats")
    )
    return layout

def render_dashboard():
    process_table, processes = make_table_processes()
    disks_table = make_table_disks()
    stats_table = make_system_stats()

    layout = build_layout()
    layout["processes"].update(Panel(process_table, title="Processes"))
    layout["disks"].update(Panel(disks_table, title="Disks"))
    layout["stats"].update(Panel(stats_table, title="System Stats"))
    return layout, processes

def dashboard_loop(live):
    global refresh_paused
    while True:
        if not refresh_paused:
            layout, _ = render_dashboard()
            live.update(layout)
        time.sleep(1)

def kill_process_menu(processes):
    global refresh_paused
    refresh_paused = True
    try:
        choice = input("\nEnter process number to kill (0 to cancel): ")
        if not choice.isdigit():
            print("Invalid selection.")
            return
        choice = int(choice)
        if choice == 0:
            print("Canceled.")
            return
        if 1 <= choice <= len(processes):
            pid = processes[choice - 1][1]
            os.system(f"sudo kill -9 {pid}")
            print(f"Process {processes[choice - 1][0]} (PID {pid}) terminated successfully.")
        else:
            print("Invalid selection.")
    finally:
        refresh_paused = False

def main():
    layout, processes = render_dashboard()
    with Live(layout, refresh_per_second=2, screen=True) as live:
        threading.Thread(target=dashboard_loop, args=(live,), daemon=True).start()
        while True:
            cmd = input("\nCommand ([K]ill/[Q]uit): ").lower().strip()
            if cmd == "q":
                break
            elif cmd == "k":
                _, processes = render_dashboard()
                kill_process_menu(processes)

if __name__ == "__main__":
    main()
