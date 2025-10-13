from dataclasses import dataclass


@dataclass(frozen=True)
class CxStatTheme:
    """Colour palette applied across CLI tables and messages."""

    header_style: str
    label_style: str
    highlight_label_style: str
    total_style: str
    input_style: str
    output_style: str
    count_style: str
    info_style: str
    warning_style: str
    accent_style: str
    row_styles: tuple[str, ...] | None = None

THEMES: dict[str, CxStatTheme] = {
    "default": CxStatTheme(
        header_style="bold cyan",
        label_style="white",
        highlight_label_style="bold white",
        total_style="green",
        input_style="white",
        output_style="white",
        count_style="yellow",
        info_style="bold white",
        warning_style="yellow",
        accent_style="bold",
        row_styles=None,
    ),
    "contrast": CxStatTheme(
        header_style="bold magenta",
        label_style="white",
        highlight_label_style="bold magenta",
        total_style="bright_cyan",
        input_style="white",
        output_style="white",
        count_style="bright_yellow",
        info_style="bold bright_white",
        warning_style="bright_yellow",
        accent_style="bold magenta",
        row_styles=("none", "dim"),
    ),
    "mono": CxStatTheme(
        header_style="bold white",
        label_style="white",
        highlight_label_style="bold white",
        total_style="white",
        input_style="white",
        output_style="white",
        count_style="white",
        info_style="bold white",
        warning_style="white",
        accent_style="bold white",
        row_styles=None,
    ),
    "monokai": CxStatTheme(
        header_style="bold #66D9EF",
        label_style="#F8F8F2",
        highlight_label_style="bold #AE81FF",
        total_style="#A6E22E",
        input_style="#E6DB74",
        output_style="#66D9EF",
        count_style="#FD971F",
        info_style="#F8F8F2",
        warning_style="#F92672",
        accent_style="bold #F92672",
        row_styles=None,
    ),
    "dracura": CxStatTheme(
        header_style="bold #BD93F9",
        label_style="#F8F8F2",
        highlight_label_style="bold #8BE9FD",
        total_style="#50FA7B",
        input_style="#F1FA8C",
        output_style="#8BE9FD",
        count_style="#FFB86C",
        info_style="#6272A4",
        warning_style="#FF5555",
        accent_style="bold #FF79C6",
        row_styles=None,
    ),
    "ayu": CxStatTheme(
        header_style="bold #FFCC66",
        label_style="#CCCAC2",
        highlight_label_style="bold #73D0FF",
        total_style="#87D96C",
        input_style="#FFAD66",
        output_style="#5CCFE6",
        count_style="#FFD173",
        info_style="#707A8C",
        warning_style="#FF6666",
        accent_style="bold #FFCC66",
        row_styles=None,
    ),
}


def _get_theme_names() -> tuple[str, ...]:
    """Return available theme identifiers for CLI option hints."""
    return tuple(sorted(THEMES))


AVAILABLE_THEMES = _get_theme_names()
