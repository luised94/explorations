@@@ id: c-ptr-deref
tags: pointers, dereferencing
Given:
    int x = 42;
    int *p = &x;
    *p = 99;
What is the value of x after the third line, and why?
criteria: x is 99. p holds the address of x. The dereference operator * on the left side of an assignment writes through the pointer to the object it points to. x and *p name the same storage location.

@@@ id: c-array-decay
tags: pointers, arrays, decay
after: c-ptr-deref
Given:
    int arr[4] = {10, 20, 30, 40};
    int *p = arr;
What value does p hold, and what is the term for the implicit
conversion that makes this assignment valid without a cast?
criteria: p holds the address of arr[0]. The conversion is called array decay (or array-to-pointer conversion). The array name in most expression contexts decays to a pointer to its first element. sizeof and & are the two primary exceptions.

@@@ id: c-sizeof-array
tags: arrays, sizeof, pointers
after: c-array-decay
Given:
    int arr[8];
    int *p = arr;
What does sizeof(arr) return versus sizeof(p), and why do they differ?
criteria: sizeof(arr) returns 32 (8 ints * 4 bytes each, assuming 4-byte int). sizeof(p) returns 8 on a 64-bit system (pointer width). arr in a sizeof operand does not decay; sizeof sees the full array type. p is just a pointer; sizeof reports the pointer size, not the referent.

@@@ id: c-str-literal
tags: strings, literals, memory
Given:
    char *s = "hello";
    s[0] = 'H';
What is wrong with this code, and how would you fix it to allow
modification?
criteria: String literals are stored in read-only memory (typically .rodata). Writing to s[0] is undefined behavior and commonly causes a segfault. Fix: declare as char s[] = "hello"; which copies the literal into a writable stack array.

@@@ id: c-ub-signed-overflow
tags: undefined-behavior, arithmetic, integers
In C, what happens when a signed integer arithmetic operation
produces a result outside the range of its type, and how does
this differ from unsigned integer overflow?
criteria: Signed integer overflow is undefined behavior in C. The compiler may assume it never occurs and optimize accordingly, producing surprising results. Unsigned integer overflow is well-defined: it wraps modulo 2^N where N is the bit width.
