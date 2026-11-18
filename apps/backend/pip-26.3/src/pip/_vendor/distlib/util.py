    kwargs = {}
            kwargs['timeout'] = self.timeout
            if not self._connection or host != self._connection[0]:
                self._extra_headers = eh
                self._connection = host, httplib.HTTPSConnection(h, None, **kwargs)
            return self._connection[1]


class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, uri, **kwargs):
        self.timeout = timeout = kwargs.pop('timeout', None)
        # The above classes only come into play if a timeout
        # is specified
        if timeout is not None:
            # scheme = splittype(uri)  # deprecated as of Python 3.8
            scheme = urlparse(uri)[0]
            use_datetime = kwargs.get('use_datetime', 0)
            if scheme == 'https':
                tcls = SafeTransport
            else:
                tcls = Transport
            kwargs['transport'] = t = tcls(timeout, use_datetime=use_datetime)
            self.transport = t
        xmlrpclib.ServerProxy.__init__(self, uri, **kwargs)


#
# CSV functionality. This is provided because on 2.x, the csv module can't
# handle Unicode. However, we need to deal with Unicode in e.g. RECORD files.
#


def _csv_open(fn, mode, **kwargs):
    if sys.version_info[0] < 3:
        mode += 'b'
    else:
        kwargs['newline'] = ''
        # Python 3 determines encoding from locale. Force 'utf-8'
        # file encoding to match other forced utf-8 encoding
        kwargs['encoding'] = 'utf-8'
    return open(fn, mode, **kwargs)


class CSVBase(object):
    defaults = {
        'delimiter': str(','),  # The strs are used because we need native
        'quotechar': str('"'),  # str in the csv API (2.x won't take
        'lineterminator': str('\n')  # Unicode)
    }

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.stream.close()


class CSVReader(CSVBase):

    def __init__(self, **kwargs):
        if 'stream' in kwargs:
            stream = kwargs['stream']
            if sys.version_info[0] >= 3:
                # needs to be a text stream
                stream = codecs.getreader('utf-8')(stream)
            self.stream = stream
        else:
            self.stream = _csv_open(kwargs['path'], 'r')
        self.reader = csv.reader(self.stream, **self.defaults)

    def __iter__(self):
        return self

    def next(self):
        result = next(self.reader)
        if sys.version_info[0] < 3:
            for i, item in enumerate(result):
                if not isinstance(item, text_type):
                    result[i] = item.decode('utf-8')
        return result

    __next__ = next


class CSVWriter(CSVBase):

    def __init__(self, fn, **kwargs):
        self.stream = _csv_open(fn, 'w')
        self.writer = csv.writer(self.stream, **self.defaults)

    def writerow(self, row):
        if sys.version_info[0] < 3:
            r = []
            for item in row:
                if isinstance(item, text_type):
                    item = item.encode('utf-8')
                r.append(item)
            row = r
        self.writer.writerow(row)


#
#   Configurator functionality
#


