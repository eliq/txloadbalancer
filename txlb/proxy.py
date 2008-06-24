from twisted.protocols import amp
from twisted.internet import error
from twisted.internet import reactor
from twisted.internet import protocol

from txlb import logging


class Proxy(object):
    """
    Listener object. Listens at a given host/port for connections.
    Creates a receiver to collect data from client, and a sender to
    connect to the eventual destination host.

    Public API:

    method __init__(self, name, host, port, scheduler, director)
    attribute .scheduler: read/write - a PDScheduler
    attribute .listening_address: read - a tuple of (host,port)
    """
    def __init__(self, name, host, port, scheduler, director):
        self.name = name
        self.port = port
        self.host = host
        self.listening_address = (host, port)
        self.director = director
        self.factory = ReceiverFactory(
            self.listening_address, scheduler, self.director)
        self.setScheduler(scheduler)

    def setScheduler(self, scheduler):
        self.scheduler = scheduler
        self.factory.setScheduler(scheduler)


class Sender(protocol.Protocol):
    """
    A Sender object connects to the remote final server, and passes data
    back and forth. Unlike the receiver, it's not necessary to buffer up
    data, since the client _must_ be connected (if it's not, toss the
    data)
    """
    receiver = None

    def setReceiver(self, receiver):
        self.receiver = receiver

    def connectionLost(self, reason):
        """
        The server is done, and has closed the connection. write out any
        remaining data, and close the socket.
        """
        if self.receiver is not None:
            if reason.type is error.ConnectionDone:
                pass
            elif reason.type is error.ConnectionLost:
                pass
            else:
                #print id(self),"connection to server lost:",reason
                pass
            self.receiver.transport.loseConnection()

    def dataReceived(self, data):
        if self.receiver is None:
            logging.log("client got data, no receiver, tho\n", datestamp=1)
        else:
            self.receiver.transport.write(data)

    def connectionMade(self):
        """
        We've connected to the destination server. tell the other end
        it's ok to send any buffered data from the client.
        """
        #XXX: OMG THIS IS HORRIBLE
        inSrc = self.receiver.transport.getPeer()
        outSrc = self.transport.getHost()
        self.receiver.factory.director.setClientAddress(
            (outSrc.host, outSrc.port),
            (inSrc.host, inSrc.port))
        if self.receiver.receiverOk:
            self.receiver.setSender(self)
        else:
            # the receiver's already given up at this point and gone
            # home. _if_ the receiver got data from the client, we
            # must send it on - the client thinks that it's successfully
            # sent it, so we should honour that. We don't need to worry
            # about the response from the server itself.
            data = self.receiver.getBuffer()
            if data:
                self.transport.write(data)
            self.transport.loseConnection()
            self.setReceiver(None)


class SenderFactory(protocol.ClientFactory):
    """
    Create a Sender when needed. The sender connects to the remote host.
    """
    protocol = Sender
    noisy = 0

    def setReceiver(self, receiver):
        self.receiver = receiver

    def buildProtocol(self, *args, **kw):
        # over-ride the base class method, because we want to connect
        # the objects together.
        protObj = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        protObj.setReceiver(self.receiver)
        return protObj

    def clientConnectionFailed(self, connector, reason):
        # this would hang up the inbound. We don't want that.
        self.receiver.factory.scheduler.deadHost(self, reason)
        next =  self.receiver.factory.scheduler.getHost(
            self, self.receiver.client_addr)
        if next:
            logging.log("retrying with %s\n"%repr(next), datestamp=1)
            host, port = next
            reactor.connectTCP(host, port, self)
        else:
            # No working servers!?
            logging.log("no working servers, manager -> aggressive\n",
                          datestamp=1)
            self.receiver.transport.loseConnection()

    def stopFactory(self):
        self.receiver.factory.scheduler.doneHost(self)


class Receiver(protocol.Protocol):
    """
    Listener bit for clients connecting to the director.
    """
    sender = None
    buffer = ''
    receiverOk = 0

    def connectionMade(self):
        """
        This is invoked when a client connects to the director.
        """
        self.receiverOk = 1
        self.client_addr = self.transport.client
        sender = SenderFactory()
        sender.setReceiver(self)
        dest = self.factory.scheduler.getHost(sender, self.client_addr)
        if dest:
            host, port = dest
            reactor.connectTCP(host, port, sender)
            connection = reactor.connectTCP(host, port, sender)
            # XXX add optional support for logging these connections
        else:
            self.transport.loseConnection()

    def setSender(self, sender):
        """
        The sender side of the proxy is connected.
        """
        self.sender = sender
        if self.buffer:
            self.sender.transport.write(self.buffer)
            self.buffer = ''

    def connectionLost(self, reason):
        """
        The client has hung up/disconnected. send the rest of the
        data through before disconnecting. Let the client know that
        it can just discard the data.
        """
        # damn. XXX TODO. If the client connects, sends, then disconnects,
        # before the end server has connected, we have data loss - the client
        # thinks it's connected and sent the data, but it won't have. damn.
        if self.sender:
            # according to the interface docstring, this sends all pending
            # data before closing the connection.
            self.sender.setReceiver(None)
            self.sender.transport.loseConnection()
            self.receiverOk = 0
        else:
            # there's a race condition here - we could be in the process of
            # setting up the director->server connection. This then comes in
            # after this, and you end up with a hosed receiver that's hanging
            # around.
            self.receiverOk = 0

    def getBuffer(self):
        """
        Return any buffered data.
        """
        return self.buffer

    def dataReceived(self, data):
        """
        Received data from the client. either send it on, or save it.
        """
        if self.sender is not None:
            self.sender.transport.write(data)
        else:
            self.buffer += data


class ReceiverFactory(protocol.ServerFactory):
    """
    Factory for the listener bit of the load balancer.
    """
    protocol = Receiver
    noisy = 0

    def __init__(self, (host, port), scheduler, director):
        self.host = host
        self.port = port
        self.scheduler = scheduler
        self.director = director

    def setScheduler(self, scheduler):
        self.scheduler = scheduler


