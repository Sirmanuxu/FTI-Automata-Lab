"""Define la estructura y las validaciones de un automata finito."""


class Automaton:
    """Representa un automata finito mediante estados y transiciones."""
    def __init__(
        self,
        states,
        alphabet,
        initial_state,
        final_states,
        transitions
    ):
        """Inicializa un automata con sus componentes principales.

        Args:
            states: Conjunto de estados del automata.
            alphabet: Conjunto de simbolos permitidos.
            initial_state: Estado desde el que comienza la ejecucion.
            final_states: Estados que aceptan una cadena terminada.
            transitions: Transiciones agrupadas por estado y simbolo.
        """
        self.states = states
        self.alphabet = alphabet
        self.initial_state = initial_state
        self.final_states = final_states
        self.transitions = transitions

    def get_destinations(self, state, symbol):
        """Devuelve los destinos alcanzables desde un estado con un simbolo.

        Args:
            state: Estado de origen.
            symbol: Simbolo de la transicion.

        Returns:
            Conjunto de estados destino, o un conjunto vacio si no existe
            la transicion.
        """
        return self.transitions.get(state,{}).get(symbol,set())
    
    def is_final_state(self, state):
        """Indica si un estado pertenece al conjunto de estados finales.

        Args:
            state: Estado que se quiere consultar.

        Returns:
            ``True`` si el estado es final; en caso contrario, ``False``.
        """
        return state in self.final_states
    
    def validate(self):
        """Comprueba que la definicion del automata sea consistente.

        Returns:
            ``True`` cuando todas las reglas de consistencia se cumplen.

        Raises:
            ValueError: Si existe un estado, simbolo o transicion invalida.
        """
        if isinstance(self.initial_state, set):
            raise ValueError("El estado inicial debe ser unico")
        if self.initial_state not in self.states:
            raise ValueError("El estado inicial debe pertenecer a states")
        if not self.final_states.issubset(self.states):
            raise ValueError("Los estados finales deben pertenecer a states")

        for state, symbols in self.transitions.items():
            if state not in self.states:
                raise ValueError(
                    f"El estado de origen '{state}' no pertenece a states"
                )

            for symbol, transitions in symbols.items():
                if symbol in {"", "epsilon", "lambda", "ε", "λ"}:
                    raise ValueError("No se permiten transiciones epsilon")
                if symbol not in self.alphabet:
                    raise ValueError(f"El símbolo '{symbol}' no está en el alfabeto: {self.alphabet}")
                for transition in transitions:
                    if transition not in self.states:
                        raise ValueError(
                            f"La transición {state}: {symbol} -> {transition} "
                            f"no pertenece a states: {self.states}"
                        )

        return True

    def is_nfa(self):
        """Indica si alguna transicion tiene mas de un estado destino.

        Returns:
            ``True`` si el automata es no determinista; en caso contrario,
            ``False``.
        """
        for state, symbols in self.transitions.items():
            for symbol, destinations in symbols.items():
                if len(destinations) > 1:
                    return True

        return False

    def is_complete(self):
        """Indica si todo estado tiene una transicion para cada simbolo.

        Returns:
            ``True`` si no falta ninguna transicion; en caso contrario,
            ``False``.
        """
        for state in self.states:
            for symbol in self.alphabet:
                if not self.get_destinations(state, symbol):
                    return False
        return True

    def reachable_states(self):
        """Calcula los estados alcanzables desde el estado inicial.

        Recorre el automata en anchura (BFS) siguiendo cada simbolo del
        alfabeto. Sirve tanto para AFD como para AFND: en un AFND, cada
        destino posible de una transicion se agrega por separado.

        Returns:
            Conjunto de estados alcanzables, incluyendo el inicial.
        """
        seen = {self.initial_state}
        pending = [self.initial_state]
        while pending:
            state = pending.pop()
            for symbol in self.alphabet:
                for destination in self.get_destinations(state, symbol):
                    if destination not in seen:
                        seen.add(destination)
                        pending.append(destination)
        return seen

    def is_dfa(self):
        """Indica si el automata ya es un AFD completo y sin estados
        inalcanzables, es decir, si no hace falta ninguna conversion.

        Returns:
            ``True`` si es determinista, completo y todos sus estados son
            alcanzables desde el inicial; en caso contrario, ``False``.
        """
        return (
            not self.is_nfa()
            and self.is_complete()
            and self.reachable_states() == self.states
        )

    def transition_count(self):
        """Cuenta la cantidad total de transiciones (origen, simbolo, destino).

        Returns:
            Numero entero de transiciones individuales del automata.
        """
        return sum(
            len(destinations)
            for symbols in self.transitions.values()
            for destinations in symbols.values()
        )


