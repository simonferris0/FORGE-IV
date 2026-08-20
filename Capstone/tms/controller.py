################################## Imports and global variables ##################################
import sys        # Used to get path of XML file and to run loop endlessly with a heartbeat number
import random     # Currently used for sequence IDs but should NOT be used. Change to incrementing values
from sys import path as sys_path  # Used to get path of XML file
from os import path as os_path    # Used to get path of XML file
from time import sleep            # Used to ensure heartbeats are 1s apart, will be used in the future for recent_change 
import pprint                     # Used to print out dictionaries from RTi topics in a readable format
import time                       # Used to ensure heartbeats are 1s apart, will be used in the future for recent_change



cycle_num = 0                     # Used with Overloaded_cycle_num for configuration 6 (requested load > rated capacity of both sources combined) 
                                  # so that we allow time to decrease load before attempting to turn on sources again
overloaded_cycle_num = -6       # 600 cycles is approx 1 min

recent_change = 0                 # Used with time_to_change_state to ensure 2 cycles through our loop are executed before switching state.
time_to_change_state = 2          # Done IOT prevent state changes every second if the requested load is right at a decision point (source's rated capacity)

total_fuel_used = 0.0       # Used for analysis of efficiency
configuration = 0           # tracks requested load vs rated capacity of sources, see below for key


# Next three blocks open and close files so that if you run the script back to back it resets the files
real_delivered_doc = open("Total_Real_Delivered_Combined.txt", "w")
real_delivered_doc.close()

max_generator_output = open("Generator_Information_24_Hours.txt", "w")
max_generator_output.close()

fuel_added_file = open("Generator_fuel_ups.txt", "w")
fuel_added_file.close()





#################################### Classes ############################################
# These Classes will be used to save the deviceInfo for each device type
# We do not use smart (Rti capable) loads though so we will never receive any 

# This section could be updated to include distribution, storage, etc devices

class Source:
    def __init__(self, power, state, fuel, low_fuel_cutoff, id, max_fuel = 34.7, realdelivered = 0, reactdelivered = 0, state_request = "NONE", fuel_usage_rate = 0.0):
        self.rated = power
        self.state = state
        self.fuel = fuel
        self.low_fuel_cutoff = low_fuel_cutoff
        self.state_request = state_request
        self.id = id
        self.realdelivered = realdelivered
        self.reactdelivered = reactdelivered
        self.max_fuel = max_fuel
        self.fuel_usage_rate = fuel_usage_rate




class Load:
    def __init__(self, maxReal, maxReact, realPower, reactPower):
        self.real = maxReal
        self.react = maxReact
        self.power = realPower
        self.var = reactPower

class Controller:
    def __init__(self, controller_role = "unkown"):
        self.controller_role = controller_role


# This dictionary saves all smart (RTi capable) devices and provides the ability to iterate through devices of one type.
# It is updated everytime a message on the deviceInfo topic is published
class_Divide_Dict = {"Controller": list(), "Source": list(), "Load": list()}


########################### Function to change generator state ######################


# Generator states are saved as ESSL Levels in RTi. Below is the key for ESSL Level to RTi integer:
# Off: 2
# Warm: 3
# Idle: 4 *not implemented
# Ready: 5
# ReadySynced: 6
# Operational: 7


def generator_state_change_request(targetDeviceID, toLevel, fromLevel = "ESSL_ANY"):
    energyStartStopRequestWriter.instance.set_dictionary({
        "requestId": {
            'requestingDeviceId': "python-1",       # This would need to be changed if you are running a main/redundant controller architecture
            'targetDeviceId': targetDeviceID,
            'config': 'CONFIG_ACTIVE'
        },
        'sequenceId': str(random.randint(1000000, 9999999)),  # This needs to be changed to an incrementing integer value
        'fromLevel': fromLevel,
        'toLevel': toLevel,
        'switchConditions': []
        })

    energyStartStopRequestWriter.write()    # This publishes the command with the information set in the above dictionary


############################# Begin situation one (2 sources, 2 loads) ##############################################

# This function is only usable with smart loads which our simulated environment does not currently use.
# But its intent was to set the generator's state before starting the infinite maintaining loop.




