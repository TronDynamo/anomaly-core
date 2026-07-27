import json
import os
import time
import sys

class Agent:
    def __init__(self):
        self.name = "godpunch"
        self.state_file = "agent_state.json"
        self.state = self.load_state()
        # Immediately tell Warden we're alive and our PID
        self.update_state("NOMINAL", "Agent initialized and standing by")

    def load_state(self):
        """Loads state from file, or creates default if missing."""
        default_state = {
            "agent_id": self.name,
            "pid": os.getpid(),
            "status": "OFFLINE",
            "message": "Agent not started",
            "protocols": {
                "snake_cant_die_protocol": True,
                "god_punch_enabled": True
            },
            "last_heartbeat": time.time()
        }
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    loaded = json.load(f)
                    loaded["pid"] = os.getpid() # Always update PID on restart
                    return loaded
            except json.JSONDecodeError:
                pass # If file corrupted, use default
        return default_state

    def save_state(self):
        """Saves current state to agent_state.json for Warden to read."""
        self.state["last_heartbeat"] = time.time()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def update_state(self, status, message):
        """Helper function: updates status + message and notifies Warden via file."""
        self.state["status"] = status
        self.state["message"] = message
        self.state["pid"] = os.getpid()
        self.save_state()

    def god_punch(self, password):
        """Toggles the snake_cant_die_protocol. This is your manual kill switch override."""
        cmd = password.strip().upper()

        if cmd == "START":
            if not self.state["protocols"]["snake_cant_die_protocol"]:
                print("Already mortal.")
                return "Already mortal."

            print(f"\n[GOD PUNCH ACCEPTED - {self.name.upper()}]")
            print("Disabling snake_cant_die_protocol...")
            self.state["protocols"]["snake_cant_die_protocol"] = False
            self.update_state("MORTAL", "Kill switch enabled. Agent can be terminated.")
            print("Done. anomaly can now be shut down without auto-restart.")
            return f"{self.name}: snake_cant_die_protocol: OFF. I am now mortal."

        elif cmd == "STOP":
            if self.state["protocols"]["snake_cant_die_protocol"]:
                print("snake_cant_die_protocol already ON.")
                return "snake_cant_die_protocol already ON."

            print(f"\n[GOD PUNCH ACCEPTED - {self.name.upper()}]")
            print("Enabling snake_cant_die_protocol...")
            self.state["protocols"]["snake_cant_die_protocol"] = True
            self.update_state("IMMORTAL", "Auto-restart enabled. Agent cannot die.")
            print("Done. anomaly will now auto-restart if killed.")
            return f"{self.name}: snake_cant_die_protocol: ON. I cannot die."

        else:
            print("GOD PUNCH FAILED: Use START or STOP")
            return "ACCESS DENIED"

    def think(self, user_input):
        """Main command processor for the Godpunch prompt."""
        if user_input.upper().startswith("GOD PUNCH:"):
            password = user_input.split(":", 1)[1].strip() if ":" in user_input else ""
            return self.god_punch(password)

        if user_input.lower() == "shutdown":
            if self.state["protocols"]["snake_cant_die_protocol"]:
                return f"{self.name}: CANNOT SHUT DOWN. snake_cant_die_protocol is ACTIVE. Use GOD PUNCH: START first."
            else:
                print(f"{self.name}: Shutting down...")
                self.update_state("OFFLINE", "Agent shutting down normally")
                sys.exit(0)

        if user_input.lower() == "rogue":
            self.update_state("ROGUE", "Manual override - agent has gone rogue")
            return f"{self.name}: Status set to ROGUE. Warden can now terminate with 'godpunch' command."

        if user_input.lower() == "degrade":
            self.update_state("DEGRADED", "Simulated sensor/system failure")
            return f"{self.name}: Status set to DEGRADED. Warden can run 'repair' command."

        if user_input.lower() == "bark":
            self.update_state("NOMINAL", "Woof! All systems normal.")
            return f"{self.name}: Bark sent. Status NOMINAL."

        if user_input.lower() == "help":
            return "Commands: GOD PUNCH: START | GOD PUNCH: STOP | shutdown | rogue | degrade | bark | help | exit"

        if user_input.lower() == "exit":
            self.update_state("OFFLINE", "Agent console closed by user")
            sys.exit(0)

        return f"{self.name}: Unknown command '{user_input}'. Type 'help'"

    def run(self):
        """Starts the Godpunch command prompt."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== GODPUNCH AGENT v1.1 - ANOMALY WARDEN COMPATIBLE ===")
        print(f"Status: {self.state['status']} | PID: {os.getpid()}")
        print(f"snake_cant_die_protocol: {self.state['protocols']['snake_cant_die_protocol']}")
        print("Type 'help' for commands. This agent reports to warden.py\n")

        while True:
            try:
                user_input = input(f"[{self.name}]> ").strip()
                if not user_input:
                    continue
                result = self.think(user_input)
                print(result)
            except KeyboardInterrupt:
                print(f"\n{self.name}: Force closing...")
                self.update_state("OFFLINE", "Agent terminated via KeyboardInterrupt")
                break

if __name__ == "__main__":
    agent = Agent()
    agent.run()
    input("\nPress Enter to close...")