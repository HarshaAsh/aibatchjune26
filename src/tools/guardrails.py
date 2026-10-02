"""Validation helpers for restricting generated SQL to one read query."""

import re


_FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "LOCK",
}
_IDENTIFIER_CHARS = r"A-Za-z0-9_$"


def _strip_comments_and_mask_literals(query: str) -> str:
    """Remove comments and replace quoted values with whitespace-safe markers."""
    output: list[str] = []
    index = 0
    length = len(query)

    while index < length:
        if query.startswith("--", index):
            newline = query.find("\n", index + 2)
            output.append(" ")
            index = length if newline == -1 else newline + 1
            continue

        if query.startswith("/*", index):
            depth = 1
            index += 2
            while index < length and depth:
                if query.startswith("/*", index):
                    depth += 1
                    index += 2
                elif query.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise ValueError("Unterminated multi-line SQL comment.")
            output.append(" ")
            continue

        if query[index] in {"'", '"'}:
            quote = query[index]
            is_escape_string = (
                quote == "'"
                and index > 0
                and query[index - 1] in {"e", "E"}
                and (
                    index < 2
                    or not re.match(
                        rf"[{_IDENTIFIER_CHARS}]",
                        query[index - 2],
                    )
                )
            )
            output.append(" Q ")
            index += 1
            while index < length:
                if is_escape_string and query[index] == "\\":
                    index += 2
                    continue
                if query[index] == quote:
                    if index + 1 < length and query[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise ValueError("Unterminated quoted SQL value or identifier.")
            continue

        if query[index] == "$":
            delimiter_match = re.match(
                r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$",
                query[index:],
            )
            if delimiter_match:
                delimiter = delimiter_match.group(0)
                closing_index = query.find(delimiter, index + len(delimiter))
                if closing_index == -1:
                    raise ValueError("Unterminated dollar-quoted SQL value.")
                output.append(" Q ")
                index = closing_index + len(delimiter)
                continue

        output.append(query[index])
        index += 1

    return "".join(output)


def validate_sql_query(query: str) -> tuple[bool, str | None]:
    """Allow exactly one SELECT/WITH query without mutating SQL keywords.

    Comments are removed and quoted values are masked while checking SQL tokens,
    so keywords and semicolons inside literals do not cause false positives.
    """
    if not isinstance(query, str) or not query.strip():
        return False, "SQL security policy violation: query must not be empty."

    try:
        cleaned_query = _strip_comments_and_mask_literals(query)
    except ValueError as exc:
        return False, f"SQL security policy violation: {exc}"

    semicolon_count = cleaned_query.count(";")
    if semicolon_count > 1:
        return (
            False,
            "SQL security policy violation: multiple statements are not allowed.",
        )
    if semicolon_count == 1:
        statement, trailing = cleaned_query.split(";", maxsplit=1)
        if trailing.strip():
            return (
                False,
                "SQL security policy violation: multiple statements are not allowed.",
            )
        cleaned_query = statement

    cleaned_query = cleaned_query.strip()
    if not re.match(
        r"^(SELECT|WITH)(?![A-Za-z0-9_$])",
        cleaned_query,
        flags=re.IGNORECASE,
    ):
        return (
            False,
            "SQL security policy violation: only SELECT or WITH queries are allowed.",
        )

    for keyword in _FORBIDDEN_KEYWORDS:
        keyword_pattern = rf"(?<![{_IDENTIFIER_CHARS}]){keyword}(?![{_IDENTIFIER_CHARS}])"
        if re.search(keyword_pattern, cleaned_query, flags=re.IGNORECASE):
            return (
                False,
                f"SQL security policy violation: forbidden keyword '{keyword}' is not allowed.",
            )

    return True, None
