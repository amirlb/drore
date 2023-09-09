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

from drore.internal.execution import Program, op_any, op_assert_end, op_assert_start, op_char, op_end_group, op_filter, op_jump, op_split, op_split_after, op_start_group
from drore.internal.pattern import GroupDescription, Pattern


class Compiler:
    r"""
    Converts from the regular expression syntax to a Program (list of Operation)
    that implements the expression.

    Goes by recursive descent, following the grammar
        <expression>  ::=  <serial>  |  <serial> "|" <expression>
        <serial>      ::=  ""  |  <single> <serial>
        <single>      ::=  <atomic>  |  <single> <quantifier>
        <quantifier>  ::=  "?"  |  "+"  |  "*"
        <atomic>      ::=  ""  |  <group>  |  <escape>  |  "^"  |  "$"  |  <char>
        <group>       ::=  "(" <group-mod> <expression> ")"
        <group-mod>   ::=  ""  |  "?:"  |  "?P<" <name> ">"
        <escape>      ::=  "\\"  |  "\n"  |  "\d"  |  "\s"  |  etc.

    Program fragments are returned from the recursive descent parser directly
    and combined by higher-level rules. The operations are designed such that
    no relocations are necessary while combining.
    """

    def __init__(self, pattern: str):
        self._pattern = pattern
        self._ind = 0
        self._groups: list[GroupDescription] = [GroupDescription("", (0, len(pattern)))]

    @classmethod
    def compile(cls, pattern: str) -> Pattern:
        compiler = cls(pattern)
        program = compiler._compile_expression()
        compiler._assert_at_end_of_pattern()
        return Pattern(program, pattern, compiler._groups)

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
        return self._compose_alternatives(branches)

    @staticmethod
    def _compose_alternatives(branches: list[Program]) -> Program:
        """
        Add jumps at the ends of all branches but the last, and add splits
        in the beginning to go to all branches. The splits go to the branches
        by order, since we first explore the split variation before continuing
        with the program fow.
        """
        if len(branches) == 1:
            return branches[0]

        jump_distance = 0
        for j in range(len(branches) - 2, -1, -1):
            jump_distance += len(branches[j + 1])
            branches[j].append(op_jump(jump_distance))

        program: Program = []
        jump_distance = 0
        for j in range(len(branches) - 1):
            program.append(op_split(len(branches) - 1 - j + jump_distance))
            jump_distance += len(branches[j])
        program.append(op_jump(jump_distance))

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
            match self._peek():
                case '?':
                    self._next()
                    program = [op_split_after(len(program))] + program
                case '+':
                    self._next()
                    program.append(op_split(-len(program) - 1))
                case '*':
                    self._next()
                    # * is the same as +?
                    program.append(op_split(-len(program) - 1))
                    program = [op_split_after(len(program))] + program
                case '{':
                    raise RuntimeError("Sorry, {} is not implemented yet")
                case _:
                    return program

    def _compile_atomic(self) -> Program:
        match ch := self._next():
            case None:
                return []
            case '.':
                return [op_any]  # TODO: should this be [^\n] instead?
            case '?' | '+' | '*':
                raise ValueError(f"Operator without argument: the {ch} at position {self._ind}) doesn't follow a sub-pattern")
            case '|':
                raise RuntimeError(f"Cannot parse regular expression: error 2 at position {self._ind}")
            case '\\':
                return self._compile_escape()
            case '^':
                return [op_assert_start]
            case '$':
                return [op_assert_end]
            case '[':
                raise RuntimeError("Sorry, [] is not implemented yet")
            case ']':
                raise ValueError(f"Mismatched brackets: unexpected ] at position {self._ind})")
            case '(':
                return self._compile_parens()
            case ')':
                raise ValueError(f"Mismatched parens: unexpected ) at position {self._ind})")
            case _:
                return [op_char(ch)]

    def _compile_parens(self) -> Program:
        if self._peek() == ')':
            raise ValueError(f"Empty parenthesis at position {self._ind}")
        group_id = len(self._groups)
        start_ind = self._ind
        group_name = self._read_group_name()
        if group_name is not None:
            # Occupy the group ID while we compile the inner expression
            self._groups.append(GroupDescription(group_name, (start_ind, start_ind)))
        program = self._compile_expression()
        ch = self._next()
        if ch is None:
            raise ValueError(f"Mismatched parens: the ( at position {start_ind} is never closed")
        if ch != ')':
            raise RuntimeError(f"Cannot parse regular expression: error 3 at position {self._ind}")
        if group_name is not None:
            self._groups[group_id] = GroupDescription(group_name, (start_ind, self._ind - 1))
            program = [op_start_group(group_id)] + program + [op_end_group]
        return program

    def _read_group_name(self) -> Optional[str]:
        """
        Called right after an open paren. Returns an empty string for
        normal groups, None if the group should not produce captures,
        and a non-empty string for named groups.
        """

        if self._peek() != '?':
            return ""
        self._next()

        match self._next():
            case None:
                raise ValueError(f"Mismatched parens: the ( at position {self._ind - 1}) is never closed")
            case ':':
                return None
            case 'P':
                if self._next() != '<':
                    raise ValueError(f"Expected group name in <angle brackets> in position {self._ind}")
                group_start = self._ind
                group_end = self._pattern.find('>', self._ind)
                if group_end == -1:
                    raise ValueError(f"Group name at position {group_start} doesn't have a closing bracket")
                self._ind = group_end + 1
                return self._pattern[group_start : group_end]
            case ch:
                raise ValueError(f"Invalid group decoration {ch!r} at position {self._ind}, only (?: and (?P are recognized")

    def _compile_escape(self) -> Program:
        match self._next():
            case None:
                raise ValueError(f"Invalid escape sequence at position {self._ind}: \\ cannot be the last thing in the pattern")
            case 'A':
                return [op_assert_start]
            case 'Z':
                return [op_assert_end]
            case 'd':
                return [op_filter(str.isdigit, "\\d")]
            case 'D':
                return [op_filter(lambda ch: not str.isdigit(ch), "\\D")]
            case 's':
                return [op_filter(str.isspace, "\\s")]
            case 'S':
                return [op_filter(lambda ch: not str.isspace(ch), "\\S")]
            case 'w':
                return [op_filter(lambda ch: ch == '_' or str.isalnum(ch), "\\w")]
            case 'W':
                return [op_filter(lambda ch: ch != '_' and not str.isalnum(ch), "\\W")]
            case 'n':
                return [op_char('\n')]
            case 't':
                return [op_char('\t')]
            case 'r':
                return [op_char('\r')]
            case '0':
                return [op_char('\0')]
            case '\\':
                return [op_char('\\')]
            case '[':
                return [op_char('[')]
            case ']':
                return [op_char(']')]
            case '(':
                return [op_char('(')]
            case ')':
                return [op_char(')')]
            case '{':
                return [op_char('{')]
            case '}':
                return [op_char('}')]
            case '?':
                return [op_char('?')]
            case '+':
                return [op_char('+')]
            case '*':
                return [op_char('*')]
            case '|':
                return [op_char('|')]
            case '.':
                return [op_char('.')]
            case '^':
                return [op_char('^')]
            case '$':
                return [op_char('$')]
            case 'x':
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
            case _:
                raise ValueError(f"Unrecognized escape sequence at position {self._ind - 1}")
