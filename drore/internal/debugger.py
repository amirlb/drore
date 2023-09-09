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

from typing import Optional

from drore.internal.execution import ClosedGroupMatch, ExecutionContext, PartialMatch, Program


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


class DebuggingContext(ExecutionContext):
    def __init__(self, string: str, program: Program):
        super().__init__(string, program)
        print("Program listing")
        for i, op in enumerate(program):
            print(f"{i:4d}:  {op.op_name}")

    def queue_state(self, state: PartialMatch) -> bool:
        queued = super().queue_state(state)
        if not queued:
            print(f"Already visited {state}")
        return queued

    def already_visited(self, state: PartialMatch, ind_offset: int, pc_offset: int) -> bool:
        visited = super().already_visited(state, ind_offset, pc_offset)
        if visited:
            print(f"Already visited [ind={state.ind + ind_offset} pc={state.pc + pc_offset}]")
        return visited

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
