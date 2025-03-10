import json
import re
import socket
from typing import Any, Dict, List

import psutil
from commonwealth.settings import settings
from loguru import logger
from pykson import (
    IntegerField,
    JsonObject,
    ListField,
    MultipleChoiceStringField,
    ObjectListField,
    StringField,
)


class InvalidIpAddress(Exception):
    pass


class DefaultSettings(JsonObject):
    domain_names = ListField(item_type=str)
    advertise = ListField(item_type=str)
    ip = StringField()


class Interface(JsonObject):
    name = StringField()
    domain_names = ListField(item_type=str)
    advertise = ListField(item_type=str)
    ip = StringField()

    def get_phys(self) -> List[psutil._common.snicaddr]:
        """
        return Physical interface from psutil
        """
        return list(filter(lambda address: address.family == socket.AF_INET, psutil.net_if_addrs()[self.name]))

    def get_ip_strs(self) -> List[str]:
        """
        get ip as a string. this also translates 'ips[n]' to the n-th ip in that interface
        """
        address = str(self.ip)
        # Check for 'ips[n]'

        if address == "ips[*]":
            addresses = []
            for iface in self.get_phys():
                try:
                    addresses.append(str(iface.address))
                except Exception as e:
                    logger.warning(f"unable to add ip {iface.address}: {e}")
            return addresses
        matches = re.findall(r"ips\[(\d+)]", self.ip)
        if len(matches) != 0:
            index = int(matches[0])
            try:
                address = str(self.get_phys()[index].address)
            except Exception as e:
                logger.warning(f"unable to get {index}-th IP address: {e}")
                return []
        # Validate ip
        try:
            socket.inet_aton(address)
            return [address]
        except OSError as e:
            raise InvalidIpAddress(f"Invalid IP address: {address}") from e

    def get_ips(self) -> List[bytes]:
        """
        returns the ip as 4 bytes
        """
        return [socket.inet_aton(ip) for ip in self.get_ip_strs()]

    def __repr__(self) -> str:
        return str(self.name)


class ServiceTypes(JsonObject):
    name = StringField()
    protocol = MultipleChoiceStringField(options=["_udp", "_tcp"], null=False)
    port = IntegerField()
    properties = StringField()

    def get_properties(self) -> Dict[str, Any]:
        if self.properties is None:
            return {}
        return json.loads(self.properties)  # type: ignore


class SettingsV1(settings.BaseSettings):
    VERSION = 1
    default = DefaultSettings()
    blacklist = ListField(item_type=str)
    interfaces = ObjectListField(Interface)
    advertisement_types = ObjectListField(ServiceTypes)

    def __init__(self, *args: str, **kwargs: int) -> None:
        super().__init__(*args, **kwargs)

        self.VERSION = SettingsV1.VERSION

    def migrate(self, data: Dict[str, Any]) -> None:
        if data["VERSION"] == SettingsV1.VERSION:
            return

        if data["VERSION"] < SettingsV1.VERSION:
            super().migrate(data)

        data["VERSION"] = SettingsV1.VERSION

    def get_interface_or_create_default(self, name: str) -> Interface:
        """
        tries to return settings for the given interface, creates a new Interface object
        based on the default settings if unable to find it.
        """
        found = [interface for interface in self.interfaces if interface.name == name]
        if found:
            assert isinstance(found[0], Interface)
            return found[0]
        new = Interface(
            name=name, domain_names=self.default.domain_names, advertise=self.default.advertise, ip=self.default.ip
        )
        self.interfaces.append(new)
        return new


class SettingsV2(SettingsV1):
    VERSION = 2

    def __init__(self, *args: str, **kwargs: int) -> None:
        super().__init__(*args, **kwargs)
        self.VERSION = SettingsV2.VERSION

    def migrate(self, data: Dict[str, Any]) -> None:
        if data["VERSION"] == SettingsV2.VERSION:
            return

        if data["VERSION"] < SettingsV2.VERSION:
            super().migrate(data)

        data["default"]["domain_names"] = [domain for domain in data["default"]["domain_names"] if domain != "blueos"]
        try:
            for interface in data["interfaces"]:
                if interface["name"] == "wlan0":
                    interface["domain_names"] = [
                        name for name in interface["domain_names"] if name not in ["blueos", "companion"]
                    ]
        except Exception as e:
            logger.error(f"unable to update SettingsV1 to SettingsV2: {e}")

        data["VERSION"] = SettingsV2.VERSION
