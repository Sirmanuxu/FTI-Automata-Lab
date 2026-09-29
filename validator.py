"""Valida cadenas recorriendo las transiciones de un automata."""


def trace_string(automaton, input_string):
    """Simula una cadena paso a paso, de forma iterativa (sin recursion).

    Funciona igual para un AFD (un unico estado activo en todo momento) que
    para un AFND (un conjunto de estados posibles, que puede crecer o
    reducirse a medida que se leen simbolos).

    Args:
        automaton: Automata (AFD o AFND) sobre el que se simula la cadena.
        input_string: Cadena a evaluar.

    Returns:
        Un diccionario con:
            ``steps``: lista de tuplas ``(simbolo, conjunto_de_estados)``,
                una por cada simbolo leido, en orden. El primer elemento
                tiene simbolo ``None`` y el conjunto inicial.
            ``accepted``: ``True`` si el conjunto final incluye un estado
                de aceptacion.
            ``error``: mensaje de error si algun simbolo no pertenece al
                alfabeto, o ``None`` si la cadena es valida.

    Raises:
        No lanza excepciones: un simbolo invalido corta la simulacion y se
        informa mediante la clave ``error``, para no interrumpir la
        comparacion de varias cadenas o varios automatas en la interfaz.
    """
    current = {automaton.initial_state}
    steps = [(None, frozenset(current))]

    for symbol in input_string:
        if symbol not in automaton.alphabet:
            return {
                "steps": steps,
                "accepted": False,
                "error": f"El símbolo '{symbol}' no pertenece al alfabeto",
            }
        current = {
            destination
            for state in current
            for destination in automaton.get_destinations(state, symbol)
        }
        steps.append((symbol, frozenset(current)))

    accepted = any(state in automaton.final_states for state in current)
    return {"steps": steps, "accepted": accepted, "error": None}


def validate_string(automaton, input_string):
    """Comprueba una cadena usando la definicion completa de un automata."""
    input_symbols = list(input_string)
    invalid_symbols = [
        symbol for symbol in input_symbols if symbol not in automaton.alphabet
    ]
    if invalid_symbols:
        invalid_text = ", ".join(sorted(set(invalid_symbols)))
        raise ValueError(f"Simbolos fuera del alfabeto: {invalid_text}")

    return validation(
        automaton.initial_state,
        automaton.transitions,
        automaton.final_states,
        input_symbols,
    )


def validation(current_state, transitions: dict, final_states, input_symbols: list):
    """Comprueba recursivamente si una cadena es aceptada por un automata.

    Args:
        current_state: Estado desde el que comienza el recorrido actual.
        transitions: Transiciones agrupadas por estado y simbolo.
        final_states: Estados que aceptan una cadena completa.
        input_symbols: Simbolos restantes por consumir.

    Returns:
        ``True`` si alguna ruta termina en un estado final; en caso
        contrario, ``False``.
    """

    if not input_symbols:
        return current_state in final_states

    current_symbol = input_symbols[0]
    remaining_symbols = input_symbols[1:]

    state_transitions = transitions.get(current_state, {})
    possible_transitions = state_transitions.get(current_symbol, set())

    if not possible_transitions:
        return False

    for next_state in possible_transitions:
        if validation(next_state, transitions, final_states, remaining_symbols):
            return True

    return False

    