from __future__ import annotations

import argparse
import pprint
import time
from dataclasses import dataclass, field
from os import path as os_path
from sys import path as sys_path
from typing import Any, Dict, List, Optional

import rticonnextdds_connector as rti

ROLE_CONTROLLER = 1
ROLE_DISTRIBUTION = 5
CONTROLLER_ID = "controller"

HEARTBEAT_TIMEOUT_S = 3.0
COMMAND_TIMEOUT_S = 5.0
STATE_SETTLE_TIMEOUT_S = 5.0
LOOP_SLEEP_S = 1.0


# ------------------------- generic helpers -------------------------

def get_nested(data: Any, *keys: Any, default: Any = None) -> Any:
    cur = data
    for key in keys:
        try:
            if isinstance(cur, dict):
                cur = cur[key]
            elif isinstance(cur, list) and isinstance(key, int):
                cur = cur[key]
            else:
                return default
        except (KeyError, IndexError, TypeError):
            return default
    return cur


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def looks_faulty(payload: Any) -> bool:
    text = normalize_text(payload)
    if not text:
        return False
    bad_words = [
        "FAULT",
        "FAIL",
        "ALARM",
        "TRIP",
        "ERROR",
        "INVALID",
        "UNSAFE",
        "REJECT",
        "OPEN_FAULT",
    ]
    return any(word in text for word in bad_words)


def continuity_matches_open(value: Any) -> Optional[bool]:
    text = normalize_text(value)
    if not text:
        return None
    if "OPEN" in text:
        return True
    if "CLOSE" in text or "CLOSED" in text:
        return False
    return None


class SequenceCounter:
    def __init__(self, start: int = 1) -> None:
        self.value = start

    def next(self) -> str:
        current = str(self.value)
        self.value += 1
        return current


@dataclass
class SourceState:
    device_id: str
    rated_kw: float = 0.0
    state: str = "ESSL_UNKNOWN"
    real_delivered_kw: float = 0.0
    last_seen: float = field(default_factory=time.time)


@dataclass
class PendingCommand:
    command_type: str
    sequence_id: str
    port_number: Optional[int]
    desired_open: Optional[bool]
    sent_at: float
    acknowledged: bool = False
    reply_ok: Optional[bool] = None
    reply_payload: Optional[Dict[str, Any]] = None


