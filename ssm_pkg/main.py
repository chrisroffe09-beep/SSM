#!/usr/bin/env python3
import psutil
import time
import socket
import threading
from datetime import timedelta
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.style import Style
import keyboard
import speedtest

console = Console()
kill_requested = False
network_visible = True
freeze = False
speedtest_active = False
speedtest_running = False
speedtest_final = None

# ---------------- Key Listener ----------------
def listen_for_keys():
    global kill_requested, network_visible, freeze, speedtest_active
    while True:
        key = keyboard.read_event()
        if key.event_type == "down":
            if key.name == "k":
                kill_requested = True
            elif key.name == "n":
                network_visible = True
                speedtest_active = True
            elif key.name == "f":
                freeze = not freeze

# ---------------- Helper Functions ----------------
def get_color(value: float) -> str:
    if value < 50:
        return "green"
    elif value < 80:
        return "yellow"
    else:
        return "red"

def format_speed(bps: float) -> str:
    mbps = bps / 1_000_000
    return f"{mbps:.2f} Mbps"

def get_system_stats():
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    uptime = str(timedelta(seconds=uptime_seconds)).split('.')[0]
    hostname = socket.gethostname()
    return {
        "cpu": cpu,
        "mem_used": mem.percent,
        "disk_used": disk.percent,
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

# ---------------- Layout ----------------
def create_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="bars", size=6),
        Layout(name="bottom")
    )
    layout["bottom"].split_row(
        Layout(name="left", ratio=60),
        Layout(name="disk_preview", ratio=40)
    )
    layout["left"].split_column(
        Layout(name="processes", ratio=60),
        Layout(name="network", ratio=40)
    )
    return layout

def build_bars(stats):
    cpu_color = get_color(stats["cpu"])
    mem_color = get_color(stats["mem_used"])
    disk_color = get_color(stats["disk_used"])

    cpu_bar = Progress(
        "[bold blue]CPU   ",
        BarColumn(bar_width=None, complete_style=Style(color=cpu_color)),
        TextColumn("{task.percentage:>3.0f}%")
    )
    mem_bar = Progress(
        "[bold magenta]Memory",
        BarColumn(bar_width=None, complete_style=Style(color=mem_color)),
        TextColumn("{task.percentage:>3.0f}%")
    )
    disk_bar = Progress(
        "[bold yellow]Disk  ",
        BarColumn(bar_width=None, complete_style=Style(color=disk_color)),
        TextColumn("{task.percentage:>3.0f}%")
    )
    cpu_bar.add_task("CPU", total=100, completed=stats["cpu"])
    mem_bar.add_task("Memory", total=100, completed=stats["mem_used"])
    disk_bar.add_task("Disk", total=100, completed=stats["disk_used"])
    bars_table = Table.grid(expand=True)
    bars_table.add_row(cpu_bar)
    bars_table.add_row(mem_bar)
    bars_table.add_row(disk_bar)
    return bars_table

def build_process_table(top_procs):
    proc_table = Table(expand=True, show_header=True, header_style="bold cyan")
    proc_table.add_column("No.", justify="right")
    proc_table.add_column("PID", justify="right")
    proc_table.add_column("Name")
    proc_table.add_column("CPU %", justify="right")
    proc_table.add_column("Memory %", justify="right")
    for i, p in enumerate(top_procs, 1):
        proc_table.add_row(
            str(i),
            str(p["pid"]),
            p["name"][:20] if p["name"] else "N/A",
            f"{p['cpu_percent']:.1f}",
            f"{p['memory_percent']:.1f}"
        )
    return proc_table

def build_disk_preview():
    disks = psutil.disk_partitions(all=False)
    table = Table(expand=True, show_header=True, header_style="bold magenta")
    table.add_column("Device")
    table.add_column("Mountpoint")
    table.add_column("FS Type")
    table.add_column("Used %", justify="right")
    for d in disks:
        try:
            usage = psutil.disk_usage(d.mountpoint)
            table.add_row(d.device, d.mountpoint, d.fstype, f"{usage.percent:.0f}%")
        except PermissionError:
            continue
    return Panel(table, title="Disk Preview", style="bold yellow")

