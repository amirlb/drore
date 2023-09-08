import drore


pattern = drore.compile(r'(\s*Name: (?P<name>\w+)\n(?:Title: (?P<title>\w+)\n)?(?:Phone: (?P<phone>\d+)\n|Email: (?P<email>\w+)\n)*\s*)*')

text = '''
Name: Amir
Phone: 0546320668
Email: amir_livne_baron

Name: Dror
Title: Mr
Email: livne_dror

Name: Hagar
Phone: 0543384678
Email: strayblues
Email: abc0543384678
'''

print(repr(pattern.match(text)))

# [[name='Amir', phone='0546320668', email='amir_livne_baron'], [name='Dror', title='Mr', email='livne_dror'], [name='Hagar', phone='0543384678', email='strayblues', email='abc0543384678']]

# Verify order of preference of alternatives
# print('1234', repr(drore.match(r'(?P<1>a)|(?P<2>a)|(?P<3>a)|(?P<4>a)', 'a')))
# print('12', repr(drore.match(r'(?P<1>a)|(?P<2>a)|(?P<3>b)|(?P<4>c)', 'a')))
# print('13', repr(drore.match(r'(?P<1>a)|(?P<2>b)|(?P<3>a)|(?P<4>c)', 'a')))
# print('14', repr(drore.match(r'(?P<1>a)|(?P<2>b)|(?P<3>c)|(?P<4>a)', 'a')))
# print('23', repr(drore.match(r'(?P<1>b)|(?P<2>a)|(?P<3>a)|(?P<4>c)', 'a')))
# print('24', repr(drore.match(r'(?P<1>b)|(?P<2>a)|(?P<3>c)|(?P<4>a)', 'a')))
# print('34', repr(drore.match(r'(?P<1>b)|(?P<2>c)|(?P<3>a)|(?P<4>a)', 'a')))
