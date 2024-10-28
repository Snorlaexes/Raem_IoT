#!/usr/bin/python
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import print_function

import argparse
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import time
import threading
import board
import neopixel
from AudioPlayer import AudioPlayer
from LEDController import LEDController

try:
    from gi.repository import GObject  # python3
except ImportError:
    import gobject as GObject  # python2

mainloop = None
player = None
ledController = None

BLUEZ_SERVICE_NAME = 'org.bluez'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'


class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = False
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power:
            properties['Includes'] = dbus.Array(["tx-power"], signature='s')

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(
                self.data, signature='yv')
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        self.data[ad_type] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        print('GetAll')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        print('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released!' % self.path)
        

class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(LEDService(bus, 0))
        self.add_service(AudioService(bus, 1))
        self.add_service(AlarmService(bus, 2))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()
        
        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_SERVICE_IFACE: {
                        'UUID': self.uuid,
                        'Primary': self.primary,
                        'Characteristics': dbus.Array(
                                self.get_characteristic_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_CHRC_IFACE: {
                        'Service': self.service.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                        'Descriptors': dbus.Array(
                                self.get_descriptor_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print('Default StartNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print('Default StopNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_DESC_IFACE: {
                        'Characteristic': self.chrc.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print ('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()


class TestAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180D')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_local_name('Raem')
        self.include_tx_power = True
        self.add_data(0x26, [0x01, 0x01, 0x00])

class LEDService(Service):
    LED_SVC_UUID = '123e4567-e89b-12d3-a456-426614174000'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.LED_SVC_UUID, True)
        self.add_characteristic(LEDCharacteristic(bus, 0, self))

class LEDCharacteristic(Characteristic):
    LED_CHRC_UUID = '123e4567-e89b-12d3-a456-426614174001'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.LED_CHRC_UUID,
                ['write', 'writable-auxiliaries'],
                service)
        self.red = 0.00
        self.blue = 0.00
        self.green = 0.00
    
    def WriteValue(self, value, options):
        global ledController
        txt = bytes(value).decode('utf-8')
        print(f"As text: {txt}")
        if "," in txt:
            colorValues = txt.split(",")
            self.red = float(colorValues[0])
            self.green = float(colorValues[1])
            self.blue = float(colorValues[2])
            
            ledController.start()
            if ledController is not None:
                ledController.update_color(self.red, self.green, self.blue, -1)
        else:
            if ledController is not None:
                ledController.stop()
 
class AudioService(Service):
    AUDIO_SVC_UUID = '123e4567-e89b-12d3-a456-426614175000'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.AUDIO_SVC_UUID, True)
        self.add_characteristic(AudioOnCharacteristic(bus, 1, self))
        self.add_characteristic(ChangeVolumeCharacteristic(bus, 2, self))
        self.add_characteristic(AudioOffCharacteristic(bus, 3, self))

class AudioOnCharacteristic(Characteristic):
    AUDIO_ON_CHRC_UUID = '123e4567-e89b-12d3-a456-426614175001'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.AUDIO_ON_CHRC_UUID,
                ['write', 'writable-auxiliaries'],
                service)
        self.file_path = ""
        self.volume = 0
    
    def WriteValue(self, value, options):
        global player
        txt = bytes(value).decode('utf-8')
        print(f"As text: {txt}")
        if "," in txt:
            audioValues = txt.split(",")
            
            if audioValues[2] == 'music':
                self.file_path = f'./SleepMusic/{audioValues[0]}.wav'
            elif audioValues[2] == 'alarm':
                self.file_path = f'./Alarm/{audioValues[0]}.wav'
                
            self.volume = int(audioValues[1])
            
            player.start()
            if player is not None:
                player.update_music(self.file_path, self.volume)
            # time.sleep(4)
            # player.stop_audio()
        else:
            print("Wrong value in AudioOnCharacteristic")

class ChangeVolumeCharacteristic(Characteristic):
    CNG_VOL_CHRC_UUID = '123e4567-e89b-12d3-a456-426614175002'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.CNG_VOL_CHRC_UUID,
                ['write', 'writable-auxiliaries'],
                service)
        self.volume = 0
    
    def WriteValue(self, value, options):
        global player
        txt = bytes(value).decode('utf-8')
        print(f"As text: {txt}")
        if "," in txt:
            print("Wrong value in ChangeVolumeCharacteristic")
        else:
            self.volume = int(txt)
            if player is not None:
                player.set_volume(self.volume)

class AudioOffCharacteristic(Characteristic):
    AUDIO_OFF_CHRC_UUID = '123e4567-e89b-12d3-a456-426614175003'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.AUDIO_OFF_CHRC_UUID,
                ['write', 'writable-auxiliaries'],
                service)
    
    def WriteValue(self, value, options):
        global player
        print(value)
        txt = bytes(value).decode('utf-8')
        print(f"As text: {txt}")
        if player is not None:
            player.stop()

class AlarmService(Service):
    ALARM_SVC_UUID = '123e4567-e89b-12d3-a456-426614176000'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.ALARM_SVC_UUID, True)
        self.add_characteristic(AlarmOnCharacteristic(bus, 1, self))
        self.add_characteristic(AlarmOffCharacteristic(bus, 2, self))

