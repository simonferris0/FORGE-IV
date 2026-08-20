from __future__ import annotations

import pprint
import sys
import time
from dataclasses import dataclass, field
from os import path as os_path
from sys import path as sys_path
from typing import Any, Dict, List, Optional

import rticonnextdds_connector as rti

ROLE_CONTROLLER = 1
ROLE_DISTRIBUTION = 5
ROLE_SOURCE = "ROLE_SOURCE"
CONTROLLER_ID = "controller"

HEARTBEAT_TIMEOUT_S = 3.0
COMMAND_REPLY_TIMEOUT_S = 5.0
PORT_STATE_TIMEOUT_S = 5.0
LOOP_SLEEP_S = 1.0


class SequenceCounter:
    def __init__(self, start: int = 1) -> None:
        self.value = start

    def next(self) -> str:
        cur = self.value
        self.value += 1
        return str(cur)


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
        except Exception:
            return default
    return cur


def first_present(data: Dict[str, Any], paths: List[tuple], default: Any = None) -> Any:
    for path in paths:
        value = get_nested(data, *path, default=None)
        if value is not None:
            return value
    return default


@dataclass
class PendingCommand:
    kind: str
    sequence_id: str
    port_number: Optional[int]
    desired_continuity: Optional[str]
    sent_at: float
    acknowledged: bool = False
    reply: Optional[Dict[str, Any]] = None


@dataclass
class SourceState:
    device_id: str
    rated_kw: float = 0.0
    state: str = "ESSL_UNKNOWN"
    real_delivered_kw: float = 0.0
    last_seen: float = field(default_factory=time.time)


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
    power_ports: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    known_ports: set = field(default_factory=set)
    measurements: Dict[str, Any] = field(default_factory=dict)
    last_reply: Optional[Dict[str, Any]] = None
    pending_command: Optional[PendingCommand] = None
    faults: List[str] = field(default_factory=list)
    advisories: List[str] = field(default_factory=list)
    desired_action: str = "NONE"
    action_reason: str = ""


