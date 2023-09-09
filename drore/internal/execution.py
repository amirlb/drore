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


class DebugMode:
    active = False

    def __init__(self, value: bool = True):
        self.value = value
        self.prev_value = None

    def __enter__(self):
        self.prev_value = DebugMode.active
        DebugMode.active = self.value

    def __exit__(self, *exc_info):
        DebugMode.active = self.prev_value


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

    def __str__(self) -> str:
        return f"[ind={self.ind} pc={self.pc}]"

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


class DebuggingContext:
    def __init__(self, string: str, program: Program):
        print("Program listing")
        for i, op in enumerate(program):
            print(f"{i:4d}:  {op.op_name}")
        self.string = string
        self._program = program
        self._states: list[PartialMatch] = []
        self._visited: set[tuple[int, int]] = set()

    def start_at(self, ind: int) -> None:
        self.queue_state(PartialMatch(ind, 0))

    def queue_state(self, state: PartialMatch) -> bool:
        inds = (state.ind, state.pc)
        if inds in self._visited:
            print(f"Already visited {state}")
            return False
        self._visited.add(inds)
        self._states.append(state)
        return True

    def already_visited(self, state: PartialMatch, ind_offset: int, pc_offset: int) -> bool:
        inds = (state.ind + ind_offset, state.pc + pc_offset)
        if inds in self._visited:
            print(f"Already visited [ind={inds[0]} pc={inds[1]}]")
            return True
        else:
            return False

    def run(self) -> Optional[ClosedGroupMatch]:
        print("Running")
        while self._states:
            state = self._states.pop()
            if state.pc == len(self._program):
                print("Finished successfully")
                return state.finalize()
            instruction = self._program[state.pc]
            scheduled_states = ""
            for i in range(3):
                if i < len(self._states):
                    state_str = str(self._states[len(self._states) - 1 - i])
                    scheduled_states += f"{state_str:17s}"
            if len(self._states) > 3:
                scheduled_states += f"... (total {len(self._states)})"
            ind_str=f"[ind={state.ind}]"
            print(f"{state.pc:4d}: {instruction.op_name:27s}{ind_str:11s}Queued:  {scheduled_states}")
            state.pc += 1
            instruction(self, state)
        return None


def op_name(name: str):
    def decorate(f):
        f.op_name = name
        return f
    return decorate


@op_name("any")
def op_any(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if state.ind < len(context.string):
        state.ind += 1
        context.queue_state(state)


def op_char(expected: str) -> Operation:
    @op_name(f"char {expected!r}")
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if state.ind < len(context.string) and context.string[state.ind] == expected:
            state.ind += 1
            context.queue_state(state)
    return op


def op_filter(condition: Callable[[str], bool], description: str = '') -> Operation:
    @op_name(f"filter {description}")
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if state.ind < len(context.string) and condition(context.string[state.ind]):
            state.ind += 1
            context.queue_state(state)
    return op


@op_name("assert start")
def op_assert_start(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if state.ind == 0:
        context.queue_state(state)


@op_name("assert end")
def op_assert_end(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if state.ind == len(context.string):
        context.queue_state(state)


def op_split(offset: int, prefer_jump: bool) -> Operation:

    @op_name(f"split {offset} (prefer jump)")
    def op_prefer_jump(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if context.queue_state(state):
            if not context.already_visited(state, 0, offset):
                state = state.clone()
                state.pc += offset
                context.queue_state(state)
        else:
            state.pc += offset
            context.queue_state(state)

    @op_name(f"split {offset} (prefer default)")
    def op_prefer_default(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        state.pc += offset
        if context.queue_state(state):
            if not context.already_visited(state, 0, -offset):
                state = state.clone()
                state.pc -= offset
                context.queue_state(state)
        else:
            state.pc -= offset
            context.queue_state(state)

    return op_prefer_jump if prefer_jump else op_prefer_default


def op_jump(offset: int) -> Operation:
    @op_name(f"jump {offset}")
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        state.pc += offset
        context.queue_state(state)
    return op


def op_start_group(group_id: int) -> Operation:
    @op_name(f"start group {group_id}")
    def op(context: ExecutionContextProtocol, state: PartialMatch) -> None:
        if context.queue_state(state):
            state.start_group(group_id)
    return op


@op_name("end group")
def op_end_group(context: ExecutionContextProtocol, state: PartialMatch) -> None:
    if context.queue_state(state):
        state.end_group()
