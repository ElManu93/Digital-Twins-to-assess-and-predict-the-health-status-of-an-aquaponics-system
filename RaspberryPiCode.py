'''Import libaries'''
import time
from datetime import datetime
import csv
import requests 	# Is needed for sending data to ThingSpeak

'''Sensor libaries'''
from w1thermsensor import W1ThermSensor		# For the Temperature Sensor
import io
import fcntl

'''Set up the I2C connection'''
bus = 1
I2C_SLAVE = 0x703

# Opens the "/dev/i2c" - file for writing to communicate with the I2C bus
file_write = io.open(file="/dev/i2c-{}".format(bus),
                                  mode="wb",    # Mode set for writing in binary format
                                  buffering=0)
# Opens the "/dev/i2c" - file for writing to communicate with the I2C bus
file_read = io.open(file="/dev/i2c-{}".format(bus), 
                                 mode="rb",     # Mode set for reading in binary format
                                 buffering=0)

'''Set the I2C-Addresses of the AtlasScientific Sensors'''
EC_SENSOR_ADDR = 0x64
pH_SENSOR_ADDR = 0x63
ORP_SENSOR_ADDR = 0x62

'''Set the Temperature Sensor with one-wire'''
if W1ThermSensor.get_available_sensors():
    temp_sensor = W1ThermSensor.get_available_sensors()[0]	# Create a list of devices with one-wire
else:
    temp_sensor = None
    
'''ThingSpeak API-Key'''
API_KEY = 'GMPTGVELAVWQRXAV'

'''Set up CSV-File'''
csv_file = '/home/ElManu/sensor_data.csv'
with open(csv_file, mode='a', newline='') as file:
    csv_writer = csv.writer(file)
    csv_writer.writerow(['Datum/Uhrzeit', 'pH', 'EC', 'ORP', 'Temperatur']) # Write the header of the csv-file
        
'''Endless Loop'''
while True:
    '''Get Temperature'''
    if temp_sensor != None:
        try:
            temperature = round(temp_sensor.get_temperature(), 1)
            print('Temperature:', temperature, '°C')
            
        except Exception as e:
            temperature = 0     # This helps to see if the sensor is disconnected
            print('Could not read temperature: ', e)
        
    else:
        temperature = 0
        
    '''Build command to send to sensors'''
    if temperature != 0:
        command = 'RT,{}'.format(temperature)   # Temperature compensation
        command += "\00"	# The Sensors expect commands to finish with 00
    else:
        command = 'R'
        command += "\00"	# The Sensors expect commands to finish with 00

    '''Get pH Value'''
    try:
        # Set the slave device to the address of pH Sensor for writing and reading data:
        fcntl.ioctl(file_write, I2C_SLAVE, pH_SENSOR_ADDR)
        fcntl.ioctl(file_read, I2C_SLAVE, pH_SENSOR_ADDR)
        file_write.write(command.encode('latin-1'))		# Endocde the command and send it
        time.sleep(2)

        raw_data = file_read.read(31)	# Read out 31 bits
        new_pH = [byte for byte in raw_data if byte != 0x00]    # Remove all 0x00 the answer
        new_pH = ''.join(map(chr, new_pH[1:]))
        # Check if the answer is empty:
        if len(new_pH) >= 1:
            pH = new_pH
        else:
            pH = '0'
        print('pH Value: ', pH)
        
    except Exception as e:
        print("Couldn't read pH: ", e)
        
    '''Get EC Value'''
    try:
        # Set the slave device to the address of EC Sensor for writing and reading data:
        fcntl.ioctl(file_write, I2C_SLAVE, EC_SENSOR_ADDR)
        fcntl.ioctl(file_read, I2C_SLAVE, EC_SENSOR_ADDR)
        file_write.write(command.encode('latin-1'))		# Endocde the command
        time.sleep(2)

        raw_data = file_read.read(31)	# Read out 31 bits
        new_EC = [byte for byte in raw_data if byte != 0x00]    # Remove all 0x00 the answer
        new_EC = ''.join(map(chr, new_EC[1:]))   # Convert the answer to a string
        # Check if the answer is empty:
        if len(new_EC) >= 1:
            EC = new_EC
        else:
            EC = '0'
        print('EC Value: ', EC, 'µS/cm')
        
    except Exception as e:
        print("Couldn't read EC: ", e)
        
    '''Get ORP Value'''
    try:
        # Set the slave device to the address of ORP Sensor for writing and reading data:
        fcntl.ioctl(file_write, I2C_SLAVE, ORP_SENSOR_ADDR)
        fcntl.ioctl(file_read, I2C_SLAVE, ORP_SENSOR_ADDR)
        orp_command = 'R'		# The ORP Sensor doesn't have temperature compensated measurements
        orp_command += '\00'	# The Sensors expect commands to finish with 00
        file_write.write(orp_command.encode('latin-1'))		# Endocde the command and send it
        time.sleep(2)

        raw_data = file_read.read(31)	#read out 31 bits
        new_ORP = [byte for byte in raw_data if byte != 0x00]    # Remove all 0x00 the answer
        new_ORP = ''.join(map(chr, new_ORP[1:]))# Convert the answer to a string
        # Check if the answer is empty:
        if len(new_ORP) >= 1:
            ORP = new_ORP
        else:
            ORP = '0'
        print('ORP Value: ', ORP, 'mV')
        
    except Exception as e:
        print("Couldn't read ORP: ", e)
        
    '''Write data to CSV-File'''
    with open(csv_file, mode='a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pH, EC, ORP, temperature])
    
    '''Send data to ThingSpeak'''
    try:
        # Build the URL:
        url = f'https://api.thingspeak.com/update?api_key={API_KEY}&field1={pH}&field2={EC}&field3={ORP}&field4={temperature}'
        response = requests.get(url)
        
        #check response code:
        if response.status_code == 200:
            print('Data sent to ThingSpeak succesfully!')
        else:
            print('Could not send data to ThingSpeak!')
            
    except Exception as e:
        print('Was not able to send data!', e)
        
    time.sleep(173)   # One measurement every ~3 minutes.