class TypeVController:
    def __init__(self, xml_path: str) -> None:
        self.xml_path = xml_path
        self.sequence = SequenceCounter(1)
        self.pp = pprint.PrettyPrinter(indent=2)
        self.feeder: Optional[FeederState] = None
        self.sources: Dict[str, SourceState] = {}
        self.loop_counter = 0

    def next_sequence(self) -> str:
        return self.sequence.next()

    def ensure_feeder(self, device_id: Optional[str], features: Optional[List[str]] = None) -> Optional[FeederState]:
        if not device_id:
            return None
        if self.feeder is None:
            self.feeder = FeederState(device_id=device_id, features=features or [])
            print(f"[DISCOVER] Locked onto Type III feeder: {device_id}")
        elif self.feeder.device_id != device_id:
            return None
        if features:
            self.feeder.features = features
        self.feeder.last_seen = time.time()
        return self.feeder

    def safe_take(self, reader: Any, wait_ms: int = 0) -> List[Dict[str, Any]]:
        try:
            if wait_ms > 0:
                reader.wait(wait_ms)
            reader.take()
            return [sample.get_dictionary() for sample in reader.samples.valid_data_iter]
        except Exception:
            return []

    def send_controller_identity(self) -> None:
        self.deviceInfoWriter.instance.set_string("deviceId", CONTROLLER_ID)
        self.deviceInfoWriter.instance.set_number("role", ROLE_CONTROLLER)
        self.deviceInfoWriter.instance.set_dictionary(
            {
                "product": {
                    "manufacturerName": "West Point",
                    "modelName": "Type V Controller",
                },
                "topics": {
                    "dataModelVersion": "1.2.3",
                    "publishedConditionalTopics": [],
                    "publishedOptionalTopics": [],
                    "supportedRequestTopics": [],
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
        seq = self.next_sequence()
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
        print(f"[WRITE] EnergyStartStopRequest target={target_device_id} to={to_level} seq={seq}")
        return seq

    def send_power_switch(self, port_number: int, open_state: bool) -> Optional[str]:
        if self.feeder is None:
            return None
        seq = self.next_sequence()
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
            kind="POWER_SWITCH",
            sequence_id=seq,
            port_number=port_number,
            desired_continuity=continuity,
            sent_at=time.time(),
        )
        print(f"[WRITE] PowerSwitchRequest target={self.feeder.device_id} port={port_number} continuity={continuity} seq={seq}")
        return seq

    def read_device_info(self) -> None:
        for msg in self.safe_take(self.deviceInfoReader, wait_ms=200):
            device_id = msg.get("deviceId")
            role = msg.get("role")
            if role == ROLE_DISTRIBUTION:
                features = get_nested(msg, "powerDevice", "distribution", "features", default=[]) or []
                self.ensure_feeder(device_id, features)
                print(f"[DEVICEINFO] feeder candidate={device_id} role={role}")
            elif role == ROLE_SOURCE:
                rated = first_present(
                    msg,
                    [
                        ("powerDevice", "source", "loadSharing", "maxRealPower"),
                        ("powerDevice", "source", "maxRealPower"),
                    ],
                    default=0.0,
                )
                src = self.sources.get(device_id) or SourceState(device_id=device_id)
                src.rated_kw = float(rated or 0.0) * 0.8 if rated else 0.0
                src.last_seen = time.time()
                self.sources[device_id] = src
                print(f"[DEVICEINFO] source={device_id} rated_kw={src.rated_kw}")

    def read_heartbeats(self) -> None:
        msgs = self.safe_take(self.heartbeatReader, wait_ms=300)
        if msgs:
            print(f"[DEBUG] heartbeat samples={len(msgs)}")
        for msg in msgs:
            device_id = msg.get("deviceId")
            seq = msg.get("sequenceNumber")
            feeder = self.ensure_feeder(device_id)
            if feeder is not None:
                feeder.last_heartbeat = time.time()
                feeder.heartbeat_sequence = seq
                print(f"[HB] feeder={device_id} seq={seq}")

    def read_energy_start_stop_state(self) -> None:
        essl_map = {1: "ESSL_UNKNOWN", 2: "ESSL_OFF", 3: "ESSL_WARM", 4: "ESSL_IDLE", 5: "ESSL_READY", 6: "ESSL_READY_SYNCED", 7: "ESSL_OPERATIONAL"}
        for msg in self.safe_take(self.energyStartStopStateReader, wait_ms=100):
            device_id = msg.get("deviceId")
            if device_id in self.sources:
                self.sources[device_id].state = essl_map.get(msg.get("presentLevel"), "ESSL_UNKNOWN")
                self.sources[device_id].last_seen = time.time()
                print(f"[STATE] source={device_id} state={self.sources[device_id].state}")

    def read_active_diagnostic_state(self) -> None:
        for msg in self.safe_take(self.activeDiagnosticStateReader, wait_ms=100):
            feeder = self.ensure_feeder(msg.get("deviceId"))
            if feeder is not None:
                feeder.diagnostic_state = msg
                print(f"[DIAG] feeder={feeder.device_id}")

    def read_control_parameter_state(self) -> None:
        for msg in self.safe_take(self.controlParameterStateReader, wait_ms=50):
            feeder = self.ensure_feeder(msg.get("deviceId"))
            if feeder is not None:
                feeder.control_parameter_state = msg

    def read_grounding_circuit_state(self) -> None:
        for msg in self.safe_take(self.groundingCircuitStateReader, wait_ms=100):
            feeder = self.ensure_feeder(msg.get("deviceId"))
            if feeder is not None:
                feeder.grounding_state = msg
                print(f"[GROUND] feeder={feeder.device_id}")

    def read_power_port_state(self) -> None:
        for msg in self.safe_take(self.powerPortStateReader, wait_ms=100):
            device_id = msg.get("deviceId") or get_nested(msg, "requestId", "targetDeviceId", default=None)
            feeder = self.ensure_feeder(device_id)
            if feeder is None:
                continue
            port = first_present(msg, [("requestId", "portNumber"), ("portNumber",), ("powerPort", "portNumber")], default=0)
            port = int(port or 0)
            feeder.power_ports[port] = msg
            feeder.known_ports.add(port)
            print(f"[PORT] feeder={feeder.device_id} port={port}")

    def read_measurements(self) -> None:
        for msg in self.safe_take(self.acMeasurementUpdateReader, wait_ms=100):
            device_id = msg.get("deviceId")
            if device_id in self.sources:
                value = first_present(msg, [("externalMeasurement", 0, "line", 0, "realPower"), ("line", 0, "realPower"), ("realPower",)], default=0.0)
                self.sources[device_id].real_delivered_kw = float(value or 0.0) * 3.0
            else:
                feeder = self.ensure_feeder(device_id)
                if feeder is not None:
                    feeder.measurements = msg

    def read_replies(self) -> None:
        for msg in self.safe_take(self.replyReader, wait_ms=100):
            request_id = msg.get("requestId", {}) if isinstance(msg.get("requestId"), dict) else {}
            target_device_id = request_id.get("targetDeviceId") or msg.get("deviceId")
            feeder = self.ensure_feeder(target_device_id)
            if feeder is None:
                continue
            feeder.last_reply = msg
            if feeder.pending_command is not None:
                reply_seq = msg.get("sequenceId")
                if reply_seq is not None and str(reply_seq) == str(feeder.pending_command.sequence_id):
                    feeder.pending_command.acknowledged = True
                    feeder.pending_command.reply = msg
            print(f"[REPLY] feeder={feeder.device_id}")

    def read_all(self) -> None:
        self.read_device_info()
        self.read_heartbeats()
        self.read_energy_start_stop_state()
        self.read_active_diagnostic_state()
        self.read_control_parameter_state()
        self.read_grounding_circuit_state()
        self.read_power_port_state()
        self.read_measurements()
        self.read_replies()

    def message_has_fault(self, msg: Optional[Dict[str, Any]]) -> bool:
        if not msg:
            return False
        text = repr(msg).upper()
        markers = ["FAULT", "FAIL", "ERROR", "TRIP", "ALARM", "INVALID", "UNSAFE", "REJECT"]
        return any(marker in text for marker in markers)

    def current_port_open_state(self, port_state: Optional[Dict[str, Any]]) -> Optional[bool]:
        if not port_state:
            return None
        text = repr(port_state).upper()
        if "DCC_OPEN" in text or " OPEN" in text:
            return True
        if "DCC_CLOSED" in text or "CLOSED" in text or " CLOSE" in text:
            return False
        return None

    def primary_port(self) -> int:
        if self.feeder and self.feeder.known_ports:
            return sorted(self.feeder.known_ports)[0]
        return 0

    def diagnose_feeder(self) -> None:
        if self.feeder is None:
            return
        feeder = self.feeder
        now = time.time()
        faults: List[str] = []
        advisories: List[str] = []

        if feeder.last_heartbeat == 0.0 or (now - feeder.last_heartbeat) > HEARTBEAT_TIMEOUT_S:
            faults.append("COMM_LOSS")

        if self.message_has_fault(feeder.diagnostic_state):
            faults.append("DIAGNOSTIC_FAULT")

        if self.message_has_fault(feeder.grounding_state):
            faults.append("GROUNDING_FAULT")

        if feeder.pending_command is not None:
            pending = feeder.pending_command
            if not pending.acknowledged and (now - pending.sent_at) > COMMAND_REPLY_TIMEOUT_S:
                faults.append("COMMAND_TIMEOUT")
            if pending.acknowledged and pending.port_number is not None and (now - pending.sent_at) > PORT_STATE_TIMEOUT_S:
                state = self.current_port_open_state(feeder.power_ports.get(pending.port_number))
                desired_open = pending.desired_continuity == "DCC_OPEN"
                if state is None:
                    advisories.append("WAITING_FOR_PORT_STATE")
                elif state != desired_open:
                    faults.append("PORT_STATE_MISMATCH")

        if not faults:
            advisories.append("FEEDER_HEALTHY")

        feeder.faults = sorted(set(faults))
        feeder.advisories = sorted(set(advisories))

    def maybe_boot_sources(self) -> None:
        for src in self.sources.values():
            if src.state in {"ESSL_UNKNOWN", "ESSL_OFF"}:
                self.send_generator_state(src.device_id, "ESSL_OPERATIONAL")

    def decide_action(self) -> None:
        if self.feeder is None:
            return
        feeder = self.feeder
        feeder.desired_action = "NONE"
        feeder.action_reason = ""

        if feeder.pending_command is not None and not any(f in feeder.faults for f in ["COMMAND_TIMEOUT", "PORT_STATE_MISMATCH"]):
            if feeder.pending_command.acknowledged:
                port_state = feeder.power_ports.get(feeder.pending_command.port_number or 0)
                actual_open = self.current_port_open_state(port_state)
                desired_open = feeder.pending_command.desired_continuity == "DCC_OPEN"
                if actual_open is not None and actual_open == desired_open:
                    feeder.pending_command = None
            return

        if "GROUNDING_FAULT" in feeder.faults or "DIAGNOSTIC_FAULT" in feeder.faults:
            feeder.desired_action = "OPEN_PORT"
            feeder.action_reason = "feeder reported unsafe condition"
            return

        if "COMMAND_TIMEOUT" in feeder.faults or "PORT_STATE_MISMATCH" in feeder.faults:
            feeder.desired_action = "RETRY_OPEN_PORT"
            feeder.action_reason = "last switch command not confirmed"
            return

        if "COMM_LOSS" in feeder.faults:
            feeder.desired_action = "HOLD_AND_ALERT"
            feeder.action_reason = "feeder heartbeat stale"
            return

        source_ready = any(src.state == "ESSL_OPERATIONAL" for src in self.sources.values()) if self.sources else False
        port_state = feeder.power_ports.get(self.primary_port())
        is_open = self.current_port_open_state(port_state)
        if source_ready and is_open is True:
            feeder.desired_action = "CLOSE_PORT"
            feeder.action_reason = "power available and feeder healthy"

    def execute_action(self) -> None:
        if self.feeder is None:
            return
        action = self.feeder.desired_action
        if action == "OPEN_PORT":
            self.send_power_switch(self.primary_port(), open_state=True)
        elif action == "RETRY_OPEN_PORT":
            self.send_power_switch(self.primary_port(), open_state=True)
        elif action == "CLOSE_PORT":
            self.send_power_switch(self.primary_port(), open_state=False)
        elif action == "HOLD_AND_ALERT":
            print(f"[ALERT] {self.feeder.action_reason}")

    def print_status(self) -> None:
        print("\n========== TYPE V STATUS ==========")
        if self.feeder is None:
            print("feeder=NONE faults=['NO_FEEDER_DISCOVERED']")
        else:
            print(
                f"feeder={self.feeder.device_id} hb_seq={self.feeder.heartbeat_sequence} ports={sorted(self.feeder.known_ports)} faults={self.feeder.faults} advisories={self.feeder.advisories} action={self.feeder.desired_action}"
            )
        for src in self.sources.values():
            print(f"source={src.device_id} state={src.state} rated_kw={src.rated_kw} real_kw={src.real_delivered_kw:.2f}")
        print("===================================\n")

    def run(self) -> None:
        with rti.open_connector(
            config_name="TmsParticipantLibrary::TmsParticipant",
            url=self.xml_path,
        ) as connector:
            self.deviceInfoReader = connector.get_input("TmsSubscriber::DeviceInfoReader")
            self.heartbeatReader = connector.get_input("TmsSubscriber::HeartbeatReader")
            self.activeDiagnosticStateReader = connector.get_input("TmsSubscriber::ActiveDiagnosticStateReader")
            self.energyStartStopStateReader = connector.get_input("TmsSubscriber::EnergyStartStopStateReader")
            self.controlParameterStateReader = connector.get_input("TmsSubscriber::ControlParameterStateReader")
            self.groundingCircuitStateReader = connector.get_input("TmsSubscriber::GroundingCircuitStateReader")
            self.powerPortStateReader = connector.get_input("TmsSubscriber::PowerPortStateReader")
            self.acMeasurementUpdateReader = connector.get_input("TmsSubscriber::ACMeasurementUpdateTypeReader")
            self.replyReader = connector.get_input("TmsSubscriber::ReplyReader")

            self.deviceInfoWriter = connector.get_output("TmsPublisher::DeviceInfoWriter")
            self.heartbeatWriter = connector.get_output("TmsPublisher::HeartbeatWriter")
            self.activeDiagnosticStateWriter = connector.get_output("TmsPublisher::ActiveDiagnosticStateWriter")
            self.energyStartStopRequestWriter = connector.get_output("TmsPublisher::EnergyStartStopRequestWriter")
            self.powerSwitchWriter = connector.get_output("TmsPublisher::PowerSwitchRequestWriter")

            self.send_controller_identity()
            print(f"[START] Controller online using XML: {self.xml_path}")

            while True:
                self.loop_counter += 1
                self.send_heartbeat()
                self.read_all()
                self.maybe_boot_sources()
                self.diagnose_feeder()
                self.decide_action()
                self.execute_action()
                self.print_status()
                time.sleep(LOOP_SLEEP_S)


def main() -> None:
    file_path = os_path.dirname(os_path.realpath(__file__))
    sys_path.append(file_path + "/../../../")
    default_xml = file_path + "/../xml/tmg_xml_24_mar.xml"
    xml_path = sys.argv[1] if len(sys.argv) > 1 else default_xml
    print("Start " + repr(__file__))
    TypeVController(xml_path).run()


if __name__ == "__main__":
    main()
