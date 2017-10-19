#!/usr/bin/env python
"""
 json utilities for larch objects
"""
import six
import json
import numpy as np
from base64 import b64encode, b64decode

try:
    import dill
    HAS_DILL = True
except ImportError:
    HAS_DILL = False

try:
    from pandas import DataFrame, Series, read_json
except ImportError:
    DataFrame = Series, type(NotImplemented)
    read_json = None

def encode4js(obj):
    """prepare an object for json encoding.
    has special handling for many Python types
    - pandas dataframes and series
    - numpy ndarrays
    - complex numbers
    """
    if isinstance(obj, DataFrame):
        return dict(__class__='PDataFrame', value=json.loads(obj.to_json()))
    elif isinstance(obj, DataFrame):
        return dict(__class__='PSeries', value=encode4js(obj.to_dict()))
    elif isinstance(obj, np.ndarray):
        if 'complex' in obj.dtype.name:
            val = [(obj.real).tolist(), (obj.imag).tolist()]
        elif obj.dtype.name == 'object':
            val = [encode4js(item) for item in out['value']]
        else:
            val = obj.flatten().tolist()
        return dict(__class__='NDArray', __shape__=obj.shape,
                    __dtype__=obj.dtype.name, value=val)
    elif isinstance(obj, (np.float, np.int)):
        return float(obj)
    elif isinstance(obj, six.string_types):
        return str(obj)
    elif isinstance(obj, np.complex):
        return dict(__class__='Complex', value=(obj.real, obj.imag))
    elif isinstance(obj, (tuple, list)):
        ctype = 'List'
        if isinstance(obj, tuple):
            ctype = 'Tuple'
        val = [encode4js(item) for item in obj]
        return dict(__class__=ctype, value=val)
    elif isinstance(obj, dict):
        out = dict(__class__='Dict')
        for key, val in obj.items():
            out[encode4js(key)] = encode4js(val)
        return out
    elif callable(obj):
        val = None
        if HAS_DILL:
            val = b64encode(dill.dumps(obj))
        return dict(__class__='Callable', __name__=obj.__name__, value=val)
    return obj

def decode4js(obj):
    """return decoded Python object from encoded object."""
    if not isinstance(obj, dict):
        return obj
    out = obj
    classname = obj.pop('__class__', None)
    if classname is None:
        return obj

    if classname == 'Complex':
        out = obj['value'][0] + 1j*obj['value'][1]
    elif classname in ('List', 'Tuple'):
        out = []
        for item in obj['value']:
            out.append(decode4js(item))
        if classname == 'Tuple':
            out = tuple(out)
    elif classname == 'NDArray':
        if obj['__dtype__'].startswith('complex'):
            re = np.fromiter(obj['value'][0], dtype='double')
            im = np.fromiter(obj['value'][1], dtype='double')
            out = re + 1j*im
        elif obj['__dtype__'].startswith('object'):
            val = [decode4js(v) for v in obj['value']]
            out = np.array(val,  dtype=obj['__dtype__'])
        else:
            out = np.fromiter(obj['value'], dtype=obj['__dtype__'])
        out.shape = obj['__shape__']
    elif classname == 'PDataFrame' and read_json is not None:
        out = read_json(jsond.dumps(obj['value']))
    elif classname == 'PSeries':
        out = Series(obj['value'])
    elif classname == 'Callable':
        out = obj['__name__']
        if HAS_DILL:
            out = b64decode(dill.load(obj))
    elif classname in ('Dict', 'dict'):
        out = {}
        for key, val in obj.items():
            out[key] = decode4js(val)
    return out