def situation_smart_start(gen1, gen2, load1, load2 = Load(0,0,0,0)):
    if gen1.rated <= gen2.rated and gen1.rated >= (load1.real + load2.real):
        generator_state_change_request(gen1.id, "ESSL_OPERATIONAL") #B.16.2.2 tms.EnergyStartStopRequest 
        #pause until B16.2.1 tms.EnergyStartStopState returns with device at desired state
        generator_state_change_request(gen2.id, "ESSL_OFF")
        

    elif gen2.rated <= gen1.rated and gen2.rated >= (load1.real + load2.real):
        generator_state_change_request(gen2.id, "ESSL_OPERATIONAL")
        #pause again as stated above
        generator_state_change_request(gen1.id, "ESSL_OFF")

    elif gen1.rated <= gen2.rated and gen1.rated <= (load1.real + load2.real) and gen2.rated >= (load1.real + load2.real):
        generator_state_change_request(gen2.id, "ESSL_OPERATIONAL")
        #pause again as stated above
        generator_state_change_request(gen1.id, "ESSL_OFF")

    elif gen1.rated >= gen2.rated and gen2.rated <= (load1.real + load2.real) and gen1.rated >= (load1.real + load2.real):
        generator_state_change_request(gen1.id, "ESSL_OPERATIONAL")
        #pause again as stated above
        generator_state_change_request(gen2.id, "ESSL_OFF")

    else:
        generator_state_change_request(gen1.id, "ESSL_OPERATIONAL")
        generator_state_change_request(gen2.id, "ESSL_OPERATIONAL")
        #pause again as stated above
    print("Gen1 state:", gen1.state)
    print("Gen2 state:", gen2.state)



######################  Main controller function for situation 1 (2 sources, 2 loads)  ######################################

