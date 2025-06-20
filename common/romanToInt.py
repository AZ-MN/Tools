SYMBOL_VALUES = {
    'I': 1,
    'V': 5,
    'X': 10,
    'L': 50,
    'C': 100,
    'D': 500,
    'M': 1000,
}


def romanToInt(s: str) -> int:
    ans = 0
    n = len(s)
    for i, ch in enumerate(s):
        value = SYMBOL_VALUES[ch]
        if i < n - 1 and value < SYMBOL_VALUES[s[i + 1]]:
            ans -= value
        else:
            ans += value
    return ans


if __name__ == '__main__':
    print(romanToInt('MCMXCIV'))
    print(romanToInt('LVIII'))
    print(romanToInt('III'))