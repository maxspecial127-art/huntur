import os
import subprocess
import platform
import datetime
import socket

from modules import banner
from modules import color

# ---------------------------------------------------------------- globals
run_tool = True
operating_system = platform.system()
opener = "start" if operating_system == "Windows" else ("open" if operating_system == "Darwin" else "xdg-open")
clear = "cls" if operating_system == "Windows" else "clear"

page_number = 0
page = banner.menu[page_number]

pull_location = ""
screenshot_location = ""
screenrecord_location = ""

selected_banner = color.color_list[0] + banner.banner_list[0]


# ---------------------------------------------------------------- helpers
def run(cmd):
    """Execute a shell command safely and return (returncode, stdout)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def adb(*args):
    """Run an adb command, return (returncode, stdout)."""
    cmd = "adb " + " ".join(args)
    return run(cmd)


def check_packages():
    required = {
        "adb": "ADB",
        "scrcpy": "Scrcpy",
        "nmap": "Nmap",
    }
    missing = []
    for binary, label in required.items():
        rc, _ = run(f"which {binary}" if operating_system != "Windows" else f"where {binary}")
        if rc != 0:
            missing.append(label)

    if missing:
        print(f"\n{color.RED}ERROR: The following required software are NOT installed:\n")
        for i, name in enumerate(missing, 1):
            print(f"{color.YELLOW}{i}. {name}{color.WHITE}")
        print(f"\n{color.CYAN}Please install the above listed software.{color.WHITE}\n")
        choice = input(f"{color.GREEN}Continue anyway? Y / N > {color.WHITE}").lower()
        if choice == "n":
            exit_tool()


def exit_tool():
    global run_tool
    run_tool = False
    print("\nExiting...\n")


# ---------------------------------------------------------------- ui
def display_menu():
    print(selected_banner, page)


def clear_screen():
    os.system(clear)
    display_menu()


def change_page(name):
    global page, page_number
    if name == "p" and page_number > 0:
        page_number -= 1
    elif name == "n" and page_number < len(banner.menu) - 1:
        page_number += 1
    page = banner.menu[page_number]
    clear_screen()


# ---------------------------------------------------------------- features
def connect():
    ip = input(f"\n{color.CYAN}Enter target phone IP{color.YELLOW} (e.g. 192.168.1.23){color.WHITE}\n> ")
    if ip == "":
        print(f"\n{color.RED}Null input{color.WHITE}")
        return
    if ip.count(".") != 3:
        print(f"\n{color.RED}Invalid IP address{color.WHITE}")
        return
    adb("kill-server")
    adb("start-server")
    adb("connect", f"{ip}:5555")


def list_devices():
    print()
    adb("devices", "-l")
    print()


def disconnect():
    print()
    adb("disconnect")
    print()


def scan_network():
    try:
        import nmap
    except ImportError:
        print(f"\n{color.RED}python-nmap not installed (pip install python-nmap){color.WHITE}")
        return

    print(f"\n{color.GREEN}Scanning local network...{color.WHITE}\n")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    subnet = s.getsockname()[0].rsplit(".", 1)[0] + ".0/24"

    scanner = nmap.PortScanner()
    scanner.scan(hosts=subnet, arguments="-sn")
    for host in scanner.all_hosts():
        if scanner[host]["status"]["state"] == "up":
            print(f"[{color.GREEN}+{color.WHITE}] {host}")
    print()


def mirror():
    print(f"""
    {color.WHITE}1.{color.GREEN} Default Mode
    {color.WHITE}2.{color.GREEN} Fast Mode (low quality)
    {color.WHITE}""")
    mode = input("> ")
    if mode == "1":
        os.system("scrcpy")
    elif mode == "2":
        os.system("scrcpy -m 1024 -b 1M")
    else:
        print(f"{color.RED}Invalid selection{color.WHITE}")


def get_screenshot():
    global screenshot_location
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"screenshot-{ts}.png"

    adb("shell", "screencap", "-p", f"/sdcard/{filename}")

    if screenshot_location == "":
        screenshot_location = input(
            f"{color.YELLOW}Save location (Enter for default 'Downloaded-Files'): {color.WHITE}> "
        ) or "Downloaded-Files"

    adb("pull", f"/sdcard/{filename}", screenshot_location)
    print(f"{color.PURPLE}Saved to {screenshot_location}/{filename}{color.WHITE}")


def screen_record():
    global screenrecord_location
    duration = input(f"{color.CYAN}Recording duration (seconds) > {color.WHITE}")
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"vid-{ts}.mp4"

    adb("shell", "screenrecord", "--time-limit", duration, f"/sdcard/{filename}")

    if screenrecord_location == "":
        screenrecord_location = input(
            f"{color.YELLOW}Save location (Enter for default): {color.WHITE}> "
        ) or "Downloaded-Files"

    adb("pull", f"/sdcard/{filename}", screenrecord_location)
    print(f"{color.PURPLE}Saved to {screenrecord_location}/{filename}{color.WHITE}")


def pull_file():
    global pull_location
    path = input(f"{color.CYAN}Path on device (e.g. /sdcard/Download/x.jpg){color.WHITE}\n> ")

    rc, _ = adb("shell", "test", "-e", path)
    if rc != 0:
        print(f"{color.RED}Location does not exist{color.WHITE}")
        return

    if pull_location == "":
        pull_location = input(
            f"{color.YELLOW}Save location (Enter for default): {color.WHITE}> "
        ) or "Downloaded-Files"

    adb("pull", path, pull_location)
    print(f"{color.PURPLE}Saved to {pull_location}{color.WHITE}")


def push_file():
    src = input(f"{color.CYAN}Local file path > {color.WHITE}")
    if not os.path.isfile(src):
        print(f"{color.RED}File not found{color.WHITE}")
        return
    dst = input(f"{color.CYAN}Destination on device (e.g. /sdcard/Documents) > {color.WHITE}")
    adb("push", f'"{src}"', dst)


def list_apps():
    print(f"""
    {color.WHITE}1.{color.GREEN} Third-party packages
    {color.WHITE}2.{color.GREEN} All packages
    {color.WHITE}""")
    mode = input("> ")
    flag = "-3" if mode == "1" else ""
    rc, out = adb("shell", "pm", "list", "packages", flag)
    for line in out.splitlines():
        print(f"{color.GREEN}• {color.WHITE}{line.replace('package:', '')}")
    print()


def launch_app():
    pkg = input(f"{color.CYAN}Package name (e.g. com.spotify.music) > {color.WHITE}")
    if not pkg:
        return
    adb("shell", "monkey", "-p", pkg, "1")


def install_app():
    path = input(f"{color.CYAN}APK path > {color.WHITE}").strip().strip('"').strip("'")
    if not os.path.isfile(path):
        print(f"{color.RED}File not found{color.WHITE}")
        return
    adb("install", f'"{path}"')


def uninstall_app():
    pkg = input(f"{color.CYAN}Package name > {color.WHITE}")
    if not pkg:
        return
    adb("uninstall", pkg)


def get_shell():
    os.system("adb shell")


def list_files():
    print()
    adb("shell", "ls", "-a", "/sdcard/")
    print()


def open_link():
    url = input(f"{color.YELLOW}URL > {color.WHITE}")
    if not url:
        return
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)


def get_device_info():
    props = [
        "ro.product.model", "ro.product.manufacturer", "ro.product.board",
        "ro.build.version.release", "ro.build.version.security_patch",
        "ro.build.date", "ro.build.version.sdk", "wifi.interface",
    ]
    for p in props:
        _, val = adb("shell", "getprop", p)
        print(f"{color.YELLOW}{p}:{color.WHITE} {val}")
    print()


def battery_info():
    _, out = adb("shell", "dumpsys", "battery")
    print(f"\n{color.YELLOW}Battery Information:{color.WHITE}\n{out}\n")


def dump_sms():
    global pull_location
    if pull_location == "":
        pull_location = input(f"{color.YELLOW}Save location: {color.WHITE}> ") or "Downloaded-Files"
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    out_file = f"{pull_location}/sms_dump-{ts}.txt"
    rc, out = adb(
        "shell", "content", "query", "--uri", "content://sms/",
        "--projection", "address:date:body",
    )
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{color.PURPLE}Saved to {out_file}{color.WHITE}")


def dump_contacts():
    global pull_location
    if pull_location == "":
        pull_location = input(f"{color.YELLOW}Save location: {color.WHITE}> ") or "Downloaded-Files"
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    out_file = f"{pull_location}/contacts_dump-{ts}.txt"
    rc, out = adb(
        "shell", "content", "query", "--uri", "content://contacts/phones/",
        "--projection", "display_name:number",
    )
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{color.PURPLE}Saved to {out_file}{color.WHITE}")


def dump_call_logs():
    global pull_location
    if pull_location == "":
        pull_location = input(f"{color.YELLOW}Save location: {color.WHITE}> ") or "Downloaded-Files"
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    out_file = f"{pull_location}/call_logs-{ts}.txt"
    rc, out = adb(
        "shell", "content", "query", "--uri", "content://call_log/calls",
        "--projection", "name:number:duration:date",
    )
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{color.PURPLE}Saved to {out_file}{color.WHITE}")


def reboot():
    adb("reboot")


def lock_device():
    adb("shell", "input", "keyevent", "26")
    print(f"{color.GREEN}Device locked{color.WHITE}")


def unlock_device():
    pw = input(f"{color.YELLOW}Password (Enter for blank) > {color.WHITE}")
    adb("shell", "input", "keyevent", "26")
    adb("shell", "input", "swipe", "200", "900", "200", "300", "200")
    if pw:
        adb("shell", "input", "text", f'"{pw}"')
    adb("shell", "input", "keyevent", "66")
    print(f"{color.GREEN}Device unlocked{color.WHITE}")


def extract_apk():
    global pull_location
    pkg = input(f"{color.CYAN}Package name > {color.WHITE}")
    if not pkg:
        return
    _, path = adb("shell", "pm", "path", pkg)
    path = path.replace("package:", "").strip()
    if not path:
        print(f"{color.RED}Package not found{color.WHITE}")
        return
    if pull_location == "":
        pull_location = "Downloaded-Files"
    adb("pull", path, pull_location)
    print(f"{color.PURPLE}Pulled to {pull_location}{color.WHITE}")


def stop_adb():
    adb("kill-server")
    print("ADB server stopped.")


def power_off():
    adb("shell", "reboot", "-p")


def keycode_menu():
    keys = {
        "1": ("3", "Home"),
        "2": ("4", "Back"),
        "3": ("187", "Recent Apps"),
        "4": ("26", "Power"),
        "5": ("24", "Volume Up"),
        "6": ("25", "Volume Down"),
        "7": ("66", "Enter"),
        "8": ("67", "Backspace"),
        "9": ("61", "Tab"),
        "10": ("111", "Esc"),
        "0": ("exit", "Back to main menu"),
    }
    while True:
        print(f"\n{color.CYAN}Keycode Menu{color.WHITE}")
        for k, (_, label) in keys.items():
            print(f"  {k}. {label}")
        choice = input(f"{color.RED}[KEYCODE] {color.WHITE}Selection > ")
        if choice == "0":
            return
        if choice in keys:
            code = keys[choice][0]
            adb("shell", "input", "keyevent", code)
            print(f"{color.YELLOW}Sent keyevent {code}{color.WHITE}")
        else:
            print(f"{color.RED}Invalid selection{color.WHITE}")


def clear_downloads():
    global pull_location
    if pull_location and os.path.isdir(pull_location):
        for f in os.listdir(pull_location):
            os.remove(os.path.join(pull_location, f))
        print(f"{color.GREEN}Cleared {pull_location}{color.WHITE}")
    else:
        print(f"{color.RED}No downloads folder set{color.WHITE}")


# ---------------------------------------------------------------- main loop
def main():
    print(f"\n {color.CYAN}99 : Clear Screen    p : Prev Page    n : Next Page    0 : Exit")
    option = input(f"\n{color.RED}[Main Menu] {color.WHITE}Enter selection > ").lower()

    match option:
        case "p": change_page("p")
        case "n": change_page("n")
        case "99": clear_screen()
        case "0": exit_tool()
        case "1": connect()
        case "2": list_devices()
        case "3": disconnect()
        case "4": scan_network()
        case "5": mirror()
        case "6": get_screenshot()
        case "7": screen_record()
        case "8": pull_file()
        case "9": push_file()
        case "10": launch_app()
        case "11": install_app()
        case "12": uninstall_app()
        case "13": list_apps()
        case "14": get_shell()
        case "15": list_files()
        case "19": open_link()
        case "20": get_device_info()
        case "21": battery_info()
        case "22": reboot()
        case "23": unlock_device()
        case "24": lock_device()
        case "25": dump_sms()
        case "26": dump_contacts()
        case "27": dump_call_logs()
        case "28": extract_apk()
        case "29": stop_adb()
        case "30": power_off()
        case "31": keycode_menu()
        case "32": clear_downloads()
        case "33": exit_tool()
        case _:
            print("\nInvalid selection!\n")


# ---------------------------------------------------------------- entry
if __name__ == "__main__":
    os.makedirs("Downloaded-Files", exist_ok=True)
    check_packages()
    clear_screen()
    while run_tool:
        try:
            main()
        except KeyboardInterrupt:
            exit_tool()