class AlarmOnCharacteristic(Characteristic):
    ALARM_ON_CHRC_UUID = '123e4567-e89b-12d3-a456-426614176001'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.ALARM_ON_CHRC_UUID,
                ['write', 'writable-auxiliaries'],
                service)
        
        self.radientSec = 0 #Slowly brightened during this time
        self.red = 0.00
        self.green = 0.00
        self.blue = 0.00
        self.file_path = ""
        self.volume = 0
    
    def WriteValue(self, value, options):
        txt = bytes(value).decode('utf-8')
        print(f"As text: {txt}")
        if "," in txt:
            audioValues = txt.split(",")
            
            self.radientSec = int(audioValues[0])
            self.red = float(audioValues[1])
            self.green = float(audioValues[2])
            self.blue = float(audioValues[3])
            self.file_path = f'./Alarm/{audioValues[4]}.wav'
            self.volume = int(audioValues[5])

            turnAlarmOn(self.radientSec, self.red, self.green, self.blue, self.file_path, self.volume)
            
        else:
            print("Wrong value in AlarmOnCharacteristic")

class AlarmOffCharacteristic(Characteristic):
    ALARM_OFF_CHRC_UUID = '123e4567-e89b-12d3-a456-426614176002'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.ALARM_OFF_CHRC_UUID,
                ['write', 'writable-auxiliaries'],
                service)
    
    def WriteValue(self, value, options):
        txt = bytes(value).decode('utf-8')
        print(f"As text: {txt}")
        turnAlarmOff()

def turnAlarmOn(second, r, g, b, file_path, volume):
    global player, ledController
    steps = second * 10
    
    ledController.start()
    if ledController is not None:
        ledController.update_color(r, g, b, steps)

    time.sleep(second + 0.1) # led 켜질때까지 대기
    
    player.start()
    if player is not None:
        player.update_music(file_path, volume)
    

def turnAlarmOff():
    global player, ledController

    if ledController is not None:
        ledController.stop()
    
    if player is not None:
        player.stop()
    

def register_app_cb():
    print('GATT application registered')
    print('-----------------------------------')


def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None


def shutdown(timeout):
    print('Advertising for {} seconds...'.format(timeout))
    time.sleep(timeout)
    mainloop.quit()


def main(timeout=0):
    global mainloop, bus, player, ledController

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print('LEAdvertisingManager1 interface not found')
        return

    service_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                   GATT_MANAGER_IFACE)

    app = Application(bus)

    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)

    test_advertisement = TestAdvertisement(bus, 0)

    

    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                     reply_handler=register_app_cb,
                                     error_handler=register_app_error_cb)
    
    
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)
    player = AudioPlayer.getInstance()
    ledController = LEDController.getInstance()
    
    if timeout > 0:
        threading.Thread(target=shutdown, args=(timeout,)).start()
    else:
        print('Advertising forever...')

    mainloop = GObject.MainLoop()
    mainloop.run()  # blocks until mainloop.quit() is called

    ad_manager.UnregisterAdvertisement(test_advertisement)
    print('Advertisement unregistered')
    dbus.service.Object.remove_from_connection(test_advertisement)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', default=0, type=int, help="advertise " +
                        "for this many seconds then stop, 0=run forever " +
                        "(default: 0)")
    args = parser.parse_args()

    main(args.timeout)
