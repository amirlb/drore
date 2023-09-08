# DroRE - A better regular expression library for Python
# Copyright (C) 2023  Amir Livne Bar-on

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import functools
from typing import Iterator, Optional

from drore.internal.pattern import Match, Pattern


@functools.cache
def compile(pattern: str) -> Pattern:
    from drore.internal.compiler import Compiler
    return Compiler.compile(pattern)


def match(pattern: str, string: str) -> Optional[Match]:
    return compile(pattern).match(string)

def search(pattern: str, string: str) -> Optional[Match]:
    return compile(pattern).search(string)

def finditer(pattern: str, string: str) -> Iterator[Match]:
    return compile(pattern).finditer(string)

def findall(pattern: str, string: str) -> list[Match]:
    return compile(pattern).findall(string)
