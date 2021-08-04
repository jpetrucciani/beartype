#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
Project-wide **Python module tester** unit tests.

This submodule unit tests the public API of the private
:mod:`beartype._util.mod.utilmodtest` submodule.
'''

# ....................{ IMPORTS                           }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To raise human-readable test errors, avoid importing from
# package-specific submodules at module scope.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
from pytest import raises

# ....................{ TESTS ~ tester                    }....................
def test_is_module() -> None:
    '''
    Test the :func:`beartype._util.mod.utilmodtest.is_module` tester.
    '''

    # Defer heavyweight imports.
    from beartype._util.mod.utilmodtest import is_module

    # Assert this tester accepts the name of a (possibly unimported) existing
    # importable module.
    assert is_module(
        'beartype_test.a00_unit.data.util.py.data_utilpymodule_good') is True

    # Assert this tester accepts the name of an already imported module.
    assert is_module(
        'beartype_test.a00_unit.data.util.py.data_utilpymodule_good') is True

    # Assert this tester rejects the name of a module guaranteed *NOT* to
    # exist, because we fully control the "beartype_test" package.
    assert is_module(
        'beartype_test.a00_unit.data.util.py.data_utilpymodule_nonexistent'
    ) is False

    # Assert this function raises the expected exception when passed the name
    # of an existing unimportable module.
    with raises(ValueError):
        is_module('beartype_test.a00_unit.data.util.py.data_utilpymodule_bad')