def situation1_maintain(gen1, gen2):
    # The loads are not smart loads so we use gen1 + gen2 realDelivered as total requested load


    #  Configuration key  #
    #  0 = unknown  #
    #  1 = 0 requested load so turn both off and wait then restart
    #  2 = gen1 (where gen1 < gen2) only handles load
    #  3 = gen2 (where gen2 < gen1) only handles load
    #  4 = gen2 (where gen2 > gen1) only handles load
    #  5 = gen1 (where gen1 > gen2) only handles load
    #  6 = gen1 + gen2 handles load
    #  7 = gen1 + gen2 cannot handle load so turn both off for 600 cycles



    global recent_change, time_to_change_state, configuration, total_fuel_used, cycle_num, overloaded_cycle_num
    
    # Config 1 was never tested or actually run. It is future work, but this means that our naming convention is wrong. 
    # In comments the config number is 1 > the config number in code e.g. config 2 in comments = config 1 in code

    # # configuration 1: requested load is 0, turn both gens off and wait then do restart
    # if gen1.realdelivered + gen2.realdelivered == 0:          # on startup will not trigger because startup turn both gens operational
    #     generator_state_change_request(gen1.id, "ESSL_OFF")
    #     generator_state_change_request(gen2.id, "ESSL_OFF")
    #     no_load_cycle_num = cycle_num         # Needs to not happen every time
    #     if cycle_num > no_load_cycle_num + 6:
    #         iter_counter = 0
    
    
    
    # Configuration 2. gen1 rating is less than gen2 but greater than the total power delivered (needed) == gen1 on, gen2 off

    if gen1.rated <= gen2.rated and gen1.rated >= (gen1.realdelivered + gen2.realdelivered): # checks requested load (aka realDelivered) vs rated values
        if configuration != 1: # checks if its the first time through the cycle when its in config 1 
                               # i.e. determines how much work you need to do
            if recent_change < time_to_change_state: # checks if we "recently" changed generators state's so that we do not constantly cycle them
                pass
            else: # Must change generators states to gen1 on, gen2 off
                configuration = 1
                recent_change = 0

                if gen1.state == "ESSL_OPERATIONAL":
                    generator_state_change_request(gen2.id, "ESSL_OFF")

                if gen1.state == "ESSL_OFF":
                    generator_state_change_request(gen1.id, "ESSL_OPERATIONAL") #B.16.2.2 tms.EnergyStartStopRequest 
                    
                
         
        elif configuration == 1 and gen1.state == "ESSL_OPERATIONAL" and gen2.state == "ESSL_OFF":   # both gens are already in the states they need to be in
            pass
        elif configuration == 1 and gen1.state == "ESSL_OPERATIONAL":    # gen 1 is correct but we need to change gen 2
            generator_state_change_request(gen2.id, "ESSL_OFF")
           


        recent_change += 1      # Everytime through the loop increment then reset upon changes

        
        max_generator_output = open("Generator_Information_24_Hours.txt", "a")  # Prints Source info to a file after every iteration through the loop
        max_generator_output.write("System Max power: " + maximum_power(gen1, gen2) + "\tGen1 State: " + gen1.state + "\tGen2 State: " + gen2.state + "\tTotal Fuel Used: " + str(total_fuel_used) +"\n")

        fuel_usage_calculation(gen1, gen2) # Prints to a file when a generator is refueled. Should be changed to give timestamp
                                            # estimates are higher than they should be, slightly innacurate





        
    #Configuration 3. gen2 rating is less than gen1 but greater than the total power delivered (needed) == gen2 on, gen1 off
    # See config 2 notes as execution is very similar
    elif gen2.rated <= gen1.rated and gen2.rated >= (gen1.realdelivered + gen2.realdelivered):
        if configuration != 2:
            if recent_change < time_to_change_state:
                pass
            else: 
                configuration = 2
                recent_change = 0
                if gen2.state == "ESSL_OPERATIONAL":
                    generator_state_change_request(gen1.id, "ESSL_OFF")

                if gen2.state == "ESSL_OFF":
                    generator_state_change_request(gen2.id, "ESSL_OPERATIONAL") #B.16.2.2 tms.EnergyStartStopRequest 
                    
                #generator 2 is operational
                
         
        elif configuration == 2 and gen2.state == "ESSL_OPERATIONAL" and gen1.state == "ESSL_OFF":
            pass
        elif configuration == 2 and gen2.state == "ESSL_OPERATIONAL":
            generator_state_change_request(gen1.id, "ESSL_OFF")
           
            
        

        recent_change += 1
        max_generator_output = open("Generator_Information_24_Hours.txt", "a")
        max_generator_output.write("System Max power: " + maximum_power(gen1, gen2) + "\tGen1 State: " + gen1.state + "\tGen2 State: " + gen2.state + "\tTotal Fuel Used: " + str(total_fuel_used) +"\n")
        

        fuel_usage_calculation(gen1, gen2)


    #Configuration 4: Generator 1 rated is too small to handle total load, gen 2 is large enough so it takes whole load == gen1 off, gen 2 on
    # see config 2 notes for what specific lines do
    elif gen1.rated < gen2.rated and gen1.rated <= (gen1.realdelivered + gen2.realdelivered) and gen2.rated >= (gen1.realdelivered + gen2.realdelivered) - gen1.rated:

        if configuration != 3:
            if recent_change < time_to_change_state:
                pass
            else: 
                configuration = 3
                recent_change = 0
                if gen2.state == "ESSL_OPERATIONAL":
                    generator_state_change_request(gen1.id, "ESSL_OFF")

                if gen2.state == "ESSL_OFF":
                    generator_state_change_request(gen2.id, "ESSL_OPERATIONAL") #B.16.2.2 tms.EnergyStartStopRequest 
                    
                #generator 2 is operational
                
         
        elif configuration == 3 and gen2.state == "ESSL_OPERATIONAL" and gen1.state == "ESSL_OFF":
            pass
        elif configuration == 3 and gen2.state == "ESSL_OPERATIONAL":
            generator_state_change_request(gen1.id, "ESSL_OFF")
           
            
        

        recent_change += 1
        max_generator_output = open("Generator_Information_24_Hours.txt", "a")
        max_generator_output.write("System Max power: " + maximum_power(gen1, gen2) + "\tGen1 State: " + gen1.state + "\tGen2 State: " + gen2.state + "\tTotal Fuel Used: " + str(total_fuel_used) +"\n")
        

        fuel_usage_calculation(gen1, gen2)

        
    #Configuration 5: Generator 2 rated is too small to handle total load, gen 1 is large enough so it takes whole load == gen2 off, gen1 on
    # see config 2 for what specific lines do
    elif gen1.rated > gen2.rated and gen2.rated <= (gen1.realdelivered + gen2.realdelivered) and gen1.rated >= (gen1.realdelivered + gen2.realdelivered):
        if configuration != 4:
            if recent_change < time_to_change_state:
                pass
            else: 
                configuration = 4
                recent_change = 0
                if gen1.state == "ESSL_OPERATIONAL":
                    generator_state_change_request(gen2.id, "ESSL_OFF")

                if gen1.state == "ESSL_OFF":
                    generator_state_change_request(gen1.id, "ESSL_OPERATIONAL") #B.16.2.2 tms.EnergyStartStopRequest 
                    
                #generator 1 is operational
                
         
        elif configuration == 4 and gen1.state == "ESSL_OPERATIONAL" and gen2.state == "ESSL_OFF":
            pass
        elif configuration == 4 and gen1.state == "ESSL_OPERATIONAL":
            generator_state_change_request(gen2.id, "ESSL_OFF")
           
            
        

        recent_change += 1
        max_generator_output = open("Generator_Information_24_Hours.txt", "a")
        max_generator_output.write("System Max power: " + maximum_power(gen1, gen2) + "\tGen1 State: " + gen1.state + "\tGen2 State: " + gen2.state + "\tTotal Fuel Used: " + str(total_fuel_used) +"\n")
        

        fuel_usage_calculation(gen1, gen2)
        

    #Configuration 6: Both Generators need to be Operational and then they can cover full load == gen1 on, gen2 on
    # See config 2 for what specific lines do
    elif gen1.rated + gen2.rated >= (gen1.realdelivered + gen2.realdelivered): 
        if configuration != 5:
            if recent_change < time_to_change_state:
                pass
            else: 
                configuration = 5
                recent_change = 0
                generator_state_change_request(gen1.id, "ESSL_OPERATIONAL")
                generator_state_change_request(gen2.id, "ESSL_OPERATIONAL")
                

        else:
            pass
        recent_change += 1
        max_generator_output = open("Generator_Information_24_Hours.txt", "a")
        max_generator_output.write("System Max power: " + maximum_power(gen1, gen2) + "\tGen1 State: " + gen1.state + "\tGen2 State: " + gen2.state + "\tTotal Fuel Used: " + str(total_fuel_used) +"\n")
        

        fuel_usage_calculation(gen1, gen2)

    
    # # configuration 7: Both generators cannot cover full load == gen1 off, gen2 off, wait many cycles
    # # Never reach this case right now, instead generators hit their limit and cannot be turned back on
    # elif cycle_num > 6 + overloaded_cycle_num:  # 600 cycles roughly equal to 1 min
    #     print(cycle_num, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")      ####### Never reaches this line
    #     generator_state_change_request(gen1.id, "ESSL_OFF")
    #     generator_state_change_request(gen2.id, "ESSL_OFF")
    #     overloaded_cycle_num = cycle_num


    





    # These lines are used for sequence control and analysis
    cycle_num += 1
    print("Gen1 state:", gen1.state)
    print("Gen2 state:", gen2.state)
    print("The real power is " + str(gen1.realdelivered + gen2.realdelivered) + "kW")
    print("\n")



