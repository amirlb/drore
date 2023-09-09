import drore
from typing import Optional


def test_first_alternative_is_taken():
    def assertGroup(group_id: int, match: Optional[drore.Match]):
        assert match is not None
        assert group_id == match.children[0].group_id
    assertGroup(1, drore.match(r'(a)|(a)|(a)|(a)', 'a'))  # 1,2,3,4
    assertGroup(1, drore.match(r'(a)|(a)|(b)|(c)', 'a'))  # 1,2
    assertGroup(1, drore.match(r'(a)|(b)|(a)|(c)', 'a'))  # 1,3
    assertGroup(1, drore.match(r'(a)|(b)|(c)|(a)', 'a'))  # 1,4
    assertGroup(2, drore.match(r'(b)|(a)|(a)|(c)', 'a'))  # 2,3
    assertGroup(2, drore.match(r'(b)|(a)|(c)|(a)', 'a'))  # 2,4
    assertGroup(3, drore.match(r'(b)|(c)|(a)|(a)', 'a'))  # 3,4
    assertGroup(1, drore.match(r'(a)|(b)|(c)|(d)', 'a'))  # 1
    assertGroup(2, drore.match(r'(a)|(b)|(c)|(d)', 'b'))  # 2
    assertGroup(3, drore.match(r'(a)|(b)|(c)|(d)', 'c'))  # 3
    assertGroup(4, drore.match(r'(a)|(b)|(c)|(d)', 'd'))  # 4
