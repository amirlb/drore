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


from __future__ import annotations

from typing import Iterator, NamedTuple, Optional, Union

from drore.internal.execution import ClosedGroupMatch, ExecutionContext, Program


class GroupDescription(NamedTuple):
    name: str
    pattern_span: tuple[int, int]

GroupID = Union[int, str, GroupDescription]


class Match:
    def __init__(self, group_match: ClosedGroupMatch, base: str, group_descs: list[GroupDescription]) -> None:
        self._base = base
        self.group_id = group_match.group_id
        self.group = group_descs[self.group_id]
        self.group_name = self.group.name
        self.span = group_match.span
        self.groups = group_descs
        self.children = [Match(sub_match, base, group_descs) for sub_match in group_match.sub_matches]

    def __str__(self) -> str:
        start_ind, end_ind = self.span
        return self._base[start_ind : end_ind]

    def __repr__(self) -> str:
        s = repr(self.children) if self.children else repr(str(self))
        if self.group_name:
            s = self.group_name + '=' + s
        return s

    def get(self, group: GroupID) -> Optional[Match]:
        return next(self.get_all(group), None)

    def get_all(self, group: GroupID) -> Iterator[Match]:
        for child in self.children:
            if child._group_matches(group):
                yield child
            yield from child.get_all(group)

    def _group_matches(self, group: GroupID) -> bool:
        return group in [self.group_id, self.group_name, self.group]


class Pattern:
    def __init__(self, program: Program, groups: list[GroupDescription]):
        self._program = program
        self._groups = groups

    def match(self, string: str, start_ind: int = 0) -> Optional[Match]:
        context = ExecutionContext(string, self._program)
        context.start_at(start_ind)
        return self._run(context)

    def search(self, string: str) -> Optional[Match]:
        context = ExecutionContext(string, self._program)
        for i in range(len(string), -1, -1):
            context.start_at(i)
        return self._run(context)

    def _run(self, context: ExecutionContext) -> Optional[Match]:
        if matched_group := context.run():
            return Match(matched_group, context.string, self._groups)

    def finditer(self, string: str) -> Iterator[Match]:
        for i in range(len(string) + 1):
            if match := self.match(string, i):
                yield match

    def findall(self, string: str) -> list[Match]:
        return list(self.finditer(string))
