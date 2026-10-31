# Can four common zeros still be false rank drops?

R206 left a seven-element off-slice standard basis after six selected maximal
minors had already closed the entire `b=0` slice. The tempting move was to add
a seventh minor immediately. R207 asks a more diagnostic question first:
what exactly is the surviving component, and does the complete matrix really
lose rank there?

At two finite fields, the component radical reduces to three compact
equations:

```text
169*a^2 + 407*c^2 = 0
169*b^2 - 576*c^2 = 0
2*u*c^2 - 1 = 0
```

The `c=1` chart contains four algebraic points, each appearing with
multiplicity two in the six-minor ideal. Yet the complete `238x37` Pauli-word
matrix and the separately built `256x37` dense matrix both retain rank 37 at
all four points.

The more useful surprise is that a 37-row minor selected on either sign of
`b` stays nonzero on the opposite sign too. One seventh minor may therefore
remove all four false zeros at once.

An independent audit expands each quadratic-field `37x37` payload into a
`74x74` ordinary finite-field matrix. It reproduces the determinant norm and
nonzero verdict for all four main and four cross-branch minors at two primes:
16/16 checks pass.

The next experiment is sharp: should one cross-branch minor make the
seven-minor saturated ideal equal to the unit ideal, or will another hidden
component appear?

No frozen holdout was executed. This is not a characteristic-zero
Nullstellensatz certificate, global full-rank theorem, Quantum PCP/NLTS result,
hardware result, scientific promotion, or new credit.

