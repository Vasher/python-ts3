import socket
import logging

class ConnectionError():

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def __str__():
        return 'Error connecting to host %s port %s' % (self.ip, self.port)

ts3_escape = { '/': r"\/",
               ' ': r'\s',
               '|': r'\p',
               "\a": r'\a',
               "\b": r'\b',
               "\f": r'\f',
               "\n": r'\n',
               "\r": r'\r',
               "\t": r'\t',
               "\v": r'\v' }
               

class TS3Proto():

    bytesin = 0
    bytesout = 0

    _connected = False

    def __init__(self):
        self._log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        pass

    def connect(self, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, port))
        except:
            #raise ConnectionError(ip, port)
            raise
        else:
            self._sock = s
            self._sockfile = s.makefile('r', 0)

        data = self._sockfile.readline()
        if data.strip() == "TS3":
            self._connected = True
            return True

    def disconnect(self):
        self.send_command("quit")
        self._sock.close()
        self._sock = None
        self._connected = False
        self._log.info('Disconnected')

    def send_command(self, command, keys=None, opts=None):
        cmd = self.construct_command(command, keys=keys, opts=opts)
        self.send('%s\n' % cmd)

        ret = []

        while True:
            resp = self._sockfile.readline()
            resp = self.parse_command(resp)
            if not 'command' in resp:
                ret.append(resp['keys'])
            else:
                break

        if resp['command'] == 'error':
            if ret and resp['keys']['id'] == '0':
                return ret
            else:
                return resp['keys']['id']

    def construct_command(self, command, keys=None, opts=None):
        """
        Constructs a TS3 formatted command string

        Keys can have a single nested list to construct a nested parameter

        @param command: Command list
        @type command: string
        @param keys: Key/Value pairs
        @type keys: dict
        @param opts: Options
        @type opts: list
        """

        cstr = []
        cstr.append(command)

        # Add the keys and values, escape as needed        
        if keys:
            for key in keys:
                if isinstance(keys[key], list):
                    ncstr = []
                    for nest in keys[key]:
                        ncstr.append("%s=%s" % (key, self._escape_str(nest)))
                    cstr.append("|".join(ncstr))
                else:
                    cstr.append("%s=%s" % (key, self._escape_str(keys[key])))

        # Add in options
        if opts:
            for opt in opts:
                cstr.append("-%s" % opt)

        return " ".join(cstr)

    def parse_command(self, commandstr):
        """
        Parses a TS3 command string into command/keys/opts tuple

        @param commandstr: Command string
        @type commandstr: string
        """

        cmdlist = commandstr.strip().split(' ')

        command = cmdlist[0]
        keys = {}
        opts = []

        start = 1
        len(command.split('='))
        if len(command.split('=')) > 1:
            start = 0
            command = ''


        for key in cmdlist[start:]:
            if len(key.split('|')) > 1:
                output = []
                # Nested Keys
                nkeys = key.split('|')
                for nkey in nkeys:
                    nvalue = nkey.split('=')
                    okey = nvalue[0]
                    output.append(nvalue[1])
                keys[okey] = output
                continue
            if len(key.split('=')) > 1:
                # Key value
                nvalue = key.split('=')
                keys[nvalue[0]] = self._unescape_str(nvalue[1])
                continue
            elif key[0] == '-':
                opts.append(key[1:])
                continue

        d = {'keys': keys, 'opts': opts}
        if command:
            d['command'] = command
        return d
         

    @staticmethod
    def _escape_str(value):
        """
        Escape a value into a TS3 compatible string

        @param value: Value
        @type value: string/int

        """

        if isinstance(value, int): return "%d" % value
        value = value.replace("\\", r'\\')
        for i, j in ts3_escape.iteritems():
            value = value.replace(i, j)
        return value

    @staticmethod
    def _unescape_str(value):
        """
        Unescape a TS3 compatible string into a normal string

        @param value: Value
        @type value: string/int

        """

        if isinstance(value, int): return "%d" % value
        value = value.replace(r"\\", "\\")
        for i, j in ts3_escape.iteritems():
            value = value.replace(j, i)
        return value


    def send(self, payload):
        if self._connected:
            self._log.debug('Sent: %s' % payload)
            self._sockfile.write(payload)


class TS3Server(TS3Proto):
    def __init__(self, ip, port, id=0, sock=None):
        """
        Abstraction class for TS3 Servers

        @param ip: IP Address
        @type ip: str
        @param port: Port Number
        @type port: int

        """
        TS3Proto.__init__(self)

        if not sock:
            if self.connect(ip, port) and id > 0:
                self.use(id)
        else:
            self._sock = sock
            self._sockfile = sock.makefile('r', 0)
            self._connected = True

    def login(self, username, password):
        """
        Login to the TS3 Server

        @param username: Username
        @type username: str
        @param password: Password
        @type password: str
        """
        d = p.send_command('login', keys={'client_login_name': username, 'client_login_password': password })
        if d > 0:
            self._log.error('Error logging in')
            return False
        elif d == 0:
            self._log.info('Login Successful')
            return True

    def serverlist(self):
        """
        Get a list of all Virtual Servers on the connected TS3 instance
        """
        if self._connected:
            return self.send_command('serverlist')

    def gm(self, msg):
        """
        Send a global message to the current Virtual Server

        @param msg: Message
        @type ip: str
        """
        if self._connected:
            return self.send_command('gm', keys={'msg': msg})

    def use(self, id):
        """
        Use a particular Virtual Server instance

        @param id: Virtual Server ID
        @type id: int
        """
        if self._connected and id > 0:
            self.send_command('use', keys={'sid': id})

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    p = TS3Server('188.165.51.239', 10011)
    p.login('serveradmin', 'Y6d5wqeo')
    print p.serverlist()
    p.gm('test')
    p.disconnect()

    #for bob in ts3_escape:
    #    print bob, ts3_escape[bob]
