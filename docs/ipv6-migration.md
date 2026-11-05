# IPv6 preparation and verification

## Known runtime and configuration scope

The Type V machine reports Python 3.10.12, Python **Connector package 1.2.4**, and native **NDDSCORE/NDDSC/RTICONNECTOR 6.1.2.21**. IPv6 configuration is checked against the **native 6.1.2** documentation, not inferred from the package's 1.2.4 number. OS/CPU platform support and runtime configuration acceptance are not yet verified. The existing baseline XML declares schema 6.1.1 and remains unchanged.

No `sim_start.sh`, `src.json`, desktop DDS configuration, or Type I launch configuration is in this checkout. A simulator title displaying IPv4 is an observation about that simulator session, not proof of its complete transport setup. Changing Type V does not change the simulator or Trevor's Type I.

For native Connext 6.1.2, transport selection is the participant's `transport_builtin.mask`. The documented default is UDPv4 plus SHMEM; selecting UDPv6 alone excludes those builtin transports. See [RTI 6.1.2 TRANSPORT_BUILTIN](https://community.rti.com/static/documentation/connext-dds/6.1.2/doc/manuals/connext_dds_professional/users_manual/users_manual/TRANSPORT_BUILTIN_Qos.htm). This is a reference configuration fact, not evidence that the Pi has successfully created a UDPv6 participant.

