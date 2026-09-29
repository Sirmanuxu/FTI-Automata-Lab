"""Convierte automatas finitos no deterministas en deterministas."""

from automaton import Automaton


def nfa_to_dfa(nfa: Automaton):
    """Convierte un AFND sin transiciones epsilon en un AFD completo.

    Args:
        nfa: Automata finito no determinista que se va a convertir.

    Returns:
        Un ``Automaton`` determinista equivalente al automata recibido.
    """
    # Cada estado interno sigue siendo un conjunto de estados del AFND.
    initial_subset = frozenset([nfa.initial_state])
    dfa_states = {subset_name(initial_subset)}
    dfa_transitions = {}
    dfa_final_states = set()
    unprocessed_states = [initial_subset]

    initial_name = subset_name(initial_subset)
    if nfa.initial_state in nfa.final_states:
        dfa_final_states.add(initial_name)

    while unprocessed_states:
        current_subset = unprocessed_states.pop()
        current_name = subset_name(current_subset)
        dfa_transitions[current_name] = {}

        for symbol in nfa.alphabet:
            next_subset = set()

            for nfa_state in current_subset:
                state_transitions = nfa.transitions.get(nfa_state, {})
                next_subset.update(state_transitions.get(symbol, set()))

            next_subset = frozenset(next_subset)
            next_name = subset_name(next_subset)
            dfa_transitions[current_name][symbol] = {next_name}

            if next_name not in dfa_states:
                dfa_states.add(next_name)
                unprocessed_states.append(next_subset)

            if any(state in nfa.final_states for state in next_subset):
                dfa_final_states.add(next_name)

    return Automaton(
        states=dfa_states,
        alphabet=nfa.alphabet,
        initial_state=initial_name,
        final_states=dfa_final_states,
        transitions=dfa_transitions
    )


SINK_STATE = "∅"


def complete_and_prune(dfa):
    """Completa y poda un automata que ya es determinista, sin renombrarlo.

    A diferencia de ``nfa_to_dfa``, esta funcion se usa cuando el automata de
    entrada ya es un AFD (no hace falta construccion por subconjuntos) pero
    puede tener transiciones faltantes o estados inalcanzables. Mantiene los
    nombres originales de los estados para que el resultado sea reconocible.

    Args:
        dfa: Automata determinista (no necesariamente completo ni podado).

    Returns:
        Una tupla ``(automaton, changed)`` donde ``automaton`` es el AFD
        completo y podado, y ``changed`` indica si se modifico algo respecto
        del original (para decidir si vale la pena mostrarlo como una etapa
        aparte).
    """
    reachable = dfa.reachable_states()
    needs_sink = any(
        not dfa.get_destinations(state, symbol)
        for state in reachable
        for symbol in dfa.alphabet
    )

    states = set(reachable)
    transitions = {
        state: {
            symbol: set(destinations)
            for symbol, destinations in dfa.transitions.get(state, {}).items()
        }
        for state in reachable
    }

    if needs_sink:
        states.add(SINK_STATE)
        transitions[SINK_STATE] = {symbol: {SINK_STATE} for symbol in dfa.alphabet}
        for state in reachable:
            transitions.setdefault(state, {})
            for symbol in dfa.alphabet:
                if not transitions[state].get(symbol):
                    transitions[state][symbol] = {SINK_STATE}

    result = Automaton(
        states=states,
        alphabet=set(dfa.alphabet),
        initial_state=dfa.initial_state,
        final_states=set(dfa.final_states) & reachable,
        transitions=transitions,
    )
    changed = needs_sink or reachable != dfa.states
    return result, changed


def subset_name(subset):
    """Devuelve un nombre estable y serializable para un subconjunto.

    Args:
        subset: Subconjunto de estados que representa un estado del AFD.

    Returns:
        Nombre textual ordenado del subconjunto o ``"∅"`` si esta vacio.
    """
    if not subset:
        return "∅"
    return "{" + ", ".join(sorted(str(state) for state in subset)) + "}"