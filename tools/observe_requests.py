"""Independent request-topic observer. Import/config generation does not load RTI.

Creates a temporary reader-only participant from the selected XML at runtime;
never keeps a separate checked-in copy of the DDS type definitions.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import time
import xml.etree.ElementTree as ET


TOPICS = ('EnergyStartStopRequest', 'PowerSwitchRequest')


def observer_xml(xml_path):
    root = ET.parse(xml_path).getroot()
    participant = root.find("./domain_participant_library/domain_participant[@name='TmsParticipant']")
    if participant is None:
        raise ValueError('Expected TmsParticipant in the selected XML')
    domain_ref = participant.attrib['domain_ref']
    participant_qos = participant.find('domain_participant_qos')
    qos = copy.deepcopy(participant_qos) if participant_qos is not None else None
    for library in list(root.findall('domain_participant_library')):
        root.remove(library)
    library = ET.SubElement(root, 'domain_participant_library', name='RequestObserverLibrary')
    observer = ET.SubElement(library, 'domain_participant', name='RequestObserver', domain_ref=domain_ref)
    subscriber = ET.SubElement(observer, 'subscriber', name='RequestObserverSubscriber')
    for topic in TOPICS:
        reader = ET.SubElement(subscriber, 'data_reader', name=topic+'Reader', topic_ref=topic)
        reader_qos = ET.SubElement(reader, 'datareader_qos', base_name='TmsTgpQosLibrary::Command')
        # Reader-only buffering override; reliability/durability/ownership stay compatible.
        history = ET.SubElement(reader_qos, 'history')
        ET.SubElement(history, 'kind').text = 'KEEP_LAST_HISTORY_QOS'
        ET.SubElement(history, 'depth').text = '1024'
    if qos is not None:
        for user_data in list(qos.findall('user_data')):
            qos.remove(user_data)
        observer.append(qos)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def emit(event, **fields):
    print(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'event': event, **fields}), flush=True)


def observe(connector, duration):
    readers = {topic: connector.get_input('RequestObserverSubscriber::'+topic+'Reader') for topic in TOPICS}
    counts = {topic: 0 for topic in TOPICS}
    controller_counts = counts.copy()
    matched = {topic: None for topic in TOPICS}
    deadline = time.monotonic() + duration
    report_at = 0.0
    try:
        while time.monotonic() < deadline:
            for topic, reader in readers.items():
                publications = reader.matched_publications
                if publications != matched[topic]:
                    emit('matches', topic=topic, publications=publications)
                    matched[topic] = publications
                reader.take()
                for sample in reader.samples.valid_data_iter:
                    data = sample.get_dictionary()
                    counts[topic] += 1
                    if data.get('requestId', {}).get('requestingDeviceId') == 'controller':
                        controller_counts[topic] += 1
                    emit('request', topic=topic, data=data)
            if time.monotonic() >= report_at:
                emit('counts', total=counts, controller=controller_counts)
                report_at = time.monotonic() + 5
            time.sleep(.1)
    except BaseException:
        emit('incomplete', total=counts, controller=controller_counts)
        raise  # Never report an error-terminated interval as a successful zero-command test.
    emit('finished', total=counts, controller=controller_counts, matches=matched)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xml_path')
    parser.add_argument('--duration', type=float, default=120)
    parser.add_argument('--write-config', type=Path, help='only generate the observer XML; do not import RTI or join DDS')
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error('--duration must be positive')
    config = observer_xml(args.xml_path)
    if args.write_config:
        args.write_config.write_bytes(config)
        return
    import rticonnextdds_connector as rti
    emit('start', xml=str(Path(args.xml_path).resolve()),
         sha256=hashlib.sha256(Path(args.xml_path).read_bytes()).hexdigest(),
         duration=args.duration, version=rti.Connector.get_version())
    with tempfile.TemporaryDirectory(prefix='forge-request-observer-') as directory:
        xml = Path(directory)/'observer.xml'
        xml.write_bytes(config)
        with rti.open_connector('RequestObserverLibrary::RequestObserver', str(xml)) as connector:
            observe(connector, args.duration)


if __name__ == '__main__':
    main()