The [6.1.2 QoS definitions XSD](https://community.rti.com/schema/6.1.2/definitions/rti_dds_qos_profiles_definitions.xsd) was inspected for `UDPv6`, `transport_builtin/udpv6`, `allow_interfaces_list` (element sequence), `multicast_enabled`, `enable_v4mapped`, and `discovery` peer/transport fields. Corresponding tags also exist in the 6.1.1 schema used by the baseline. The [6.1.2 transport properties manual](https://community.rti.com/static/documentation/connext-dds/6.1.2/doc/manuals/connext_dds_professional/users_manual/users_manual/Transport_Properties.htm) describes transport-specific XML configuration. This was static syntax inspection, not a full runtime or XSD validation of deployment settings.

Interface restrictions live under `domain_participant_qos/transport_builtin/udpv6/allow_interfaces_list`. The legacy property is `dds.transport.UDPv6.builtin.parent.allow_interfaces_list`; use one representation consistently. See [6.1.2 property reference](https://community.rti.com/static/documentation/connext-dds/6.1.2/doc/manuals/connext_dds_professional/properties_reference/property_full.html). IPv4-mapped handling is explicitly disabled in the generated configuration; [RTI's UDPv6 property reference](https://community.rti.com/static/documentation/connext-dds/6.1.2/doc/api/connext_dds/api_cpp2/structNDDS__Transport__UDPv6__Property__t.html) documents that `enable_v4mapped` controls processing IPv4 addresses.

Discovery peers are set in participant `discovery.initial_peers`; `enabled_transports` restricts discovery transport and `multicast_receive_addresses` controls discovery multicast listening. RTI's [6.1.2 peer descriptor syntax](https://community.rti.com/static/documentation/connext-dds/6.1.2/doc/manuals/connext_dds_professional/users_manual/users_manual/Peer_Descriptor_Format.htm) supports `participant-limit@udpv6://IPv6-address`. The generator defaults to probing participant IDs 0–10; coordinate that range if many participants run on one host. Initial peers are discovery destinations, not a restriction on all discovered traffic. RTI's [peer configuration precedence](https://community.rti.com/static/documentation/connext-dds/6.1.2/doc/manuals/connext_dds_professional/users_manual/users_manual/ConfigPeersListUsed_inDiscov.htm) also covers `NDDS_DISCOVERY_PEERS` files/environment. Record those and any additional loaded QoS files rather than assuming a shell export is the effective setting.

## Separate generated configuration

[tools/build_ipv6_config.py](../tools/build_ipv6_config.py) is an offline generator. It reads the current baseline afresh, preserves types/topics/domain/endpoint QoS, and adds only participant discovery/transport settings to its output. There is no second checked-in type schema to drift. It refuses to overwrite the baseline or layer onto already customized discovery/transport/property settings.

It creates a **UDPv6-only builtin, unicast-only** configuration: exact interface allow list, IPv4-mapped processing off, no SHMEM, no multicast sends/listeners, explicit peers and discovery transport. That describes requested settings, not observed IPv6-only operation. It deliberately rejects IPv4, mapped, multicast, unspecified, loopback and scoped/link-local peer addresses. Use existing mutually reachable ULA/global addresses; link-local-only networks need separate scope syntax and platform verification. It does not assign addresses or change host networking.

After collecting actual interface/peer addresses, from the Pi repository root:

```bash
source ~/FORGE-IV-SS6/.venv/bin/activate
mkdir -p outputs
python tools/build_ipv6_config.py Capstone/xml/tmg_xml_24_mar.xml --interface eth0 --peer fd12:3456::10 --peer fd12:3456::20 --output outputs/tmg_ipv6.xml
```

`eth0`, `fd12:3456::10`, and `fd12:3456::20` are **examples to replace**, not known machine settings. Supply the actual Pi interface and addresses for the Pi itself (for a local observer), simulator, and later Type I using repeated `--peer`. Use `--max-participant-id` if the agreed participant range requires it. Keep the generator's baseline SHA-256 output with the test log. Generate host-specific configs with each host's own interface name.

After reviewing the generated file and coordinating the desktop settings, the exact Type V monitoring entry point is:

```bash
set -o pipefail
ipv6_log="outputs/typev-ipv6-monitor-$(date -u +%Y%m%dT%H%M%SZ).log"
python -u -X faulthandler controller_typev_interface_patched_v2.py outputs/tmg_ipv6.xml --monitor-only 2>&1 | tee "$ipv6_log"
```

Use the generated file with the independent observer too:

```bash
python -u tools/observe_requests.py outputs/tmg_ipv6.xml --duration 300
```

The observer inherits the selected transport/discovery settings. On another host, generate its own file with that host's interface and peers. To return to the known baseline transport, stop Type V and launch monitoring with `Capstone/xml/tmg_xml_24_mar.xml`. No package upgrade or host-wide IPv4 disablement is part of this process.

## Coordinated settings

| Setting | Type V / Jeffrey | Simulator desktop / Simon and operator | Trevor's Type I |
| --- | --- | --- | --- |
| Domain | Baseline domain 0 retained | Verify actual launch domain is 0 | Agree and configure domain 0 |
| Native DDS build/platform | Reported 6.1.2.21; OS/architecture still needed | Supply vendor/build, OS/architecture, actual flags/XML | Supply vendor/build and supported transport syntax |
| Transport | Generated UDPv6 mask, mapped IPv4 off, no SHMEM | Independently enable compatible IPv6 transport; title/Type V settings are insufficient | Independently select compatible IPv6 transport |
| Discovery | Explicit unicast peers, IDs 0–10 by default, multicast off | Reciprocal peer addresses/range; confirm effective file/environment/profile | Peer addresses/range and transport selection agreed |
| Interface/address scope | Actual chosen NIC and existing routable ULA/global address | Actual NIC/address on reachable path | Actual NIC/address; agree routing/scope |
| Topics/types/keys | Baseline types reused without edits | Compare effective IDL/XML, bounds, key layout, enum values and representation | Use compatible definitions and compare hashes/versions |
| QoS | Baseline endpoint QoS retained | Match reliability/durability/ownership/history compatibility | Match offered/requested QoS; verify exclusive ownership |
| Evidence | Startup acceptance, matched endpoints, captured IPv6 user samples | Same plus actual simulator transport config | Same when Type I is available |

Request the actual desktop `sim_start.sh`, `src.json`, included configs, resolved simulator command line/environment, simulator build/commit or container digest, effective XML/QoS/IDL and generated types, and complete error output. On **each host**, collect `ip -br address`, `ip -6 route`, `uname -a`, `/etc/os-release`, DDS build/version, domain/peer/profile environment and working-directory peer/profile files. Inspect the referenced configs, not just their filenames. No simulator launch flag can be specified responsibly until those files are available.

## Host reachability first, then DDS

Read-only addressing/routing inspection and a reachability check, using actual values:

```bash
ip -br address
ip -6 route
ping -6 -c 4 PEER_IPV6_ADDRESS
```

Repeat bidirectionally between Pi and desktop and later Type I. ICMP failure can be policy-related; record it without changing firewall settings. A ping reply proves only that IP exchange, not DDS discovery or user-data delivery. Then check participant creation, discovery locators, matched endpoints/type/QoS, actual DeviceInfo/state/measurement samples, and separate command absence evidence.

## Packet evidence, including IPv4 fallback detection

Use already available capture tools; do not install tools or change system networking merely for this repository change. On both participating machines, choose the actual NIC (or `any` on Linux to include local traffic). For a short coordinated test, capture both address families, not just IPv6:

```bash
mkdir -p outputs
capture_iface=eth0
packet_log="outputs/dds-$(date -u +%Y%m%dT%H%M%SZ).pcap"
sudo tcpdump -i "$capture_iface" -s 0 -U -w "$packet_log" 'ip or ip6'
```

Stop capture after the test and retain tcpdump's drop summary. If permission is unavailable, have the operator use an existing approved capture path. Inspect with Wireshark or an existing tshark installation:

```bash
tshark -n -r "$packet_log" -Y 'rtps && ipv6' -V
tshark -n -r "$packet_log" -Y 'rtps && ip' -V
tshark -n -r "$packet_log" -Y 'rtps && ipv6 && (rtps.sm.id == 0x15 || rtps.sm.id == 0x16)' -V
```

If ports are nonstandard and RTPS is not automatically decoded, use Wireshark **Decode As → RTPS** on the observed UDP conversation; verify tool field names against the installed version. See [Wireshark RTPS filter reference](https://www.wireshark.org/docs/dfref/r/rtps.html) and [RTI's RTPS debugging guide](https://community.rti.com/static/documentation/wireshark/2023-09/doc/debugging.html).

DATA/DATA_FRAG filters include discovery data too. To establish IPv6 **user data**, map the participant GUID prefix and writer entity IDs from SPDP/SEDP discovery to the desired application topic/type, then inspect DATA/DATA_FRAG from those writers carrying actual DeviceInfo, state, heartbeat-topic or AC measurement samples. Record source/destination IPv6 locators and the receiving application's samples. RTPS protocol HEARTBEAT submessages are not `tms::Heartbeat` topic samples. Conversely inspect IPv4 RTPS and attribute it to test participants or unrelated processes; record capture interfaces, interval, loss, and any shared-memory paths before claiming no IPv4 fallback. Merely seeing IPv6 discovery, or no IPv4 on one NIC, is insufficient.

Local verification covers generator behavior and preservation of baseline content. Pi parser acceptance, UDPv6 sockets/interfaces, discovery, user-data delivery, zero commands, and three-party interoperability all remain runtime tests. Do not claim IPv6-only success until coordinated configuration and traffic evidence support it.
