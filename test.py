from pydbus import SystemBus
import dbus
import dbus.exceptions
import dbus.service
import dbus.mainloop.glib

try:
    from gi.repository import GLib
except ImportError:
    import glib as GLib

# Bluez D-Bus interfaces
BLUEZ_SERVICE_NAME = 'org.bluez'

GATT_MANAGER_IFACE = BLUEZ_SERVICE_NAME + '.GattManager1'
GATT_SERVICE_IFACE = BLUEZ_SERVICE_NAME + '.GattService1'
GATT_CHRC_IFACE = BLUEZ_SERVICE_NAME + '.GattCharacteristic1'
GATT_DESC_IFACE = BLUEZ_SERVICE_NAME + '.GattDescriptor1'

LE_ADVERTISING_MANAGER_IFACE = BLUEZ_SERVICE_NAME + '.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = BLUEZ_SERVICE_NAME + '.LEAdvertisement1'

DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
LOCAL_NAME = 'Raem'

# Test UUIDs
TEST_SERVICE = '0000ffff-beef-c0c0-c0de-c0ffeefacade'
TEST_CHARACTERISTIC = '0000bbbb-beef-c0c0-c0ffeefacade'

# Boiler plate start
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
    
def register_app_cb():
    print("GATT application registered")

def register_app_error_cb(error):
    print("Failed to register application: " + str(error))
    mainloop.quit()
    
def register_ad_cb():
    print("Advertisement registered")
    
def register_ad_error_cb(error):
    print("Failed to register advertisement: " + str(error))
    mainloop.quit()

class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'
    
    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.local_name = LOCAL_NAME
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.include_tx_power = False
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)
    
    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(self.manufacturer_data, signature='qv')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='sv')
        if self.include_tx_power:
            properties['Include'] = dbus.Array(["tx-power"], signature='s')
        if self.data is not None:
            properties['Data'] = dbus.Dictionary(self.data, signature='yu')
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
    
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        print("GetAll")
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        print('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]
    
    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        print('%s: Released!' % self.path)
        
class Service(dbus.service.Object):
    PATH_BASE = '/org/bluez/app/service'
    
    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = gus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)
        
    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(self.get_charateristic_paths(), signature="o")
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
        return self.charcteristics
    
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_SERVICE_IFACE]
    
class Characteristic(dbus.service.Object):

    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/chrc" + str(index)
        self.bus = gus
        self.uuid = uuid
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)
        
    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Descriptors": dbus.Array(self.get_descriptor_path(), signature="o")
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
    
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]
    
    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        print("Default ReadValue called, returning error")
        raise NotSupportedException()
    
    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        print("Default WriteValue called, returning error")
        raise NotSupportedException()
    
    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print("Default StartNotify called, returning error")
        raise NotSupportedException()
    
    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print("Default StopNotify called, returning error")
        raise NotSupportedException()
    
    @dbus.service.method(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass
    
def find_adapter(bus, iface):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    
    for o, props in objects.items():
        if iface in props:
            return o
    return None

# Bolier plate end

class TestService(Service):
    
    def __init__(self, bus, index):
        Service.__init__(self, bus, index, TEST_SERVICE, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))
        
class TestCharacteristic(Characteristic):
    
    def __init__(self, bus, index, service):
        Charcteristic.__init__(self, bus, index, TEST_CHARACTERISTIC, ["write"], service)
        self.value = ""
        
    def WriteValue(self, value, options):
        print(f"TestCharacteristic Write: {value}")
        txt = bytes(value).decode('utf8')
        print(f"As text: {txt}")
        self.value = txt
        my_write_callback(txt)
    
class TestAdvertisement(Advertisement):
    
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_local_name(LOCAL_NAME)
        self.include_tx_power = True
        
class Application(dbus.service.Object):
    
    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(TestService(bus, 0))
        
    def get_path(self):
        return dbus.ObjectPath(self.path)
    
    def add_service(self, service):
        self.services.append(self.path)
    
    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        print("GetManagedObjects")
        
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()
        
        return response
    
def my_write_callback(txt):
    print(f"This is where I can use the <<{txt}>> value")
    
def main():
    global mainloop
    
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    adapter = find_adapter(bus, LE_ADVERTISING_MANAGER_IFACE)
    if not adapter:
        print("Adapter not found")
        return
    
    service_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), GATT_MANAGER_IFACE)
    
    app = Application(bus)
    
    test_advertisement = TestAdvertisement(bus, 0)
    
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), LE_ADVERTISING_MANAGER_IFACE)
    
    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {}, reply_handler=register_ad_cb, error_handler=register_ad_error_cb)
    
    mainloop = GLib.MainLoop()
    
    print("Registering GATT application...")
    
    service_manager.RegisterApplication(app.get_path(), {}, reply_handler=register_app_cb, error_handler=register_app_error_db)
        
    mainloop.run()
    
    if __name__ == '__main__':
        main()