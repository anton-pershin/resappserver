import collections

class Graph:
    def __init__(self, init_state):
        self._init_state = init_state
        self._initialized = False

    def run(self, data):
        if not self._initialized:
            self._init_state.idle_run([self._init_state.name], initialize_state=True)
            self._initialized = True
        cur_state = self._init_state
        while cur_state is not None:
            morph = _run_state(cur_state, data)
            if '__EXCEPTION__' in data:
                return data, False
            cur_state = morph(data)
            if '__EXCEPTION__' in data:
                return data, False
        return data, True

class State:
    __slots__ = [
        'name',
        'input_edges_number',
        'looped_edges_number',
        'activated_input_edges_number',
        'output_edges',
        'parallelization_policy',
        'parallel_branches_selection_policy',
        '_branching_states_history',
        ]
    def __init__(self, name, 
                 parallelization_policy=None,
                 parallel_branches_selection_policy=None,
                 ):
        self.name = name
        self.parallelization_policy = parallelization_policy
        self.parallel_branches_selection_policy = parallel_branches_selection_policy
        self.input_edges_number = 0
        self.looped_edges_number = 0
        self.activated_input_edges_number = 0
        self.output_edges = []
        self._branching_states_history = None

    def idle_run(self, branching_states_history, initialize_state=False):
#        print('{} {} -> '.format(self.name, branching_states_history), end='')
        if initialize_state:
            self.input_edges_number += 1
            if self.input_edges_number != 1:
                if self._is_looped_branch(branching_states_history):
#                    print('Looping found')
                    self.looped_edges_number += 1
#                else:
#                    print('Branches joint found')
#                print('\tStop going further')
                return # no need to go further if we already were there
            if self._branching_states_history is None:
                self._branching_states_history = branching_states_history
        else:
            self.activated_input_edges_number += 1 # BUG: here we need to choose somehow whether we proceed or not
#        if len(self.output_edges) == 0:
#            print('Terminate state found')
        if len(self.output_edges) == 1:
            self.output_edges[0].identity().idle_run(branching_states_history, initialize_state)
        else:
            for i, edge in enumerate(self.output_edges):
                next_state = edge.identity()
                next_state.idle_run(branching_states_history + [next_state.name], initialize_state)

    def connect_to(self, term_state, edge):
        edge.set_output_state(term_state)
        self.output_edges.append(edge)

    def run(self, data):
#        print(self.name, data['a'])
        self.activated_input_edges_number += 1
        if not self._ready_to_morph():
            return None # it means that this state waits for some incoming edges (it is a point of collision of several edges)
        self._reset_activity()
        if len(self.output_edges) == 0:
            return morphism_to_termination
        predicate_values = []
        for edge in self.output_edges:
            predicate_values.append(edge.predicate(data))
        selected_edge_indices = self.parallel_branches_selection_policy.select(predicate_values)
        if not selected_edge_indices:
            raise GraphUnexpectedTermination(
                'State {}: Predicate values {} do not conform selection policy'.format(self.name, predicate_values))
        selected_edges = [self.output_edges[i] for i in selected_edge_indices]
        return self.parallelization_policy.make_morphism(selected_edges)

    def _ready_to_morph(self):
        required_activated_input_edges_number = self.input_edges_number - self.looped_edges_number
        #print(self.input_edges_number, self.looped_edges_number)
        return self.activated_input_edges_number == required_activated_input_edges_number

    def _reset_activity(self):
        self.activated_input_edges_number = 0

    def _is_looped_branch(self, branching_states_history):
        return set(self._branching_states_history).issubset(branching_states_history)

class Edge:
    __slots__ = [
        '_predicate', 
        '_morphism', 
        '_output_state', 
        ]
    def __init__(self, predicate, morphism, output_state=None):
        self._predicate = predicate
        self._morphism = morphism
        self._output_state = output_state

    def set_output_state(self, output_state):
        self._output_state = output_state

    def predicate(self, data):
        return self._predicate(data)

    def morph(self, data):
        self._morphism(data)
        return self._output_state

    def identity(self):
        return self._output_state

def morphism_to_termination(data):
    return None

class SerialParallelizationPolicy:
#    def __init__(self, data):
#        self.data = data
    def __init__(self):
        pass

    def make_morphism(self, edges):
        def _morph(data):
            next_morphisms = [edge.morph for edge in edges]
            cur_morphisms = []
            while len(next_morphisms) != 1:
                cur_morphisms[:] = next_morphisms[:]
                del next_morphisms[:]
                for morph in cur_morphisms:
                    next_state = morph(data)
                    if next_state is None:
                        return None
                    next_morphism = _run_state(next_state, data)
                    if '__EXCEPTION__' in data:
                        return None
                    if next_morphism is not None:
                        next_morphisms.append(next_morphism)
            next_state = next_morphisms[0](data)
            return next_state
        return _morph

class OnlyOneSelectionPolicy:
    def __init__(self):
        pass

    def select(self, predicate_values):
        trues_indices = _get_trues(predicate_values)
        if len(trues_indices) != 1:
            return None
        return trues_indices

class AllSelectionPolicy:
    def __init__(self):
        pass

    def select(self, predicate_values):
        trues_indices = _get_trues(predicate_values)
        if len(trues_indices) != len(predicate_values):
            return None
        return trues_indices

class BadGraphStructure(Exception):
    pass

class GraphUnexpectedTermination(Exception):
    pass

def _get_trues(boolean_list):
    return [i for i, val in enumerate(boolean_list) if val == True]

def _run_state(state, data):
    try:
        next_morphism = state.run(data)
    except GraphUnexpectedTermination as e:
        data['__EXCEPTION__'] = str(e)
        return None
    return next_morphism