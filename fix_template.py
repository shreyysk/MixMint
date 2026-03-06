import re
import sys

try:
    with open('templates/explore.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix spacing around ==
    content = content.replace("sort=='popular'", "sort == 'popular'")
    content = content.replace("sort=='latest'", "sort == 'latest'")
    content = content.replace("sort=='price_low'", "sort == 'price_low'")
    content = content.replace("sort=='price_high'", "sort == 'price_high'")
    content = content.replace("type=='track'", "type == 'track'")
    content = content.replace("type=='album'", "type == 'album'")

    # Remove duplicate class="hidden"> lines
    content = re.sub(r'(class="hidden">\s*){2,}', 'class="hidden">\\n                            ', content)

    with open('templates/explore.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print('Replaced successfully.')
except Exception as e:
    print('Error:', e)
    sys.exit(1)
