"""Lee y escribe automatas en el formato JSON del proyecto."""

import json
from automaton import Automaton

def read_json(file_path):
	"""Lee un archivo JSON y devuelve su contenido como objetos Python.

	Args:
		file_path: Ruta del archivo JSON que se quiere leer.

	Returns:
		Datos decodificados desde el archivo JSON.
	"""
	with open(file_path, "r", encoding="utf-8") as archivo:
		contenido = json.load(archivo)
		return contenido


def automaton_from_dict(data):
	"""Construye un automata a partir de un diccionario deserializado.

	Args:
		data: Diccionario con estados, alfabeto y transiciones del automata.

	Returns:
		Instancia de ``Automaton`` con los conjuntos reconstruidos.
	"""
	automaton = Automaton(
		set(data["states"]),
		set(data["alphabet"]),
		data["initial_state"],
		set(data["final_states"]),
		convert_transitions(data["transitions"])
    )
	return automaton


def convert_transitions(transitions_data):
	"""Convierte destinos de transiciones de listas a conjuntos.

	Args:
		transitions_data: Transiciones representadas con listas serializables.

	Returns:
		Diccionario de transiciones cuyos destinos son conjuntos.
	"""
	transitions = {}

	for state, symbols in transitions_data.items():
		transitions[state] = {}
		for symbol, destinations in symbols.items():
			transitions[state][symbol] = set(destinations)

	return transitions


def automaton_to_dict(automaton):
	"""Convierte un automata a un diccionario compatible con JSON.

	Args:
		automaton: Automata que se quiere serializar.

	Returns:
		Diccionario con listas en lugar de conjuntos no serializables.
	"""
	return {
		"states": list(automaton.states),
        "alphabet": list(automaton.alphabet),
        "initial_state": automaton.initial_state,
        "final_states": list(automaton.final_states),
        "transitions": {
			state: {
				symbol: list(destinations)
				for symbol, destinations in symbols.items()
			}
			for state, symbols in automaton.transitions.items()
		}
	}


def write_json(file_path, data):
	"""Escribe datos Python en un archivo JSON con formato legible.

	Args:
		file_path: Ruta del archivo que se quiere crear o sobrescribir.
		data: Datos serializables que se guardaran en el archivo.
	"""
	with open(file_path, "w", encoding="utf-8") as archivo:
		json.dump(data, archivo, indent=4, ensure_ascii=False)


