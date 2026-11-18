  True
        >>> Version("1.2.3") in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.0.1" in SpecifierSet(">=1.0.0,!=1.0.1")
        False
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1")
        True
        >>> "1.3.0a1" in SpecifierSet(">=1.0.0,!=1.0.1", prereleases=True)
        True
        """
        return self.contains(item)

    def contains(
        self,
        item: UnparsedVersion,
        prereleases: bool | None = None,
        installed: bool | None = None,
    ) -> bool:
        """Return whether or not the item is contained in this SpecifierSet.

        :param item:
            The item to check for, which can be a version string or a
            :class:`~packaging.version.Version` instance.
        :param prereleases:
            Whether or not to match prereleases with this SpecifierSet. If set to
            ``None`` (the default), it will follow the recommendation from :pep:`440`
            and match prereleases, as there are no other versions.
        :param installed:
            Whether or not the item is installed. If set to ``True``, it will
            accept prerelease versions even if the specifier does not allow them.

        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.2.3")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains(Version("1.2.3"))
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.0.1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1")
        True
        >>> SpecifierSet(">=1.0.0,!=1.0.1", prereleases=False).contains("1.3.0a1")
        False
        >>> SpecifierSet(">=1.0.0,!=1.0.1").contains("1.3.0a1", prereleases=True)
        True

        .. versionchanged:: 26.0

            With ``prereleases=None``, a prerelease now matches. A single
            version has no alternatives, so the :pep:`440` rule to accept
            prereleases when nothing else satisfies the specifiers applies.
            Earlier versions rejected it. An unparsable version now returns
            ``False`` instead of raising :exc:`~packaging.version.InvalidVersion`.
        """
        version = coerce_version(item)

        if version is not None and installed and version.is_prerelease:
            prereleases = True

        # When item is a string and === is involved, keep it as-is
        # so the comparison isn't done against the normalized form.
        if version is None or (self._has_arbitrary and not isinstance(item, Version)):
            check_item = item
        else:
            check_item = version

        # Fast path: a parseable, local-free version against a rangelike set.
        # A local on ``version`` needs PEP 440 stripping that the range path
        # applies.
        if (
            version is not None
            and not self._has_arbitrary
            and version.local is None
            and self._specs
        ):
            if version.is_prerelease and (
                prereleases is False
                or (prereleases is None and self._prereleases is False)
            ):
                return False

            bounds = self._ranges
            if bounds is None:
                # Per-spec ``_fast_match`` answers a set of simple specifiers
                # without folding anything. If a spec needs the range path,
                # fold the intersected bounds once and cache them so repeated
                # checks on the same set stay cheap.
                for spec in self._specs:
                    match = _fast_match(spec, version)
                    if match is None:
                        break
                    if not match:
                        return False
                else:
                    return True

                bounds = self._ranges = self._get_ranges()

            return matches_bounds_only(bounds, version)

        return bool(list(self.filter([check_item], prereleases=prereleases)))

    @typing.overload
    def filter(
        self,
        iterable: Iterable[UnparsedVersionVar],
        prereleases: bool | None = None,
        key: None = ...,
    ) -> Iterator[UnparsedVersionVar]: ...

    @typing.overload
    def filter(
        self,
        iterable: Iterable[T],
        prereleases: bool | None = None,
        key: Callable[[T], UnparsedVersion] = ...,
    ) -> Iterator[T]: ...

    def filter(
        self,
        iterable: Iterable[Any],
        prereleases: bool | None = None,
        key: Callable[[Any], UnparsedVersion] | None = None,
    ) -> Iterator[Any]:
        """Filter items in the given iterable, that match the specifiers in this set.

        :param iterable:
            An iterable that can contain version strings and
            :class:`~packaging.version.Version` instances. The items in the
            iterable will be filtered according to the specifier.
        :param prereleases:
            Whether or not to allow prereleases in the returned iterator. If set to
            ``None`` (the default), it will follow the recommendation from :pep:`440`
            and match prereleases if there are no other versions.
        :param key:
            A callable that takes a single argument (an item from the iterable) and
            returns a version string or :class:`~packaging.version.Version`
            instance to be used for filtering.

        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.3", Version("1.4")]))
        ['1.3', <Version('1.4')>]
        >>> list(SpecifierSet(">=1.2.3").filter(["1.2", "1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet(">=1.2.3").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet(">=1.2.3").filter(
        ... [{"ver": "1.2"}, {"ver": "1.3"}],
        ... key=lambda x: x["ver"]))
        [{'ver': '1.3'}]

        An "empty" SpecifierSet will filter items based on the presence of prerelease
        versions in the set.

        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"]))
        ['1.3']
        >>> list(SpecifierSet("").filter(["1.5a1"]))
        ['1.5a1']
        >>> list(SpecifierSet("", prereleases=True).filter(["1.3", "1.5a1"]))
        ['1.3', '1.5a1']
        >>> list(SpecifierSet("").filter(["1.3", "1.5a1"], prereleases=True))
        ['1.3', '1.5a1']

        .. versionchanged:: 26.0

            Prerelease filtering now follows the PEP 440 recommendation of
            yielding prereleases only when no final release is present.

        .. versionchanged:: 26.1

            Added the ``key`` parameter.
        """
        # Determine if we're forcing a prerelease or not, if we're not forcing
        # one for this particular filter call, then we'll use whatever the
        # SpecifierSet thinks for whether or not we should support prereleases.
        if prereleases is None and self.prereleases is not None:
            prereleases = self.prereleases

        if self._specs:
            if self._has_arbitrary:
                # Slow path for ===
                specs = self._specs
                matches = (
                    item
                    for item in iterable
                    if all(
                        s.contains(item if key is None else key(item), prereleases=True)
                        for s in specs
                    )
                )
                return _apply_prereleases_filter(matches, key, prereleases)

            ranges = self._ranges
            if ranges is None:
                ranges = self._get_ranges()
            return filter_by_ranges(ranges, iterable, key, prereleases)

        # Empty SpecifierSet.
        return _apply_prereleases_filter(iterable, key, prereleases)


def _pep440_filter_prereleases(
    iterable: Iterable[Any], key: Callable[[Any], UnparsedVersion] | None
) -> Iterator[Any]:
    """Filter per PEP 440: exclude prereleases unless no finals exist."""
    # Two lists used:
    #   * all_nonfinal to preserve order if no finals exist
    #   * arbitrary_strings for streaming when first final found
    all_nonfinal: list[Any] = []
    arbitrary_strings: list[Any] = []

    found_final = False
    for item in iterable:
        parsed = coerce_version(item if key is None else key(item))

        if parsed is None:
            # Arbitrary strings are always included as it is not
            # possible to determine if they are prereleases,
            # and they have already passed all specifiers.
            if found_final:
                yield item
            else:
                arbitrary_strings.append(item)
                all_nonfinal.append(item)
            continue

        if not parsed.is_prerelease:
            # Final release found - flush arbitrary strings, then yield
            if not found_final:
                yield from arbitrary_strings
                found_final = True
            yield item
            continue

        # Prerelease - buffer if no finals yet, otherwise skip
        if not found_final:
            all_nonfinal.append(item)

    # No finals found - yield all buffered items
    if not found_final:
        yield from all_nonfinal
