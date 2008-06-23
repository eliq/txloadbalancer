from twisted.web import server
from twisted.internet import ssl
from twisted.application import service
from twisted.application import internet
from twisted.application import strports

from txlb import name
from txlb import util
from txlb import manager
from txlb.admin import pages
from txlb.manager import checkBadHosts


def setupAdminServer(director):
    """
    Given the director, set up a potentially SSL-enabled admin web UI on the
    configured port.
    """
    site = server.Site(pages.AdminServer(director))
    adminPort = director.conf.admin.listen[1]
    if director.conf.admin.secure:
        util.setupServerCert()
        context = ssl.DefaultOpenSSLContextFactory(
            util.privKeyFile, util.certFile)
        admin = internet.SSLServer(adminPort, site, context)
    else:
        admin = internet.TCPServer(adminPort, site)
    return admin


def setupHostChecker(director):
    """
    This is the setup for the "bad host check" management task.
    """
    checkInterval = director.conf.manager.hostCheckInterval
    return internet.TimerService(checkInterval, checkBadHosts, director)


def setup(configFile):
    """
    Given the configuration file, instantiate the proxy manager and setup the
    necessary services.
    """
    application = service.Application(name)
    services = service.IServiceCollection(application)

    # instantiate the proxy manager to direct the proxies
    director = manager.ProxyManager(configFile)

    # set up proxies for each service the proxy manager balances
    # XXX

    # set up the control socket
    # XXX

    # set up the web server
    admin = setupAdminServer(director)
    admin.setServiceParent(services)

    # set up the manager timer service
    checker = setupHostChecker(director)
    checker.setServiceParent(services)

    return application

