# Style guide

This is not the code; this is just a tribute.

## General guidelines

This section has yet to be written, but for a start...

Read [PEP 8], then immediately watch Raymond Hettinger's [Beyond PEP 8] talk.
Write code somewhere between those lines.

In this repository, newer drivers are usually better examples than older
ones.  Experience with the domain helps to write better code.

Try to keep lines around 80-ish columns wide; in some modules 100-ish columns
may be more suited, but definitively try to avoid going beyond that.

Be consistent within a given module; *try* to be consistent between similar
modules.

[PEP 8]: https://pep8.org/
[Beyond PEP 8]: https://www.youtube.com/watch?v=wf-BqAjZb8M

### Nits

- indent with 4 spaces
- prefer to continue lines vertically, aligned with the opening delimiter
- prefer single quotes for string literals, unless double quotes will avoid
  some escaping
- use f-strings whenever applicable, except for `logging` messages (more about
  those bellow) which wont necessarily be shown
- use lowercase hexadecimal literals

## Use of automatic formatters

Pull requests are welcome.

_(For a suggestion of a formatter and associated configuration to use, not just
to fill this section)._

## Writing messages

Liquidctl generates a substantial amount of human readable messages, either
intended for direct consumption by CLI users, or for _a posteriori_ debugging
by developers.

While discussing the format of these messages deviates from the usual tab ×
spaces wars we have learned to love [citation needed], it is very important to
keep the messages clear, objective and consistent.

### Errors

Raise exceptions, preferably `liquidctl.error.*` or Python's
[built-in exceptions].

Error messages should start with a lowercase letter.

[built-in exceptions]: https://docs.python.org/3/library/exceptions.html

### Warnings
[warnings]: #warnings

Warnings are used to convey information that are deemed always relevant.  They
should be used to alert of unexpected conditions, degraded states, and other
high-importance issues.

By default the CLI outputs these to `stderr` for all users.  Since the messages
are visible to non-developers, the should follow the simplified guidelines
bellow:

- start with a lowercase letter
- string values that the user is expected to type, or that absolutely need to
  delimited: use single quotes
- other values: no quotes or backticks
- command line commands or options: no quotes or backticks

Deprecated guidelines for warnings:

- outputting values as `key=value` pairs

### Info

Information messages are normally hidden, but can be enabled with the
`--verbose` or `--debug` flags.  They should be used to display complementary
information that may interest any user, like additional `status` items or
computed `temp × rpm` curves.

Since these messages are also targeted to non-developers, they should follow
the same simplified guidelines used for [warnings].

### Debug

Debug messages are only intended for developers or users interested in dealing
with the internals of the program.  In the CLI these are normally disabled and
require the `--debug` flag.

Since they are intended for internal use, they follow relaxed guidelines:

- start with a lowercase letter
- use `key=value`, `` `expression` ``, `'string'`, or `value`, whichever is clearer

### A quick refresher on `logging`

Get a logger at the start of the module.

```py
import logging
...
_LOGGER = logging.getLogger(__name__)
```

Prefer old-style %-formatting for logging messages, since this is evaluated
lazyly by `logging`, and the message will only be formated if the logging level
is enabled.

```py
_LOGGER.warning('value %d, expected %d', current, expected)
```

_(While `%d` and `%i` are equivalent, and both print integers, prefer the
former over the latter)._

_(The rest of the time `f-strings` are preferred, following the `PEP 498`
guideline)._

When writing informational or debug messages, pay attention to the cost of
computing each value.  A classic example is hex formatting some bytes, which
can be expensive; this case can be solved by using
`liquidctl.util.LazyHexRepr`, and other similar wrapper types can be
constructed for other scenarios.

```py
from liquidctl.util import LazyHexRepr
...
_LOGGER.debug('buffer: %r', LazyHexRepr(some_bytes))
```
