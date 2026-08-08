# pyright: basic, reportArgumentType=false
'''Optional fluent builder for pysm state machines.'''
from .pysm import State, StateMachine, StateMachineException


class StateMachineBuilder(object):
    '''Small opt-in helper that builds machines through the public core API.'''

    def __init__(self, name, machine_class=StateMachine, state_class=State):
        self.root = machine_class(name)
        self.machine_class = machine_class
        self.state_class = state_class
        self._states = {(name,): self.root}

    def state(self, name, initial=False, parent_path=None):
        parent = self._resolve_machine(parent_path)
        path = self._child_path(parent, name)
        self._ensure_new_path(path)
        state = self.state_class(name)
        parent.add_state(state, initial=initial)
        self._states[path] = state
        return self

    def machine(self, name, initial=False, parent_path=None):
        parent = self._resolve_machine(parent_path)
        path = self._child_path(parent, name)
        self._ensure_new_path(path)
        machine = self.machine_class(name)
        parent.add_state(machine, initial=initial)
        self._states[path] = machine
        return self

    def transition(self, from_path, to_path, events, input=None, action=None,
                   condition=None, before=None, after=None):
        from_state = self._resolve_state(from_path)
        to_state = None if to_path is None else self._resolve_state(to_path)
        events = self._normalize_values(events)
        if input is not None:
            input = self._normalize_values(input)
        machine = from_state.parent
        if machine is None:
            raise StateMachineException(
                'Cannot add a transition from the root machine')
        machine.add_transition(
            from_state, to_state, events, input=input, action=action,
            condition=condition, before=before, after=after)
        return self

    def chain(self, names, events, parent_path=None, initial=False):
        names = list(names)
        if len(names) < 2:
            raise StateMachineException(
                'A chain needs at least two states: {0}'.format(names))
        if len(set(names)) != len(names):
            raise StateMachineException(
                'A chain cannot repeat a state name: {0}'.format(names))
        parent = self._resolve_machine(parent_path)
        under = self._path_for(parent)
        for name in names:
            self._ensure_new_path(under + (name,))
        for position, name in enumerate(names):
            self.state(name, initial=initial and position == 0,
                       parent_path=under)
        for before, after in zip(names, names[1:]):
            self.transition(under + (before,), under + (after,), events)
        return self

    def outline(self, path=None):
        state = self.root if path is None else self._resolve_state(path)
        children = ()
        if isinstance(state, StateMachine):
            children = tuple(
                self.outline(self._path_for(child))
                for child in sorted(state.states, key=lambda item: item.name))
        kind = 'machine' if isinstance(state, StateMachine) else 'state'
        return (state.name, kind, bool(state.initial), children)

    def build(self, initialize=True, fire_events_on_init=False):
        if initialize:
            self.root.initialize(fire_events_on_init=fire_events_on_init)
        return self.root

    def _resolve_machine(self, path):
        if path is None:
            return self.root
        state = self._resolve_state(path)
        if not isinstance(state, StateMachine):
            raise StateMachineException(
                'Path does not point to a state machine: {0}'.format(path))
        return state

    def _resolve_state(self, path):
        parts = self._normalize_path(path)
        if parts in self._states:
            return self._states[parts]

        matches = [state for key, state in self._states.items()
                   if key[-len(parts):] == parts]
        if not matches:
            raise StateMachineException('Unknown state path: {0}'.format(path))
        if len(matches) > 1:
            raise StateMachineException('Ambiguous state path: {0}'.format(
                path))
        return matches[0]

    def _child_path(self, parent, name):
        return self._path_for(parent) + (name,)

    def _path_for(self, state):
        for path, item in self._states.items():
            if item is state:
                return path
        raise StateMachineException('Unknown state: {0}'.format(state.name))

    def _ensure_new_path(self, path):
        if path in self._states:
            raise StateMachineException('State path already exists: {0}'.format(
                path))

    def _normalize_path(self, path):
        if isinstance(path, tuple):
            return path
        if isinstance(path, list):
            return tuple(path)
        if isinstance(path, str):
            if '/' in path:
                return tuple(part for part in path.split('/') if part)
            return (path,)
        raise StateMachineException('Unsupported state path: {0}'.format(path))

    def _normalize_values(self, values):
        if isinstance(values, str):
            return [values]
        return values
