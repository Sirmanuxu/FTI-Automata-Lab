"""Minimiza automatas finitos deterministas completos."""

from automaton import Automaton


def minimize_dfa(dfa: Automaton):
    """Minimiza un AFD completo usando el algoritmo recursivo de Moore.

    Args:
        dfa: Automata finito determinista completo que se va a minimizar.

    Returns:
        Un ``Automaton`` equivalente con las particiones minimizadas.
    """
    partitions = []

    non_final_states = dfa.states - dfa.final_states
    if non_final_states:
        partitions.append(non_final_states)
    if dfa.final_states:
        partitions.append(set(dfa.final_states))

    def refine_partition(partition, current_partitions, k):
        """Refina una particion usando cadenas de longitud hasta ``k + 1``.

        Args:
            partition: Grupo de estados que se esta refinando.
            current_partitions: Particiones calculadas en la ronda actual.
            k: Longitud maxima considerada en la ronda anterior.

        Returns:
            Lista de grupos resultantes del refinamiento.
        """
        if len(partition) == 1:
            return [set(partition)]

        state_to_partition = {}
        for partition_index, current_partition in enumerate(current_partitions):
            for state in current_partition:
                state_to_partition[state] = partition_index

        groups = {}
        for state in partition:
            signature = tuple(
                state_to_partition[
                    next(iter(dfa.transitions[state][symbol]))
                ]
                for symbol in sorted(dfa.alphabet)
            )
            groups.setdefault(signature, set()).add(state)

        refined_partition = list(groups.values())
        if refined_partition == [partition]:
            return [set(partition)]

        return refined_partition

    def refine_partitions(current_partitions, k):
        """Ejecuta rondas de Moore hasta que las particiones se estabilicen.

        Args:
            current_partitions: Particiones de estados de la ronda actual.
            k: Longitud maxima considerada en la ronda actual.

        Returns:
            Particiones finales, sin grupos que puedan separarse.
        """
        refined_partitions = []
        changed = False

        for partition in current_partitions:
            new_partitions = refine_partition(partition, current_partitions, k)
            refined_partitions.extend(new_partitions)
            if new_partitions != [partition]:
                changed = True

        if not changed:
            return current_partitions

        return refine_partitions(refined_partitions, k + 1)

    partitions = refine_partitions(partitions, 0)

    def partition_name(partition):
        """Genera un nombre estable para el estado que representa un grupo.

        Args:
            partition: Grupo de estados que se quiere nombrar.

        Returns:
            Nombre de un estado o de un grupo de estados minimizados.
        """
        names = sorted(str(state) for state in partition)
        if len(names) == 1:
            return names[0]

        members = set()
        for name in names:
            if name.startswith("{") and name.endswith("}"):
                members.update(
                    member.strip() for member in name[1:-1].split(",")
                )
            else:
                members.add(name)

        return "{" + ", ".join(sorted(members)) + "}"

    state_to_name = {}
    for partition in partitions:
        name = partition_name(partition)
        for state in partition:
            state_to_name[state] = name

    minimized_states = set(state_to_name.values())
    minimized_transitions = {}

    for partition in partitions:
        representative = next(iter(partition))
        minimized_state = state_to_name[representative]
        minimized_transitions[minimized_state] = {}

        for symbol in dfa.alphabet:
            destination = next(iter(dfa.transitions[representative][symbol]))
            minimized_transitions[minimized_state][symbol] = {
                state_to_name[destination]
            }

    minimized_final_states = {
        state_to_name[state]
        for state in dfa.final_states
    }

    return Automaton(
        states=minimized_states,
        alphabet=set(dfa.alphabet),
        initial_state=state_to_name[dfa.initial_state],
        final_states=minimized_final_states,
        transitions=minimized_transitions,
    )