############################### Total combined max power ########################

# used for analysis, gives total possible output

def maximum_power(gen1, gen2):
    if gen1.state == "ESSL_OFF" and gen2.state == "ESSL_OFF":
        return str(0)
    elif gen2.state == "ESSL_OPERATIONAL" and gen1.state != "ESSL_OPERATIONAL":
        return str(gen2.rated)
    elif gen2.state != "ESSL_OPERATIONAL" and gen1.state == "ESSL_OPERATIONAL":
        return str(gen1.rated)
    else: 
        return str(gen1.rated + gen2.rated)


######################### Fuel usage func ####################################

# currenty gives too high of estimates, not accurate but close enough for small approximations

def fuel_usage_calculation(gen1, gen2):
    global recent_change, time_to_change_state, configuration, total_fuel_used, load_sorter
    total_load = (gen1.realdelivered + gen2.realdelivered)
    if gen1.state == "ESSL_OPERATIONAL":
        if gen2.state == "ESSL_OPERATIONAL":
            load_percentage = total_load / (gen1.rated + gen2.rated)

            load_sorter = int(round(load_percentage, 1) * 10)
            #rate in gallons per hour here
            if load_sorter == 1:
                gen1.fuel_usage_rate = 0.802
                gen2.fuel_usage_rate = 0.802
            elif load_sorter == 2:
                gen1.fuel_usage_rate = 1.254
                gen2.fuel_usage_rate = 1.254
            elif load_sorter == 3:
                gen1.fuel_usage_rate = 1.706
                gen2.fuel_usage_rate = 1.706
            elif load_sorter == 4:
                gen1.fuel_usage_rate = 2.158
                gen2.fuel_usage_rate = 2.158
            elif load_sorter == 5:
                gen1.fuel_usage_rate = 2.61
                gen2.fuel_usage_rate = 2.61
            elif load_sorter == 6:
                gen1.fuel_usage_rate = 3.062
                gen2.fuel_usage_rate = 3.062
            elif load_sorter == 7:
                gen1.fuel_usage_rate = 3.514
                gen2.fuel_usage_rate = 3.514
            elif load_sorter == 8:
                gen1.fuel_usage_rate = 3.966
                gen2.fuel_usage_rate = 3.966
            elif load_sorter == 9:
                gen1.fuel_usage_rate = 4.418
                gen2.fuel_usage_rate = 4.418
            else:
                gen1.fuel_usage_rate = 4.87
                gen2.fuel_usage_rate = 4.87
            


        else:    # We know gen 2 not operational because if statement captures that
            if gen2.state != "ESSL_OFF":  # Minimum fuel usage happens in all states except states operational and off
                load_percentage = total_load / (gen1.rated)
                gen2.fuel_usage_rate = 0.35        # min fuel usage
            else:
                load_percentage = total_load / (gen1.rated)
                gen2.fuel_usage_rate = 0.0           # Off
        
            load_sorter = int(round(load_percentage, 1) * 10)
            #rate in gallons per hour here
            if load_sorter == 1:
                gen1.fuel_usage_rate = 0.802
            elif load_sorter == 2:
                gen1.fuel_usage_rate = 1.254
            elif load_sorter == 3:
                gen1.fuel_usage_rate = 1.706
            elif load_sorter == 4:
                gen1.fuel_usage_rate = 2.158
            elif load_sorter == 5:
                gen1.fuel_usage_rate = 2.61
            elif load_sorter == 6:
                gen1.fuel_usage_rate = 3.062
            elif load_sorter == 7:
                gen1.fuel_usage_rate = 3.514
            elif load_sorter == 8:
                gen1.fuel_usage_rate = 3.966
            elif load_sorter == 9:
                gen1.fuel_usage_rate = 4.418
            else:
                gen1.fuel_usage_rate = 4.87
            
    
    
    elif gen2.state == "ESSL_OPERATIONAL": # gen 1 != operational
        load_percentage = total_load / (gen2.rated)
        if gen1.state != "ESSL_OFF":
            gen1.fuel_usage_rate = 0.35    # Fuel usage min
        else:
            gen1.fuel_usage_rate = 0.0     # Off
        
        load_sorter = int(round(load_percentage, 1) * 10)
        #rate in gallons per hour here
        if load_sorter == 1:
            gen2.fuel_usage_rate = 0.802
        elif load_sorter == 2:
            gen2.fuel_usage_rate = 1.254
        elif load_sorter == 3:
            gen2.fuel_usage_rate = 1.706
        elif load_sorter == 4:
            gen2.fuel_usage_rate = 2.158
        elif load_sorter == 5:
            gen2.fuel_usage_rate = 2.61
        elif load_sorter == 6:
            gen2.fuel_usage_rate = 3.062
        elif load_sorter == 7:
            gen2.fuel_usage_rate = 3.514
        elif load_sorter == 8:
            gen2.fuel_usage_rate = 3.966
        elif load_sorter == 9:
            gen2.fuel_usage_rate = 4.418
        else:
            gen2.fuel_usage_rate = 4.87


    #both generators off
    elif gen1.state == "ESSL_OFF" and gen2.state == "ESSL_OFF":
        gen1.fuel_usage_rate = 0.0
        gen2.fuel_usage_rate = 0.0
    
    #both generators are primed
    else: 
        gen1.fuel_usage_rate = 0.35
        gen2.fuel_usage_rate = 0.35
    
    #evaluating fuel loss for updates and evaluation every minute
    gen1.fuel = gen1.fuel - (gen1.fuel_usage_rate / 60)
    gen2.fuel = gen2.fuel - (gen2.fuel_usage_rate / 60)
    
    # need a timestamp for when we filled up: future work
    if gen1.fuel <= gen1.low_fuel_cutoff:
        #fill up the 1 generator
        gen1.fuel = gen1.max_fuel
        fuel_added_file = open("Generator_fuel_ups.txt", "a")
        fuel_added_file.write("Generator 1 was filled up with " + str(gen1.max_fuel) + "gallons" + "\n") # Add timestamp to this file
    
    if gen2.fuel <= gen1.low_fuel_cutoff:
        #fill up the 2 generator
        gen2.fuel = gen2.max_fuel
        fuel_added_file = open("Generator_fuel_ups.txt", "a")
        fuel_added_file.write("Generator 2 was filled up with " + str(gen2.max_fuel) + "gallons" + "\n")

    total_fuel_used = total_fuel_used + (gen1.fuel_usage_rate / 60) + (gen2.fuel_usage_rate / 60)
 


