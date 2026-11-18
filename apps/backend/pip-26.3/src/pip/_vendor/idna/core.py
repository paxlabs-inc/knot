:
            continue
        elif status == _STATUS_IGNORED:
            replacement = None
        else:
            raise InvalidCodepoint(
                f"Codepoint {_unot(code_point)} not allowed at position {pos + 1} in {domain!r}",
                code="uts46_disallowed",
                text=domain,
                codepoint=code_point,
                position=pos + 1,
            )
        if start < pos:
            run = domain[start:pos]
            if std3_rules:
                _check_std3(run, domain, start)
            output.append(run)
        if replacement:
            if std3_rules and _std3_disallowed_re.search(replacement):
                raise InvalidCodepoint(
                    f"Codepoint {_unot(code_point)} not allowed at position {pos + 1} in {domain!r}",
                    code="uts46_std3",
                    text=domain,
                    codepoint=code_point,
                    position=pos + 1,
                )
            output.append(replacement)
        start = pos + 1

    if start == 0:
        if std3_rules:
            _check_std3(domain, domain, 0)
        return unicodedata.normalize("NFC", domain)
    tail = domain[start:]
    if std3_rules:
        _check_std3(tail, domain, start)
    output.append(tail)
    return unicodedata.normalize("NFC", "".join(output))


def encode(
    s: str | bytes | bytearray,
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
    transitional: bool = False,
) -> bytes:
    """Encode a Unicode domain name into its ASCII (A-label) form.

    Splits the input on label separators (only ``U+002E`` if ``strict`` is
    set; otherwise also IDEOGRAPHIC FULL STOP ``U+3002``, FULLWIDTH FULL
    STOP ``U+FF0E``, and HALFWIDTH IDEOGRAPHIC FULL STOP ``U+FF61``),
    encodes each label with :func:`alabel`, and rejoins them with ``.``.
    Optionally pre-processes the input through :func:`uts46_remap`.

    :param s: The domain name to encode.
    :param strict: If ``True``, only ``U+002E`` is recognised as a label
        separator.
    :param uts46: If ``True``, apply UTS #46 mapping before encoding.
    :param std3_rules: Forwarded to :func:`uts46_remap` when ``uts46`` is
        ``True``.
    :param transitional: Deprecated and ignored (see :func:`uts46_remap`):
        emits a :class:`DeprecationWarning` and will be removed in a
        future version.
    :returns: The encoded domain as ASCII :class:`bytes`.
    :raises IDNAError: If the domain is empty, contains an invalid label,
        or exceeds the maximum domain length.
    """
    if transitional:
        _warn_transitional()
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except (UnicodeDecodeError, TypeError) as err:
            raise IDNAError(
                "should pass a unicode string to the function rather than a byte string.", code="invalid_ascii"
            ) from err
    if len(s) > _max_input_length:
        raise IDNAError("Domain too long", code="input_too_long")
    if uts46:
        s = uts46_remap(s, std3_rules)

    if not valid_string_length(s, trailing_dot=True):
        raise IDNAError("Domain too long", code="domain_too_long")

    trailing_dot = False
    result = []
    labels = s.split(".") if strict else _unicode_dots_re.split(s)
    if not labels or labels == [""]:
        raise IDNAError("Empty domain", code="empty_domain")
    if labels[-1] == "":
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = alabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label", code="empty_label")
    if trailing_dot:
        result.append(b"")
    s = b".".join(result)
    if not valid_string_length(s, trailing_dot):
        raise IDNAError("Domain too long", code="domain_too_long")
    return s


def decode(
    s: str | bytes | bytearray,
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
    display: bool = False,
) -> str:
    """Decode an A-label-encoded domain name back to Unicode.

    Splits the input on label separators (see :func:`encode` for the
    rules), decodes each label with :func:`ulabel`, and rejoins them
    with ``.``. Optionally pre-processes the input through
    :func:`uts46_remap`.

    :param s: The domain name to decode.
    :param strict: If ``True``, only ``U+002E`` is recognised as a label
        separator.
    :param uts46: If ``True``, apply UTS #46 mapping before decoding.
    :param std3_rules: Forwarded to :func:`uts46_remap` when ``uts46`` is
        ``True``.
    :param display: If ``True``, any ``xn--`` label that fails IDNA
        validation is passed through unchanged (lowercased) rather than
        aborting the whole call. Intended for "decode for display"
        consumers (e.g. URL libraries, HTTP clients) that want to show
        the user the label as it appears on the wire when it cannot be
        rendered as Unicode. Matches the per-label recovery prescribed
        by UTS #46 §4 and the WHATWG URL "domain to Unicode" algorithm.
    :returns: The decoded domain as a Unicode string.
    :raises IDNAError: If the input is not valid ASCII, contains an
        invalid label, or is empty.
    """
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except (UnicodeDecodeError, TypeError) as err:
            raise IDNAError("Invalid ASCII in A-label", code="invalid_ascii") from err
    if len(s) > _max_input_length:
        raise IDNAError("Domain too long", code="input_too_long")
    if uts46:
        s = uts46_remap(s, std3_rules, False)
    if not valid_string_length(s, trailing_dot=True):
        raise IDNAError("Domain too long", code="domain_too_long")
    trailing_dot = False
    result = []
    labels = s.split(".") if strict else _unicode_dots_re.split(s)
    if not labels or labels == [""]:
        raise IDNAError("Empty domain", code="empty_domain")
    if not labels[-1]:
        del labels[-1]
        trailing_dot = True
    for label in labels:
        try:
            u = ulabel(label)
        except IDNAError:
            if display and label[:4].lower() == "xn--":
                u = label.lower()
            else:
                raise
        if u:
            result.append(u)
        else:
            raise IDNAError("Empty label", code="empty_label")
    if trailing_dot:
        result.append("")
    return ".".join(result)
