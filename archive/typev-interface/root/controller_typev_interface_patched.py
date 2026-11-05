import sys
import time
import pprint
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from os import path as os_path
from sys import path as sys_path


# -----------------------------------------------------------------------------
# Utility / state models
# -----------------------------------------------------------------------------

ROLE_CONTROLLER = 1
ROLE_DISTRIBUTION_NUM = 5
ROLE_DISTRIBUTION_STR = "ROLE_DISTRIBUTION"
ROLE_SOURCE_NUM = 2
ROLE_SOURCE_STR = "ROLE_SOURCE"
ROLE_LOAD_STR = "ROLE_LOAD"

HEARTBEAT_STALE_SEC = 3.0
MEASUREMENT_STALE_SEC = 3.0
RESTORE_SETTLE_SEC = 2.5
COMMAND_COOLDOWN_SEC = 2.0
LOAD_PRESENT_KW = 0.20
ENERGIZED_VOLTAGE_MIN = 30.0
SOURCE_MIN_USEFUL_KW = 0.10
RESERVE_MARGIN_KW = 0.50


@dataclass
class SequenceCounter:
    current: int = 0

    def next(self) -> str:
        self.current += 1
        return str(self.current)


@dataclass
class SourceState:
    device_id: str
    rated_kw: float = 0.0
    state: str = "ESSL_UNKNOWN"
    real_kw: float = 0.0
    reactive_kvar: float = 0.0
    last_measurement: float = 0.0
    low_fuel_cutoff: float = 0.0
    max_fuel: float = 0.0


@dataclass
class FeederState:
    device_id: str
    port_number: int = 0
    features: List[str] = field(default_factory=list)
    last_heartbeat: float = 0.0
    heartbeat_seq: Optional[int] = None
    last_measurement: float = 0.0
    line_voltage: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0})
    line_current: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0})
    line_frequency: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0})
    line_real_kw: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0})
    line_reactive_kvar: Dict[str, float] = field(default_factory=lambda: {"A": 0.0, "B": 0.0, "C": 0.0})
    metric_params: Dict[str, float] = field(default_factory=dict)
    tripped: bool = False
    estimated_closed: Optional[bool] = None
    last_switch_command: Optional[str] = None
    last_switch_seq: Optional[str] = None
    last_switch_time: float = 0.0
    faults: List[str] = field(default_factory=list)
    advisories: List[str] = field(default_factory=list)
    desired_action: str = "NONE"

    @property
    def total_real_kw(self) -> float:
        return sum(self.line_real_kw.values())

    @property
    def total_reactive_kvar(self) -> float:
        return sum(self.line_reactive_kvar.values())

    @property
    def avg_voltage(self) -> float:
        vals = list(self.line_voltage.values())
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def max_current(self) -> float:
        vals = list(self.line_current.values())
        return max(vals) if vals else 0.0

    @property
    def avg_frequency(self) -> float:
        vals = [v for v in self.line_frequency.values() if v > 0.0]
        return sum(vals) / len(vals) if vals else 0.0


# -----------------------------------------------------------------------------
# Type V-style controller
# -----------------------------------------------------------------------------


