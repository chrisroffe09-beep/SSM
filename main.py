#!/usr/bin/env python3
import psutil
import time
import socket
from datetime import timedelta
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live
from rich.style import Style

console = Console()
prev_net = None  # keep previous net counters to compute rates

def get_color(value: float) -> str:
    if value < 50:
        return "green"
    elif value < 80:
        return "yellow"
    else:
        return "red"

def format_bytes_per_sec(bps: float) -> str:
    """Convert bytes/sec into KB/s, MB/s, or GB/s with auto-scaling."""
    kb = bps / 1024
    mb = kb / 1024
    gb = mb / 1024
    if gb >= 1:
        return f"{gb:.2f} GB/s"
    elif mb >= 1:
        return f"{mb:.2f} MB/s"
    elif kb >= 1:
        return f"{kb:.2f} KB/s"
    else:
        return f"{bps:.0f} B/s"

def get_system_stats():
    global prev_net
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    uptime = str(timedelta(seconds=uptime_seconds)).split('.')[0]
    hostname = socket.gethostname()

    # Calculate network speed
    if prev_net:
        sent_rate = net.bytes_sent - prev_net.bytes_sent
        recv_rate = net.bytes_recv - prev_net.bytes_recv
    else:
        sent_rate = 0
        recv_rate = 0
    prev_net = net

    return {
        "cpu": cpu,
        "mem_used": mem.percent,
        "disk_used": disk.percent,
        "net_sent_rate": sent_rate,
        "net_recv_rate": recv_rate,
        "uptime": uptime,
        "hostname": hostname
    }

def get_top_processes(limit=10):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except psutil.NoSuchProcess:
            continue
    procs = sorted(procs, key=lambda p: p['cpu_percent'], reverse=True)
    return procs[:limit]

def render_ui():
    stats = get_system_stats()

    # Header
    console.clear()
    console.print(f"[bold underline green]Sour CLI Sys Monitor[/bold underline green] — {stats['hostname']} | Uptime: {stats['uptime']}")
    console.print("[dim]Press Ctrl+C to exit.\n")

    # CPU, Memory, Disk bars
    cpu_color = get_color(stats["cpu"])
    mem_color = get_color(stats["mem_used"])
    disk_color = get_color(stats["disk_used"])

    cpu_bar = Progress(
        TextColumn("[bold blue]CPU"),
        BarColumn(bar_width=None, complete_style=Style(color=cpu_color)),
        TextColumn("{task.percentage:>3.0f}%"),
        transient=True
    )
    mem_bar = Progress(
        TextColumn("[bold magenta]Memory"),
        BarColumn(bar_width=None, complete_style=Style(color=mem_color)),
        TextColumn("{task.percentage:>3.0f}%"),
        transient=True
    )
    disk_bar = Progress(
        TextColumn("[bold yellow]Disk"),
        BarColumn(bar_width=None, complete_style=Style(color=disk_color)),
        TextColumn("{task.percentage:>3.0f}%"),
        transient=True
    )

    cpu_bar.add_task("CPU", total=100, completed=stats["cpu"])
    mem_bar.add_task("MEM", total=100, completed=stats["mem_used"])
    disk_bar.add_task("DISK", total=100, completed=stats["disk_used"])

    # Network table with auto-scaled speeds
    net_table = Table(title="[bold green]Network Info", show_header=True, header_style="bold green")
    net_table.add_column("Upload", justify="right")
    net_table.add_column("Download", justify="right")
    net_table.add_row(
        format_bytes_per_sec(stats["net_sent_rate"]),
        format_bytes_per_sec(stats["net_recv_rate"])
    )

    # Top processes
    proc_table = Table(title="[bold cyan]Top 10 Processes", show_header=True, header_style="bold cyan")
    proc_table.add_column("PID", justify="right")
    proc_table.add_column("Name")
    proc_table.add_column("CPU %", justify="right")
    proc_table.add_column("Memory %", justify="right")
    for p in get_top_processes():
        proc_table.add_row(
            str(p["pid"]),
            p["name"][:20],
            f"{p['cpu_percent']:.1f}",
            f"{p['memory_percent']:.1f}"
        )

    console.print(cpu_bar)
    console.print(mem_bar)
    console.print(disk_bar)
    console.print(net_table)
    console.print(proc_table)

def main():
    # Prime network counters
    global prev_net
    prev_net = psutil.net_io_counters()
    time.sleep(1)  # wait 1 second to calculate first speed

    with Live(refresh_per_second=1, screen=False):
        try:
            while True:
                render_ui()
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[red]Exiting Sour CLI Sys Monitor...[/red]")

if __name__ == "__main__":
    main()
