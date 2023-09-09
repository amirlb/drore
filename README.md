# DroRE: A better regular expression library for Python

This library is largely compatible with the Python built-in `re` module,
but with some improvements.

## Multiple captures of the same group

Regular expressions allow capturing sub-groups by putting them in parentesis.
If such a sub-group appears in a repeating expression, the built-in `re`
module only saves one value, whereas `drore` keeps all of them.

For example,
```python
>>> m = re.match(r'^(\d+)(,(\d+))*$', '12,34,56,78,90')
>>> m.group(1)
'12'
>>> m.group(3)
'90'

>>> m = drore.match(r'^(\d+)(,(\d+))*$', '12,34,56,78,90')
>>> m.get(1), list(m.get_all(3))
('12', ['34', '56', '78', '90'])
```

See also [examples/parsing.py](parsing.py) for a multi-line example.

## No slow edge cases

The built-in `re` module uses a backtracking algorithm that results in
exponential complexity on some inputs. For example,

```python
re.match(r'(a+)+b', 'a'*27 + 'c')
```

takes several seconds to reject. In contrast, `drore` compiles the expression
to an NFA program which implements the regular expression, and then runs it.
The NFA program is efficient to generate and always runs quickly. So the
corresponding code

```python
drore.match(r'(a+)+b', 'a'*27 + 'c')
```

takes less than a millisecond.

## Features

TBD
