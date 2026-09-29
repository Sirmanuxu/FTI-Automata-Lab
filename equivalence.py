"""Verificación de equivalencia entre autómatas finitos.

Dos autómatas son equivalentes si aceptan exactamente el mismo lenguaje, es
decir, si NO existe ninguna cadena que uno acepte y el otro rechace.

Se ofrecen dos métodos que se complementan:

1. Autómata producto (formal): recorre todos los pares de "situaciones" que
   pueden darse al leer una misma cadena en ambos autómatas. Si nunca aparece
   un par donde uno acepta y el otro no, los lenguajes son iguales. Es una
   DEMOSTRACIÓN y, si falla, devuelve la cadena más corta que los distingue.

2. Prueba por cadenas (empírico): prueba TODAS las cadenas hasta cierta
   longitud. Sirve para ilustrar en el informe, pero no demuestra nada por sí
   sola (una diferencia podría aparecer en cadenas más largas).

Las funciones sirven tanto para AFND como para AFD, así que se puede comparar
el AFND original directamente contra el AFD mínimo.
"""

from collections import deque
from itertools import product


# ---------------------------------------------------------------------------
# Piezas básicas
# ---------------------------------------------------------------------------

def _step(automaton, states, symbol):
    """Devuelve el conjunto de estados a los que se llega desde `states`
    leyendo `symbol`. Funciona igual para un AFD (un destino) que para un AFND
    (varios destinos)."""
    result = set()
    for state in states:
        result.update(automaton.get_destinations(state, symbol))
    # frozenset = conjunto inmutable. Lo necesitamos porque solo los objetos
    # inmutables pueden usarse como claves de diccionario o guardarse en un set.
    return frozenset(result)


def _is_accepting(automaton, states):
    """True si al menos uno de los estados actuales es final."""
    # isdisjoint devuelve True si los dos conjuntos NO comparten elementos.
    return not states.isdisjoint(automaton.final_states)


def accepts(automaton, string):
    """Indica si el autómata (AFND o AFD) acepta la cadena.

    Si la cadena tiene un símbolo que el autómata no conoce, no hay ninguna
    transición posible y la cadena simplemente se rechaza.
    """
    current = frozenset([automaton.initial_state])
    for symbol in string:
        current = _step(automaton, current, symbol)
    return _is_accepting(automaton, current)


# ---------------------------------------------------------------------------
# Método 1: autómata producto (demostración formal)
# ---------------------------------------------------------------------------

def find_counterexample(a, b):
    """Busca la cadena MÁS CORTA que un autómata acepta y el otro rechaza.

    Devuelve:
        None  -> no existe tal cadena: los autómatas son equivalentes.
        str   -> una cadena distinguidora. Ojo: puede ser "" (cadena vacía),
                 por eso hay que comparar con `is None` y no con `if not`.
    """
    # Si los alfabetos difieren se usa la unión: un símbolo que solo conoce un
    # autómata lleva al otro a "ningún estado" (conjunto vacío).
    alphabet = sorted(a.alphabet | b.alphabet)

    # Un nodo del recorrido es un par (situación en a, situación en b), donde
    # cada situación es el conjunto de estados posibles tras leer la misma cadena.
    start = (frozenset([a.initial_state]), frozenset([b.initial_state]))

    # parents recuerda de qué par vinimos y con qué símbolo. Sirve para dos
    # cosas: saber qué pares ya visitamos y reconstruir la cadena al final.
    parents = {start: None}
    queue = deque([start])  # BFS: se procesa primero lo más cercano al inicio

    while queue:
        pair = queue.popleft()
        set_a, set_b = pair  # "desempaquetado" de tupla

        # Si uno acepta y el otro no, la cadena que nos trajo hasta acá
        # es un contraejemplo. Como es BFS, es de las más cortas.
        if _is_accepting(a, set_a) != _is_accepting(b, set_b):
            return _rebuild_string(parents, pair)

        for symbol in alphabet:
            next_pair = (_step(a, set_a, symbol), _step(b, set_b, symbol))
            if next_pair not in parents:  # todavía no lo visitamos
                parents[next_pair] = (pair, symbol)
                queue.append(next_pair)

    return None  # recorrimos todo sin encontrar diferencias


def _rebuild_string(parents, pair):
    """Reconstruye la cadena caminando hacia atrás desde `pair` hasta el inicio."""
    symbols = []
    while parents[pair] is not None:
        pair, symbol = parents[pair]
        symbols.append(symbol)
    symbols.reverse()  # la construimos al revés, así que la damos vuelta
    return "".join(symbols)


