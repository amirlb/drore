import drore


pattern = drore.compile(r'(\s*Name: (?P<name>\w+)\n(?:Title: (?P<title>\w+)\n)?(?:Phone: (?P<phone>\d+)\n|Email: (?P<email>\w+)\n)*\s*)*$')

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