@dataclass
class FeederState:
    device_id: str
    features: List[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    last_heartbeat: float = 0.0
    heartbeat_sequence: Optional[int] = None

    diagnostic_state: Optional[Dict[str, Any]] = None
    grounding_state: Optional[Dict[str, Any]] = None
    control_parameter_state: Optional[Dict[str, Any]] = None
    measurements: Dict[str, Any] = field(default_factory=dict)
    power_ports: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    known_ports: set[int] = field(default_factory=set)

    last_reply: Optional[Dict[str, Any]] = None
    pending_command: Optional[PendingCommand] = None

    faults: List[str] = field(default_factory=list)
    advisories: List[str] = field(default_factory=list)
    desired_action: str = "NONE"
    desired_port: Optional[int] = None
    desired_open: Optional[bool] = None
    action_reason: str = ""

    def primary_port(self) -> int:
        if self.known_ports:
            return sorted(self.known_ports)[0]
        return 0


class MicrogridController:
    def __init__(self, xml_path: str, participant: str) -> None:
        self.xml_path = xml_path
        self.participant = participant
        self.pp = pprint.PrettyPrinter(indent=2)
        self.seq = SequenceCounter(1)
        self.feeder: Optional[FeederState] = None
        self.sources: Dict[str, SourceState] = {}
        self.loop_counter = 0

    # ------------------------- writer actions -------------------------
    def publish_identity(self) -> None:
        self.deviceInfoWriter.instance.set_dictionary(
            {
                "deviceId": CONTROLLER_ID,
                "role": ROLE_CONTROLLER,
                "product": {
                    "manufacturerName": "West Point",
                    "modelName": "Type V Controller",
                },
            }
        )
        self.deviceInfoWriter.write()
        self.activeDiagnosticStateWriter.instance.set_string("deviceId", CONTROLLER_ID)
        self.activeDiagnosticStateWriter.write()

    def send_heartbeat(self) -> None:
        self.heartbeatWriter.instance.set_string("deviceId", CONTROLLER_ID)
        self.heartbeatWriter.instance.set_number("sequenceNumber", self.loop_counter)
        self.heartbeatWriter.write()

    def send_generator_state(self, target_device_id: str, to_level: str, from_level: str = "ESSL_ANY") -> str:
        seq = self.seq.next()
        self.energyStartStopRequestWriter.instance.set_dictionary(
            {
                "requestId": {
                    "requestingDeviceId": CONTROLLER_ID,
                    "targetDeviceId": target_device_id,
                    "config": "CONFIG_ACTIVE",
                },
                "sequenceId": seq,
                "fromLevel": from_level,
                "toLevel": to_level,
                "switchConditions": [],
            }
        )
        self.energyStartStopRequestWriter.write()
        print(f"[WRITE] EnergyStartStopRequest target={target_device_id} toLevel={to_level} seq={seq}")
        return seq

    def send_power_switch(self, port_number: int, open_state: bool) -> Optional[str]:
        if self.feeder is None:
            return None

        seq = self.seq.next()
        continuity = "DCC_OPEN" if open_state else "DCC_CLOSED"
        payload = {
            "requestId": {
                "requestingDeviceId": CONTROLLER_ID,
                "targetDeviceId": self.feeder.device_id,
                "config": "CONFIG_ACTIVE",
                "portNumber": port_number,
            },
            "sequenceId": seq,
            "continuity": continuity,
        }
        self.powerSwitchWriter.instance.set_dictionary(payload)
        self.powerSwitchWriter.write()
        self.feeder.pending_command = PendingCommand(
            command_type="POWER_SWITCH",
            sequence_id=seq,
            port_number=port_number,
            desired_open=open_state,
            sent_at=time.time(),
        )
        print(
            f"[WRITE] PowerSwitchRequest target={self.feeder.device_id} port={port_number} continuity={continuity} seq={seq}"
        )
        return seq

    # ------------------------- reader plumbing -------------------------
    def _safe_take(self, reader: Any, wait_ms: int = 0) -> List[Dict[str, Any]]:
        try:
            if wait_ms > 0:
                reader.wait(wait_ms)
            reader.take()
            return [sample.get_dictionary() for sample in reader.samples.valid_data_iter]
        except Exception:
            return []

    def get_or_create_feeder(self, device_id: str, features: Optional[List[str]] = None) -> FeederState:
        if self.feeder is None or self.feeder.device_id != device_id:
            self.feeder = FeederState(device_id=device_id, features=features or [])
            print(f"[DISCOVER] Type III feeder locked: {device_id}")
        if features:
            self.feeder.features = features
        self.feeder.last_seen = time.time()
        return self.feeder

    def read_device_info(self) -> None:
        for msg in self._safe_take(self.deviceInfoReader):
            device_id = msg.get("deviceId")
            role = msg.get("role")
            if not device_id:
                continue

            if role == ROLE_DISTRIBUTION:
                features = get_nested(msg, "powerDevice", "distribution", "features", default=[]) or []
                self.get_or_create_feeder(device_id, features)
            else:
                source_max = get_nested(msg, "powerDevice", "source", "loadSharing", "maxRealPower", default=None)
                if source_max is None:
                    source_max = get_nested(msg, "powerDevice", "source", "maxRealPower", default=None)
                if source_max is not None:
                    src = self.sources.get(device_id) or SourceState(device_id=device_id)
                    src.rated_kw = float(source_max or 0.0) * 0.8
                    src.last_seen = time.time()
                    self.sources[device_id] = src
                    print(f"[DISCOVER] Source {device_id} rated_kw={src.rated_kw}")

    def read_heartbeat(self) -> None:
        for msg in self._safe_take(self.heartbeatReader):
            if self.feeder and msg.get("deviceId") == self.feeder.device_id:
                self.feeder.last_heartbeat = time.time()
                self.feeder.last_seen = self.feeder.last_heartbeat
                self.feeder.heartbeat_sequence = msg.get("sequenceNumber")
                print(f"[HB] feeder={self.feeder.device_id} seq={self.feeder.heartbeat_sequence}")

    def read_energy_start_stop_state(self) -> None:
        essl_map = {
            1: "ESSL_UNKNOWN",
            2: "ESSL_OFF",
            3: "ESSL_WARM",
            4: "ESSL_IDLE",
            5: "ESSL_READY",
            6: "ESSL_READY_SYNCED",
            7: "ESSL_OPERATIONAL",
        }
        for msg in self._safe_take(self.energyStartStopStateReader):
            device_id = msg.get("deviceId")
            src = self.sources.get(device_id)
            if src:
                src.state = essl_map.get(msg.get("presentLevel"), "ESSL_UNKNOWN")
                src.last_seen = time.time()

    def read_active_diagnostic_state(self) -> None:
        for msg in self._safe_take(self.activeDiagnosticStateReader):
            if self.feeder and msg.get("deviceId") == self.feeder.device_id:
                self.feeder.diagnostic_state = msg
                self.feeder.last_seen = time.time()

    def read_control_parameter_state(self) -> None:
        for msg in self._safe_take(self.controlParameterStateReader):
            if self.feeder and msg.get("deviceId") == self.feeder.device_id:
                self.feeder.control_parameter_state = msg
                self.feeder.last_seen = time.time()

    def read_grounding_circuit_state(self) -> None:
        for msg in self._safe_take(self.groundingCircuitStateReader):
            if self.feeder and msg.get("deviceId") == self.feeder.device_id:
                self.feeder.grounding_state = msg
                self.feeder.last_seen = time.time()

    def read_power_port_state(self) -> None:
        for msg in self._safe_take(self.powerPortStateReader):
            if self.feeder and msg.get("deviceId") == self.feeder.device_id:
                port = get_nested(msg, "powerPortId", "portNumber", default=None)
                if port is None:
                    port = msg.get("portNumber")
                if port is None:
                    port = self.feeder.primary_port()
                port = int(port)
                self.feeder.known_ports.add(port)
                self.feeder.power_ports[port] = msg
                self.feeder.last_seen = time.time()

    def read_ac_measurement_update(self) -> None:
        for msg in self._safe_take(self.acMeasurementUpdateReader):
            device_id = msg.get("deviceId")
            if self.feeder and device_id == self.feeder.device_id:
                self.feeder.measurements = msg
                self.feeder.last_seen = time.time()
            src = self.sources.get(device_id)
            if src:
                try:
                    real_kw = get_nested(msg, "externalMeasurement", 0, "line", 0, "realPower", default=0.0) or 0.0
                    src.real_delivered_kw = float(real_kw) * 3.0
                    src.last_seen = time.time()
                except Exception:
                    pass

    def read_reply(self) -> None:
        for msg in self._safe_take(self.replyReader):
            if self.feeder is None:
                continue

            target_id = get_nested(msg, "requestId", "targetDeviceId", default=None)
            if target_id and target_id != self.feeder.device_id:
                continue

            self.feeder.last_reply = msg
            self.feeder.last_seen = time.time()

            pending = self.feeder.pending_command
            if not pending:
                continue

            reply_seq = msg.get("sequenceId")
            if reply_seq is not None and str(reply_seq) != str(pending.sequence_id):
                continue

            pending.acknowledged = True
            pending.reply_payload = msg
            reply_text = normalize_text(msg)
            pending.reply_ok = not looks_faulty(reply_text)
            print(f"[REPLY] seq={pending.sequence_id} ok={pending.reply_ok}")

    def read_all(self) -> None:
        self.read_device_info()
        self.read_heartbeat()
        self.read_energy_start_stop_state()
        self.read_active_diagnostic_state()
        self.read_control_parameter_state()
        self.read_grounding_circuit_state()
        self.read_power_port_state()
        self.read_ac_measurement_update()
        self.read_reply()

    # ------------------------- diagnosis logic -------------------------
    def current_port_open_state(self, port: int) -> Optional[bool]:
        if self.feeder is None:
            return None
        msg = self.feeder.power_ports.get(port)
        if not msg:
            return None

        candidates = [
            get_nested(msg, "continuity", default=None),
            get_nested(msg, "state", default=None),
            get_nested(msg, "presentContinuity", default=None),
            get_nested(msg, "powerPortState", default=None),
        ]
        for candidate in candidates:
            result = continuity_matches_open(candidate)
            if result is not None:
                return result

        if looks_faulty(msg):
            return True
        return None

    def any_source_operational(self) -> bool:
        return any(src.state == "ESSL_OPERATIONAL" for src in self.sources.values())

    def diagnose_feeder(self) -> None:
        if self.feeder is None:
            return

        feeder = self.feeder
        feeder.faults = []
        feeder.advisories = []
        feeder.desired_action = "NONE"
        feeder.desired_port = None
        feeder.desired_open = None
        feeder.action_reason = ""

        now = time.time()

        if feeder.last_heartbeat == 0.0 or (now - feeder.last_heartbeat) > HEARTBEAT_TIMEOUT_S:
            feeder.faults.append("COMM_LOSS")

        if feeder.diagnostic_state and looks_faulty(feeder.diagnostic_state):
            feeder.faults.append("DIAGNOSTIC_FAULT")

        if feeder.grounding_state and looks_faulty(feeder.grounding_state):
            feeder.faults.append("GROUNDING_FAULT")

        pending = feeder.pending_command
        if pending is not None:
            elapsed = now - pending.sent_at
            if elapsed > COMMAND_TIMEOUT_S and not pending.acknowledged:
                feeder.faults.append("COMMAND_TIMEOUT")
            if pending.acknowledged and pending.reply_ok is False:
                feeder.faults.append("COMMAND_REJECTED")
            if pending.port_number is not None and elapsed > STATE_SETTLE_TIMEOUT_S:
                actual_open = self.current_port_open_state(pending.port_number)
                if actual_open is not None and pending.desired_open is not None and actual_open != pending.desired_open:
                    feeder.faults.append("PORT_STATE_MISMATCH")

        if not feeder.faults:
            feeder.advisories.append("FEEDER_HEALTHY")

    def decide_feeder_action(self) -> None:
        if self.feeder is None:
            return

        feeder = self.feeder
        port = feeder.primary_port()

        if feeder.pending_command is not None:
            pending = feeder.pending_command
            if pending.acknowledged and pending.reply_ok is not False:
                actual_open = self.current_port_open_state(pending.port_number or port)
                if pending.desired_open is None or actual_open is None or actual_open == pending.desired_open:
                    feeder.pending_command = None
                    feeder.advisories.append("LAST_COMMAND_CONFIRMED")
                return
            if (time.time() - pending.sent_at) < COMMAND_TIMEOUT_S:
                feeder.advisories.append("AWAITING_REPLY")
                return

        if "GROUNDING_FAULT" in feeder.faults or "DIAGNOSTIC_FAULT" in feeder.faults:
            feeder.desired_action = "OPEN_PORT"
            feeder.desired_port = port
            feeder.desired_open = True
            feeder.action_reason = "Isolate feeder because it reported a fault"
            return

        if "COMMAND_REJECTED" in feeder.faults or "PORT_STATE_MISMATCH" in feeder.faults:
            feeder.desired_action = "RETRY_OPEN_PORT"
            feeder.desired_port = port
            feeder.desired_open = True
            feeder.action_reason = "Retry isolation because requested state was not achieved"
            return

        if "COMM_LOSS" in feeder.faults:
            feeder.desired_action = "HOLD_AND_ALERT"
            feeder.action_reason = "Feeder heartbeat lost; hold state and alert operator"
            return

        if self.any_source_operational() and feeder.power_ports:
            actual_open = self.current_port_open_state(port)
            if actual_open is True:
                feeder.desired_action = "CLOSE_PORT"
                feeder.desired_port = port
                feeder.desired_open = False
                feeder.action_reason = "Restore feeder because sources are operational and no faults are active"
                return

        feeder.advisories.append("NO_ACTION_REQUIRED")

    def execute_action(self) -> None:
        if self.feeder is None:
            return

        feeder = self.feeder
        if feeder.desired_action in {"OPEN_PORT", "RETRY_OPEN_PORT", "CLOSE_PORT"} and feeder.desired_port is not None:
            self.send_power_switch(feeder.desired_port, bool(feeder.desired_open))
        elif feeder.desired_action == "HOLD_AND_ALERT":
            print(f"[ALERT] {feeder.action_reason}")

    def maybe_boot_sources(self) -> None:
        for src in self.sources.values():
            if src.state in {"ESSL_UNKNOWN", "ESSL_OFF"}:
                self.send_generator_state(src.device_id, "ESSL_OPERATIONAL")

    def print_status(self) -> None:
        print("\n========== CONTROLLER STATUS ==========")
        print(f"loop={self.loop_counter}")
        if self.feeder is None:
            print("feeder=NOT_DISCOVERED")
        else:
            print(f"feeder={self.feeder.device_id}")
            print(f"known_ports={sorted(self.feeder.known_ports) if self.feeder.known_ports else [0]}")
            print(f"faults={self.feeder.faults}")
            print(f"advisories={self.feeder.advisories}")
            print(f"desired_action={self.feeder.desired_action}")
            print(f"reason={self.feeder.action_reason}")
            print(f"pending={self.feeder.pending_command}")
        print("sources=")
        for src in self.sources.values():
            print(f"  - {src.device_id}: state={src.state} rated_kw={src.rated_kw} real_kw={src.real_delivered_kw}")
        print("=======================================\n")

    def run(self) -> None:
        with rti.open_connector(config_name=self.participant, url=self.xml_path) as connector:
            self.heartbeatReader = connector.get_input("TmsSubscriber::HeartbeatReader")
            self.deviceInfoReader = connector.get_input("TmsSubscriber::DeviceInfoReader")
            self.activeDiagnosticStateReader = connector.get_input("TmsSubscriber::ActiveDiagnosticStateReader")
            self.energyStartStopStateReader = connector.get_input("TmsSubscriber::EnergyStartStopStateReader")
            self.controlParameterStateReader = connector.get_input("TmsSubscriber::ControlParameterStateReader")
            self.groundingCircuitStateReader = connector.get_input("TmsSubscriber::GroundingCircuitStateReader")
            self.powerPortStateReader = connector.get_input("TmsSubscriber::PowerPortStateReader")
            self.acMeasurementUpdateReader = connector.get_input("TmsSubscriber::ACMeasurementUpdateTypeReader")
            self.replyReader = connector.get_input("TmsSubscriber::ReplyReader")

            self.heartbeatWriter = connector.get_output("TmsPublisher::HeartbeatWriter")
            self.deviceInfoWriter = connector.get_output("TmsPublisher::DeviceInfoWriter")
            self.activeDiagnosticStateWriter = connector.get_output("TmsPublisher::ActiveDiagnosticStateWriter")
            self.energyStartStopRequestWriter = connector.get_output("TmsPublisher::EnergyStartStopRequestWriter")
            self.powerSwitchWriter = connector.get_output("TmsPublisher::PowerSwitchRequestWriter")

            self.publish_identity()
            print("[START] feeder-driven controller running")

            while True:
                self.loop_counter += 1
                self.send_heartbeat()
                self.read_all()
                self.maybe_boot_sources()
                self.diagnose_feeder()
                self.decide_feeder_action()
                self.execute_action()
                self.print_status()
                time.sleep(LOOP_SLEEP_S)


def parse_args() -> argparse.Namespace:
    file_path = os_path.dirname(os_path.realpath(__file__))
    default_xml = os_path.join(file_path, "../xml/tmg_xml_24_mar.xml")
    parser = argparse.ArgumentParser(description="Feeder-driven Type V microgrid controller")
    parser.add_argument("xml_path", nargs="?", default=default_xml)
    parser.add_argument("--participant", default="TmsParticipantLibrary::TmsParticipant")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    file_path = os_path.dirname(os_path.realpath(__file__))
    sys_path.append(file_path + "/../../../")
    controller = MicrogridController(args.xml_path, args.participant)
    controller.run()
