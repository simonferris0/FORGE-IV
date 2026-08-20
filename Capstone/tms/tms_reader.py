import sys
import pprint

# See RTI python documentation for how to make sure
# the RTI provided python packages can be loaded 
from sys import path as sys_path
from os import path as os_path

file_path = os_path.dirname(os_path.realpath(__file__))
sys_path.append(file_path + "/../../../")

import rticonnextdds_connector as rti

print("Start " + repr(__file__))

# Join a DDS Domain with the specified subscriber
with rti.open_connector(
        config_name="TmsParticipantLibrary::TmsParticipant",
        url=file_path + "/../xml/tmg_xml_24_mar.xml") as connector:

    # Get a data reader from the subscrbier for each TMS topic needed
    print("Get HeartbeatReader...")
    heartbeatReader = connector.get_input("TmsSubscriber::HeartbeatReader")

    print("Get DeviceInfoReader...")
    deviceInfoReader = connector.get_input("TmsSubscriber::DeviceInfoReader")

    ################################################################
    ###################### New Readers #############################
    ################################################################

    print("Get ActiveDiagnosticStateReader...")
    activeDiagnosticStateReader = connector.get_input("TmsSubscriber::ActiveDiagnosticStateReader")

    print("Get PowerHardwareUpdateReader...")
    powerHardwareUpdateReader = connector.get_input("TmsSubscriber::PowerHardwareUpdateReader")

    print("Get ControlHardwareUpdateReader...")
    controlHardwareUpdateReader = connector.get_input("TmsSubscriber::ControlHardwareUpdateReader")

    print("Get EnergyStartStopStateReader...")
    energyStartStopStateReader = connector.get_input("TmsSubscriber::EnergyStartStopStateReader")

    print("Get ControlParameterStateReader...")
    controlParameterStateReader = connector.get_input("TmsSubscriber::ControlParameterStateReader")

    print("Get GroundingCircuitStateReader...")
    groundingCircuitStateReader = connector.get_input("TmsSubscriber::GroundingCircuitStateReader")

    print("Get PowerPortStateReader...")
    powerPortStateReader = connector.get_input("TmsSubscriber::PowerPortStateReader")
    
    print("Get ac::MeasurementUpdateReader...")
    ac_MeasurementUpdateReader = connector.get_input("TmsSubscriber::ACMeasurementUpdateTypeReader")

    print("Get PowerPortStateReader...")
    powerPortStateReader = connector.get_input("TmsSubscriber::PowerPortStateReader")

    print("Get ReplyReader...")
    replyReader = connector.get_input("TmsSubscriber::ReplyReader")
    #################################################################

    # Create a pretty printer to format topic data dictionary
    pp = pprint.PrettyPrinter(indent=2)

    print("Waiting for topic data...")
    for i in range(1, sys.maxsize):  # sys.maxsize
        try:
            # Add additional data readers as needed.
            # read the TMS DeviceInfo topic
            # Throws exception if timeout is reached
            deviceInfoReader.wait(100) # wait for data
            # if this is reached, there is at least 1 instance to "read".
            deviceInfoReader.take()

            # Each instance read include sample information and the topic data
            for sample in deviceInfoReader.samples.valid_data_iter:
                # Get the time stamp from when the publisher wrote the instance
                source_timestamp = sample.info['source_timestamp']
                # Get the type data for this topic
                deviceInfo = sample.get_dictionary()
                print(repr(i) + " DeviceInfo: ")
                # Use the pretty printer so the output can be copy/pasted into a data writer
                # call to set_dictionary.
                pp.pprint(deviceInfo)
        except:
            print("No DeviceInfo samples")

        # # read the TMS Heart beat topic
        # try:
        #     # Throws exception if timeout
        #     heartbeatReader.wait(1000) # wait for data on this heartbeatReader
        #     heartbeatReader.take()

        #     for sample in heartbeatReader.samples.valid_data_iter:
        #         heartbeat = sample.get_dictionary()
        #         deviceId = heartbeat['deviceId']
        #         sequenceNumber = heartbeat['sequenceNumber']
        #         print(repr(i) + " heartbeat: " + repr(heartbeat))
        # except:
        #     print("No heartbeat samples")
        




        # ###################################################################
        # #########     New Code For New Topics  ############################
        # ###################################################################

        # try:
        #     powerHardwareUpdateReader.wait(1000) 
        #     powerHardwareUpdateReader.take()

        #     for sample in powerHardwareUpdateReader.samples.valid_data_iter:
        #         powerHardwareUpdate = sample.get_dictionary()
                
        #         deviceId_PHU = powerHardwareUpdate['deviceId']
        #         timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better

        #         print(repr(i) + " PowerHardwareUpdate: ")
        #         pp.pprint(powerHardwareUpdate)
                
                
        # except:
        #     print("No PowerHardwareUpdate samples")

        # try:
        #     controlHardwareUpdateReader.wait(1000) 
        #     controlHardwareUpdateReader.take()

        #     for sample in controlHardwareUpdateReader.samples.valid_data_iter:
        #         controlHardwareUpdate = sample.get_dictionary()
                
        #         # deviceId_PHU = powerHardwareUpdate['deviceId']
        #         # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better

        #         print(repr(i) + " ControlHardwareUpdate: ")
        #         pp.pprint(controlHardwareUpdate)
                
                
        # except:
        #     print("No EnergyStartStopStateReader samples")

        try:
            energyStartStopStateReader.wait(1000) 
            energyStartStopStateReader.take()

            for sample in energyStartStopStateReader.samples.valid_data_iter:
                energyStartStopState = sample.get_dictionary()
                
                # deviceId_PHU = powerHardwareUpdate['deviceId']
                # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

                #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better

                print(repr(i) + " EnergyStartStopState: ")
                pp.pprint(energyStartStopState)
                
                
        except:
            print("No EnergyStartStopState samples")


        # try:
        #     activeDiagnosticStateReader.wait(1000) 
        #     activeDiagnosticStateReader.take()

        #     for sample in activeDiagnosticStateReader.samples.valid_data_iter:
        #         activeDiagnosticState = sample.get_dictionary()
                
        #         # deviceId_PHU = powerHardwareUpdate['deviceId']
        #         # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better

        #         print(repr(i) + " ActiveDiagnosticState: ")
        #         pp.pprint(activeDiagnosticState)
                
                
        # except:
        #     print("No ActiveDiagnosticState samples")

        # try:
        #     controlParameterStateReader.wait(1000) 
        #     controlParameterStateReader.take()

        #     for sample in controlParameterStateReader.samples.valid_data_iter:
        #         controlParameterState = sample.get_dictionary()
                
        #         # deviceId_PHU = powerHardwareUpdate['deviceId']
        #         # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better

        #         print(repr(i) + " ControlParameterState: ")
        #         pp.pprint(controlParameterState)
                
                
        # except:
        #     print("No ControlParameterState samples")

        # try:
        #     groundingCircuitStateReader.wait(1000) 
        #     groundingCircuitStateReader.take()

        #     for sample in groundingCircuitStateReader.samples.valid_data_iter:
        #         groundingCircuitState = sample.get_dictionary()
                
        #         # deviceId_PHU = powerHardwareUpdate['deviceId']
        #         # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better

        #         print(repr(i) + " GroundingCircuitState: ")
        #         pp.pprint(groundingCircuitState)
                
                
        # except:
        #     print("No GroundingCircuitState samples")

        # try:
        #     powerPortStateReader.wait(1000) 
        #     powerPortStateReader.take()

        #     for sample in powerPortStateReader.samples.valid_data_iter:
        #         powerPortState = sample.get_dictionary()
                
        #         # deviceId_PHU = powerHardwareUpdate['deviceId']
        #         # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better
        #         print(repr(i) + " PowerPortState:")
        #         pp.pprint(powerPortState)
                
                
        # except:
        #     print("No PowerPortState samples")



        # try:
        #     ac_MeasurementUpdateReader.wait(1000) 
        #     ac_MeasurementUpdateReader.take()

        #     for sample in ac_MeasurementUpdateReader.samples.valid_data_iter:
        #         ac_MeasurementUpdate = sample.get_dictionary()
                
        #         # deviceId_PHU = powerHardwareUpdate['deviceId']
        #         # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

        #         #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better
        #         print("####################################################################")
        #         print(repr(i) + " ac::MeasurementUpdate:")
        #         pp.pprint(ac_MeasurementUpdate)
                
                
        # except:
        #     print("No ac::MeasurementUpdate samples")

        try:
            replyReader.wait(1000) 
            replyReader.take()

            for sample in replyReader.samples.valid_data_iter:
                replyReaderUpdate = sample.get_dictionary()
                
                # deviceId_PHU = powerHardwareUpdate['deviceId']
                # timestamp_PHU  = powerHardwareUpdate['timestamp']   # doesn't change current printing in reader

                #print(repr(i) + " powerHardwareUpdate: " + repr(powerHardwareUpdate))                 pretty printer does it better
                print("####################################################################")
                print(repr(i) + " replyReaderUpdate")
                pp.pprint(replyReaderUpdate)
                
                
        except:
            print("No replyReaderUpdate samples")

        ####################################################################


            
    print("Exiting after a really long time :)")
