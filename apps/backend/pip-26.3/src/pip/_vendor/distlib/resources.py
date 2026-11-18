ue  # Backwards compatibility

    @cached_property
    def resources(self):
        return self.finder.get_resources(self)


class ResourceFinder(object):
    """
    Resource finder for file system resources.
    """

    if sys.platform.startswith('java'):
        skipped_extensions = ('.pyc', '.pyo', '.class')
    else:
        skipped_extensions = ('.pyc', '.pyo')

    def __init__(self, module):
        self.module = module
        self.loader = getattr(module, '__loader__', None)
        self.base = os.path.dirname(getattr(module, '__file__', ''))

    def _adjust_path(self, path):
        return os.path.realpath(path)

    def _is_in_base(self, path):
        base = self._adjust_path(self.base)
        if path == base:
            return True
        if not base.endswith(os.sep):
            base = base + os.sep
        return path.startswith(base)

    def _make_path(self, resource_name):
        # Issue #50: need to preserve type of path on Python 2.x
        # like os.path._get_sep
        if isinstance(resource_name, bytes):  # should only happen on 2.x
            sep = b'/'
        else:
            sep = '/'
        parts = resource_name.split(sep)
        parts.insert(0, self.base)
        result = os.path.join(*parts)
        result = self._adjust_path(result)
        # See issue 263: code below commented out as it proved to be
        # too aggressively cautious, causing problems in valid use case scenarios.
        # Confine the resolved resource to the package base so a resource
        # name containing '..' cannot read files outside the package.
        # if not self._is_in_base(result):
            # raise DistlibException('Resource name escapes package: '
                                   # '%r' % resource_name)
        return result

    def _find(self, path):
        return os.path.exists(path)

    def get_cache_info(self, resource):
        return None, resource.path

    def find(self, resource_name):
        path = self._make_path(resource_name)
        if not self._find(path):
            result = None
        else:
            if self._is_directory(path):
                result = ResourceContainer(self, resource_name)
            else:
                result = Resource(self, resource_name)
            result.path = path
        return result

    def get_stream(self, resource):
        return open(resource.path, 'rb')

    def get_bytes(self, resource):
        with open(resource.path, 'rb') as f:
            return f.read()

    def get_size(self, resource):
        return os.path.getsize(resource.path)

    def get_resources(self, resource):

        def allowed(f):
            return (f != '__pycache__' and not f.endswith(self.skipped_extensions))

        return set([f for f in os.listdir(resource.path) if allowed(f)])

    def is_container(self, resource):
        return self._is_directory(resource.path)

    _is_directory = staticmethod(os.path.isdir)

    def iterator(self, resource_name):
        resource = self.find(resource_name)
        if resource is not None:
            todo = [resource]
            while todo:
                resource = todo.pop(0)
                yield resource
                if resource.is_container:
                    rname = resource.name
                    for name in resource.resources:
                        if not rname:
                            new_name = name
                        else:
                            new_name = '/'.join([rname, name])
                        child = self.find(new_name)
                        if child.is_container:
                            todo.append(child)
                        else:
                            yield child


class ZipResourceFinder(ResourceFinder):
    """
    Resource finder for resources in .zip files.
    """

    def __init__(self, module):
        super(ZipResourceFinder, self).__init__(module)
        archive = self.loader.archive
        self.prefix_len = 1 + len(archive)
        # PyPy doesn't have a _files attr on zipimporter, and you can't set one
        if hasattr(self.loader, '_files'):
            self._files = self.loader._files
        else:
            self._files = zipimport._zip_directory_cache[archive]
        self.index = sorted(self._files)

    def _adjust_path(self, path):
        return path

    def _find(self, path):
        path = path[self.prefix_len:]
        if path in self._files:
            result = True
        else:
            if path and path[-1] != os.sep:
                path = path + os.sep
            i = bisect.bisect(self.index, path)
            try:
                result = self.index[i].startswith(path)
            except IndexError:
                result = False
        if not result:
            logger.debug('_find failed: %r %r', path, self.loader.prefix)
        else:
            logger.debug('_find worked: %r %r', path, self.loader.prefix)
        return result

    def get_cache_info(self, resource):
        prefix = self.loader.archive
        path = resource.path[1 + len(prefix):]
        return prefix, path

    def get_bytes(self, resource):
        return self.loader.get_data(resource.path)

    def get_stream(self, resource):
        return io.BytesIO(self.get_bytes(resource))

    def get_size(self, resource):
        path = resource.path[self.prefix_len:]
        return self._files[path][3]

    def get_resources(self, resource):
        path = resource.path[self.prefix_len:]
        if path and path[-1] != os.sep:
            path += os.sep
        plen = len(path)
        result = set()
        i = bisect.bisect(self.index, path)
        while i < len(self.index):
            if not self.index[i].startswith(path):
                break
            s = self.index[i][plen:]
            result.add(s.split(os.sep, 1)[0])  # only immediate children
            i += 1
        return result

    def _is_directory(self, path):
        path = path[self.prefix_len:]
        if path and path[-1] != os.sep:
            path += os.sep
        i = bisect.bisect(self.index, path)
        try:
            result = self.index[i].startswith(path)
        except IndexError:
            result = False
        return result


_finder_registry = {type(None): ResourceFinder, zipimport.zipimporter: ZipResourceFinder}

try:
    # In Python 3.6, _frozen_importlib -> _frozen_importlib_external
    try:
        import _frozen_importlib_external as _fi
    except ImportError:
        import _frozen_importlib as _fi
    _finder_registry[_fi.SourceFileLoader] = ResourceFinder
    _finder_registry[_fi.FileFinder] = ResourceFinder
    # See issue #146
    _finder_registry[_fi.SourcelessFileLoader] = ResourceFinder
    del _fi
except (ImportError, AttributeError):
    pass


def register_finder(loader, finder_maker):
    _finder_registry[type(loader)] = finder_maker


_finder_cache = {}


def finder(package):
    """
    Return a resource finder for a package.
    :param package: The name of the package.
    :return: A :class:`ResourceFinder` instance for the package.
    """
    if package in _finder_cache:
        result = _finder_cache[package]
    else:
        if package not in sys.modules:
            __import__(package)
        module = sys.modules[package]
        path = getattr(module, '__path__', None)
        if path is None:
            raise DistlibException('You cannot get a finder for a module, '
                                   'only for a package')
        loader = getattr(module, '__loader__', None)
        finder_maker = _finder_registry.get(type(loader))
        if finder_maker is None:
            raise DistlibException('Unable to locate finder for %r' % package)
        result = finder_maker(module)
        _finder_cache[package] = result
    return result


_dummy_module = types.ModuleType(str('__dummy__'))


def finder_for_path(path):
    """
    Return a resource finder for a path, which should represent a container.

    :param path: The path.
    :return: A :class:`ResourceFinder` instance for the path.
    """
    result = None
    # calls any path hooks, gets importer into cache
    pkgutil.get_importer(path)
    loader = sys.path_importer_cache.get(path)
    finder = _finder_registry.get(type(loader))
    if finder:
        module = _dummy_module
        module.__file__ = os.path.join(path, '')
        module.__loader__ = loader
        result = finder(module)
    return result
