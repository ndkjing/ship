a = [1, 2, 3, 4, 5]
print(a[:-2])

b = {1: 2, 3: [1, 2, 3]}
c = {1: 2, 3: [1, 2, 3]}
d = {1: 2, 3: 4}
print(b == c, c == d)

for k, v in b.items():
    print(k, v)