####################### begin controller execution #######################

# getting to the XML
file_path = os_path.dirname(os_path.realpath(__file__))
sys_path.append(file_path + "/../../../")

print("Start " + repr(__file__))

import rticonnextdds_connector as rti

with rti.open_connector(
        config_name="TmsParticipantLibrary::TmsParticipant",
        url=file_path + "/../xml/tmg_xml_24_mar.xml") as connector: # XML defines all topics and QoS


    ################################################################
    ###################### Readers Set Up ##########################
    ################################################################

    print("Get HeartbeatReader...")
    heartbeatReader = connector.get_input("TmsSubscriber::HeartbeatReader")

    print("Get DeviceInfoReader...")
    deviceInfoReader = connector.get_input("TmsSubscriber::DeviceInfoReader")

    print("Get ActiveDiagnosticStateReader...")
    activeDiagnosticStateReader = connector.get_input("TmsSubscriber::ActiveDiagnosticStateReader")

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


    # Create a pretty printer to format topic data dictionary
    pp = pprint.PrettyPrinter(indent=2)


    ################################################################
    ####################### Writers set up #########################
    ################################################################


    heartbeatWriter = connector.get_output("TmsPublisher::HeartbeatWriter")
    deviceInfoWriter = connector.get_output("TmsPublisher::DeviceInfoWriter")
    activeDiagnosticStateWriter = connector.get_output("TmsPublisher::ActiveDiagnosticStateWriter")
    energyStartStopRequestWriter = connector.get_output("TmsPublisher::EnergyStartStopRequestWriter")


    print("Writing DeviceInfo.")

    # Set single field using the instance methods; for deviceInfo TOPIC
    deviceInfoWriter.instance.set_string("deviceId", "python-1")  
    deviceInfoWriter.instance.set_number("role", 1)
    deviceInfoWriter.instance.set_string("product.manufacturerName", "West Point")
    
    # Set the instance values using a dictionary
    deviceInfoWriter.instance.set_dictionary({
        "product": {
             'nsn': ['4', '5', '6', '9', '1', '1', '1', '1', '1', '0', '0', '0', '1'], 
             'manufacturerName': 'My Name Goes Here',
             'modelName': 'West Point MC'
        },
        'topics': { 
            'dataModelVersion': '1.2.3',
            'publishedConditionalTopics': [],
            'publishedOptionalTopics': [],
            'supportedRequestTopics': []
        }
    })


    # Set the instance values using a dictionary; for energyStartStopRequest TOPIC
    energyStartStopRequestWriter.instance.set_dictionary({
        "requestId": {
            'requestingDeviceId': 'python-1',
            'targetDeviceId': 'ammps-1',
            'config': 'CONFIG_ACTIVE'
        },
        'sequenceId': str(random.randint(1000000, 9999999)),   # This should be an integer that sequentially increments per request, not random
        'fromLevel': 'ESSL_ANY',
        'toLevel': 'ESSL_OPERATIONAL',
        'switchConditions': []
    })


    # which microcontroller made the change
    activeDiagnosticStateWriter.instance.set_string("deviceId", "python-1")


    ################################################################
    ###################### Writer publishing #######################
    ################################################################

    # Call write to publish the device info instance
    print(" Writing deviceInfoWriter: " + repr(deviceInfoWriter.instance.get_dictionary()))
    deviceInfoWriter.wait(1000)
    deviceInfoWriter.write()

    
    # Publish additional topics
    print(" Writing ActiveDiagnosticState: " + repr(activeDiagnosticStateWriter.instance.get_dictionary()))
    activeDiagnosticStateWriter.write()


    ################################################################
    ############ Loop for heartbeats and reading info ##############
    ################################################################
    
    
    iter_counter = 0    # Used on start up case and on requested load overloading sources

    print("Loop for heartbeats and reading info started...")
    for i in range(1, sys.maxsize):
        


        # Heartbeats being written every iteration
        heartbeatWriter.instance.set_string("deviceId", "python-1")
        heartbeatWriter.instance.set_number("sequenceNumber", i)
        print("Writing heartbeatWriter sequenceNumber: " + repr(i))
        heartbeatWriter.write()
        
        
        # Pause before the next call to write, IOT space out heartbeats by 1s
        sleep(1) 
        
        ################################################################
        ################### readers within the loop ####################
        ################################################################
        
        ########## deviceInfoReader ################
        try:
            #deviceInfoReader.wait(100)   not needed but leaving this in so we remember its possible
            deviceInfoReader.take()    # Read from any writers that have published to this topic

            for sample in deviceInfoReader.samples.valid_data_iter:   # Sample = single device's info
                source_timestamp = sample.info['source_timestamp']
                
                deviceInfo = sample.get_dictionary()   # The actual data within the dictionary
                

                print(repr(i) + " DeviceInfo: ")
                pp.pprint(deviceInfo)
                
                
                if deviceInfo["role"] == 1:
                    # Create a source instance in our dictionary
                    
                    newInstance =  Controller()
                    

                    oldController = class_Divide_Dict["Controller"]  # list of all previously tracked controllers
                    
                    oldController.append(newInstance)  # Add this new controller to the list
                    

                    class_Divide_Dict.update({"Controller" : oldController})  # Replace old list with new list

                
            
                if deviceInfo["role"] == 2:     # Same as controller, but includes more fields within the source class
                    # Create a source instance
                    
                    maxRealPowerAdjusted = deviceInfo["powerDevice"]["source"]["loadSharing"]["maxRealPower"] * .8  # "* .8" Done IOT keep generators under their true realPower
                                                                                                                     # If it exceeds true real power we cannot turn them back on
                    newInstance =  Source(maxRealPowerAdjusted, "ESSL_UNKNOWN", deviceInfo["powerHardware"]["fuel"]["maxFuelLevel"], deviceInfo["powerHardware"]["fuel"]["lowFuelLevelCutoff"], deviceInfo["deviceId"], deviceInfo["powerHardware"]["fuel"]["maxFuelLevel"])
                    
                    oldSource = class_Divide_Dict["Source"]
                    oldSource.append(newInstance)

                    class_Divide_Dict.update({"Source" : oldSource})
                    

                if deviceInfo["role"] == 3:  # Same as source but for loads
                    # create a load instance // right now doesnt work because we dont have smart loads

                    
                    newInstance = Load(deviceInfo["powerDevice"]["load"]["maxRealPower"],deviceInfo["powerDevice"]["load"]["maxReactivePower"], 0, 0)
                    
                    oldLoad = class_Divide_Dict["Load"]
                    oldLoad.append(newInstance)

                    class_Divide_Dict.update({"Load" : oldLoad})
                    


            
        except:
            print("No DeviceInfo samples")

        

        ########### heartbeatReader ############
        try:
            heartbeatReader.wait(1000) 
            heartbeatReader.take()

            for sample in heartbeatReader.samples.valid_data_iter:
                heartbeat = sample.get_dictionary()

                print(repr(i) + " heartbeat: " + repr(heartbeat))
        except:
            print("No heartbeat samples")
        


        ############ energyStartStopStateReader #############
        try:
            #energyStartStopStateReader.wait(1000) 
            energyStartStopStateReader.take()

            for sample in energyStartStopStateReader.samples.valid_data_iter:
                energyStartStopState = sample.get_dictionary()

                print(repr(i) + " EnergyStartStopState: ")
                pp.pprint(energyStartStopState)
            
                # ESSL Levels of sources
                # Unknown: 1
                # Off: 2
                # Warm: 3
                # Idle: 4 *not implemented
                # Ready: 5
                # ReadySynced: 6
                # Operational: 7
                

                for src in class_Divide_Dict["Source"]:    # updating our dicitonary
                    if src.id == energyStartStopState['deviceId']:  # specifying which source we are working with. i.e. making the sample match the src
                        if energyStartStopState['presentLevel'] == 1:
                            # Unknown
                            src.state = "ESSL_UNKNOWN"
                        if energyStartStopState['presentLevel'] == 2:
                            # Off
                            src.state = "ESSL_OFF"
                        if energyStartStopState['presentLevel'] == 3:
                            # Warm
                            src.state = "ESSL_WARM"
                        if energyStartStopState['presentLevel'] == 4:
                            # Idle
                            src.state = "ESSL_IDLE"
                        if energyStartStopState['presentLevel'] == 5:
                            # Ready
                            src.state = "ESSL_READY"
                        if energyStartStopState['presentLevel'] == 6:
                            # Ready_Synced
                            src.state = "ESSL_READY_SYNCED"
                        if energyStartStopState['presentLevel'] == 7:
                            # Operational
                            src.state = "ESSL_OPERATIONAL"
                
                
        except:
            print("No EnergyStartStopState samples")


        ########## activeDiagnosticStateReader ###########
        try:
            #activeDiagnosticStateReader.wait(1000) 
            activeDiagnosticStateReader.take()

            for sample in activeDiagnosticStateReader.samples.valid_data_iter:
                activeDiagnosticState = sample.get_dictionary()
                
                print(repr(i) + " ActiveDiagnosticState: ")
                pp.pprint(activeDiagnosticState)       # Just printed out and read so the controller knows what state the sources are in
                
                
        except:
            print("No ActiveDiagnosticState samples")


        ########## controlParameterStateReader ###########
        try:
            #controlParameterStateReader.wait(1000) 
            controlParameterStateReader.take()

            for sample in controlParameterStateReader.samples.valid_data_iter:
                controlParameterState = sample.get_dictionary()

                print(repr(i) + " ControlParameterState: ")
                pp.pprint(controlParameterState)
                
                
        except:
            print("No ControlParameterState samples")

        
        ######## groundingCircuitStateReader #########
        try:
            #groundingCircuitStateReader.wait(1000) 
            groundingCircuitStateReader.take()

            for sample in groundingCircuitStateReader.samples.valid_data_iter:
                groundingCircuitState = sample.get_dictionary()

                print(repr(i) + " GroundingCircuitState: ")
                pp.pprint(groundingCircuitState)
                
                
        except:
            print("No GroundingCircuitState samples")


        ########### powerPortStateReader ###########
        try:
            #powerPortStateReader.wait(1000) 
            powerPortStateReader.take()

            for sample in powerPortStateReader.samples.valid_data_iter:
                powerPortState = sample.get_dictionary()

                print(repr(i) + " PowerPortState:")
                pp.pprint(powerPortState)
                
                
        except:
            print("No PowerPortState samples")


        ######## ac_MeasurementUpdateReader #########
        try:
            #ac_MeasurementUpdateReader.wait(1000) 
            ac_MeasurementUpdateReader.take()

            total_real_delivered = 0

            for sample in ac_MeasurementUpdateReader.samples.valid_data_iter:
                ac_MeasurementUpdate = sample.get_dictionary()
                
                print(repr(i) + " ac::MeasurementUpdate:")
                pp.pprint(ac_MeasurementUpdate)

                devID = ac_MeasurementUpdate["deviceId"]
                
                for src in class_Divide_Dict["Source"]:     # Updating the info in our dictionary for the power delivered, used for control decisions
                    if devID == src.id:
                        src.realdelivered = ac_MeasurementUpdate["externalMeasurement"][0]["line"][0]["realPower"]
                        
                        src.realdelivered *= 3     # all three lines are equal so * 3 = real total load from one source
                
                    total_real_delivered += src.realdelivered
            
            
            real_delivered_doc = open("Total_Real_Delivered_Combined.txt", "a")
            real_delivered_doc.write(str(total_real_delivered) + "\n")
            # Written to file for analysis 
                        
                        

                
                
        except:
            print("No ac::MeasurementUpdate samples")

        
        
        
        ####### replyReader ##########
        # Informs controller that command has been executed
        try:
            #replyReader.wait(1000) 
            replyReader.take()

            for sample in replyReader.samples.valid_data_iter:
                replyReaderUpdate = sample.get_dictionary()
                
                print(repr(i) + " replyReaderUpdate")
                pp.pprint(replyReaderUpdate)
                
        
        except:
            print("No replyReaderUpdate samples")



        
        
        ###############################################
        # starts all gens on startup
        ###############################################
        if iter_counter <= 0 or iter_counter == 3:  # initialized outside of large loop, runs first time through then roughly 3 seconds later IOT establish MC as master
            for src in class_Divide_Dict["Source"]:
                generator_state_change_request(src.id, "ESSL_OPERATIONAL")
        iter_counter += 1
                
            
        ###############################################
        # continue control after startup
        ###############################################

        if iter_counter > 10:
            # Only works with 2 gens
            gen1 = class_Divide_Dict["Source"][0]
            gen2 = class_Divide_Dict["Source"][1]
            situation1_maintain(gen1, gen2)
           
            
            
            

