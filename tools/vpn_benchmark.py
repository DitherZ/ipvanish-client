#!/usr/bin/env python3

# ╒═══ VPN BENCHMARK ═══════════════════════════════════════════════════════════════════════════════╕
# ├─────────────────────────────────────────────────────────────────────────────────────────────────┤
# │ >> FILEPATH:       $HOME/Projects/IPVanish-Client-v2/vpn_benchmark.py                           │
# │ >> AUTHOR:         DitherZ  /  https://github.com/DitherZ                                       │
# │ >> DESCRIPTION:    Parallel benchmark of OVPN configs with Australian speedtest endpoints       │
# │ >> VERSION LOG:    30 April — v2.2.2 | Replaced colorama with canonical pill ANSI system        │
# │                                                                                                 │
# ╰─────────────────────────────────────────────────────────────────────────────────────────────────╯

import os
import sys
import time
import json
import socket
import signal
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from urllib.parse import urlparse
import threading
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    from urllib.request import urlopen
    from urllib.error import URLError

# ════ TEXT FORMATTING / STYLING ══════════════════════════════════════════════════════════════════ #
BOLD="\033[1m"; ITL="\033[3m"; DIM="\033[2m"; SHDW="\033[1;2m"; STRB="\033[5m"
RC="\033[0m";   RCFG="\033[39m"; RCBG="\033[49m"; RCFX="\033[22m"; RCSB="\033[25m"
RVRS="\033[7m"; ULINE="\033[4;58;5;231m"

# ════ ANSI 256 COLORS (FG) ═══════════════════════════════════════════════════════════════════════ #
RED="\033[38;5;196m"; GRN="\033[38;5;46m";  YLW="\033[38;5;226m"; MAG="\033[38;5;201m"
CYN="\033[38;5;45m";  SKY="\033[38;5;123m"; WHT="\033[38;5;231m"; GRY="\033[38;5;234m"

# ════ RESET-PREFIX VARIANTS ══════════════════════════════════════════════════════════════════════ #
_RED="\033[0;38;5;196m"; _GRN="\033[0;38;5;46m";  _YLW="\033[0;38;5;226m"; _MAG="\033[0;38;5;201m"
_CYN="\033[0;38;5;45m";  _SKY="\033[0;38;5;123m"; _WHT="\033[0;38;5;231m"; _GRY="\033[0;38;5;234m"

# ════ PILL SHELL COMPONENTS ══════════════════════════════════════════════════════════════════════ #
_L1="\033[1;38;5;234m◢";  _L2="\033[1;38;5;234;48;5;234m◤"; _LBG="\033[22;3;48;5;234m"
_R1="\033[23;39;38;5;0m"; _R2="\033[1;38;5;234;48;5;234m◢"; _R3="\033[0;1;38;5;234m◤"
_S1="\033[22;23;38;5;239;48;5;234m◢"; _S2="\033[48;5;239m◤"; _SBG="\033[3;38;5;195m"
_SR="\033[25;23;38;5;239m◢\033[0;38;5;239m◤\033[0m"

# ════ PRINT ABSTRACTIONS ═════════════════════════════════════════════════════════════════════════ #
def print_info(msg): print(f"{_L1}{_L2}{_LBG}{CYN}{SHDW}INFO{_R1}{_R2}{_R3} {_CYN}{msg}{RC}")
def print_task(msg): print(f"\n{_L1}{_L2}{_LBG}{MAG}{SHDW}TASK{_R1}{_R2}{_R3} {_MAG}{msg}{RC}")
def print_done(msg): print(f"{_L1}{_L2}{_LBG}{GRN}{SHDW}DONE{_R1}{_R2}{_R3} {_GRN}{msg}{RC}")
def print_fail(msg): print(f"\n{_L1}{_L2}{_LBG}{RED}{SHDW}FAIL{_R1}{_R2}{_R3} {_RED}{msg}{RC}")
def print_warn(msg): print(f"{_L1}{_L2}{_LBG}{YLW}{SHDW}WARN{_R1}{_R2}{_R3} {_YLW}{msg}{RC}")
def user_input(msg): return input(f"\n{_L1}{_L2}{_LBG}{WHT}{SHDW}USER{_R1}{_R2}{_R3}{SKY}/ {RC}{msg}")
def print_path(p):   return f"{_SKY}{ITL}{p}{RC}"

