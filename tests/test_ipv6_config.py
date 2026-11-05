from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from tools.build_ipv6_config import ipv6_xml, main


BASELINE = Path('Capstone/xml/tmg_xml_24_mar.xml')


class IPv6ConfigTests(unittest.TestCase):
    def test_changes_only_participant_discovery_and_transport(self):
        original = BASELINE.read_bytes()
        source = ET.fromstring(original)
        result = ET.fromstring(ipv6_xml(BASELINE, 'eth0', ['fd12:3456::1', 'fd12:3456::2']))
        qos_path = './/domain_participant_qos'
        qos = result.find(qos_path)
        self.assertEqual(qos.findtext('transport_builtin/mask'), 'UDPv6')
        self.assertEqual(qos.findtext('transport_builtin/udpv6/enable_v4mapped'), 'false')
        self.assertEqual(qos.findtext('transport_builtin/udpv6/allow_interfaces_list/element'), 'eth0')
        self.assertEqual([e.text for e in qos.findall('discovery/initial_peers/element')],
                         ['10@udpv6://fd12:3456::1', '10@udpv6://fd12:3456::2'])
        for tag in ('transport_builtin', 'discovery'):
            qos.remove(qos.find(tag))
        self.assertEqual(ET.tostring(source), ET.tostring(result))
        self.assertEqual(BASELINE.read_bytes(), original)

    def test_rejects_unverified_scopes_and_ipv4(self):
        for address in ('192.0.2.1', 'fe80::1', 'fe80::1%eth0', '::ffff:192.0.2.1', '::', '::1', 'ff02::1'):
            with self.subTest(address=address), self.assertRaises(ValueError):
                ipv6_xml(BASELINE, 'eth0', [address])
        with self.assertRaises(ValueError):
            ipv6_xml(BASELINE, 'eth*', ['fd12:3456::1'])

    def test_refuses_customized_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ipv6.xml'
            path.write_bytes(ipv6_xml(BASELINE, 'eth0', ['fd12:3456::1']))
            with self.assertRaises(ValueError):
                ipv6_xml(path, 'eth0', ['fd12:3456::1'])

    def test_refuses_baseline_overwrite(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main([str(BASELINE), '--interface', 'eth0', '--peer', 'fd12:3456::1', '--output', str(BASELINE)])


if __name__ == '__main__':
    unittest.main()
