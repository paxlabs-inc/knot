arget)
    if not match:  # Defensive:
        raise LocationParseError(f"{target!r} is not a valid request URI")

    path, query = match.groups()
    encoded_target = _encode_invalid_chars(path, _PATH_CHARS)
    if query is not None:
        query = _encode_invalid_chars(query, _QUERY_CHARS)
        encoded_target += "?" + query
    return encoded_target


def parse_url(url: str) -> Url:
    """
    Given a url, return a parsed :class:`.Url` namedtuple. Best-effort is
    performed to parse incomplete urls. Fields not provided will be None.
    This parser is RFC 3986 and RFC 6874 compliant.

    The parser logic and helper functions are based heavily on
    work done in the ``rfc3986`` module.

    :param str url: URL to parse into a :class:`.Url` namedtuple.

    Partly backwards-compatible with :mod:`urllib.parse`.

    Example:

    .. code-block:: python

        from pip._vendor import urllib3

        print( urllib3.util.parse_url('http://google.com/mail/'))
        # Url(scheme='http', host='google.com', port=None, path='/mail/', ...)

        print( urllib3.util.parse_url('google.com:80'))
        # Url(scheme=None, host='google.com', port=80, path=None, ...)

        print( urllib3.util.parse_url('/foo?bar'))
        # Url(scheme=None, host=None, port=None, path='/foo', query='bar', ...)
    """
    if not url:
        # Empty
        return Url()

    if not _SCHEME_RE.search(url):
        url = "//" + url

    scheme: str | None
    authority: str | None
    auth: str | None
    host: str | None
    port: str | None
    port_int: int | None
    path: str | None
    query: str | None
    fragment: str | None

    scheme, authority, path, query, fragment = _URI_RE.match(url).groups()  # type: ignore[union-attr]
    normalize_uri = scheme is None or scheme.lower() in _NORMALIZABLE_SCHEMES

    if scheme:
        scheme = scheme.lower()

    if authority:
        auth, _, host_port = authority.rpartition("@")
        auth = auth or None
        host_port_match = _HOST_PORT_RE.fullmatch(host_port)
        if not host_port_match:
            invalid_host_char = _HOST_INVALID_CHAR_RE.search(host_port)
            if invalid_host_char:
                raise LocationParseError(
                    f"Host {host_port!r} contains invalid character "
                    f"{invalid_host_char.group()!r}"
                )
            raise LocationParseError(f"{host_port!r} is not a valid host or port")
        host, port = host_port_match.groups()
        if auth and normalize_uri:
            auth = _encode_invalid_chars(auth, _USERINFO_CHARS)
        if port == "":
            port = None
    else:
        auth, host, port = None, None, None

    if port is not None:
        port_int = int(port)
        if not (0 <= port_int <= 65535):
            raise LocationParseError(url)
    else:
        port_int = None

    host = _normalize_host(host, scheme)

    if normalize_uri and path:
        path = _remove_path_dot_segments(path)
        path = _encode_invalid_chars(path, _PATH_CHARS)
    if normalize_uri and query:
        query = _encode_invalid_chars(query, _QUERY_CHARS)
    if normalize_uri and fragment:
        fragment = _encode_invalid_chars(fragment, _FRAGMENT_CHARS)

    # For the sake of backwards compatibility we put empty
    # string values for path if there are any defined values
    # beyond the path in the URL.
    # TODO: Remove this when we break backwards compatibility.
    if not path:
        if query is not None or fragment is not None:
            path = ""
        else:
            path = None

    return Url(
        scheme=scheme,
        auth=auth,
        host=host,
        port=port_int,
        path=path,
        query=query,
        fragment=fragment,
    )