# ════ SPEEDTEST SERVER CONFIGURATION ═════════════════════════════════════════════════════════════ #

@dataclass
class SpeedtestServer:
    name: str
    host: str
    port: int = 8080
    path: str = "/speedtest/upload.php"
    protocol: str = "http"
    priority: int = 1  # 1 = primary, 2 = secondary
    description: str = ""

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}{self.path}"

    @property
    def download_url(self) -> str:
        if "aarnet" in self.host:
            return f"{self.protocol}://{self.host}:{self.port}/speedtest/random4000x4000.jpg"
        elif "softlayer" in self.host:
            return f"{self.protocol}://{self.host}:{self.port}/downloads/test10.zip"
        else:
            return f"{self.protocol}://{self.host}:{self.port}/speedtest/random4000x4000.jpg"


AUSTRALIAN_SERVERS = [
    SpeedtestServer(
        name="Telstra",
        host="mel1.speedtest.telstra.net",
        port=8080,
        priority=1,
        description="Large backbone, excellent peering, very stable"
    ),
    SpeedtestServer(
        name="AARNet",
        host="vic-crlt-speedtest.aarnet.net.au",
        port=8080,
        priority=1,
        description="Academic/research network, extremely high capacity"
    ),
    SpeedtestServer(
        name="Vocus",
        host="speedtest.mel.m2core.net.au",
        port=8080,
        priority=1,
        description="Major wholesale backbone provider"
    ),
    SpeedtestServer(
        name="Internode",
        host="speedtest-mel.cdn.on.net",
        port=8080,
        priority=2,
        description="Solid infrastructure, decent peering"
    ),
    SpeedtestServer(
        name="Vodafone",
        host="my1.speedtest.vodafone.com.au",
        port=8080,
        priority=2,
        description="Mobile carrier network performance"
    ),
    SpeedtestServer(
        name="SoftLayer",
        host="speedtest.mel01.softlayer.com",
        port=8080,
        priority=2,
        description="Cloud/datacenter route testing"
    ),
    SpeedtestServer(
        name="CloudFlare",
        host="speed.cloudflare.com",
        port=443,
        path="/__down?bytes=100000000",
        protocol="https",
        priority=3,
        description="Global CDN fallback"
    ),
    SpeedtestServer(
        name="CacheFly",
        host="cachefly.cachefly.net",
        port=80,
        path="/100mb.test",
        priority=3,
        description="International CDN fallback"
    )
]

# ════ DATA CLASSES ════════════════════════════════════════════════════════════════════════════════ #

@dataclass
class VPNTestResult:
    config_name: str
    interface: str
    server_used: str
    server_host: str
    speed_mbps: float
    bytes_transferred: int
    duration: float
    success: bool = True
    error_msg: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ServerTestResult:
    server: SpeedtestServer
    speed_mbps: float
    latency_ms: float
    success: bool
    error_msg: str = ""

# ════ SPEEDTEST CLIENT ════════════════════════════════════════════════════════════════════════════ #

