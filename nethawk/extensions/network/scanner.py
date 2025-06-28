import json
import re
import shutil
import logging
import tempfile
from urllib.parse import urlparse
import xmltodict
import subprocess

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union

from rich.status import Status
from rich.console import Console

from nethawk.cli.options import Options
from nethawk.core.config import Config
from .highlight import NmapHighlighter

class NetworkScanner:
    # Initializes the NetworkScanner with host, configuration, and optional scan type.
    # Sets up temporary directories and finds the nmap executable.
    def __init__(
        self, 
        host: str, 
        config: dict | None = None, 
        scan_type: Optional[str] = None,
        version: bool = False
    ):
        if config:
            self.config = config
        else:
            self.config = Config().get('nmap')

        self.options = Options()
        self.console = Console()
        self.host = host
        self.scan_type = scan_type
        self.version = version
        self.results_dir = Path(tempfile.mkdtemp(prefix="nmap_scan_"))
        self.nmap_path = self._find_nmap()
        self.last_xml_results: Optional[Path] = None
        self.last_raw_results: Optional[Path] = None
        self.profile = self._load_profile()

        logging.debug(f"Nmap path: {self.nmap_path}")
        logging.debug(f"Temp results dir: {self.results_dir}")
        logging.debug(f"Config: {self.config}")

    # Finds the nmap executable in the system's PATH.
    def _find_nmap(self) -> str:
        path = shutil.which("nmap")
        if not path:
            raise EnvironmentError("Nmap not found in PATH.")
        return path

    # Loads the scan profile based on the specified scan type from the configuration.
    def _load_profile(self) -> dict:
        profiles = self.config.get("profiles", {})
        profile = {}

        if self.scan_type and self.scan_type in profiles:
            profile = profiles[self.scan_type]

            # validate if profile has ports if not and not False set the default ports
            if profile and not profile.ports and profile["ports"] is not False:
                profile["ports"] = self.get_formatted_default_ports()

        logging.debug(f"Profile Details: {profile}")

        return profile

    # Generates file paths for saving raw and XML nmap output.
    def _generate_output_paths(self, label: str) -> Tuple[Path, Path]:
        txt_path = self.results_dir / f"{label}.nmap"
        xml_path = self.results_dir / f"{label}.xml"
        return txt_path, xml_path

    # Initiates an Nmap scan with optional ports, sudo privileges, and output display.
    def scan(self, ports: Optional[str] = None, sudo: bool = False, output: bool = True):
        label = f"scan_{datetime.now():%Y%m%d%H%M%S}"
        self.last_raw_results, self.last_xml_results = self._generate_output_paths(label)

        if ports:
            logging.debug(f'Ports set [{ports}] Skipping default ports scans')

        cmd = self._build_command(ports, sudo)
        logging.debug(cmd)
        logging.debug(f"Executing command: {' '.join(map(str, cmd))}")

        self._execute_nmap(cmd, output)
    
    # Formats the default TCP and UDP ports from the configuration into an Nmap-compatible string.
    def get_formatted_default_ports(self):
        # Format TCP ports range into the T:<tcp> format
        tcp_ports = self.config.get("ports", {}).get("tcp")

        if isinstance(tcp_ports, str):  # If the TCP ports are a string range (e.g., "1-65535")
            tcp_str = f"T:{tcp_ports}"
        elif isinstance(tcp_ports, list):  # If it's a list of specific ports
            tcp_str = f"T:{','.join(map(str, tcp_ports))}"
        else:
            tcp_str = ""

        # Format UDP ports into the U:<udp> format
        udp_ports = self.config.get("ports", {}).get("udp")
        if isinstance(udp_ports, list):  # If it's a list of ports
            udp_str = f"U:{','.join(map(str, udp_ports))}"
        else:
            udp_str = ""

        # Combine both strings with a comma
        return f"{tcp_str},{udp_str}" if tcp_str and udp_str else tcp_str or udp_str
       
    # Builds the Nmap command based on the host, ports, sudo option, and profile arguments.
    def _build_command(self, ports: Optional[str], sudo: bool) -> List[str]:
        cmd = []

        # Determine scan flags based on ports string (TCP/UDP)
        has_tcp = False
        has_udp = False

        effective_ports = ports or self.profile.get("ports") # override default ports if provided
        # if ports are none use default ports
        if not effective_ports or effective_ports == 'default': 
            effective_ports = self.get_formatted_default_ports()

        if self.profile.get("ports") is False:
            effective_ports = None
            logging.warning(f"[{str(self.scan_type).upper()}] Profile ports are set to 'False'. it cannot be override by default.")
        
        logging.debug(f"Ports to use: {effective_ports}")

        if sudo:
            cmd.append("sudo")

        cmd.append(self.nmap_path)

        if self.host:
            cmd.append(self.host)

        if effective_ports:
            if "U:" in effective_ports:
                has_udp = True
            if "T:" in effective_ports or ("," in effective_ports and not has_udp):
                has_tcp = True # Presence of TCP ports detected (or no UDP at all)

        args_str = self.profile.get("arguments", "")
        
        logging.debug(f"Arguments command: {args_str}")

        # Add appropriate scan flags if not already specified in profile arguments
        # (If profile arguments already have -sS/-sT/-sU etc, skip adding)
        if not any(flag in args_str for flag in ["-sS"]) : # Check for common TCP scan flags
            if has_tcp:
                cmd.append("-sS")  # SYN scan

        if not any(flag in args_str for flag in ["-sU"]) : # Check for common UDP scan flags
            if has_udp:
                cmd.append("-sU") # UDP scan

        if not any(flag in args_str for flag in ["-sV"]) : # Check for version enabled
            if self.version:
                cmd.append("-sV") # Version enumeration
                
        # Add profile arguments
        if args_str:
            cmd.extend(args_str.split())
        
        if effective_ports:
            cmd.extend(["-p", effective_ports])
        
        # if '--min-rate' not in args_str:
        #     cmd.extend(["--min-rate", str(self.config.get('min_rate'))])

        # if '--max-retries' not in args_str:
        #     cmd.extend(["--max-retries", str(self.config.get('max_retries'))])

        # check if prfiles have scripts command
        if self.profile.get("scripts"):
            cmd.extend(["--script", self.profile["scripts"]])

        # save output on temp location
        cmd.extend([
            "-oN", str(self.last_raw_results),
            "-oX", str(self.last_xml_results),
        ])
        
        options = self.options.main_args()

        if options.verbose:
            cmd.append("-v")

        return cmd

    # Executes the Nmap command and optionally displays the output using a highlighter.
    def _execute_nmap(self, cmd: List[str], output: bool):
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        if not proc.stdout:
            return

        if not output:
            # Consume output silently to avoid hanging
            for _ in proc.stdout:
                pass
            return
        
        highlighter = NmapHighlighter(console=self.console)

        with Status("[bold green]Scanning with Nmap...", console=self.console, spinner="dots"):
            for line in proc.stdout:
                highlighter.process_output([line])

    # Recursively removes 'extraports' entries from the parsed Nmap XML data.
    def remove_extraports(self, data: Union[dict, list]) -> Union[dict, list]:
        if isinstance(data, dict):
            if "extraports" in data:
                del data["extraports"]
            for key in data:
                self.remove_extraports(data[key])
        elif isinstance(data, list):
            for item in data:
                self.remove_extraports(item)

        return data

    # Retrieves and parses the Nmap XML results.
    def get_results(self) -> dict:
        if not self.last_xml_results or not self.last_xml_results.exists():
            raise FileNotFoundError("XML output not found.")

        with open(self.last_xml_results, "r") as f:
            xml_content = f.read()

        parsed = xmltodict.parse(xml_content, attr_prefix="")

        cleaned = self.remove_extraports(parsed)

        if not isinstance(cleaned, dict):
            raise ValueError("Parsed XML did not return a dictionary.")

        return cleaned

    # Extracts host data from the parsed Nmap results.
    def _get_host_data(self) -> List[dict]:
        data = self.get_results()
        hosts = data["nmaprun"].get("host", [])
        if isinstance(hosts, dict):
            return [hosts]
        return hosts

    # Gets a list of host IP addresses from the scan results.
    def get_hosts(self) -> List[str]:
        hosts = self._get_host_data()
        return [host["address"]["addr"] for host in hosts]
    
    # Returns the IP address of the first scanned host.
    def _get_primary_host_ip(self) -> Optional[str]:
        """Returns the IP of the first scanned host."""
        hosts = self.get_hosts()
        return hosts[0] if hosts else None

    # Retrieves port information for all hosts or a specific host from the scan results.
    def get_ports(self, host: Optional[str] = None) -> Union[List[dict], Dict[str, List[dict]]]:
        results = {}

        if not host:
            host = self._get_primary_host_ip()

        for h in self._get_host_data():
            ip = h["address"]["addr"]
            ports_info = []

            ports_data = h.get("ports", {}).get("port", [])
            if isinstance(ports_data, dict):
                ports_data = [ports_data]

            for p in ports_data:
                state = p.get("state", {}).get("state")
                reason = p.get("state", {}).get("reason")
                ttl = p.get("state", {}).get("reason_ttl")
                # if state != "open":
                #     continue

                service_name = p.get("service", {}).get("name", "")
                ports_info.append({
                    "protocol": p["protocol"],
                    "port": int(p["portid"]),
                    "service": service_name,
                    "state": state,
                    "reason": reason,
                    "reason_ttl": ttl
                })

            results[ip] = ports_info

        if host:
            return results.get(host, [])
        
        return results
    
    # Gets a list of open ports, optionally formatted for Nmap input or with extra ports included.
    def get_open_ports(self, formatted: bool = False, extra_ports: Optional[List[int]] = None) -> Union[List[int], str]:
        """ Example Results: [22, 80]"""
        parts = []
        ports_data = self.get_ports()
        ports_by_proto = {"tcp": [], "udp": []}

        for host_ports in (ports_data.values() if isinstance(ports_data, dict) else [ports_data]):
            for entry in host_ports:
                ports_by_proto[entry["protocol"]].append(str(entry["port"]))

        if extra_ports and formatted:
            ports_by_proto["tcp"].extend(str(p) for p in extra_ports)

        if not formatted:
            return sorted(set(int(p) for p in ports_by_proto["tcp"] + ports_by_proto["udp"]))

        if ports_by_proto["tcp"]:
            parts.append("T:" + ",".join(sorted(set(ports_by_proto["tcp"]))))

        if ports_by_proto["udp"]:
            parts.append("U:" + ",".join(sorted(set(ports_by_proto["udp"]))))

        return ",".join(parts)

    # Extracts service information from the raw Nmap output.
    def get_service_info(self) -> dict:
        if not self.last_raw_results or not self.last_raw_results.exists():
            raise FileNotFoundError("Raw output not available.")

        with open(self.last_raw_results, "r") as f:
            for line in f:
                if "Service Info:" not in line:
                    continue

                parts = line.split("Service Info:")[1].strip().split(";")
                return {
                    key.strip(): value.strip()
                    for part in parts if ":" in part
                    for key, value in [part.split(":", 1)]
                }

        return {}

    # Retrieves the scan summary from the parsed Nmap results.
    def get_scan_summary(self) -> dict:
        """
        Example Results:
        {
        'elapsed': 0.76,
        'end_time': 'Mon Jun  2 00:17:14 2025',
        'status': 'success',
        'summary': 'Nmap done at Mon Jun  2 00:17:14 2025; 1 IP address (1 host up) ' 'scanned in 0.76 seconds'
        }
        """
        data = self.get_results()
        finished = data["nmaprun"]["runstats"]["finished"]

        return {
            "summary": finished["summary"],
            "elapsed": float(finished["elapsed"]),
            "end_time": finished["timestr"],
            "status": finished["exit"]
        }

    # Gets detailed service information for all hosts or a specific host from the scan results.
    def get_services(self, host: Optional[str] = None) -> List[dict]:
        results = []

        if not host:
            host = self._get_primary_host_ip()

        for h in self._get_host_data():
            ip = h["address"]["addr"]

            if host and ip != host:
                continue

            ports = h.get("ports", {}).get("port", [])
            if isinstance(ports, dict):
                ports = [ports]

            for p in ports:
                if p["state"]["state"] != "open":
                    continue

                service = p.get("service", {})
                cpe = service.get("cpe")
                if cpe and not isinstance(cpe, list):
                    service["cpe"] = [cpe]

                results.append({
                    "protocol": p["protocol"],
                    "port": int(p["portid"]),
                    "name": service.get("name"),
                    "product": service.get("product", "unknown"),
                    "version": service.get("version", "unknown"),
                    "extrainfo": service.get("extrainfo", "unknown"),
                    "cpe": service.get("cpe", [])
                })

        return results
    
    def get_vhost(self):
        data = self.get_results()
        host = data.get('nmaprun', {}).get('host', {})
        ports = host.get('ports', {}).get('port', [])

        if isinstance(ports, dict):
            ports = [ports]

        # Scan once, prioritize HTTP/HTTPS immediately
        for port in ports:
            service_name = port.get('service', {}).get('name')
            
            if service_name in ('http', 'https'):
                scripts = port.get('script', [])

                if isinstance(scripts, dict):
                    scripts = [scripts]

                for script in scripts:
                    if script.get('id') == 'http-title':
                        elem = script.get('elem')
                        if isinstance(elem, dict) and elem.get('key') == 'redirect_url':
                            url_text = elem.get('#text')
                            if url_text:
                                hostname = urlparse(url_text).hostname
                                if hostname:
                                    return hostname

        return None
    
    # Retrieves host information (hostnames, status, reason) for all hosts from the scan results.
    def get_host_info(self) -> Dict[str, dict]:
        results = {}

        for h in self._get_host_data():
            ip = h["address"]["addr"]

            # Check if 'hostnames' exists and is not None
            hostnames_data = h.get("hostnames", None)
            
            # If hostnames_data is None or not a list, initialize it as an empty list
            if hostnames_data is None:
                hostnames_data = []
            elif isinstance(hostnames_data, dict):  # If it's a dictionary, convert it to a list
                hostnames_data = [hostnames_data]
            
            # Safely extract the hostnames, ensuring 'name' key exists in the dictionaries
            hostnames = [hn.get("name") for hn in hostnames_data if isinstance(hn, dict) and hn.get("name")]

            status = h.get("status", {}).get("state")
            reason = h.get("status", {}).get("reason")

            results[ip] = {
                "hostnames": hostnames,
                "status": status,
                "reason": reason
            }

        return results

    
    # Gets script output for all hosts or a specific host from the scan results.
    def get_scripts(self, host: Optional[str] = None) -> Union[List[dict], Dict[str, List[dict]]]:
        results = {}

        if not host:
            host = self._get_primary_host_ip()

        for h in self._get_host_data():
            ip = h["address"]["addr"]
            script_results = []

            ports = h.get("ports", {}).get("port", [])
            if isinstance(ports, dict):
                ports = [ports]

            for p in ports:
                scripts = p.get("script", [])
                if isinstance(scripts, dict):
                    scripts = [scripts]

                for script in scripts:
                    script_results.append({
                        "port": int(p["portid"]),
                        "protocol": p["protocol"],
                        "id": script.get("id"),
                        "output": script.get("output")
                    })

            results[ip] = script_results

        if host:
            return results.get(host, [])
        return results