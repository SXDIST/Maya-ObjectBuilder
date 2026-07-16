"""a3ob* MPxCommand implementations (one module per command)."""

from a3ob.mayabridge.commands.validate import ValidateCommand
from a3ob.mayabridge.commands.mass import SetMassCommand
from a3ob.mayabridge.commands.material import SetMaterialCommand
from a3ob.mayabridge.commands.flag import SetFlagCommand
from a3ob.mayabridge.commands.components import FindComponentsCommand
from a3ob.mayabridge.commands.lod import CreateLODCommand
from a3ob.mayabridge.commands.proxy import ProxyCommand
from a3ob.mayabridge.commands.named_property import NamedPropertyCommand
from a3ob.mayabridge.commands.update_proxy import UpdateProxyCommand

COMMANDS = [
    ValidateCommand, SetMassCommand, SetMaterialCommand, SetFlagCommand,
    FindComponentsCommand, CreateLODCommand, ProxyCommand, NamedPropertyCommand,
    UpdateProxyCommand,
]

__all__ = [
    "ValidateCommand", "SetMassCommand", "SetMaterialCommand", "SetFlagCommand",
    "FindComponentsCommand", "CreateLODCommand", "ProxyCommand", "NamedPropertyCommand",
    "UpdateProxyCommand", "COMMANDS",
]