def are_equivalent(a, b):
    """True si los dos autómatas aceptan el mismo lenguaje."""
    return find_counterexample(a, b) is None


# ---------------------------------------------------------------------------
# Método 2: prueba exhaustiva por cadenas (complemento empírico)
# ---------------------------------------------------------------------------

def compare_by_strings(a, b, max_length):
    """Prueba todas las cadenas de longitud 0 hasta `max_length`.

    Devuelve (cantidad_probada, primera_diferencia), donde la diferencia es
    None si los dos autómatas se comportaron igual en todas las cadenas.

    Cuidado con el crecimiento: hay |alfabeto|^n cadenas de longitud n. Con
    alfabeto binario y max_length=10 son 2047; con max_length=20 ya son más de 2 millones.
    """
    alphabet = sorted(a.alphabet | b.alphabet)
    tested = 0

    for length in range(max_length + 1):
        # product(alphabet, repeat=length) genera todas las combinaciones
        # posibles de `length` símbolos, por ejemplo ('0', '1', '1').
        for symbols in product(alphabet, repeat=length):
            string = "".join(symbols)
            tested += 1
            if accepts(a, string) != accepts(b, string):
                return tested, string

    return tested, None


# ---------------------------------------------------------------------------
# Verificación completa pedida por la consigna (puntos 3a y 3b)
# ---------------------------------------------------------------------------

def verify_minimization(original, dfa, minimized, max_length=8):
    """Ejecuta las verificaciones que pide la consigna y devuelve un resumen.

    original  -> el autómata tal como se leyó del archivo (AFND o AFD)
    dfa       -> el AFD resultante de la construcción de subconjuntos
    minimized -> el AFD mínimo

    3a) El lenguaje del mínimo es el mismo que el del original.
    3b) El mínimo no tiene más estados que el AFD del que se partió.
        Se compara contra el AFD y no contra el AFND original, porque un AFD
        equivalente puede necesitar más estados que el AFND (hasta 2^n).
    """
    counterexample = find_counterexample(original, minimized)
    tested, string_difference = compare_by_strings(original, minimized, max_length)

    return {
        # 3a
        "equivalent_to_original": counterexample is None,
        "counterexample": counterexample,
        "strings_tested": tested,
        "max_length": max_length,
        "string_difference": string_difference,
        # 3b
        "states_original": len(original.states),
        "states_dfa": len(dfa.states),
        "states_minimized": len(minimized.states),
        "not_bigger_than_dfa": len(minimized.states) <= len(dfa.states),
    }


def print_report(report):
    """Imprime el resultado de verify_minimization de forma legible."""

    def show(string):
        return "ε (cadena vacía)" if string == "" else repr(string)

    print("Verificación de equivalencia")
    print(f"  Estados: original={report['states_original']}, "
          f"AFD={report['states_dfa']}, mínimo={report['states_minimized']}")

    if report["equivalent_to_original"]:
        print("  [OK] 3a) Autómata producto: el mínimo y el original aceptan el mismo lenguaje")
    else:
        print(f"  [ERROR] 3a) Autómata producto: cadena distinguidora "
              f"{show(report['counterexample'])}")

    if report["string_difference"] is None:
        print(f"  [OK] 3a) Prueba por cadenas: {report['strings_tested']} cadenas "
              f"(hasta longitud {report['max_length']}) sin diferencias")
    else:
        print(f"  [ERROR] 3a) Prueba por cadenas: difieren en "
              f"{show(report['string_difference'])}")

    if report["not_bigger_than_dfa"]:
        print("  [OK] 3b) El mínimo no tiene más estados que el AFD")
    else:
        print("  [ERROR] 3b) El mínimo tiene MÁS estados que el AFD")


# ---------------------------------------------------------------------------
# Uso desde la terminal:  python equivalence.py tests/caso_1.json
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    from io_handler import automaton_from_dict, read_json
    from minimizer import minimize_dfa
    from nfa_to_dfa import complete_and_prune, nfa_to_dfa

    if len(sys.argv) != 2:
        print("Uso: python equivalence.py archivo.json")
        sys.exit(1)

    original = automaton_from_dict(read_json(sys.argv[1]))
    original.validate()
    if original.is_nfa():
        dfa = nfa_to_dfa(original)
    else:
        dfa, _ = complete_and_prune(original)
    minimized = minimize_dfa(dfa)
    print_report(verify_minimization(original, dfa, minimized))