class TypeVControllerInterface:
    def __init__(self, xml_path: Optional[str] = None):
        self.pp = pprint.PrettyPrinter(indent=2)
        self.seq = SequenceCounter()
        self.sources: Dict[str, SourceState] = {}
        self.feeder: Optional[FeederState] = None
        self.loop_counter = 0
        self.last_controller_diag: Tuple[str, Tuple[str, ...]] = ("", tuple())
        self.pending_source_boot: Dict[str, float] = {}

        file_path = os_path.dirname(os_path.realpath(__file__))
        sys_path.append(file_path + "/../../../")
        self.xml_path = xml_path or (file_path + "/../xml/tmg_xml_24_mar.xml")
        self.file_path = file_path

    def run(self) -> None:
        print("Start", repr(__file__))
        print("Using XML:", self.xml_path)

        import rticonnextdds_connector as rti

        with rti.open_connector(
            config_name="TmsParticipantLibrary::TmsParticipant",
            url=self.xml_path,
        ) as connector:
            self.connector = connector
            self._bind_io()
            self._publish_controller_identity()

            print("Type V controller interface loop started...")
            while True:
                self.loop_counter += 1
                self._write_controller_heartbeat()
                self._read_all_topics()
                self._diagnose_microgrid()
                self._manage_generation()
                self._manage_feeder()
                self._publish_controller_diagnostics()
                self._print_status_summary()
                time.sleep(1.0)

    # ------------------------------------------------------------------
    # DDS setup / publication
    # ------------------------------------------------------------------

    def _bind_io(self) -> None:
        c = self.connector
        self.heartbeatReader = c.get_input("TmsSubscriber::HeartbeatReader")
        self.deviceInfoReader = c.get_input("TmsSubscriber::DeviceInfoReader")
        self.activeDiagnosticStateReader = c.get_input("TmsSubscriber::ActiveDiagnosticStateReader")
        self.energyStartStopStateReader = c.get_input("TmsSubscriber::EnergyStartStopStateReader")
        self.controlParameterStateReader = c.get_input("TmsSubscriber::ControlParameterStateReader")
        self.groundingCircuitStateReader = c.get_input("TmsSubscriber::GroundingCircuitStateReader")
        self.powerPortStateReader = c.get_input("TmsSubscriber::PowerPortStateReader")
        self.acMeasurementUpdateReader = c.get_input("TmsSubscriber::ACMeasurementUpdateTypeReader")
        self.replyReader = c.get_input("TmsSubscriber::ReplyReader")
        self.metricParameterStateReader = c.get_input("TmsSubscriber::MetricParameterStateReader")

        self.heartbeatWriter = c.get_output("TmsPublisher::HeartbeatWriter")
        self.deviceInfoWriter = c.get_output("TmsPublisher::DeviceInfoWriter")
        self.activeDiagnosticStateWriter = c.get_output("TmsPublisher::ActiveDiagnosticStateWriter")
        self.energyStartStopRequestWriter = c.get_output("TmsPublisher::EnergyStartStopRequestWriter")
        self.powerSwitchWriter = c.get_output("TmsPublisher::PowerSwitchRequestWriter")

    def _publish_controller_identity(self) -> None:
        self.deviceInfoWriter.instance.set_string("deviceId", "controller")
        self.deviceInfoWriter.instance.set_number("role", ROLE_CONTROLLER)
        self.deviceInfoWriter.instance.set_dictionary(
            {
                "product": {
                    "nsn": ["4", "5", "6", "9", "1", "1", "1", "1", "1", "0", "0", "0", "1"],
                    "manufacturerName": "West Point",
                    "modelName": "Type V Controller Interface",
                },
                "topics": {
                    "dataModelVersion": "1.2.3",
                    "publishedConditionalTopics": [],
                    "publishedOptionalTopics": [],
                    "supportedRequestTopics": [],
                },
            }
        )
        print("Publishing controller DeviceInfo")
        self.deviceInfoWriter.write()

    def _write_controller_heartbeat(self) -> None:
        self.heartbeatWriter.instance.set_string("deviceId", "controller")
        self.heartbeatWriter.instance.set_number("sequenceNumber", self.loop_counter)
        self.heartbeatWriter.write()

    def _publish_controller_diagnostics(self) -> None:
        if not self.feeder:
            message = "WAITING_FOR_FEEDER"
            active = ["NO_FEEDER_DISCOVERED"]
        else:
            active = list(dict.fromkeys(self.feeder.faults + self.feeder.advisories))
            message = "; ".join(active) if active else "MICROGRID_HEALTHY"

        key = (message, tuple(active))
        if key == self.last_controller_diag:
            return

        payload = {
            "deviceId": "controller",
            "message": message,
            "activeDiagnostics": [{"diagnostic": diag} for diag in active],
        }
        try:
            self.activeDiagnosticStateWriter.instance.set_dictionary(payload)
            self.activeDiagnosticStateWriter.write()
            self.last_controller_diag = key
        except Exception as exc:
            print("[WARN] failed to publish controller diagnostics:", exc)

    # ------------------------------------------------------------------
    # DDS readers
    # ------------------------------------------------------------------

    def _safe_take(self, reader, wait_ms: int = 0) -> List[dict]:
        try:
            if wait_ms > 0:
                reader.wait(wait_ms)
            reader.take()
        except Exception:
            return []

        results: List[dict] = []
        try:
            for sample in reader.samples.valid_data_iter:
                results.append(sample.get_dictionary())
        except Exception:
            return []
        return results

    def _read_all_topics(self) -> None:
        self._read_device_info()
        self._read_heartbeat()
        self._read_energy_start_stop_state()
        self._read_ac_measurement_update()
        self._read_metric_parameter_state()
        self._read_active_diagnostics()
        self._read_grounding()
        self._read_power_port_state()
        self._read_reply()
        self._read_control_parameter_state()

    def _read_device_info(self) -> None:
        for msg in self._safe_take(self.deviceInfoReader, wait_ms=50 if self.loop_counter < 3 else 0):
            role = msg.get("role")
            device_id = str(msg.get("deviceId", ""))
            if not device_id:
                continue

            if role == ROLE_CONTROLLER:
                continue

            if role in (ROLE_DISTRIBUTION_NUM, ROLE_DISTRIBUTION_STR):
                features = []
                try:
                    features = msg["powerDevice"]["distribution"].get("features", [])
                except Exception:
                    pass
                self._ensure_feeder(device_id, port_number=self._extract_port_number_from_device_info(msg), features=features)
                print(f"[DISCOVERY] Type III feeder: {device_id}")
                continue

            if role in (ROLE_SOURCE_NUM, ROLE_SOURCE_STR):
                source = self.sources.get(device_id)
                if source is None:
                    source = SourceState(device_id=device_id)
                    self.sources[device_id] = source
                try:
                    source.rated_kw = float(msg["powerDevice"]["source"]["loadSharing"]["maxRealPower"]) * 0.8
                except Exception:
                    pass
                try:
                    source.max_fuel = float(msg["powerHardware"]["fuel"]["maxFuelLevel"])
                    source.low_fuel_cutoff = float(msg["powerHardware"]["fuel"]["lowFuelLevelCutoff"])
                except Exception:
                    pass
                print(f"[DISCOVERY] Source: {device_id}")

    def _read_heartbeat(self) -> None:
        for msg in self._safe_take(self.heartbeatReader):
            device_id = str(msg.get("deviceId", ""))
            if not device_id or device_id == "controller":
                continue

            if self.feeder and device_id == self.feeder.device_id:
                self.feeder.last_heartbeat = time.time()
                self.feeder.heartbeat_seq = msg.get("sequenceNumber")
            elif self._looks_like_junction_node(device_id):
                feeder = self._ensure_feeder(device_id)
                feeder.last_heartbeat = time.time()
                feeder.heartbeat_seq = msg.get("sequenceNumber")

    def _read_energy_start_stop_state(self) -> None:
        for msg in self._safe_take(self.energyStartStopStateReader):
            device_id = str(msg.get("deviceId", ""))
            if device_id not in self.sources:
                continue
            present = int(msg.get("presentLevel", 1))
            self.sources[device_id].state = {
                1: "ESSL_UNKNOWN",
                2: "ESSL_OFF",
                3: "ESSL_WARM",
                4: "ESSL_IDLE",
                5: "ESSL_READY",
                6: "ESSL_READY_SYNCED",
                7: "ESSL_OPERATIONAL",
            }.get(present, "ESSL_UNKNOWN")

    def _read_ac_measurement_update(self) -> None:
        now = time.time()
        for msg in self._safe_take(self.acMeasurementUpdateReader):
            device_id = str(msg.get("deviceId", ""))
            ex = msg.get("externalMeasurement", []) or []
            if not ex:
                continue

            first = ex[0]
            port_number = int(first.get("portNumber", 0))
            lines = first.get("line", []) or []

            if device_id in self.sources:
                source = self.sources[device_id]
                source.last_measurement = now
                source.real_kw = self._sum_real_kw(lines)
                source.reactive_kvar = self._sum_reactive_kvar(lines)
                continue

            if self.feeder and device_id == self.feeder.device_id or self._looks_like_junction_node(device_id):
                feeder = self._ensure_feeder(device_id, port_number=port_number)
                feeder.last_measurement = now
                feeder.port_number = port_number
                for idx, phase in enumerate(["A", "B", "C"]):
                    if idx >= len(lines):
                        break
                    line = lines[idx]
                    feeder.line_voltage[phase] = float(line.get("voltage", 0.0))
                    feeder.line_current[phase] = float(line.get("amperage", 0.0))
                    feeder.line_frequency[phase] = float(line.get("frequency", 0.0))
                    feeder.line_real_kw[phase] = float(line.get("realPower", 0.0)) / 1000.0
                    feeder.line_reactive_kvar[phase] = float(line.get("reactivePower", 0.0)) / 1000.0

                self._infer_feeder_switch_state(feeder)

    def _read_metric_parameter_state(self) -> None:
        for msg in self._safe_take(self.metricParameterStateReader):
            device_id = str(msg.get("deviceId", ""))
            if not (self.feeder and device_id == self.feeder.device_id) and not self._looks_like_junction_node(device_id):
                continue

            feeder = self._ensure_feeder(device_id)
            metric_params = {}
            for item in msg.get("metricParameters", []) or []:
                name = str(item.get("name", ""))
                try:
                    metric_params[name] = float(item.get("value", 0.0))
                except Exception:
                    pass
            feeder.metric_params.update(metric_params)
            feeder.tripped = feeder.metric_params.get("TRIPPED", 0.0) >= 0.5

    def _read_active_diagnostics(self) -> None:
        for msg in self._safe_take(self.activeDiagnosticStateReader):
            device_id = str(msg.get("deviceId", ""))
            if device_id and device_id != "controller" and self._looks_like_junction_node(device_id):
                self._ensure_feeder(device_id)

    def _read_grounding(self) -> None:
        for msg in self._safe_take(self.groundingCircuitStateReader):
            device_id = str(msg.get("deviceId", ""))
            if device_id and self._looks_like_junction_node(device_id):
                self._ensure_feeder(device_id)

    def _read_power_port_state(self) -> None:
        for msg in self._safe_take(self.powerPortStateReader):
            device_id = str(msg.get("deviceId", ""))
            if device_id and self._looks_like_junction_node(device_id):
                feeder = self._ensure_feeder(device_id)
                if "requestId" in msg:
                    feeder.port_number = int(msg.get("requestId", {}).get("portNumber", feeder.port_number))

    def _read_reply(self) -> None:
        for msg in self._safe_take(self.replyReader):
            req = msg.get("requestId", {}) or {}
            device_id = str(req.get("targetDeviceId", ""))
            if device_id and self._looks_like_junction_node(device_id):
                feeder = self._ensure_feeder(device_id)
                feeder.last_switch_seq = str(msg.get("sequenceId", feeder.last_switch_seq or ""))

    def _read_control_parameter_state(self) -> None:
        _ = self._safe_take(self.controlParameterStateReader)

    # ------------------------------------------------------------------
    # Diagnosis / control
    # ------------------------------------------------------------------

    def _diagnose_microgrid(self) -> None:
        if not self.feeder:
            return

        f = self.feeder
        f.faults = []
        f.advisories = []
        now = time.time()

        if f.last_heartbeat == 0.0 or (now - f.last_heartbeat) > HEARTBEAT_STALE_SEC:
            f.faults.append("FEEDER_HEARTBEAT_STALE")

        if f.last_measurement == 0.0 or (now - f.last_measurement) > MEASUREMENT_STALE_SEC:
            f.faults.append("FEEDER_MEASUREMENT_STALE")

        if f.avg_voltage >= ENERGIZED_VOLTAGE_MIN:
            f.advisories.append("FEEDER_ENERGIZED")
        else:
            f.advisories.append("FEEDER_DEENERGIZED")

        if abs(f.total_real_kw) >= LOAD_PRESENT_KW:
            f.advisories.append("LOAD_PRESENT")
        else:
            f.advisories.append("NO_LOAD_DETECTED")

        if f.tripped:
            f.faults.append("SAFETY_TRIP_ACTIVE")

        v_imb = f.metric_params.get("V_IMBALANCE", 0.0)
        if v_imb >= 0.10:
            f.faults.append("VOLTAGE_IMBALANCE_FAULT")
        elif v_imb >= 0.05:
            f.advisories.append("VOLTAGE_IMBALANCE_WARNING")

        if f.avg_frequency > 0:
            if f.avg_frequency < 55.0 or f.avg_frequency > 65.0:
                f.faults.append("FREQUENCY_OUT_OF_RANGE")
            elif f.avg_frequency < 58.0 or f.avg_frequency > 62.0:
                f.advisories.append("FREQUENCY_DRIFT")

        for phase in ["A", "B", "C"]:
            vthd = f.metric_params.get(f"L{phase}_VTHD", 0.0)
            ithd = f.metric_params.get(f"L{phase}_ITHD", 0.0)
            pf = f.metric_params.get(f"L{phase}_VPF", 1.0)
            if vthd >= 0.08:
                f.faults.append(f"PHASE_{phase}_HIGH_VTHD")
            elif vthd >= 0.05:
                f.advisories.append(f"PHASE_{phase}_VTHD_WARNING")
            if ithd >= 0.15:
                f.advisories.append(f"PHASE_{phase}_HIGH_ITHD")
            if abs(pf) < 0.70 and abs(f.line_current.get(phase, 0.0)) > 0.5:
                f.advisories.append(f"PHASE_{phase}_LOW_POWER_FACTOR")

            if f.line_voltage.get(phase, 0.0) < 10.0 and f.avg_voltage >= ENERGIZED_VOLTAGE_MIN:
                f.faults.append(f"PHASE_{phase}_LOSS")

        if f.last_switch_command == "OPEN" and (time.time() - f.last_switch_time) > RESTORE_SETTLE_SEC:
            if abs(f.total_real_kw) >= LOAD_PRESENT_KW or f.avg_voltage >= ENERGIZED_VOLTAGE_MIN:
                f.faults.append("OPEN_FAILED_POWER_STILL_PRESENT")
            else:
                f.advisories.append("OPEN_CONFIRMED_BY_MEASUREMENT")

        if f.last_switch_command == "CLOSE" and (time.time() - f.last_switch_time) > RESTORE_SETTLE_SEC:
            if f.avg_voltage < ENERGIZED_VOLTAGE_MIN:
                f.faults.append("CLOSE_FAILED_NO_POWER_RESTORED")
            else:
                f.advisories.append("CLOSE_CONFIRMED_BY_MEASUREMENT")

    def _manage_generation(self) -> None:
        total_feeder_kw = self.feeder.total_real_kw if self.feeder else 0.0
        online_sources = [s for s in self.sources.values() if s.state == "ESSL_OPERATIONAL"]
        available_kw = sum(max(0.0, s.rated_kw) for s in online_sources)

        for source in self.sources.values():
            if source.state in ("ESSL_UNKNOWN", "ESSL_OFF"):
                last = self.pending_source_boot.get(source.device_id, 0.0)
                if time.time() - last >= COMMAND_COOLDOWN_SEC:
                    self._send_generator_state(source.device_id, "ESSL_OPERATIONAL")
                    self.pending_source_boot[source.device_id] = time.time()

        if total_feeder_kw > 0.0 and available_kw > 0.0 and total_feeder_kw > (available_kw - RESERVE_MARGIN_KW):
            for source in self.sources.values():
                if source.state in ("ESSL_OFF", "ESSL_READY", "ESSL_WARM", "ESSL_UNKNOWN"):
                    last = self.pending_source_boot.get(source.device_id, 0.0)
                    if time.time() - last >= COMMAND_COOLDOWN_SEC:
                        self._send_generator_state(source.device_id, "ESSL_OPERATIONAL")
                        self.pending_source_boot[source.device_id] = time.time()
                        break

    def _manage_feeder(self) -> None:
        if not self.feeder:
            return

        f = self.feeder
        has_fault = any(
            x in f.faults
            for x in [
                "SAFETY_TRIP_ACTIVE",
                "FREQUENCY_OUT_OF_RANGE",
                "OPEN_FAILED_POWER_STILL_PRESENT",
                "VOLTAGE_IMBALANCE_FAULT",
            ]
        ) or any(item.startswith("PHASE_") and item.endswith("LOSS") for item in f.faults)

        if has_fault:
            f.desired_action = "ISOLATE_FEEDER"
            if f.last_switch_command != "OPEN" and self._command_cooldown_ok(f):
                self._send_power_switch(f.device_id, f.port_number, open_state=True)
            return

        source_power_available = any(
            s.state == "ESSL_OPERATIONAL" and s.real_kw >= SOURCE_MIN_USEFUL_KW
            for s in self.sources.values()
        )
        if source_power_available and not f.tripped:
            f.advisories.append("SOURCE_AVAILABLE_FOR_RESTORE")

        if source_power_available and not has_fault and f.estimated_closed is False and self._command_cooldown_ok(f):
            f.desired_action = "RESTORE_FEEDER"
            self._send_power_switch(f.device_id, f.port_number, open_state=False)
            return

        if source_power_available and not has_fault:
            f.advisories.append("READY_TO_RESTORE")
            f.desired_action = "HOLD_MONITORING"
        else:
            f.desired_action = "WAIT_FOR_SOURCE_SUPPORT"

    # ------------------------------------------------------------------
    # Command writers
    # ------------------------------------------------------------------

    def _send_generator_state(self, target_device_id: str, to_level: str, from_level: str = "ESSL_ANY") -> None:
        seq = self.seq.next()
        payload = {
            "requestId": {
                "requestingDeviceId": "controller",
                "targetDeviceId": target_device_id,
                "config": "CONFIG_ACTIVE",
            },
            "sequenceId": seq,
            "fromLevel": from_level,
            "toLevel": to_level,
            "switchConditions": [],
        }
        self.energyStartStopRequestWriter.instance.set_dictionary(payload)
        self.energyStartStopRequestWriter.write()
        print(f"[CMD] EnergyStartStopRequest -> {target_device_id} to {to_level} seq={seq}")

    def _send_power_switch(self, target_device_id: str, port_number: int, open_state: bool) -> None:
        seq = self.seq.next()
        payload = {
            "requestId": {
                "requestingDeviceId": "controller",
                "targetDeviceId": target_device_id,
                "config": "CONFIG_ACTIVE",
                "portNumber": int(port_number),
            },
            "sequenceId": seq,
            "continuity": "DCC_OPEN" if open_state else "DCC_CLOSED",
        }
        self.powerSwitchWriter.instance.set_dictionary(payload)
        self.powerSwitchWriter.write()
        if self.feeder:
            self.feeder.last_switch_command = "OPEN" if open_state else "CLOSE"
            self.feeder.last_switch_seq = seq
            self.feeder.last_switch_time = time.time()
            self.feeder.estimated_closed = not open_state
        print(f"[CMD] PowerSwitchRequest -> {target_device_id} port={port_number} continuity={payload['continuity']} seq={seq}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_feeder(self, device_id: str, port_number: Optional[int] = None, features: Optional[List[str]] = None) -> FeederState:
        if self.feeder is None:
            self.feeder = FeederState(device_id=device_id)
        if port_number is not None:
            self.feeder.port_number = port_number
        if features:
            self.feeder.features = features
        return self.feeder

    def _extract_port_number_from_device_info(self, msg: dict) -> int:
        try:
            return int(msg["powerDevice"]["distribution"].get("portNumber", 0))
        except Exception:
            return 0

    def _sum_real_kw(self, lines: List[dict]) -> float:
        return sum(float(line.get("realPower", 0.0)) for line in lines) / 1000.0

    def _sum_reactive_kvar(self, lines: List[dict]) -> float:
        return sum(float(line.get("reactivePower", 0.0)) for line in lines) / 1000.0

    def _infer_feeder_switch_state(self, feeder: FeederState) -> None:
        energized = feeder.avg_voltage >= ENERGIZED_VOLTAGE_MIN or abs(feeder.total_real_kw) >= LOAD_PRESENT_KW
        feeder.estimated_closed = energized

    def _looks_like_junction_node(self, device_id: str) -> bool:
        lowered = device_id.lower()
        return "junction-node" in lowered or "sbc" in lowered

    def _command_cooldown_ok(self, feeder: FeederState) -> bool:
        return (time.time() - feeder.last_switch_time) >= COMMAND_COOLDOWN_SEC

    def _print_status_summary(self) -> None:
        print("\n================ TYPE V CONTROLLER STATUS ================")
        print(f"Loop: {self.loop_counter}")
        if self.feeder is None:
            print("Feeder: not discovered")
        else:
            f = self.feeder
            print(f"Feeder: {f.device_id} port={f.port_number} hb_seq={f.heartbeat_seq}")
            print(
                "Feeder electrical: "
                f"Vavg={f.avg_voltage:.1f}V "
                f"Freq={f.avg_frequency:.2f}Hz "
                f"P={f.total_real_kw:.3f}kW "
                f"Q={f.total_reactive_kvar:.3f}kVAR "
                f"Imax={f.max_current:.2f}A"
            )
            print(
                f"Feeder state: estimated_closed={f.estimated_closed} "
                f"tripped={f.tripped} action={f.desired_action}"
            )
            if f.faults:
                print("Faults:", ", ".join(sorted(set(f.faults))))
            if f.advisories:
                print("Advisories:", ", ".join(sorted(set(f.advisories))))
        if self.sources:
            print("Sources:")
            for src in self.sources.values():
                print(
                    f"  - {src.device_id}: state={src.state} rated={src.rated_kw:.2f}kW "
                    f"P={src.real_kw:.3f}kW Q={src.reactive_kvar:.3f}kVAR"
                )
        else:
            print("Sources: none discovered")
        print("==========================================================\n")


if __name__ == "__main__":
    xml_override = sys.argv[1] if len(sys.argv) > 1 else None
    controller = TypeVControllerInterface(xml_override)
    controller.run()
