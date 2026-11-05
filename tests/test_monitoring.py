"""Offline controller tests: no Connector import, DDS participant, or equipment."""
import contextlib
import io
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

from controller_typev_interface_patched_v2 import (
    FeederState, SourceState, TypeVControllerInterface, parse_args,
)


class Writer:
    def __init__(self):
        self.instance = self
        self.payload = {}
        self.writes = []

    def set_string(self, key, value):
        self.payload[key] = value

    set_number = set_string

    def set_dictionary(self, payload):
        self.payload.update(payload)

    def write(self):
        self.writes.append(self.payload.copy())


class Reader:
    def __init__(self, *messages):
        self.samples = SimpleNamespace(valid_data_iter=[
            SimpleNamespace(get_dictionary=lambda m=m: m) for m in messages
        ])

    def wait(self, timeout):
        pass

    def take(self):
        pass


def controller(control=False):
    c = TypeVControllerInterface('Capstone/xml/tmg_xml_24_mar.xml', enable_control=control)
    for name in ('energyStartStopRequestWriter', 'powerSwitchWriter', 'heartbeatWriter',
                 'deviceInfoWriter', 'activeDiagnosticStateWriter'):
        setattr(c, name, Writer())
    return c


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.out = io.StringIO()
        self.err = io.StringIO()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(contextlib.redirect_stdout(self.out))
        stack.enter_context(contextlib.redirect_stderr(self.err))

    def assert_no_sent_state(self, c):
        self.assertEqual(c.energyStartStopRequestWriter.writes, [])
        self.assertEqual(c.powerSwitchWriter.writes, [])
        self.assertEqual(c.pending_source_boot, {})
        self.assertEqual(c.seq.current, 0)
        if c.feeder:
            self.assertIsNone(c.feeder.last_switch_command)
            self.assertIsNone(c.feeder.last_switch_seq)
            self.assertEqual(c.feeder.last_switch_time, 0)

    def test_source_boot_in_both_modes(self):
        for state in ('ESSL_OFF', 'ESSL_UNKNOWN'):
            for enabled in (False, True):
                with self.subTest(state=state, control=enabled):
                    c = controller(enabled)
                    c.sources['ammps30'] = SourceState('ammps30', state=state)
                    c._manage_generation()  # No feeder is required by the original logic.
                    if enabled:
                        self.assertEqual(len(c.energyStartStopRequestWriter.writes), 1)
                        self.assertEqual(c.energyStartStopRequestWriter.writes[0]['toLevel'], 'ESSL_OPERATIONAL')
                        self.assertIn('ammps30', c.pending_source_boot)
                        c._manage_generation()
                        self.assertEqual(len(c.energyStartStopRequestWriter.writes), 1)
                    else:
                        c._manage_generation()
                        self.assert_no_sent_state(c)

    def test_reserve_capacity_path(self):
        for enabled in (False, True):
            c = controller(enabled)
            c.feeder = FeederState('junction-node', line_real_kw={'A': 1.0})
            c.sources['online'] = SourceState('online', state='ESSL_OPERATIONAL', rated_kw=1)
            c.sources['ready'] = SourceState('ready', state='ESSL_READY')
            c._manage_generation()
            if enabled:
                self.assertEqual(c.energyStartStopRequestWriter.writes[0]['requestId']['targetDeviceId'], 'ready')
                self.assertIn('ready', c.pending_source_boot)
            else:
                self.assert_no_sent_state(c)

    def test_feeder_open_close_in_both_modes(self):
        for action in ('OPEN', 'CLOSE'):
            for enabled in (False, True):
                with self.subTest(action=action, control=enabled):
                    c = controller(enabled)
                    c.feeder = FeederState('junction-node', estimated_closed=False)
                    if action == 'OPEN':
                        c.feeder.faults = ['SAFETY_TRIP_ACTIVE']
                    else:
                        c.sources['ammps30'] = SourceState('ammps30', state='ESSL_OPERATIONAL', real_kw=1)
                    c._manage_feeder()
                    if enabled:
                        self.assertEqual(len(c.powerSwitchWriter.writes), 1)
                        self.assertEqual(c.powerSwitchWriter.writes[0]['continuity'], 'DCC_' + ('OPEN' if action == 'OPEN' else 'CLOSED'))
                        self.assertEqual(c.feeder.last_switch_command, action)
                        self.assertGreater(c.feeder.last_switch_time, 0)
                        self.assertEqual(c.feeder.estimated_closed, action == 'CLOSE')
                    else:
                        self.assert_no_sent_state(c)
                        self.assertFalse(c.feeder.estimated_closed)

    def test_direct_helpers_guard_start_stop_open_close(self):
        for enabled in (False, True):
            c = controller(enabled)
            c.feeder = FeederState('junction-node', estimated_closed=True)
            for state in ('ESSL_OPERATIONAL', 'ESSL_OFF'):
                self.assertEqual(c._send_generator_state('ammps30', state), enabled)
            for opened in (True, False):
                self.assertEqual(c._send_power_switch('junction-node', 0, opened), enabled)
            if enabled:
                self.assertEqual(len(c.energyStartStopRequestWriter.writes), 2)
                self.assertEqual(len(c.powerSwitchWriter.writes), 2)
            else:
                self.assert_no_sent_state(c)
                self.assertTrue(c.feeder.estimated_closed)

    def test_monitor_guard_does_not_even_need_command_writers(self):
        c = TypeVControllerInterface()
        self.assertFalse(c._send_generator_state('ammps30', 'ESSL_OFF'))
        self.assertFalse(c._send_power_switch('junction-node', 0, True))
        self.assertEqual(c.seq.current, 0)

    def test_failed_write_does_not_record_pending_or_switch_state(self):
        c = controller(True)
        c.sources['ammps30'] = SourceState('ammps30')
        with patch.object(c.energyStartStopRequestWriter, 'write', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                c._manage_generation()
        self.assertEqual(c.pending_source_boot, {})
        c.feeder = FeederState('junction-node', estimated_closed=False)
        with patch.object(c.powerSwitchWriter, 'write', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                c._send_power_switch('junction-node', 0, False)
        self.assertIsNone(c.feeder.last_switch_command)
        self.assertFalse(c.feeder.estimated_closed)

    def test_suppressed_intentions_are_rate_limited(self):
        c = controller()
        with patch('controller_typev_interface_patched_v2.time.monotonic', return_value=100):
            for _ in range(100):
                c._send_generator_state('ammps30', 'ESSL_OPERATIONAL')
        self.assertEqual(self.out.getvalue().count('[MONITOR]'), 1)
        with patch('controller_typev_interface_patched_v2.time.monotonic', return_value=131):
            c._send_generator_state('ammps30', 'ESSL_OPERATIONAL')
        self.assertIn('99 repeats', self.out.getvalue())

    def test_identity_heartbeat_and_existing_diagnostics_remain_enabled(self):
        c = controller()
        c.loop_counter = 5
        c._publish_controller_identity()
        c._write_controller_heartbeat()
        c._publish_controller_diagnostics()
        c._publish_controller_diagnostics()
        self.assertEqual(c.deviceInfoWriter.writes[0]['deviceId'], 'controller')
        self.assertEqual(c.heartbeatWriter.writes, [{'deviceId': 'controller', 'sequenceNumber': 5}])
        self.assertEqual(c.activeDiagnosticStateWriter.writes, [{'deviceId': 'controller'}])
        self.assert_no_sent_state(c)

    def test_reception_discovery_state_and_measurements_in_monitor(self):
        c = controller()
        for name in ('deviceInfoReader', 'heartbeatReader', 'energyStartStopStateReader',
                     'acMeasurementUpdateReader', 'metricParameterStateReader',
                     'activeDiagnosticStateReader', 'groundingCircuitStateReader',
                     'powerPortStateReader', 'replyReader', 'controlParameterStateReader'):
            setattr(c, name, Reader())
        c.deviceInfoReader = Reader({'deviceId': 'ammps30', 'role': 2})
        c.energyStartStopStateReader = Reader({'deviceId': 'ammps30', 'presentLevel': 2})
        c.acMeasurementUpdateReader = Reader({'deviceId': 'ammps30', 'externalMeasurement': [
            {'portNumber': 0, 'line': [{'realPower': 1500, 'reactivePower': 200}]}]})
        c._read_all_topics()
        self.assertEqual(c.sources['ammps30'].state, 'ESSL_OFF')
        self.assertEqual(c.sources['ammps30'].real_kw, 1.5)
        self.assertEqual(c.sources['ammps30'].reactive_kvar, .2)
        self.assertGreater(c.sources['ammps30'].last_measurement, 0)
        c.energyStartStopStateReader = Reader({'deviceId': 'ammps30', 'presentLevel': 7})
        c._read_energy_start_stop_state()
        self.assertEqual(c.sources['ammps30'].state, 'ESSL_OPERATIONAL')
        c._print_status_summary()
        self.assertIn('Mode: MONITOR ONLY', self.out.getvalue())
        self.assert_no_sent_state(c)

    def test_cli_defaults_and_positional_xml(self):
        self.assertFalse(parse_args([]).enable_control)
        for args in (['config.xml'], ['--monitor-only', 'config.xml'], ['config.xml', '--monitor-only']):
            parsed = parse_args(args)
            self.assertEqual(parsed.xml_path, 'config.xml')
            self.assertFalse(parsed.enable_control)
        self.assertTrue(parse_args(['config.xml', '--enable-control']).enable_control)
        with self.assertRaises(SystemExit) as error:
            parse_args(['config.xml', '--monitor-only', '--enable-control'])
        self.assertEqual(error.exception.code, 2)

    def test_monitor_run_startup_and_loop_with_fake_connector(self):
        c = controller()
        writers = {}
        class Connector:
            def get_input(self, name):
                return Reader()
            def get_output(self, name):
                writers[name] = Writer()
                return writers[name]
        fake_rti = SimpleNamespace(
            TimeoutError=TimeoutError,
            open_connector=lambda **kwargs: contextlib.nullcontext(Connector()),
        )
        with patch.dict(sys.modules, {'rticonnextdds_connector': fake_rti}):
            with patch('controller_typev_interface_patched_v2.time.sleep', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    c.run()
        self.assertIn('[MODE] MONITOR ONLY', self.out.getvalue())
        self.assertEqual(len(writers['TmsPublisher::DeviceInfoWriter'].writes), 1)
        self.assertEqual(len(writers['TmsPublisher::HeartbeatWriter'].writes), 1)
        self.assertEqual(writers['TmsPublisher::EnergyStartStopRequestWriter'].writes, [])
        self.assertEqual(writers['TmsPublisher::PowerSwitchRequestWriter'].writes, [])

    def test_control_mode_is_prominent_in_status(self):
        controller(True)._print_status_summary()
        self.assertIn('Mode: CONTROL ENABLED', self.out.getvalue())


class ReaderDiagnosticsTests(unittest.TestCase):
    def test_empty_samples_and_expected_timeout_are_quiet(self):
        c = controller()
        class ConnectorTimeout(Exception):
            pass
        c._timeout_errors = (TimeoutError, ConnectorTimeout)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(c._safe_take(Reader()), [])
            for exc in (TimeoutError(), ConnectorTimeout()):
                r = Reader()
                r.wait = lambda ms, exc=exc: (_ for _ in ()).throw(exc)
                self.assertEqual(c._safe_take(r, wait_ms=1), [])
        self.assertEqual(err.getvalue(), '')

    def test_unexpected_errors_have_context_and_are_throttled(self):
        for operation in ('wait', 'take', 'sample conversion'):
            with self.subTest(operation=operation):
                c = controller()
                r = Reader()
                def fail(*args):
                    raise RuntimeError('decode detail')
                if operation == 'sample conversion':
                    r.samples.valid_data_iter = [SimpleNamespace(get_dictionary=fail)]
                else:
                    setattr(r, operation, fail)
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    for _ in range(3):
                        self.assertEqual(c._safe_take(r, wait_ms=1, context='ReplyReader / Reply'), [])
                text = err.getvalue()
                self.assertEqual(text.count('[DDS ERROR]'), 1)
                for detail in ('ReplyReader / Reply', operation, 'RuntimeError', 'decode detail'):
                    self.assertIn(detail, text)

    def test_processing_failure_names_topic_and_continues_other_readers(self):
        c = controller()
        handlers = ('_read_device_info', '_read_heartbeat', '_read_energy_start_stop_state',
                    '_read_ac_measurement_update', '_read_metric_parameter_state',
                    '_read_active_diagnostics', '_read_grounding', '_read_power_port_state',
                    '_read_reply', '_read_control_parameter_state')
        with contextlib.ExitStack() as stack:
            mocks = {name: stack.enter_context(patch.object(c, name)) for name in handlers}
            mocks['_read_energy_start_stop_state'].side_effect = ValueError('bad presentLevel')
            with contextlib.redirect_stderr(io.StringIO()) as err:
                c._read_all_topics()
        self.assertIn('EnergyStartStopStateReader / EnergyStartStopState', err.getvalue())
        self.assertIn('topic processing', err.getvalue())
        mocks['_read_reply'].assert_called_once()

    def test_timeout_outside_wait_is_reported(self):
        c = controller()
        r = Reader()
        r.take = lambda: (_ for _ in ()).throw(TimeoutError('unexpected take error'))
        with contextlib.redirect_stderr(io.StringIO()) as err:
            c._safe_take(r, context='HeartbeatReader / Heartbeat')
        self.assertIn('unexpected take error', err.getvalue())


if __name__ == '__main__':
    unittest.main()
