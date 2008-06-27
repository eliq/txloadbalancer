"""
This module contains a series of classes that are used to model (in a very
simplified manner) services, groups of proxied hosts, and proxied hosts.

There are potentially many uses for such classes, but they are currently used
in order to separate configuration/application logic and the libraries. They do
this by mapping configuration information to model class instances.
"""


class ProxyService(object):
    """
    A class that represents a collection of groups whose hosts need to be
    proxied.
    """
    def __init__(self, name, ports=[], groups={}):
        self.name = name
        self.ports = ports
        self.groups =groups


    def getEnabledGroup(self):
        """
        There should only ever be one enabled group. This method returns it. If
        there is more than one enabled group, only the first one this method
        finds will be returned.
        """
        groups = [x for x in self.groups.values() if x.isEnabled]
        if groups:
            return groups[0]


    def addGroup(self, proxyGroup):
        """
        Update the service's group data structure with a new ProxyGroup
        instance.
        """
        self.groups[proxyGroup.name] = proxyGroup


    def getGroups(self):
        """
        Return the keys and values of the groups attribute.
        """
        return self.groups.items()


class ProxyGroup(object):
    """
    A class that represnts a group of hosts that need to be proxied.
    """
    def __init__(self, name, scheduler=None, enabled=False):
        self.name = name
        self.hosts = {}
        self.isEnabled = enabled
        self.lbType = scheduler


    def enable(self):
        """
        This method is required to be called in order for a group to be
        enabled. Only an enabled group can generate connection proxies.
        """
        self.isEnabled = True


    def disable(self):
        """
        This method needs to be called in order to disable a group. If it is
        not called, and there are two enabled groups, only one group will be
        retuted by ProxyService.getEneabledGroup.
        """
        self.isEnabled = False


    def addHost(self, proxyHost):
        """
        Update the group's hosts data structure with a new ProxyHost instance.
        """
        self.hosts[proxyHost.name] = proxyHost


    def getHosts(self):
        """
        Return the keys and values of the hosts attribute.
        """
        return self.hosts.items()


class ProxyHost(object):
    """
    A class that represents a host that needs to be proxied.
    """
    def __init__(self, name='', ipOrHost='', port=None):
        self.name = name
        self.hostname = ipOrHost
        self.port = port




