s* and the cell length of the entire string. A span is a list of tuples
            of three values consisting of (<START>, <END>, <CELL LENGTH>), where START and END are string indices,
            and CELL LENGTH is the cell length of the single grapheme.
    """

    cell_table = load_cell_table(unicode_version)
    codepoint_count = len(text)
    index = 0
    last_measured_character: str | None = None

    total_width = 0
    spans: list[tuple[int, int, int]] = []
    SPECIAL = {"\u200d", "\ufe0f"}
    while index < codepoint_count:
        if (character := text[index]) in SPECIAL:
            if not spans:
                # ZWJ or variation selector at the beginning of the string doesn't really make sense.
                # But handle it, we must.
                spans.append((index, index := index + 1, 0))
                continue
            if character == "\u200d":
                # zero width joiner
                # The condition handles the case where a ZWJ is at the end of the string, and has nothing to join
                index += 2 if index < (codepoint_count - 1) else 1
                start, _end, cell_length = spans[-1]
                spans[-1] = (start, index, cell_length)
            else:
                # variation selector 16
                index += 1
                if last_measured_character:
                    start, _end, cell_length = spans[-1]
                    if last_measured_character in cell_table.narrow_to_wide:
                        last_measured_character = None
                        cell_length += 1
                        total_width += 1
                    spans[-1] = (start, index, cell_length)
                else:
                    # No previous character to change the size of.
                    # Shouldn't occur in practice.
                    # But handle it, we must.
                    start, _end, cell_length = spans[-1]
                    spans[-1] = (start, index, cell_length)
            continue

        if character_width := get_character_cell_size(character, unicode_version):
            last_measured_character = character
            spans.append((index, index := index + 1, character_width))
            total_width += character_width
        else:
            # Character has zero width
            if spans:
                # zero width characters are associated with the previous character
                start, _end, cell_length = spans[-1]
                spans[-1] = (start, index := index + 1, cell_length)
            else:
                # A zero width character with no prior spans
                spans.append((index, index := index + 1, 0))

    return (spans, total_width)


def _split_text(
    text: str, cell_position: int, unicode_version: str = "auto"
) -> tuple[str, str]:
    """Split text by cell position.

    If the cell position falls within a double width character, it is converted to two spaces.

    Args:
        text: Text to split.
        cell_position Offset in cells.
        unicode_version: Unicode version, `"auto"` to auto detect, `"latest"` for the latest unicode version.

    Returns:
        Tuple to two split strings.
    """
    if cell_position <= 0:
        return "", text

    spans, cell_length = split_graphemes(text, unicode_version)

    # Guess initial offset
    offset = int((cell_position / cell_length) * len(spans))
    left_size = sum(map(_span_get_cell_len, spans[:offset]))

    while True:
        if left_size == cell_position:
            if offset >= len(spans):
                return text, ""
            split_index = spans[offset][0]
            return text[:split_index], text[split_index:]
        if left_size < cell_position:
            start, end, cell_size = spans[offset]
            if left_size + cell_size > cell_position:
                return text[:start] + " ", " " + text[end:]
            offset += 1
            left_size += cell_size
        else:  # left_size > cell_position
            start, end, cell_size = spans[offset - 1]
            if left_size - cell_size < cell_position:
                return text[:start] + " ", " " + text[end:]
            offset -= 1
            left_size -= cell_size


def split_text(
    text: str, cell_position: int, unicode_version: str = "auto"
) -> tuple[str, str]:
    """Split text by cell position.

    If the cell position falls within a double width character, it is converted to two spaces.

    Args:
        text: Text to split.
        cell_position Offset in cells.
        unicode_version: Unicode version, `"auto"` to auto detect, `"latest"` for the latest unicode version.

    Returns:
        Tuple to two split strings.
    """
    if _is_single_cell_widths(text):
        return text[:cell_position], text[cell_position:]
    return _split_text(text, cell_position, unicode_version)


def set_cell_size(text: str, total: int, unicode_version: str = "auto") -> str:
    """Adjust a string by cropping or padding with spaces such that it fits within the given number of cells.

    Args:
        text: String to adjust.
        total: Desired size in cells.
        unicode_version: Unicode version.

    Returns:
        A string with cell size equal to total.
    """
    if _is_single_cell_widths(text):
        size = len(text)
        if size < total:
            return text + " " * (total - size)
        return text[:total]
    if total <= 0:
        return ""
    cell_size = cell_len(text)
    if cell_size == total:
        return text
    if cell_size < total:
        return text + " " * (total - cell_size)
    text, _ = _split_text(text, total, unicode_version)
    return text


def chop_cells(text: str, width: int, unicode_version: str = "auto") -> list[str]:
    """Split text into lines such that each line fits within the available (cell) width.

    Args:
        text: The text to fold such that it fits in the given width.
        width: The width available (number of cells).

    Returns:
        A list of strings such that each string in the list has cell width
        less than or equal to the available width.
    """
    if _is_single_cell_widths(text):
        return [text[index : index + width] for index in range(0, len(text), width)]
    spans, _ = split_graphemes(text, unicode_version)
    line_size = 0  # Size of line in cells
    lines: list[str] = []
    line_offset = 0  # Offset (in codepoints) of start of line
    for start, end, cell_size in spans:
        if line_size + cell_size > width:
            lines.append(text[line_offset:start])
            line_offset = start
            line_size = 0
        line_size += cell_size
    if line_size:
        lines.append(text[line_offset:])

    return lines
