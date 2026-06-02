import pathlib

p = pathlib.Path('modules/typst_writer.py')
txt = p.read_text(encoding='utf-8')

old = (
    "def _to_chinese_numeral(num: int) -> str:\n"
    "    digits = '零一二三四五六七八九'\n"
    "    if num <= 0:  return digits[0]\n"
    "    if num < 10:  return digits[num]\n"
    "    if num == 10: return '十'\n"
    "    if num < 20:  return '十' + digits[num % 10]\n"
    "    tens, ones = divmod(num, 10)\n"
    "    return digits[tens] + '十' + (digits[ones] if ones else '')"
)

new = (
    "def _to_chinese_numeral(num: int) -> str:\n"
    "    \"\"\"将任意正整数转为中文数字（支持三位及以上页码）。\"\"\"\n"
    "    digits = '零一二三四五六七八九'\n"
    "    units  = ['', '十', '百', '千', '万']\n"
    "    if num <= 0:  return digits[0]\n"
    "    if num < 10:  return digits[num]\n"
    "    # 逐位拆解\n"
    "    result = ''\n"
    "    mag = 1\n"
    "    while 10 ** mag <= num:\n"
    "        mag += 1\n"
    "    for i in range(mag - 1, -1, -1):\n"
    "        d = (num // (10 ** i)) % 10\n"
    "        if d == 0:\n"
    "            if result and result[-1] != '零':\n"
    "                result += '零'\n"
    "        else:\n"
    "            result += digits[d] + units[i]\n"
    "    result = result.rstrip('零')\n"
    "    # 壹十 → 十\n"
    "    if result.startswith('一十'):\n"
    "        result = result[1:]\n"
    "    return result"
)

txt2 = txt.replace(old, new)
if txt2 == txt:
    print('ERROR: old string not found')
else:
    p.write_text(txt2, encoding='utf-8', newline='\r\n')
    print('OK: _to_chinese_numeral patched to support any page number')

# quick smoke test
exec(new.replace('def _to_chinese_numeral', 'def _cn'))
for n in [1, 9, 10, 11, 20, 99, 100, 764, 770, 1000]:
    print(f'  {n:4d} -> {_cn(n)}')