class SpeedtestClient:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = None
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Speedtest Client)'})

    def test_latency(self, server: SpeedtestServer) -> Optional[float]:
        try:
            start = time.time()
            if HAS_REQUESTS:
                self.session.head(server.url, timeout=5)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((server.host, server.port))
                sock.close()
            return (time.time() - start) * 1000
        except Exception:
            return None

    def test_download_speed(self, server: SpeedtestServer, duration: int = 10) -> Tuple[float, int]:
        bytes_downloaded = 0
        start_time = time.time()

        try:
            if HAS_REQUESTS:
                response = self.session.get(server.download_url, stream=True, timeout=self.timeout)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=8192):
                    if time.time() - start_time > duration:
                        break
                    if chunk:
                        bytes_downloaded += len(chunk)
            else:
                response = urlopen(server.download_url, timeout=self.timeout)
                while True:
                    if time.time() - start_time > duration:
                        break
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    bytes_downloaded += len(chunk)

            elapsed = time.time() - start_time
            if elapsed > 0:
                speed_mbps = (bytes_downloaded * 8) / (elapsed * 1_000_000)
                return speed_mbps, bytes_downloaded
            return 0, 0

        except Exception:
            return 0, 0

    def find_best_server(self, servers: List[SpeedtestServer]) -> List[ServerTestResult]:
        print_info("Testing speedtest servers...")

        server_results = []

        for server in servers:
            latency = self.test_latency(server)
            if latency:
                server_results.append(ServerTestResult(
                    server=server,
                    speed_mbps=0,
                    latency_ms=latency,
                    success=True
                ))
                print_info(f"  {server.name}: {latency:.1f}ms latency")
            else:
                print_warn(f"  {server.name}: unreachable")

        server_results.sort(key=lambda x: (x.server.priority, x.latency_ms))

        print_task("Testing server throughput...")
        for result in server_results[:3]:
            if result.success:
                speed, bytes_dl = self.test_download_speed(result.server, duration=5)
                if speed > 0:
                    result.speed_mbps = speed
                    print_done(f"  {result.server.name}: {speed:.1f} Mbps")
                else:
                    result.success = False
                    print_warn(f"  {result.server.name}: speed test failed")

        successful = [r for r in server_results if r.success and r.speed_mbps > 0]
        successful.sort(key=lambda x: (-x.speed_mbps, x.latency_ms))
        return successful

# ════ VPN BENCHMARK ══════════════════════════════════════════════════════════════════════════════ #

