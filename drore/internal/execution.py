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

from typing import Callable, NamedTuple, Optional, Protocol


class ClosedGroupMatch(NamedTuple):
    group_id: int
    span: tuple[int, int]
    sub_matches: tuple[ClosedGroupMatch, ...]

class OpenGroupMatch(NamedTuple):
    group_id: int
    start_ind: int
    sub_matches: list[ClosedGroupMatch]

    def clone(self) -> OpenGroupMatch:
        return OpenGroupMatch(self.group_id, self.start_ind, list(self.sub_matches))

class PartialMatch:
    def __init__(self, ind: int, pc: int) -> None:
        self.ind = ind
        self.pc = pc
        self._stack: list[OpenGroupMatch] = []
        self._match = OpenGroupMatch(0, ind, [])

    def start_group(self, group_id: int) -> None:
        self._stack.append(self._match)
        self._match = OpenGroupMatch(group_id, self.ind, [])

    def end_group(self) -> None:
        current = self._close_current_match()
        self._match = self._stack.pop()
        self._match.sub_matches.append(current)

    def clone(self) -> PartialMatch:
        other = PartialMatch(self.ind, self.pc)
        other._stack = [x.clone() for x in self._stack]
        other._match = self._match.clone()
        return other

    def finalize(self) -> ClosedGroupMatch:
        assert not self._stack
        return self._close_current_match()

    def _close_current_match(self) -> ClosedGroupMatch:
        return ClosedGroupMatch(
            group_id=self._match.group_id,
            span=(self._match.start_ind, self.ind),
            sub_matches=tuple(self._match.sub_matches),
        )


class ExecutionContextProtocol(Protocol):
    @property
    def string(self) -> str:
        ...

    def queue_state(self, state: PartialMatch) -> bool:
        ...

    def already_visited(self, state: PartialMatch, ind_offset: int, pc_offset: int) -> bool:
        ...

Operation = Callable[[ExecutionContextProtocol, PartialMatch], None]
Program = list[Operation]


class ExecutionContext:
    def __init__(self, string: str, program: Program):
        self.string = string
        self._program = program
        self._states: list[PartialMatch] = []
        self._visited: set[tuple[int, int]] = set()

    def start_at(self, ind: int) -> None:
        self.queue_state(PartialMatch(ind, 0))

    def queue_state(self, state: PartialMatch) -> bool:
        inds = (state.ind, state.pc)
        if inds in self._visited:
            return False
        self._visited.add(inds)
        self._states.append(state)
        return True

    def already_visited(self, state: PartialMatch, ind_offset: int, pc_offset: int) -> bool:
        inds = (state.ind + ind_offset, state.pc + pc_offset)
        return inds in self._visited

    def run(self) -> Optional[ClosedGroupMatch]:
        while self._states:
            state = self._states.pop()
            if state.pc == len(self._program):
                return state.finalize()
            instruction = self._program[state.pc]
            state.pc += 1
            instruction(self, state)
        return None


def op_any(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if state.ind < len(context.string):
        state.ind += 1
        context.queue_state(state)

def op_char(expected: str) -> Operation:
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if state.ind < len(context.string) and context.string[state.ind] == expected:
            state.ind += 1
            context.queue_state(state)
    return op

def op_filter(condition: Callable[[str], bool]) -> Operation:
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if state.ind < len(context.string) and condition(context.string[state.ind]):
            state.ind += 1
            context.queue_state(state)
    return op

def op_assert_start(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if state.ind == 0:
        context.queue_state(state)

def op_assert_end(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if state.ind == len(context.string):
        context.queue_state(state)

def op_split(offset: int) -> Operation:
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if context.queue_state(state):
            if not context.already_visited(state, 0, offset):
                state = state.clone()
                state.pc += offset
                context.queue_state(state)
        else:
            state.pc += offset
            context.queue_state(state)
    return op

def op_jump(offset: int) -> Operation:
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        state.pc += offset
        context.queue_state(state)
    return op

def op_start_group(group_id: int) -> Operation:
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if context.queue_state(state):
            state.start_group(group_id)
    return op

def op_end_group(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if context.queue_state(state):
        state.end_group()
