% ── Family relationships ──────────────────────────────────────────────

% parent(Parent, Child).
parent(alice, bob).
parent(alice, carol).
parent(bob, dave).
parent(bob, eve).
parent(carol, frank).
parent(dave, grace).

% male(Person).
male(bob).
male(dave).
male(frank).

% female(Person).
female(alice).
female(carol).
female(eve).
female(grace).

% ── Rules ─────────────────────────────────────────────────────────────

grandparent(GP, GC) :- parent(GP, P), parent(P, GC).
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
mother(M, C) :- parent(M, C), female(M).
father(F, C) :- parent(F, C), male(F).
