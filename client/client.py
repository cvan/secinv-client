#!/usr/bin/env python
import xmlrpclib
import sys

from common import *
from inventory import *

proxy = xmlrpclib.ServerProxy(uri="%s:%s" % (HOST, PORT), verbose=False)

multicall = xmlrpclib.MultiCall(proxy)

# Send authentication key.
multicall.authenticate(AUTH_TOKEN)


ip = Interfaces()
ip_dict = ip.get_interfaces()

system = System()
system_dict = system.get_system_dict()

services = Services()
services_dict = services.get_services()

rpms = RPMs()
rpms_dict = rpms.get_rpms()

cp = SSHConfig()
sshconfig_dict = cp.parse()

ipt = IPTables()
ipt_dict = ipt.get_ipt_dict()

acl = ApacheConfigList()
acl_list = acl.get_apache_configs()

phpini = PHPConfig()
phpini_dict = phpini.parse()

mycnf = MySQLConfig()
mycnf_dict = mycnf.parse()


multicall.machine(ip_dict, system_dict, services_dict, rpms_dict,
                  sshconfig_dict, ipt_dict, acl_list, phpini_dict, mycnf_dict)
result = multicall()

print "Authentication:  %s" % result[0]
print "Received machine info:  %s" % result[1]

