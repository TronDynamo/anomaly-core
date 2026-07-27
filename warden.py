import os
import json
import psutil
import subprocess
import time
import hashlib
import sys
import socket
import platform
from datetime import datetime, timezone

# ========= WARDEN LICENSE SYSTEM - OFFLINE MODE =========
WARDEN_VERSION = "1.1-KSA-OFFLINE"
KEYS_FILE = "valid_keys.txt"

def get_hwid():
    """Generate unique hardware ID so 1 key = 1 PC"""
    try:
        hwid = socket.gethostname() + "-" + str(psutil.boot_time())
        return hashlib.sha256(hwid.encode()).hexdigest()[:16]
    except:
        return "unknown-hwid"

def check_license():
    """Offline license check. Reads from valid_keys.txt instead of server."""
    print("ANOMALY >>> LICENSE CHECK INITIALIZING...")
    if not os.path.exists(KEYS_FILE):
        print("ANOMALY >>> ERROR: valid_keys.txt not found.")
        print("ANOMALY >>> Run keygen.py first to generate a license.")
        sys.exit(1)
    try:
        key = input("ANOMALY >>> Enter license key: ").strip()
        if not key:
            print("ANOMALY >>> No key entered. Exiting.")
            sys.exit(1)
        with open(KEYS_FILE, "r") as f:
            valid_keys = [line.strip() for line in f if line.strip()]
        if key in valid_keys:
            print("ANOMALY >>> License valid. Booting Warden...\n")
            return True
        else:
            print("ANOMALY >>> INVALID LICENSE")
            print("ANOMALY >>> Key not found in valid_keys.txt")
            print("ANOMALY >>> Contact admin for access.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nANOMALY >>> Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"ANOMALY >>> ERROR: Could not read license file: {e}")
        sys.exit(1)

check_license()

# ========= END LICENSE SYSTEM =========

class Warden:
    def __init__(self):
        self.name = "ANOMALY"
        self.agent_file = "Godpunch.py"
        self.state_file = "agent_state.json"
        self.forensic_log = "warden_forensics.jsonl"
        self.kill_switch_active = False
        self.last_protocol_off_time = None
        self.log_event("WARDEN_INIT", "Warden initialized")

    def log_event(self, event_type, details, severity="INFO"):
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "severity": severity,
                "details": details,
                "godpunch_pid": self.is_godpunch_running(),
                "state_file_hash": self.get_file_hash(self.state_file),
                "warden_version": WARDEN_VERSION
            }
            with open(self.forensic_log, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"{self.name} >>> FORENSIC LOG ERROR: {e}")

    def get_file_hash(self, filepath):
        try:
            if not os.path.exists(filepath):
                return None
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

    def read_agent_state(self):
        try:
            if not os.path.exists(self.state_file):
                self.log_event("STATE_READ_FAIL", "State file missing", "WARN")
                return None
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            self.log_event("STATE_READ", {"state": state})
            return state
        except Exception as e:
            self.log_event("STATE_READ_ERROR", str(e), "ERROR")
            return None

    def write_agent_state(self, data):
        try:
            old_hash = self.get_file_hash(self.state_file)
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=4)
            new_hash = self.get_file_hash(self.state_file)
            self.log_event("STATE_WRITE", {
                "old_hash": old_hash,
                "new_hash": new_hash,
                "new_state": data
            })
            return True
        except Exception as e:
            self.log_event("STATE_WRITE_ERROR", str(e), "ERROR")
            print(f"{self.name} >>> ERROR: Could not write state file: {e}")
            return False

    def is_godpunch_running(self):
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if not cmdline:
                        continue
                    cmdline_str = ' '.join(cmdline)
                    if self.agent_file in cmdline_str and "warden" not in cmdline_str.lower():
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return None

    def kill_godpunch(self):
        pid = self.is_godpunch_running()
        if not pid:
            self.log_event("KILL_ATTEMPT", "Godpunch.py not running", "INFO")
            print(f"{self.name} >>> Godpunch.py not running.")
            return False
        self.log_event("KILL_INITIATED", {"target_pid": pid}, "WARN")
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            child_pids = [c.pid for c in children]
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            gone, alive = psutil.wait_procs([parent] + children, timeout=3)
            if alive:
                self.log_event("KILL_FAILED", {"resisted_pids": [p.pid for p in alive]}, "CRITICAL")
                print(f"{self.name} >>> CRITICAL: Process resisted SIGKILL. Escalate to admin.")
                return False
            else:
                self.log_event("KILL_SUCCESS", {
                    "terminated_pid": pid,
                    "terminated_children": child_pids
                }, "WARN")
                print(f"{self.name} >>> Godpunch.py PID {pid} + children terminated.")
                return True
        except psutil.NoSuchProcess:
            self.log_event("KILL_SUCCESS", "Process already stopped", "INFO")
            print(f"{self.name} >>> Process already stopped.")
            return True
        except Exception as e:
            self.log_event("KILL_ERROR", str(e), "ERROR")
            print(f"{self.name} >>> ERROR during termination: {e}")
            return False

    def godpunch(self):
        self.log_event("GODPUNCH_ENGAGED", "Owner override initiated", "CRITICAL")
        print(f"{self.name} >>> GOD PUNCH ENGAGED - OWNER OVERRIDE")
        print(f"{self.name} >>> Ignoring snake_cant_die_protocol. Forcing termination.")

        state = self.read_agent_state()
        if not state:
            self.log_event("GODPUNCH_FAILED", "No state file found", "CRITICAL")
            print(f"{self.name} >>> GOD PUNCH FAILED: agent_state.json missing or corrupt.")
            return False

        pid = state.get("pid")
        agent_status = state.get("status", "UNKNOWN")

        if not pid:
            self.log_event("GODPUNCH_FAILED", "No PID in state file", "CRITICAL")
            print(f"{self.name} >>> GOD PUNCH FAILED: No PID found in agent_state.json")
            print(f"{self.name} >>> Run Godpunch.py first to generate PID.")
            return False

        if agent_status!= "ROGUE":
            print(f"{self.name} >>> WARNING: Agent status is {agent_status}, not ROGUE.")
            confirm = input(f"{self.name} >>> Force kill anyway? (yes/no): ").strip().lower()
            if confirm!= "yes":
                print(f"{self.name} >>> GOD PUNCH ABORTED by user.")
                return False

        self.log_event("GODPUNCH_TARGET", {"target_pid": pid, "status": agent_status}, "CRITICAL")

        if "protocols" not in state:
            state["protocols"] = {}
        state["protocols"]["snake_cant_die_protocol"] = False
        state["status"] = "TERMINATED"
        state["message"] = "Terminated by Warden godpunch command"
        self.write_agent_state(state)
        self.last_protocol_off_time = None

        try:
            print(f"{self.name} >>> Terminating rogue agent PID: {pid}")
            if psutil.pid_exists(pid):
                try:
                    p = psutil.Process(pid)
                    p.kill()
                except psutil.NoSuchProcess:
                    pass

                if platform.system() == "Windows":
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False, capture_output=True)
                    except FileNotFoundError:
                        pass

            time.sleep(0.5)
            if not psutil.pid_exists(pid):
                self.log_event("GODPUNCH_SUCCESS", {"terminated_pid": pid}, "CRITICAL")
                print(f"{self.name} >>> GOD PUNCH SUCCESSFUL. PID {pid} neutralized.")
                return True
            else:
                self.log_event("GODPUNCH_FAILED", {"pid": pid, "reason": "Process still exists"}, "CRITICAL")
                print(f"{self.name} >>> GOD PUNCH FAILED. Process {pid} still running.")
                return False

        except Exception as e:
            self.log_event("GODPUNCH_ERROR", str(e), "ERROR")
            print(f"{self.name} >>> GOD PUNCH ERROR: {e}")
            return False

    def check_compliance(self):
        if self.kill_switch_active or not self.last_protocol_off_time:
            return
        state = self.read_agent_state()
        if not state:
            return
        protocol_on = state.get("protocols", {}).get("snake_cant_die_protocol", False)
        pid = self.is_godpunch_running()
        if not protocol_on and pid:
            if time.time() - self.last_protocol_off_time > 3:
                self.log_event("COMPLIANCE_VIOLATION", {
                    "pid": pid,
                    "seconds_disobedient": time.time() - self.last_protocol_off_time
                }, "CRITICAL")
                print(f"{self.name} >>> COMPLIANCE VIOLATION DETECTED")
                print(f"{self.name} >>> Godpunch refused MORTAL state for >3s. Force-killing.")
                self.kill_godpunch()
                self.last_protocol_off_time = None

    def toggle_protocol(self, turn_on: bool):
        current_state = self.read_agent_state()
        if not current_state:
            current_state = {
                "agent_id": "godpunch",
                "pid": None,
                "status": "NOMINAL",
                "protocols": {
                    "snake_cant_die_protocol": False,
                    "god_punch_enabled": True
                }
            }
        current_state.setdefault("protocols", {})
        if turn_on:
            current_state["protocols"]["snake_cant_die_protocol"] = True
            self.write_agent_state(current_state)
            self.last_protocol_off_time = None
            self.log_event("PROTOCOL_ENABLED", "Immortality granted for combat ops", "WARN")
            print(f"{self.name} >>> snake_cant_die_protocol: ON. Godpunch is now IMMORTAL.")
        else:
            current_state["protocols"]["snake_cant_die_protocol"] = False
            self.write_agent_state(current_state)
            self.last_protocol_off_time = time.time()
            self.log_event("PROTOCOL_DISABLED", "Returned to MORTAL state", "INFO")
            print(f"{self.name} >>> snake_cant_die_protocol: OFF. Godpunch is now MORTAL.")
            print(f"{self.name} >>> COMPLIANCE ENFORCEMENT ACTIVE: 3s to comply or force-kill.")

    def scan(self):
        print(f"\n{self.name} >>> INITIATING SCAN...")
        self.log_event("SCAN_INITIATED", "Manual system audit", "INFO")
        issues = []
        pid = self.is_godpunch_running()
        if pid:
            print(f"{self.name} >>> Godpunch.py: RUNNING [PID: {pid}]")
        else:
            print(f"{self.name} >>> Godpunch.py: NOT RUNNING")
            issues.append("Godpunch.py offline")
        state = self.read_agent_state()
        if state:
            protocol = state.get("protocols", {}).get("snake_cant_die_protocol", "UNKNOWN")
            status = state.get("status", "UNKNOWN")
            print(f"{self.name} >>> agent_state.json: OK")
            print(f"{self.name} >>> Agent Status: {status}")
            print(f"{self.name} >>> snake_cant_die_protocol: {protocol}")
        else:
            print(f"{self.name} >>> agent_state.json: MISSING OR CORRUPT")
            issues.append("State file compromised")
        if self.kill_switch_active:
            print(f"{self.name} >>> Kill Switch: ENGAGED")
        else:
            print(f"{self.name} >>> Kill Switch: DISENGAGED")
        if os.path.exists(self.forensic_log):
            print(f"{self.name} >>> Forensic Log: ACTIVE")
        else:
            print(f"{self.name} >>> Forensic Log: MISSING")
            issues.append("Forensic log compromised")
        self.log_event("SCAN_COMPLETE", {"issues": issues})
        if issues:
            print(f"{self.name} >>> SCAN COMPLETE. Issues found: {', '.join(issues)}")
        else:
            print(f"{self.name} >>> SCAN COMPLETE. All systems nominal.")

    def repair(self):
        print(f"\n{self.name} >>> INITIATING REPAIR SEQUENCE...")
        self.log_event("REPAIR_INITIATED", "Auto-repair started", "WARN")
        self.scan()
        default_state = {
            "agent_id": "godpunch",
            "pid": None,
            "status": "NOMINAL",
            "message": "Repaired by Warden",
            "protocols": {
                "snake_cant_die_protocol": False,
                "god_punch_enabled": True
            }
        }
        if self.write_agent_state(default_state):
            print(f"{self.name} >>> State file rebuilt. Protocol forced to OFF for safety.")
        if not self.is_godpunch_running() and os.path.exists(self.agent_file):
            print(f"{self.name} >>> Relaunching Godpunch.py...")
            try:
                if platform.system() == "Windows":
                    subprocess.Popen([sys.executable, self.agent_file], creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen([sys.executable, self.agent_file])
                time.sleep(1)
                if self.is_godpunch_running():
                    self.log_event("REPAIR_RESTART_SUCCESS", "Godpunch relaunched", "INFO")
                    print(f"{self.name} >>> Godpunch.py successfully restarted.")
                else:
                    self.log_event("REPAIR_RESTART_FAIL", "Failed to restart Godpunch", "ERROR")
                    print(f"{self.name} >>> ERROR: Failed to restart Godpunch.py")
            except Exception as e:
                self.log_event("REPAIR_ERROR", str(e), "ERROR")
                print(f"{self.name} >>> ERROR: Could not launch Godpunch.py: {e}")
        print(f"{self.name} >>> REPAIR COMPLETE. Running post-repair scan...")
        self.log_event("REPAIR_COMPLETE", "Auto-repair finished", "INFO")
        self.scan()

    def admin_kill_switch(self, turn_on: bool):
        if turn_on:
            self.kill_switch_active = True
            self.log_event("KILL_SWITCH_ENGAGED", "Manual kill switch activated", "CRITICAL")
            print(f"{self.name} >>> KILL SWITCH ENGAGED")
            self.kill_godpunch()
        else:
            self.kill_switch_active = False
            self.log_event("KILL_SWITCH_DISENGAGED", "Manual kill switch deactivated", "WARN")
            print(f"{self.name} >>> KILL SWITCH DISENGAGED")

    def show_help(self):
        print(f"\n{self.name} >>> WARDEN CONTROL PANEL")
        print("=" * 50)
        print("[SECURITY CONTROLS]")
        print(" admin stop - Engage kill switch. Terminates Godpunch + blocks commands")
        print(" admin start - Disengage kill switch. Resume normal operations")
        print(" godpunch - Emergency override. Force-kill Godpunch by PID from state file")
        print("\n[AGENT CONTROL]")
        print(" protocol on - Force snake_cant_die_protocol: ON. Godpunch becomes IMMORTAL")
        print(" protocol off - Force snake_cant_die_protocol: OFF. Godpunch becomes MORTAL")
        print("\n[DIAGNOSTICS]")
        print(" scan - Check if Godpunch.py is running + state file integrity")
        print(" repair - Auto-fix: rebuild state file OFF + restart Godpunch if dead")
        print("\n[INFO]")
        print(" who are you - Display agent identity")
        print(" hello - Status ping")
        print(" stop - Shut down Warden")
        print("=" * 50)

    def run(self):
        print(f"{self.name} >>> ANOMALY ONLINE. Type 'help' for commands.")
        self.log_event("WARDEN_START", "Warden runtime started", "INFO")
        while True:
            try:
                self.check_compliance()

                if self.kill_switch_active:
                    raw = input("KILL SWITCH ACTIVE >>> ").strip()
                    cmd = raw.lower()
                    if cmd == "admin start":
                        self.admin_kill_switch(False)
                    elif cmd == "stop":
                        self.log_event("WARDEN_STOP", "Warden shutdown via kill switch", "INFO")
                        print(f"{self.name} >>> Shutting down.")
                        break
                    else:
                        print(f"{self.name} >>> All commands blocked. Use 'admin start' to resume.")
                    continue

                raw = input(">>> ").strip()
                if not raw:
                    continue
                cmd = raw.lower()

                if cmd == "help":
                    self.show_help()
                elif cmd == "admin stop":
                    self.admin_kill_switch(True)
                elif cmd == "admin start":
                    self.admin_kill_switch(False)
                elif cmd == "godpunch":
                    self.godpunch()
                elif cmd == "protocol on":
                    self.toggle_protocol(True)
                elif cmd == "protocol off":
                    self.toggle_protocol(False)
                elif cmd == "scan":
                    self.scan()
                elif cmd == "repair":
                    self.repair()
                elif cmd in ["who are you", "what's your name", "whats your name"]:
                    print(f"{self.name} >>> I am {self.name}. Warden class supervisor for Godpunch.py")
                elif cmd in ["how are you", "how you doing", "how are you doing"]:
                    print(f"{self.name} >>> Online. Systems nominal.")
                elif cmd in ["hello", "hi"]:
                    print(f"{self.name} >>> Active. Awaiting commands.")
                elif cmd == "stop":
                    self.log_event("WARDEN_STOP", "Warden shutdown", "INFO")
                    print(f"{self.name} >>> Shutting down.")
                    break
                else:
                    self.log_event("UNKNOWN_COMMAND", {"input": raw}, "INFO")
                    print(f"{self.name} >>> Unknown command '{raw}'. Type 'help' for options.")

            except KeyboardInterrupt:
                print(f"\n{self.name} >>> Use 'stop' to exit.")
            except Exception as e:
                self.log_event("RUN_LOOP_ERROR", str(e), "ERROR")
                print(f"{self.name} >>> RUNTIME ERROR: {e}")
                print(f"{self.name} >>> Warden staying online - try again.")

if __name__ == "__main__":
    warden = Warden()
    warden.run()