"""Generate a separate UDPv6 unicast configuration for native Connext 6.1.2.

Offline only. Reuses the selected baseline's types, topics and endpoint QoS;
changes only TmsParticipant's discovery and builtin transport configuration.
"""
import argparse
import hashlib
import ipaddress
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def peer_address(value):
    address = ipaddress.IPv6Address(value)
    if (address.is_link_local or address.is_multicast or address.is_unspecified
            or address.is_loopback or address.ipv4_mapped is not None or '%' in value):
        raise ValueError('Use a bare, routable ULA/global IPv6 unicast address; scoped/link-local and mapped addresses need separate validation')
    return str(address)


def ipv6_xml(xml_path, interface, peers, max_participant_id=10):
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', interface):
        raise ValueError('Specify one exact interface name, without patterns or lists')
    if not peers or not 0 <= max_participant_id <= 119:
        raise ValueError('At least one peer and a participant ID limit from 0 to 119 are required')
    addresses = list(dict.fromkeys(peer_address(p) for p in peers))
    root = ET.parse(xml_path).getroot()
    participant = root.find("./domain_participant_library/domain_participant[@name='TmsParticipant']")
    if participant is None:
        raise ValueError('Expected TmsParticipant in the selected XML')
    qos = participant.find('domain_participant_qos')
    if qos is None:
        qos = ET.SubElement(participant, 'domain_participant_qos')
    # Fail rather than silently overriding a previously customized transport setup.
    if qos.find('transport_builtin') is not None or qos.find('discovery') is not None or qos.find('property') is not None:
        raise ValueError('Input already customizes transport/discovery/properties; review it instead of layering an override')
    discovery = ET.SubElement(qos, 'discovery')
    peers_element = ET.SubElement(discovery, 'initial_peers')
    for address in addresses:
        ET.SubElement(peers_element, 'element').text = f'{max_participant_id}@udpv6://{address}'
    transports = ET.SubElement(discovery, 'enabled_transports')
    ET.SubElement(transports, 'element').text = 'udpv6'
    ET.SubElement(discovery, 'multicast_receive_addresses')
    builtin = ET.SubElement(qos, 'transport_builtin')
    ET.SubElement(builtin, 'mask').text = 'UDPv6'
    udp = ET.SubElement(builtin, 'udpv6')
    allowed = ET.SubElement(udp, 'allow_interfaces_list')
    ET.SubElement(allowed, 'element').text = interface
    ET.SubElement(udp, 'multicast_enabled').text = 'false'
    ET.SubElement(udp, 'enable_v4mapped').text = 'false'
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xml_path', type=Path)
    parser.add_argument('--interface', required=True)
    parser.add_argument('--peer', action='append', required=True, help='repeat for each ULA/global peer address, including local host when using a local observer')
    parser.add_argument('--max-participant-id', type=int, default=10)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.xml_path.resolve() == args.output.resolve():
        parser.error('Output must differ from the baseline XML')
    try:
        config = ipv6_xml(args.xml_path, args.interface, args.peer, args.max_participant_id)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_bytes(config)
    print(f'Generated {args.output}; baseline SHA-256 {hashlib.sha256(args.xml_path.read_bytes()).hexdigest()}')
    print('Target: native Connext 6.1.2. Configuration prepared only; runtime transport acceptance and peer compatibility remain unverified.')


if __name__ == '__main__':
    main()