class VPNBenchmark:
    def __init__(self, config_dir: str, duration: int = 30, warmup: int = 5,
                 max_parallel: int = 10, auth_file: str = None,
                 use_curl: bool = True, test_servers: List[SpeedtestServer] = None):
        self.config_dir = Path(config_dir).expanduser()
        self.duration = duration
        self.warmup = warmup
        self.max_parallel = max_parallel
        self.auth_file = auth_file
        self.use_curl = use_curl
        self.test_servers = test_servers or AUSTRALIAN_SERVERS
        self.tmp_dir = Path(f"/tmp/vpn_bench_{os.getpid()}")
        self.results: List[VPNTestResult] = []
        self.active_tunnels: Dict[int, Dict] = {}
        self.lock = threading.Lock()
        self.speedtest_client = SpeedtestClient()
        self.selected_servers: List[ServerTestResult] = []

        self.tmp_dir.mkdir(exist_ok=True)
        log_dir = Path.home() / "Projects" / "IPVanish-Client-v2" / ".log"
        log_dir.mkdir(parents=True, exist_ok=True)

    def setup_auth(self, username: str = None, password: str = None) -> Optional[Path]:
        if self.auth_file and Path(self.auth_file).exists():
            return Path(self.auth_file)

        auth_path = self.tmp_dir / "auth.txt"

        if not username:
            username = user_input("Username: ")
        if not password:
            import getpass
            password = getpass.getpass(f"\n{_L1}{_L2}{_LBG}{WHT}{SHDW}USER{_R1}{_R2}{_R3}{SKY}/ {RC}Password: ")

        auth_path.write_text(f"{username}\n{password}\n")
        auth_path.chmod(0o600)
        return auth_path

    def find_configs(self) -> List[Path]:
        if not self.config_dir.exists():
            print_fail(f"Config directory not found: {print_path(str(self.config_dir))}")
            return []

        configs = list(self.config_dir.glob("ipvanish-*.ovpn")) + \
                  list(self.config_dir.glob("*.ovpn"))
        configs = sorted(list(dict.fromkeys(configs)))
        print_info(f"Found {len(configs)} config files in {print_path(str(self.config_dir))}")
        return configs

    def select_best_servers(self) -> List[SpeedtestServer]:
        self.selected_servers = self.speedtest_client.find_best_server(self.test_servers)

        if not self.selected_servers:
            print_warn("No speedtest servers available, using fallback")
            fallback = SpeedtestServer(
                name="CacheFly (Fallback)",
                host="cachefly.cachefly.net",
                port=80,
                path="/100mb.test",
                priority=99
            )
            return [fallback]

        best = self.selected_servers[0]
        print_done(f"Primary server: {best.server.name} ({best.speed_mbps:.1f} Mbps, {best.latency_ms:.1f}ms)")

        if len(self.selected_servers) > 1:
            fallbacks = ", ".join(s.server.name for s in self.selected_servers[1:3])
            print_info(f"Fallback servers: {fallbacks}")

        return [s.server for s in self.selected_servers]

    def start_vpn(self, config: Path, idx: int, auth_path: Path) -> Optional[int]:
        log_file = self.tmp_dir / f"vpn_{idx}.log"

        cmd = [
            "sudo", "openvpn",
            "--config", str(config),
            "--dev", f"tun{idx}",
            "--auth-user-pass", str(auth_path),
            "--daemon",
            "--log", str(log_file),
            "--writepid", str(self.tmp_dir / f"pid_{idx}")
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            pid_file = self.tmp_dir / f"pid_{idx}"
            for _ in range(5):
                if pid_file.exists():
                    try:
                        return int(pid_file.read_text().strip())
                    except ValueError:
                        pass
                time.sleep(0.5)
            return None
        except subprocess.CalledProcessError as e:
            print_warn(f"Failed to start VPN for {config.name}: {e.stderr}")
            return None

    def wait_for_interface(self, iface: str, timeout: int = 15) -> bool:
        for _ in range(timeout):
            result = subprocess.run(
                ["ip", "link", "show", iface],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True
            time.sleep(1)
        return False

    def get_rx_bytes(self, iface: str) -> int:
        stat_file = Path(f"/sys/class/net/{iface}/statistics/rx_bytes")
        try:
            return int(stat_file.read_text().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def is_dead_tunnel(self, iface: str) -> bool:
        b1 = self.get_rx_bytes(iface)
        time.sleep(2)
        b2 = self.get_rx_bytes(iface)
        return b2 <= b1

    def test_speed_with_fallback(self, iface: str, servers: List[SpeedtestServer]) -> Tuple[float, int, str, str]:
        for server in servers:
            try:
                if self.use_curl:
                    cmd = [
                        "timeout", str(self.duration),
                        "curl", "--interface", iface, "-s", "-o", "/dev/null",
                        "-w", "%{size_download}", server.url
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.duration + 5)
                    if result.returncode == 0 and result.stdout.strip():
                        bytes_downloaded = int(result.stdout.strip())
                        speed_mbps = (bytes_downloaded * 8) / (self.duration * 1_000_000)
                        if speed_mbps > 0:
                            return speed_mbps, bytes_downloaded, server.name, server.host
                else:
                    start_bytes = self.get_rx_bytes(iface)
                    traffic_cmd = [
                        "timeout", str(self.duration),
                        "curl", "--interface", iface, "-s", server.download_url, "-o", "/dev/null"
                    ]
                    subprocess.run(traffic_cmd, capture_output=True, timeout=self.duration + 5)
                    end_bytes = self.get_rx_bytes(iface)
                    bytes_downloaded = end_bytes - start_bytes
                    speed_mbps = (bytes_downloaded * 8) / (self.duration * 1_000_000)
                    if speed_mbps > 0:
                        return speed_mbps, bytes_downloaded, server.name, server.host

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
                print_warn(f"  Server {server.name} failed: {str(e)[:50]}")
                continue

        return 0, 0, "None", "None"

    def test_single_config(self, config: Path, idx: int, auth_path: Path,
                           servers: List[SpeedtestServer]) -> Optional[VPNTestResult]:
        pid = self.start_vpn(config, idx, auth_path)
        if not pid:
            return None

        iface = f"tun{idx}"
        if not self.wait_for_interface(iface):
            print_warn(f"{iface} never appeared for {config.name}")
            return None

        time.sleep(self.warmup)

        if self.is_dead_tunnel(iface):
            print_warn(f"{iface} appears dead (no traffic)")
            return None

        print_info(f"{iface} active — testing {config.name}")

        speed_mbps, bytes_dl, server_name, server_host = self.test_speed_with_fallback(iface, servers)

        if speed_mbps > 0:
            return VPNTestResult(
                config_name=config.name,
                interface=iface,
                server_used=server_name,
                server_host=server_host,
                speed_mbps=speed_mbps,
                bytes_transferred=bytes_dl,
                duration=self.duration,
                success=True
            )
        else:
            return VPNTestResult(
                config_name=config.name,
                interface=iface,
                server_used="None",
                server_host="None",
                speed_mbps=0,
                bytes_transferred=0,
                duration=self.duration,
                success=False,
                error_msg="All speedtest servers failed"
            )

    def run_parallel_benchmark(self, configs: List[Path], servers: List[SpeedtestServer],
                                username: str = None, password: str = None) -> List[VPNTestResult]:
        print_task(f"Starting parallel benchmark — up to {self.max_parallel} concurrent VPNs")

        auth_path = self.setup_auth(username, password)
        results = []
        test_configs = configs[:self.max_parallel]

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_to_config = {
                executor.submit(self.test_single_config, config, idx, auth_path, servers): config
                for idx, config in enumerate(test_configs)
            }

            completed = 0
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                completed += 1
                try:
                    result = future.result(timeout=self.duration + 45)
                    if result and result.success:
                        results.append(result)
                        print_done(f"[{completed}/{len(test_configs)}] {config.name}: {result.speed_mbps:.2f} Mbps via {result.server_used}")
                    else:
                        error = result.error_msg if result else "Unknown error"
                        print_warn(f"[{completed}/{len(test_configs)}] {config.name}: {error}")
                except TimeoutError:
                    print_fail(f"{config.name}: Test timeout")
                except Exception as e:
                    print_fail(f"{config.name}: {e}")

        return results

    def cleanup(self):
        print_task("Cleaning up VPN tunnels")
        try:
            subprocess.run(["sudo", "pkill", "-f", "openvpn.*tun"], capture_output=True)
        except Exception:
            pass
        time.sleep(2)
        try:
            import shutil
            shutil.rmtree(self.tmp_dir)
        except Exception:
            pass
        print_done("Cleanup complete")

    def display_results(self, results: List[VPNTestResult], top_n: int = 6):
        if not results:
            print_warn("No results to display")
            return

        results.sort(key=lambda x: x.speed_mbps, reverse=True)

        sep = f"{DIM}{'─' * 80}{RC}"
        hdr = f"{BOLD}{'═' * 80}{RC}"

        print(f"\n{hdr}")
        print(f"{BOLD}{CYN}  BENCHMARK RESULTS{RC}")
        print(hdr)
        print(f"{BOLD}  {'CONFIG':<40} {'SERVER':<15} {'SPEED':>12} {'DATA':>12}  STATUS{RC}")
        print(sep)

        for result in results:
            if result.success:
                status   = f"{GRN}✓{RC}"
                speed_str = f"{YLW}{result.speed_mbps:>7.2f} Mbps{RC}"
                data_str  = f"{self._format_bytes(result.bytes_transferred):>10}"
            else:
                status   = f"{RED}✗{RC}"
                speed_str = f"{RED}{'FAILED':>12}{RC}"
                data_str  = "       N/A"

            print(f"  {result.config_name:<40} {result.server_used:<15} {speed_str} {data_str}  {status}")

        print(f"\n{hdr}")
        print(f"{BOLD}{GRN}  TOP {top_n} CONFIGURATIONS{RC}")
        print(f"{hdr}\n")

        for i, result in enumerate(results[:top_n], 1):
            print(f"  {BOLD}{GRN}{i}. {result.config_name}{RC}")
            print(f"     {CYN}Speed    {RC}  {YLW}{result.speed_mbps:.2f} Mbps{RC}")
            print(f"     {CYN}Server   {RC}  {result.server_used} ({result.server_host})")
            print(f"     {CYN}Data     {RC}  {self._format_bytes(result.bytes_transferred)} in {result.duration}s")
            print(f"     {CYN}Interface{RC}  {result.interface}")
            print(f"     {DIM}Config    {print_path(str(self.config_dir / result.config_name))}{RC}\n")

    def _format_bytes(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"

    def save_results_json(self, results: List[VPNTestResult], output_file: str = None):
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"vpn_benchmark_{timestamp}.json"

        data = {
            "timestamp": datetime.now().isoformat(),
            "duration": self.duration,
            "warmup": self.warmup,
            "servers_tested": [{
                "name": s.server.name,
                "host": s.server.host,
                "latency_ms": s.latency_ms,
                "speed_mbps": s.speed_mbps,
                "success": s.success
            } for s in self.selected_servers],
            "results": [{
                "config": r.config_name,
                "interface": r.interface,
                "server_used": r.server_used,
                "speed_mbps": r.speed_mbps,
                "bytes_transferred": r.bytes_transferred,
                "duration": r.duration,
                "success": r.success,
                "error": r.error_msg,
                "timestamp": r.timestamp.isoformat()
            } for r in results]
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print_done(f"Results saved to {print_path(output_file)}")

# ════ MAIN ════════════════════════════════════════════════════════════════════════════════════════ #

def main():
    parser = argparse.ArgumentParser(
        description="Parallel VPN benchmark tool for OpenVPN configs with Australian speedtest endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d ~/configs
  %(prog)s -d ~/configs -t 60 -p 5 --json
  %(prog)s -d ~/configs --no-curl -u username --top 10
  %(prog)s --list-servers
        """
    )

    parser.add_argument("-d", "--config-dir",
                        default="~/Projects/IPVanish-Client-v2/config",
                        help="Directory containing OpenVPN configs")
    parser.add_argument("-u", "--username",    help="VPN username")
    parser.add_argument("-p", "--password",    help="VPN password")
    parser.add_argument("-t", "--duration",    type=int, default=30,
                        help="Test duration in seconds (default: 30)")
    parser.add_argument("-w", "--warmup",      type=int, default=5,
                        help="Warmup period in seconds (default: 5)")
    parser.add_argument("-c", "--concurrency", type=int, default=10,
                        help="Maximum concurrent VPNs (default: 10)")
    parser.add_argument("--top",               type=int, default=6,
                        help="Number of top results to display (default: 6)")
    parser.add_argument("--no-curl",           action="store_true",
                        help="Use interface counters instead of curl")
    parser.add_argument("--auth-file",         help="Path to auth file (user/pass on separate lines)")
    parser.add_argument("--json",              action="store_true",
                        help="Save results to JSON file")
    parser.add_argument("--list-servers",      action="store_true",
                        help="List available speedtest servers and exit")

    args = parser.parse_args()

    if args.list_servers:
        print(f"\n{BOLD}Available Australian Speedtest Servers:{RC}\n")
        for server in AUSTRALIAN_SERVERS:
            tier = "Primary" if server.priority == 1 else "Secondary" if server.priority == 2 else "Fallback"
            print(f"  {GRN}{server.name:<12}{RC}  {server.host}")
            print(f"  {DIM}  [{tier}] {server.description}{RC}\n")
        return 0

    if args.no_curl and os.geteuid() != 0:
        print_warn("Interface counter mode requires root — restarting with sudo...")
        os.execvp("sudo", ["sudo", "/usr/bin/python3", __file__] + sys.argv[1:])

    benchmark = VPNBenchmark(
        config_dir=args.config_dir,
        duration=args.duration,
        warmup=args.warmup,
        max_parallel=args.concurrency,
        auth_file=args.auth_file,
        use_curl=not args.no_curl
    )

    try:
        print_task("Selecting optimal speedtest servers")
        test_servers = benchmark.select_best_servers()

        if not test_servers:
            print_fail("No speedtest servers available")
            return 1

        configs = benchmark.find_configs()
        if not configs:
            print_fail("No configuration files found")
            return 1

        results = benchmark.run_parallel_benchmark(
            configs,
            test_servers,
            username=args.username,
            password=args.password
        )

        if results:
            benchmark.display_results(results, top_n=args.top)

            if args.json:
                benchmark.save_results_json(results)

            total = len(configs[:args.concurrency])
            print_done(f"Benchmark complete — {len(results)} successful / {total} tested")
        else:
            print_fail("No successful tests completed")
            return 1

        log_dir  = Path.home() / "Projects" / "IPVanish-Client-v2" / ".log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"vpnbench_{datetime.now().strftime('%d-%m')}.log"

        with open(log_file, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n[{ts}] === Results ===\n")
            for result in results:
                f.write(f"{result.config_name},{result.speed_mbps:.2f},{result.server_used},{result.bytes_transferred}\n")

        return 0

    except KeyboardInterrupt:
        print_warn("Interrupted by user")
        return 130
    except Exception as e:
        print_fail(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    sys.exit(main())
