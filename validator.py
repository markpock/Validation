import inspect
from copy import copy
from functools import update_wrapper, wraps
from typing import Callable, get_args, get_origin, Union


IMPORTS = [] # Because problems arise when trying to import things, it may
    # happen that imports need to be manually specified here as part of a
    # list.
COMPLEX_IMPORTS = [] # This exists similarly, just used for from x import y
    # syntax (should use a list of tuples or other iterable). Admittedly,
    # this is a very hacky solution.

def instance_or_union(obj: object, compared: type):
    """
    A version of isinstance that should work with Unions in Python 3.6+.
    """
    try:
        return isinstance(obj, compared)
    except TypeError:
        if get_origin(compared) is Union:
            return isinstance(obj, get_args(compared))
        return isinstance(obj, get_origin(compared))


def validatedclass(cls):
    """
    A class decorator to naively validate fields declared in a 
    dataclass-esque way as class-level variables.

    #### Example

    from dataclasses import dataclass
    
    from simulations.classes.ClassUtilities import validated

    @validated
    
    @dataclass

    class example:

        name: str

        id: int = 1000

        weight: Union[int, float] = 100

    #### Details
    - Validates a class for types using instance_or_union (just does basic
    type checking and throws a TypeError if the initialization doesn't
    pass).
    
    - Since this decorator is based on dataclass, use it with the dataclass
    decorator and syntax (class-level variables will be interpreted as
    fields, and must be type annotated).

    - Execution takes place like so: __new__ -> __init__: (Validation -> 
    Creation of fields) -> __post_init__.

    #### Other Notes
    - Checking whether an object is an instance of a Union is a Python
    3.10 feature, which should be kept in mind if a field is annotated as
    a Union and this validator class errors out. In theory, using
    instance_or_union should work but there may be some problems.
    """
    old_init = cls.__init__

    @wraps(cls.__init__)
    def validation(self, *args, **kwargs):
        validate(old_init, *args, **kwargs)
        # Creates the fields using the dataclass initialization
        old_init(self, *args, **kwargs)

    # Wraps the validation function in a function with the same signature as the init
    params = list(inspect.signature(old_init).parameters.keys())
    text = ', '.join([param for param in params])
    temp = dict(**globals(), **locals())
    while True:
        for imp in IMPORTS:
            exec(f'import {imp}', temp, temp)
        for complex in COMPLEX_IMPORTS:
            exec(f'from {complex[0]} import {complex[1]}')
        try:
            exec(f'from typing import Union, Optional\n'
                 f'def func{inspect.signature(old_init)}:\n'
                 f'\tvalidation({text})', temp, temp)
            break
        except NameError as error:
            try:
                exec(f'import {error.name}', temp, temp)
            except:
                try:
                    exec(f'from typing import {error.name}', temp, temp)
                except:
                    exec(f'from types import {error.name}', temp, temp)


    # Changes attributes of the new initialization to match the old
    new_init = update_wrapper(temp['func'], old_init)
    setattr(cls, '__init__', new_init)
    return cls


def validatedfunction(func: Callable):
    """
    A function decorator to validate the arguments of a type-annotated function.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        validate(func, *args, **kwargs)
        func(*args, **kwargs)
        
    return wrapper


def validate(func: Callable, *args, **kwargs):
    """
    Validates the parameters of an arbitrary callable.
    """

    # Uses inspect to get the parameters and passed arguments
    arguments = copy(kwargs)
    params = inspect.signature(func).parameters
    paramlist = list(params.keys())
    for index in range(len(args)):
        if func.__name__ == '__init__':
            index += 1
        arguments[paramlist[index]] = args[index]
    bad_args, bad_types, good_types = [], [], []
    
    # Actually does the parameter checking
    for argument in arguments:
        value = arguments[argument]
        required_type = params[argument].annotation
        if not instance_or_union(value, required_type):
            bad_args.append(argument)
            bad_types.append(str(type(value))[8:-2])
            if str(required_type).startswith('typing'):
                good_types.append(str(required_type)[7:])
            else:
                good_types.append(str(required_type)[8:-2])
                
    # Raises the error if necessary
    plural = ''
    if len(bad_args) > 1:
        plural = 's'
    if len(bad_args) > 0:
        raise TypeError(f'Argument{plural} {str(bad_args)[1:-1]} was passed incorrectly, '
                    f'of type{plural} {str(bad_types)[1:-1]}, should be of type{plural} '
                    f'{str(good_types)[1:-1]}.')
