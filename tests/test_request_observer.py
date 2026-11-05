import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from tools.observe_requests import observer_xml, observe, TOPICS


class ObserverTests(unittest.TestCase):
    def test_config_reuses_types_domains_qos_and_has_no_writers(self):
        path = Path('Capstone/xml/tmg_xml_24_mar.xml')
        original = path.read_bytes()
        source = ET.fromstring(original)
        generated = ET.fromstring(observer_xml(path))
        for tag in ('types', 'domain_library', 'qos_library'):
            self.assertEqual([ET.tostring(e) for e in source.findall(tag)],
                             [ET.tostring(e) for e in generated.findall(tag)])
        self.assertEqual(len(generated.findall('.//domain_participant')), 1)
        self.assertEqual(generated.findall('.//data_writer'), [])
        self.assertEqual({e.attrib['topic_ref'] for e in generated.findall('.//data_reader')}, set(TOPICS))
        self.assertEqual(path.read_bytes(), original)

    def test_observer_counts_requests_and_reports_matches(self):
        sample = SimpleNamespace(get_dictionary=lambda: {'requestId': {'requestingDeviceId': 'controller'}})
        reader = SimpleNamespace(matched_publications=[{'name': 'writer'}],
                                 take=lambda: None, samples=SimpleNamespace(valid_data_iter=[sample]))
        connector = SimpleNamespace(get_input=lambda name: reader)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with patch('tools.observe_requests.time.monotonic', side_effect=[0, 0, 0, 0, 2]):
                with patch('tools.observe_requests.time.sleep'):
                    observe(connector, 1)
        events = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(events[-1]['event'], 'finished')
        self.assertEqual(events[-1]['controller'], {topic: 1 for topic in TOPICS})
        self.assertTrue(any(e['event'] == 'matches' for e in events))

    def test_read_failure_is_not_reported_as_success(self):
        def fail():
            raise RuntimeError('decode failed')
        reader = SimpleNamespace(matched_publications=[], take=fail)
        connector = SimpleNamespace(get_input=lambda name: reader)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(RuntimeError):
                observe(connector, 1)
        self.assertIn('"event": "incomplete"', out.getvalue())
        self.assertNotIn('"event": "finished"', out.getvalue())


if __name__ == '__main__':
    unittest.main()
