import drore
from typing import Optional


def test_first_alternative_is_taken():
    def assertGroup(group_id: int, match: Optional[drore.Match]):
        assert match is not None
        assert group_id == match.children[0].group_id
    assertGroup(1, drore.match(r'(?P<1>a)|(?P<2>a)|(?P<3>a)|(?P<4>a)', 'a'))  # 1,2,3,4
    assertGroup(1, drore.match(r'(?P<1>a)|(?P<2>a)|(?P<3>b)|(?P<4>c)', 'a'))  # 1,2
    assertGroup(1, drore.match(r'(?P<1>a)|(?P<2>b)|(?P<3>a)|(?P<4>c)', 'a'))  # 1,3
    assertGroup(1, drore.match(r'(?P<1>a)|(?P<2>b)|(?P<3>c)|(?P<4>a)', 'a'))  # 1,4
    assertGroup(2, drore.match(r'(?P<1>b)|(?P<2>a)|(?P<3>a)|(?P<4>c)', 'a'))  # 2,3
    assertGroup(2, drore.match(r'(?P<1>b)|(?P<2>a)|(?P<3>c)|(?P<4>a)', 'a'))  # 2,4
    assertGroup(3, drore.match(r'(?P<1>b)|(?P<2>c)|(?P<3>a)|(?P<4>a)', 'a'))  # 3,4
