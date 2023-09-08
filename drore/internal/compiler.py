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


from typing import Optional

from drore.internal.execution import Program, op_any, op_assert_end, op_assert_start, op_char, op_end_group, op_filter, op_jump, op_split, op_start_group
from drore.internal.pattern import GroupDescription, Pattern


class Compiler:
    def __init__(self, pattern: str):
        self._pattern = pattern
        self._ind = 0
        self._groups: list[GroupDescription] = [GroupDescription('', (0, len(pattern)))]

    @classmethod
    def compile(cls, pattern: str) -> Pattern:
        compiler = cls(pattern)
        program = compiler._compile_expression()
        compiler._assert_at_end_of_pattern()
        return Pattern(program, compiler._groups)

    def _peek(self) -> Optional[str]:
        if self._ind == len(self._pattern):
            return None
        return self._pattern[self._ind]

    def _next(self) -> Optional[str]:
        if self._ind == len(self._pattern):
            return None
        self._ind += 1
        return self._pattern[self._ind - 1]

    def _assert_at_end_of_pattern(self) -> None:
        if self._peek() is not None:
            raise RuntimeError(f"Cannot parse regular expression: error 1 at position {self._ind + 1}")

    def _compile_expression(self) -> Program:
        branches = [self._compile_serial()]
        while self._peek() == '|':
            self._next()
            branches.append(self._compile_serial())
        if len(branches) == 1:
            return branches[0]
        else:
            code_length = len(branches[-1])
            for j in range(len(branches) - 2, -1, -1):
                branches[j].append(op_jump(code_length))
                code_length += len(branches[j])
            program: Program = []
            code_length = len(branches[0])
            for j in range(1, len(branches)):
                program.append(op_split(len(branches) - 1 - j + code_length))
                code_length += len(branches[j])
            for branch in branches:
                program.extend(branch)
            return program

    def _compile_serial(self) -> Program:
        program: Program = []
        while self._peek() not in {None, '|', ')'}:
            program.extend(self._compile_single())
        return program

    def _compile_single(self) -> Program:
        program = self._compile_atomic()
        while True:
            ch = self._peek()
            if ch == '?':
                self._next()
                program = [op_split(len(program))] + program
            elif ch == '+':
                self._next()
                program.append(op_split(-len(program) - 1))
            elif ch == '*':
                self._next()
                program = [op_split(len(program) + 1)] + program + [op_split(-len(program) - 1)]
            elif ch == '{':
                raise RuntimeError("Sorry, {} is not implemented yet")
            else:
                break
        return program

    def _compile_atomic(self) -> Program:
        ch = self._next()
        if ch is None:
            return []
        elif ch == '.':
            return [op_any]  # TODO: should this be [^\n] instead?
        elif ch in '?+*':
            raise ValueError(f"Operator without argument: the {ch} at position {self._ind}) doesn't follow a sub-pattern")
        elif ch == '|':
            raise RuntimeError(f"Cannot parse regular expression: error 2 at position {self._ind}")
        elif ch == '\\':
            return self._compile_escape()
        elif ch == '^':
            return [op_assert_start]
        elif ch == '$':
            return [op_assert_end]
        elif ch == '[':
            raise RuntimeError("Sorry, [] is not implemented yet")
        elif ch == ']':
            raise ValueError(f"Mismatched brackets: unexpected ] at position {self._ind})")
        elif ch == '(':
            return self._compile_parens()
        elif ch == ')':
            raise ValueError(f"Mismatched parens: unexpected ) at position {self._ind})")
        else:
            return [op_char(ch)]

    def _compile_parens(self) -> Program:
        if self._peek() == ')':
            raise ValueError(f"Empty parenthesis at position {self._ind}")
        group_name = ''
        if self._peek() == '?':
            self._next()
            ch = self._next()
            if ch is None:
                raise ValueError(f"Mismatched parens: the ( at position {self._ind - 1}) is never closed")
            elif ch == ':':
                start_ind = self._ind - 2
                program = self._compile_expression()
                ch = self._next()
                if ch is None:
                    raise ValueError(f"Mismatched parens: the ( at position {start_ind} is never closed")
                if ch != ')':
                    raise RuntimeError(f"Cannot parse regular expression: error 3 at position {self._ind}")
                return program
            elif ch == 'P':
                group_name = self._read_group_name()
            else:
                raise ValueError(f"Invalid group decoration at position {self._ind}, only (:? and (:P are recognized")
        group_id = len(self._groups)
        start_ind = self._ind
        self._groups.append(GroupDescription(group_name, (start_ind, start_ind)))
        program = self._compile_expression()
        ch = self._next()
        if ch is None:
            raise ValueError(f"Mismatched parens: the ( at position {start_ind} is never closed")
        if ch != ')':
            raise RuntimeError(f"Cannot parse regular expression: error 4 at position {self._ind}")
        self._groups[group_id] = GroupDescription(group_name, (start_ind, self._ind - 1))
        program = [op_start_group(group_id)] + program + [op_end_group]
        return program

    def _read_group_name(self) -> str:
        if self._next() != '<':
            raise ValueError(f"Expected group name in <angle brackets> in position {self._ind}")
        group_start = self._ind
        group_end = self._pattern.find('>', self._ind)
        if group_end == -1:
            raise ValueError(f"Group name at position {group_start} doesn't have a closing bracket")
        self._ind = group_end + 1
        return self._pattern[group_start : group_end]

    def _compile_escape(self) -> Program:
        ch = self._next()
        if ch is None:
            raise ValueError(f"Invalid escape sequence at position {self._ind}: \\ cannot be the last thing in the pattern")
        elif ch == 'A':
            return [op_assert_start]
        elif ch == 'Z':
            return [op_assert_end]
        elif ch == 'd':
            return [op_filter(str.isdigit)]
        elif ch == 'D':
            return [op_filter(lambda ch: not str.isdigit(ch))]
        elif ch == 's':
            return [op_filter(str.isspace)]
        elif ch == 'S':
            return [op_filter(lambda ch: not str.isspace(ch))]
        elif ch == 'w':
            return [op_filter(lambda ch: ch == '_' or str.isalnum(ch))]
        elif ch == 'W':
            return [op_filter(lambda ch: ch != '_' and not str.isalnum(ch))]
        elif ch == 'n':
            return [op_char('\n')]
        elif ch == 't':
            return [op_char('\t')]
        elif ch == 'r':
            return [op_char('\r')]
        elif ch == '0':
            return [op_char('\0')]
        elif ch == '\\':
            return [op_char('\\')]
        elif ch == '[':
            return [op_char('[')]
        elif ch == ']':
            return [op_char(']')]
        elif ch == '(':
            return [op_char('(')]
        elif ch == ')':
            return [op_char(')')]
        elif ch == '{':
            return [op_char('{')]
        elif ch == '}':
            return [op_char('}')]
        elif ch == '?':
            return [op_char('?')]
        elif ch == '+':
            return [op_char('+')]
        elif ch == '*':
            return [op_char('*')]
        elif ch == '|':
            return [op_char('|')]
        elif ch == '.':
            return [op_char('.')]
        elif ch == '^':
            return [op_char('^')]
        elif ch == '$':
            return [op_char('$')]
        elif ch == 'x':
            start_ind = self._ind - 1
            d1 = self._next()
            d2 = self._next()
            if d1 is None or d2 is None:
                raise ValueError(f"Escape sequence at position {start_ind} is cut in the middle")
            if d1 not in '0123456789abcdef':
                raise ValueError(f"Invalid escape sequence at position {start_ind}: the character {d1!r} is not a hex digit")
            if d2 not in '0123456789abcdef':
                raise ValueError(f"Invalid escape sequence at position {start_ind}: the character {d2!r} is not a hex digit")
            return [op_char(chr(int(d1 + d2, 16)))]
        else:
            raise ValueError(f"Unrecognized escape sequence at position {self._ind - 1}")