class Configurator(BaseConfigurator):

    value_converters = dict(BaseConfigurator.value_converters)
    value_converters['inc'] = 'inc_convert'

    def __init__(self, config, base=None):
        super(Configurator, self).__init__(config)
        self.base = base or os.getcwd()

    def configure_custom(self, config):

        def convert(o):
            if isinstance(o, (list, tuple)):
                result = type(o)([convert(i) for i in o])
            elif isinstance(o, dict):
                if '()' in o:
                    result = self.configure_custom(o)
                else:
                    result = {}
                    for k in o:
                        result[k] = convert(o[k])
            else:
                result = self.convert(o)
            return result

        c = config.pop('()')
        if not callable(c):
            c = self.resolve(c)
        props = config.pop('.', None)
        # Check for valid identifiers
        args = config.pop('[]', ())
        if args:
            args = tuple([convert(o) for o in args])
        items = [(k, convert(config[k])) for k in config if valid_ident(k)]
        kwargs = dict(items)
        result = c(*args, **kwargs)
        if props:
            for n, v in props.items():
                setattr(result, n, convert(v))
        return result

    def __getitem__(self, key):
        result = self.config[key]
        if isinstance(result, dict) and '()' in result:
            self.config[key] = result = self.configure_custom(result)
        return result

    def inc_convert(self, value):
        """Default converter for the inc:// protocol."""
        if not os.path.isabs(value):
            value = os.path.join(self.base, value)
        with codecs.open(value, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return result


class SubprocessMixin(object):
    """
    Mixin for running subprocesses and capturing their output
    """

    def __init__(self, verbose=False, progress=None):
        self.verbose = verbose
        self.progress = progress

    def reader(self, stream, context):
        """
        Read lines from a subprocess' output stream and either pass to a progress
        callable (if specified) or write progress information to sys.stderr.
        """
        progress = self.progress
        verbose = self.verbose
        while True:
            s = stream.readline()
            if not s:
                break
            if progress is not None:
                progress(s, context)
            else:
                if not verbose:
                    sys.stderr.write('.')
                else:
                    sys.stderr.write(s.decode('utf-8'))
                sys.stderr.flush()
        stream.close()

    def run_command(self, cmd, **kwargs):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        t1 = threading.Thread(target=self.reader, args=(p.stdout, 'stdout'))
        t1.start()
        t2 = threading.Thread(target=self.reader, args=(p.stderr, 'stderr'))
        t2.start()
        p.wait()
        t1.join()
        t2.join()
        if self.progress is not None:
            self.progress('done.', 'main')
        elif self.verbose:
            sys.stderr.write('done.\n')
        return p


def normalize_name(name):
    """Normalize a python package name a la PEP 503"""
    # https://peps.python.org/pep-0503/#normalized-names
    # Emulates re.sub(r"[-_.]+", "-", name).lower()
    # Much faster than re, and even faster than str.translate
    value = name.lower().replace("_", "-").replace(".", "-")
    while "--" in value:
        value = value.replace("--", "-")
    return value


# def _get_pypirc_command():
# """
# Get the distutils command for interacting with PyPI configurations.
# :return: the command.
# """
# from distutils.core import Distribution
# from distutils.config import PyPIRCCommand
# d = Distribution()
# return PyPIRCCommand(d)


class PyPIRCFile(object):

    DEFAULT_REPOSITORY = 'https://upload.pypi.org/legacy/'
    DEFAULT_REALM = 'pypi'

    def __init__(self, fn=None, url=None):
        if fn is None:
            fn = os.path.join(os.path.expanduser('~'), '.pypirc')
        self.filename = fn
        self.url = url

    def read(self):
        result = {}

        if os.path.exists(self.filename):
            repository = self.url or self.DEFAULT_REPOSITORY

            config = configparser.RawConfigParser()
            config.read(self.filename)
            sections = config.sections()
            if 'distutils' in sections:
                # let's get the list of servers
                index_servers = config.get('distutils', 'index-servers')
                _servers = [server.strip() for server in index_servers.split('\n') if server.strip() != '']
                if _servers == []:
                    # nothing set, let's try to get the default pypi
                    if 'pypi' in sections:
                        _servers = ['pypi']
                else:
                    for server in _servers:
                        result = {'server': server}
                        result['username'] = config.get(server, 'username')

                        # optional params
                        for key, default in (('repository', self.DEFAULT_REPOSITORY), ('realm', self.DEFAULT_REALM),
                                             ('password', None)):
                            if config.has_option(server, key):
                                result[key] = config.get(server, key)
                            else:
                                result[key] = default

                        # work around people having "repository" for the "pypi"
                        # section of their config set to the HTTP (rather than
                        # HTTPS) URL
                        if (server == 'pypi' and repository in (self.DEFAULT_REPOSITORY, 'pypi')):
                            result['repository'] = self.DEFAULT_REPOSITORY
                        elif (result['server'] != repository and result['repository'] != repository):
                            result = {}
            elif 'server-login' in sections:
                # old format
                server = 'server-login'
                if config.has_option(server, 'repository'):
                    repository = config.get(server, 'repository')
                else:
                    repository = self.DEFAULT_REPOSITORY
                result = {
                    'username': config.get(server, 'username'),
                    'password': config.get(server, 'password'),
                    'repository': repository,
                    'server': server,
                    'realm': self.DEFAULT_REALM
                }
        return result

    def update(self, username, password):
        # import pdb; pdb.set_trace()
        config = configparser.RawConfigParser()
        fn = self.filename
        config.read(fn)
        if not config.has_section('pypi'):
            config.add_section('pypi')
        config.set('pypi', 'username', username)
        config.set('pypi', 'password', password)
        with open(fn, 'w') as f:
            config.write(f)


def _load_pypirc(index):
    """
    Read the PyPI access configuration as supported by distutils.
    """
    return PyPIRCFile(url=index.url).read()


def _store_pypirc(index):
    PyPIRCFile().update(index.username, index.password)


#
# get_platform()/get_host_platform() copied from Python 3.10.a0 source, with some minor
# tweaks
#


def get_host_platform():
    """Return a string that identifies the current platform.  This is used mainly to
    distinguish platform-specific build directories and platform-specific built
    distributions.  Typically includes the OS name and version and the
    architecture (as supplied by 'os.uname()'), although the exact information
    included depends on the OS; eg. on Linux, the kernel version isn't
    particularly important.

    Examples of returned values:
       linux-i586
       linux-alpha (?)
       solaris-2.6-sun4u

    Windows will return one of:
       win-amd64 (64bit Windows on AMD64 (aka x86_64, Intel64, EM64T, etc)
       win32 (all others - specifically, sys.platform is returned)

    For other non-POSIX platforms, currently just returns 'sys.platform'.

    """
    if os.name == 'nt':
        if 'amd64' in sys.version.lower():
            return 'win-amd64'
        if '(arm)' in sys.version.lower():
            return 'win-arm32'
        if '(arm64)' in sys.version.lower():
            return 'win-arm64'
        return sys.platform

    # Set for cross builds explicitly
    if "_PYTHON_HOST_PLATFORM" in os.environ:
        return os.environ["_PYTHON_HOST_PLATFORM"]

    if os.name != 'posix' or not hasattr(os, 'uname'):
        # XXX what about the architecture? NT is Intel or Alpha,
        # Mac OS is M68k or PPC, etc.
        return sys.platform

    # Try to distinguish various flavours of Unix

    (osname, host, release, version, machine) = os.uname()

    # Convert the OS name to lowercase, remove '/' characters, and translate
    # spaces (for "Power Macintosh")
    osname = osname.lower().replace('/', '')
    machine = machine.replace(' ', '_').replace('/', '-')

    if osname[:5] == 'linux':
        # At least on Linux/Intel, 'machine' is the processor --
        # i386, etc.
        # XXX what about Alpha, SPARC, etc?
        return "%s-%s" % (osname, machine)

    elif osname[:5] == 'sunos':
        if release[0] >= '5':  # SunOS 5 == Solaris 2
            osname = 'solaris'
            release = '%d.%s' % (int(release[0]) - 3, release[2:])
            # We can't use 'platform.architecture()[0]' because a
            # bootstrap problem. We use a dict to get an error
            # if some suspicious happens.
            bitness = {2147483647: '32bit', 9223372036854775807: '64bit'}
            machine += '.%s' % bitness[sys.maxsize]
        # fall through to standard osname-release-machine representation
    elif osname[:3] == 'aix':
        from _aix_support import aix_platform
        return aix_platform()
    elif osname[:6] == 'cygwin':
        osname = 'cygwin'
        rel_re = re.compile(r'[\d.]+', re.ASCII)
        m = rel_re.match(release)
        if m:
            release = m.group()
    elif osname[:6] == 'darwin':
        import _osx_support
        try:
            from distutils import sysconfig
        except ImportError:
            import sysconfig
        osname, release, machine = _osx_support.get_platform_osx(sysconfig.get_config_vars(), osname, release, machine)

    return '%s-%s-%s' % (osname, release, machine)


_TARGET_TO_PLAT = {
    'x86': 'win32',
    'x64': 'win-amd64',
    'arm': 'win-arm32',
}


def get_platform():
    if os.name != 'nt':
        return get_host_platform()
    cross_compilation_target = os.environ.get('VSCMD_ARG_TGT_ARCH')
    if cross_compilation_target not in _TARGET_TO_PLAT:
        return get_host_platform()
    return _TARGET_TO_PLAT[cross_compilation_target]


def is_in_directory(path, target):
    """
    Check if a path is inside a target directory. This doesn't check case (might be an issue on Windows)
    """
    path = os.path.abspath(path)
    target = os.path.abspath(target)
    return path == target or path.startswith(target + os.sep)