# ---------------- Speedtest ----------------
def run_speedtest(panel):
    global speedtest_running, speedtest_final
    speedtest_running = True
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_bps = upload_bps = 0

        download_task = st.download
        upload_task = st.upload

        # Animate both download and upload
        download_bar = Progress(
            "[bold green]Download ",
            BarColumn(bar_width=None, complete_style=Style(color="green")),
            TextColumn("{task.percentage:>3.0f}% {task.fields[speed]}"),
        )
        upload_bar = Progress(
            "[bold cyan]Upload   ",
            BarColumn(bar_width=None, complete_style=Style(color="cyan")),
            TextColumn("{task.percentage:>3.0f}% {task.fields[speed]}"),
        )
        download_id = download_bar.add_task("download", total=100, speed="0 Mbps")
        upload_id = upload_bar.add_task("upload", total=100, speed="0 Mbps")

        panel.update(Panel(download_bar, title="Speedtest Download", style="bold green"))

        # Run download
        for i in range(20):
            partial = download_task()
            percent = min((i+1)*5, 100)
            download_bar.update(download_id, completed=percent, speed=format_speed(partial))
            panel.update(Panel(download_bar, title="Speedtest Download", style="bold green"))
            time.sleep(0.2)

        # Run upload
        for i in range(20):
            partial = upload_task()
            percent = min((i+1)*5, 100)
            upload_bar.update(upload_id, completed=percent, speed=format_speed(partial))
            panel.update(Panel(upload_bar, title="Speedtest Upload", style="bold cyan"))
            time.sleep(0.2)

        # Final results
        download_bps = st.results.download
        upload_bps = st.results.upload
        speedtest_final = (download_bps, upload_bps)
        panel.update(
            Panel(
                Text(f"Final Outputs:\nUp.: {format_speed(upload_bps)}\nDown.: {format_speed(download_bps)}", justify="center"),
                title="Speedtest Complete", style="bold green"
            )
        )

    except Exception as e:
        panel.update(Panel(Text(f"Speedtest failed: {e}", justify="center"), style="bold red"))
    finally:
        speedtest_running = False

# ---------------- Render ----------------
def render_layout(layout, stats, top_procs):
    header_text = Text(
        f"Sour CLI Sys Monitor — {stats['hostname']} | Uptime: {stats['uptime']}",
        style="bold green"
    )
    commands_text = Text(
        "Commands: Ctrl+C = Exit | k = Kill | n = Speedtest | f = Freeze",
        style="bold cyan"
    )
    layout["header"].update(Panel(header_text + "\n" + commands_text, style="bold white"))
    layout["bars"].update(build_bars(stats))
    layout["processes"].update(build_process_table(top_procs))
    layout["disk_preview"].update(build_disk_preview())

    if network_visible:
        if speedtest_running:
            pass  # The thread updates the panel directly
        elif speedtest_final:
            download_bps, upload_bps = speedtest_final
            layout["network"].update(
                Panel(
                    Text(f"Final Outputs:\nUp.: {format_speed(upload_bps)}\nDown.: {format_speed(download_bps)}", justify="center"),
                    title="Speedtest Complete", style="bold green"
                )
            )
        else:
            layout["network"].update(
                Panel(Text("Press 'n' to run Speedtest", justify="center"), style="bold green")
            )
    else:
        layout["network"].update(Panel(Text("Network panel hidden", justify="center"), style="bold green"))

# ---------------- Kill Process ----------------
def kill_proc_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
        psutil.wait_procs(children, timeout=3)
    except Exception as e:
        console.print(f"[red]Error killing process: {e}[/red]")

def kill_process_prompt(top_procs, live):
    live.stop()
    console.clear()
    console.print("[bold yellow]Kill a process[/bold yellow]")
    for i, p in enumerate(top_procs, 1):
        console.print(f"[cyan]{i}[/cyan]: {p['name']} (PID {p['pid']}) CPU {p['cpu_percent']:.1f}%")
    try:
        console.print()
        choice = int(console.input("[bold white]Enter process number to kill (0 to cancel): [/bold white]"))
        if choice == 0:
            console.print("[yellow]Canceled.[/yellow]")
        else:
            proc = top_procs[choice - 1]
            kill_proc_tree(proc["pid"])
            console.print(f"[green]Killed {proc['name']} (PID {proc['pid']})[/green]")
    except:
        console.print("[red]Invalid selection[/red]")
    finally:
        time.sleep(1)
        live.start()

# ---------------- Main ----------------
def main():
    global kill_requested, speedtest_active

    threading.Thread(target=listen_for_keys, daemon=True).start()
    layout = create_layout()

    with Live(layout, refresh_per_second=4, screen=True) as live:
        try:
            while True:
                stats = get_system_stats()
                top_procs = get_top_processes()

                if freeze:
                    time.sleep(0.2)
                    continue

                render_layout(layout, stats, top_procs)

                if kill_requested:
                    kill_requested = False
                    kill_process_prompt(top_procs, live)

                # Trigger Speedtest
                if network_visible and speedtest_active and not speedtest_running:
                    speedtest_active = False
                    threading.Thread(target=run_speedtest, args=(layout["network"],), daemon=True).start()

                time.sleep(0.2)

        except KeyboardInterrupt:
            console.print("\n[red]Exiting Sour CLI Sys Monitor...[/red]")

if __name__ == "__main__":
    main()
