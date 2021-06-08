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

- indent with 4 spaces;
- prefer to continue lines vertically, aligned with the opening delimiter;
- prefer single quotes for string literals, unless double quotes will avoid
  some escaping;
- use f-strings whenever applicable, except for `logging` messages (more about
  those bellow) which wont necessarily be shown;
- use lowercase hexadecimal literals.

### Grouping and sorting of import statements

In normal modules, import statements should be grouped into standard library
modules, modules from third-party libraries, and local modules.

In test modules, an additional group for test scaffolding modules (inclunding
`pytest` and `_testutils`) should come before the standard library modules.

Within each group, `import` statements should come before `from <...> import`
ones.  After that, they should be sorted ascending order.


## Dependencies

When adding new dependencies, their benefit must be carefully weighted.
Additionally, the new dependency should:

- have a small number of transitive dependencies;
- support Linux:
    * be available on ArchLinux;
    * be available on Fedora;
    * be available on Debian;
    * be expected to be packaged in other distributions;
- support Windows:
    * be easily installed (by being pure Python or have binary wheels);
- support Mac OS;
- be compatible for use in a GPL v3 program (including being distributed under
  the GPL in the case of the Windows executable).


## Driver behavior

### Fixing or raising on user errors

Drivers should fix as most user errors as possible, without making actual
choices for the user.

For example, it is fine to clamp an integer, like a fan duty cycle, to its
minimum and maximum allowed values, since values bellow or above the possible
range can safely be interpreted as requests for, respectively, the "minimum"
and "maximum" values themselves.

On the other hand, if a device has two channels, and the user specifies a third
one, the driver should raise a suitable error (`ValueError`, in this case) so
the user can check the documentation and decide for *themselves* which channel
to use.

### Case sensitivity of string constants

Channel and mode names, as well as some other values, must be specified as
strings.  While this is more explicit then using magic numbers, it introduces
the problem of whether comparisons are case sensitive.

In fact, from the point of view of a CLI user, the comparisons are case
*insensitive.*  As of this version of the style guide, ensuring
case-insensitive comparisons is a shared responsibility of both CLI and
drivers; but whenever possible this should be kept in the CLI code, making the
drivers simpler and the behavior more consistent.

On the other hand, the liquidctl APIs are **not** specified to ignore casing
issues; when that happens it is usually just to keep the implementation
simpler.


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

- start with a lowercase letter;
- string values that the user is expected to type, or that absolutely need to
  delimited: use single quotes;
- other values: no quotes or backticks;
- command line commands or options: no quotes or backticks.

Deprecated guidelines for warnings:

- outputting values as `key=value` pairs.

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

- start with a lowercase letter;
- use `key=value`, `` `expression` ``, `'string'`, or `value`, whichever is
  clearer;

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


## Use of automatic formatters

We are considering it for a near future (tracking issue is [#321]).  Until
then, code is expected to be formated according to _this_ document.

[#321]: https://github.com/liquidctl/liquidctl/issues/321
