#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2020 Cecil Curry.
# See "LICENSE" for further details.

'''
**Beartypistry** (i.e., singleton dictionary mapping from the fully-qualified
classnames of all type hints annotating callables decorated by the
:func:`beartype.beartype` decorator to those types).**

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                              }....................
#FIXME: For efficiency, register tuples under their numeric hashes rather than
#strings embedding numeric hashes formatted as "+{numeric_hash}". Thus:
#* Tuples would be registered instead with numeric hashes.
#* Types would continue to be registered with fully-qualified classnames.
#
#Note that there's guaranteed to be *NO* key collisions between the two, as
#the first characters of Python identifiers and thus classnames are prohibited
#from being digits. Conversely, all characters (and thus the first characters)
#of numeric hashes are guaranteed to be digits. Ergo, no collisions.

# ....................{ IMPORTS                           }....................
from beartype.roar import (
    BeartypeCallHintForwardRefException,
    BeartypeDecorHintForwardRefException,
    _BeartypeDecorBeartypistryException,
)
from beartype._decor._code.codesnip import PARAM_NAME_TYPISTRY
from beartype._util.cache.utilcachecall import callable_cached
from beartype._util.hint.nonpep.utilhintnonpeptest import (
    die_unless_hint_nonpep)
from beartype._util.py.utilpymodule import (
    die_unless_module_attr_name,
    import_module_attr,
)
from beartype._util.utilclass import (
    die_unless_class,
    is_class_builtin,
    is_classname_builtin,
)
from beartype._util.utilobject import (
    get_object_classname,
    get_object_class_basename,
)

# See the "beartype.__init__" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ CONSTANTS                         }....................
_TYPISTRY_HINT_NAME_TUPLE_PREFIX = '+'
'''
**Beartypistry tuple key prefix** (i.e., substring prefixing the keys of all
beartypistry key-value pairs whose values are tuples).

Since fully-qualified classnames are guaranteed *not* to be prefixed by this
prefix, this prefix suffices to uniquely distinguish key-value pairs whose
values are types from pairs whose values are tuples.
'''

# ....................{ CONSTANTS ~ code                  }....................
_CODE_TYPISTRY_HINT_NAME_TO_HINT_PREFIX = PARAM_NAME_TYPISTRY + '['
'''
Substring prefixing a Python expression mapping from the subsequent string to
an arbitrary object cached by the beartypistry singleton via the private
beartypistry parameter.
'''


_CODE_TYPISTRY_HINT_NAME_TO_HINT_SUFFIX = ']'
'''
Substring prefixing a Python expression mapping from the subsequent string to
an arbitrary object cached by the beartypistry singleton via the private
beartypistry parameter.
'''

# ....................{ REGISTRARS ~ forwardref           }....................
#FIXME: Unit test us up.
@callable_cached
def register_typistry_forwardref(hint_classname: str) -> str:
    '''
    Register the passed **fully-qualified forward reference** (i.e., string
    whose value is the fully-qualified name of a user-defined class that
    typically has yet to be defined) with the beartypistry singleton *and*
    return a Python expression evaluating to this class when accessed via the
    private ``__beartypistry`` parameter implicitly passed to all wrapper
    functions generated by the :func:`beartype.beartype` decorator.

    This function is memoized for both efficiency *and* safety, preventing
    accidental reregistration.

    Parameters
    ----------
    hint_classname : object
        Forward reference to be registered, defined as either:

        * A string whose value is the syntactically valid name of a class.
        * An instance of the :class:`typing.ForwardRef` class.

    Returns
    ----------
    str
        Python expression evaluating to the user-defined referred to by this
        forward reference when accessed via the private ``__beartypistry``
        parameter implicitly passed to all wrapper functions generated by the
        :func:`beartype.beartype` decorator.

    Raises
    ----------
    BeartypeDecorHintForwardRefException
        If this forward reference is *not* a syntactically valid
        fully-qualified classname.
    '''

    # If this object is *NOT* the syntactically valid fully-qualified name of a
    # module attribute that may or may not actually exist, raise an exception.
    die_unless_module_attr_name(
        module_attr_name=hint_classname,
        exception_label='Forward reference',
        exception_cls=BeartypeDecorHintForwardRefException,
    )

    # Return a Python expression evaluating to this type *WITHOUT* explicitly
    # registering this forward reference with the beartypistry singleton. Why?
    # Because the Beartypistry.__missing__() dunder method implicitly handles
    # forward references by dynamically registering types on their first access
    # if *NOT* already registered. Ergo, our job is actually done here.
    return (
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_PREFIX}{repr(hint_classname)}'
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_SUFFIX}'
    )

# ....................{ REGISTRARS ~ type                 }....................
@callable_cached
def register_typistry_type(hint: type) -> str:
    '''
    Register the passed **PEP-noncompliant type** (i.e., class neither defined
    by the :mod:`typing` module *nor* subclassing such a class) with the
    beartypistry singleton *and* return a Python expression evaluating to this
    type when accessed via the private ``__beartypistry`` parameter implicitly
    passed to all wrapper functions generated by the :func:`beartype.beartype`
    decorator.

    This function is syntactic sugar improving consistency throughout the
    codebase, but is otherwise roughly equivalent to:

        >>> from beartype._decor._typistry import bear_typistry
        >>> from beartype._util.utilobject import get_object_classname
        >>> bear_typistry[get_object_classname(hint)] = hint

    This function is memoized for both efficiency *and* safety, preventing
    accidental reregistration.

    Parameters
    ----------
    hint : type
        PEP-noncompliant type to be registered.

    Returns
    ----------
    str
        Python expression evaluating to this type when accessed via the private
        ``__beartypistry`` parameter implicitly passed to all wrapper functions
        generated by the :func:`beartype.beartype` decorator.

    Raises
    ----------
    _BeartypeDecorBeartypistryException
        If this object is either:

        * *Not* a type.
        * **PEP-compliant** (i.e., either a class defined by the :mod:`typing`
          module *or* subclass of such a class and thus a PEP-compliant type
          hint, which all violate standard type semantics and thus require
          PEP-specific handling).
    '''

    # If this object is *NOT* a type, raise an exception.
    die_unless_class(hint)
    # Else, this object is a type.
    #
    # Note that we defer all further validation of this type to the
    # Beartypistry.__setitem__() method implicitly invoked on subsequently
    # assigning this type as a "bear_typistry" key.

    # If this type is a builtin (i.e., globally accessible C-based type
    # requiring *no* explicit importation), this type requires no registration.
    # In this case, return the unqualified basename of this type as is.
    if is_class_builtin(hint):
        return get_object_class_basename(hint)
    # Else, this type is *NOT* a builtin and thus requires registration.
    # assert hint_basename != 'NoneType'

    # Fully-qualified name of this type.
    hint_classname = get_object_classname(hint)

    # If this type has yet to be registered with the beartypistry singleton, do
    # so.
    #
    # Note that the beartypistry singleton's __setitem__() dunder method
    # intentionally raises exceptions on attempts to re-register the same
    # object twice, as tuple re-registration requires special handling to avoid
    # hash collisions. Nonetheless, this is a non-issue. Why? Since this
    # function is memoized, re-registration should *NEVER* happen.
    bear_typistry[hint_classname] = hint

    # Return a Python expression evaluating to this type.
    return (
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_PREFIX}{repr(hint_classname)}'
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_SUFFIX}'
    )

# ....................{ REGISTRARS ~ tuple                }....................
@callable_cached
def register_typistry_tuple(
    # Mandatory parameters.
    hint: tuple,

    # Optional parameters.
    is_types_unique: bool = False,
) -> type:
    '''
    Register the passed tuple of one or more **PEP-noncompliant types** (i.e.,
    classes neither defined by the :mod:`typing` module *nor* subclassing such
    classes) with the beartypistry singleton *and* return a Python
    expression evaluating to this tuple when accessed via the private
    ``__beartypistry`` parameter implicitly passed to all wrapper functions
    generated by the :func:`beartype.beartype` decorator.

    This function is memoized for both efficiency *and* safety, preventing
    accidental reregistration.

    Design
    ----------
    Unlike types, tuples are commonly dynamically constructed on-the-fly by
    various tuple factories (e.g., :attr:`beartype.cave.NoneTypeOr`,
    :attr:`typing.Optional`) and hence have no reliable fully-qualified names.
    Instead, this function synthesizes the string uniquely identifying this
    tuple as the concatenation of:

    * The magic substring :data:`_TYPISTRY_HINT_NAME_TUPLE_PREFIX`. Since
      fully-qualified classnames uniquely identifying types as beartypistry
      keys are guaranteed to *never* contain this substring, this substring
      prevents collisions between tuple and type names.
    * This tuple's hash. Note that this tuple's object ID is intentionally
      *not* embedded in this string. Two tuples with the same items are
      typically different objects and thus have different object IDs, despite
      producing identical hashes: e.g.,

          >>> ('Das', 'Kapitel',) is ('Das', 'Kapitel',)
          False
          >>> id(('Das', 'Kapitel',)) == id(('Das', 'Kapitel',))
          False
          >>> hash(('Das', 'Kapitel',)) == hash(('Das', 'Kapitel',))
          True

      The exception is the empty tuple, which is a singleton and thus *always*
      has the same object ID and hash: e.g.,

          >>> () is ()
          True
          >>> id(()) == id(())
          True
          >>> hash(()) == hash(())
          True

    Identifying tuples by their hashes enables the beartypistry singleton to
    transparently cache duplicate tuple unions having distinct object IDs as
    the same underlying object, reducing space consumption. While hashing
    tuples *does* impact time performance, the tangible gains are considered
    worth the cost.

    Parameters
    ----------
    hint : tuple
        Tuple of all PEP-noncompliant types to be registered.
    is_types_unique : bool
        ``True`` only if the caller guarantees this tuple to contain *no*
        duplicates. If ``False``, this function assumes this tuple to contain
        duplicates by internally:

        #. Coercing this tuple into a set, thus implicitly ignoring both
           duplicates and ordering of types in this tuple.
        #. Coercing that set back into another tuple.
        #. If these two tuples differ, the passed tuple contains one or more
           duplicates; in this case, the duplicate-free tuple is registered.
        #. Else, the passed tuple contains no duplicates; in this case, the
           passed tuple is registered.

        Ergo, this boolean does *not* simply enable an edge-case optimization
        (though it certainly does do that). This boolean enables callers to
        guarantee that this function registers the passed tuple rather than a
        new tuple internally created by this function.

    Returns
    ----------
    str
        Python expression evaluating to this tuple when accessed via the
        private ``__beartypistry`` parameter implicitly passed to all wrapper
        functions generated by the :func:`beartype.beartype` decorator.

    Raises
    ----------
    _BeartypeDecorBeartypistryException
        If this tuple is either:

        * *Not* a tuple.
        * Is a tuple containing one or more items that are either:

          * *Not* types.
          * **PEP-compliant types** (i.e., either classes defined by the
            :mod:`typing` module *or* subclasses of such classes and thus
            PEP-compliant type hints, which all violate standard type semantics
            and thus require PEP-specific handling).

    See Also
    ----------
    :func:`register_typistry_tuple_from_frozenset`
        Further details.
    '''
    assert isinstance(is_types_unique, bool), (
        f'{repr(is_types_unique)} not bool.')

    # If this object is *NOT* a tuple, raise an exception.
    if not isinstance(hint, tuple):
        raise _BeartypeDecorBeartypistryException(
            f'Beartypistry tuple {repr(hint)} not tuple.')
    # Else, this object is a tuple.
    #
    # Note that we defer all further validation of this tuple and its contents
    # to the Beartypistry.__setitem__() method, implicitly invoked on
    # subsequently assigning a "bear_typistry" key-value pair.

    # If this tuple only contains one type, register only this type.
    if len(hint) == 1:
        return register_typistry_type(hint[0])
    # Else, this tuple either contains no types or two or more types.

    # If the caller failed to guarantee this tuple to be duplicate-free...
    if not is_types_unique:
        # Coerce this tuple into a set (thus ignoring duplicates and ordering).
        hint_set = set(hint)

        # Coerce this set back into a duplicate-free tuple, replacing the
        # passed tuple with this tuple.
        hint = tuple(hint_set)
    # This tuple is now guaranteed to be duplicate-free.

    # Name uniquely identifying this tuple as a beartypistry key.
    hint_name = f'{_TYPISTRY_HINT_NAME_TUPLE_PREFIX}{hash(hint)}'

    #FIXME: *WOOPS.* Memoization doesn't help us much here, as we need to
    #explicitly test for differing tuple objects that have the same items.
    #FIXME: *UNIT TEST* this up, please.

    # While this name collides with an existing name of a tuple previously
    # registered with the beartypistry singleton, iteratively disambiguate this
    # name by appending an arbitrary character to this name.
    #
    # Note that, if this name *DOES* collide with one or more existing names of
    # tuples previously registered with the beartypistry singleton, the passed
    # tuple is guaranteed to *NOT* be those tuples. Why? Because this function
    # is memoized, the passed tuple is necessarily distinct from those passed
    # to all prior calls of this function and thus requires registration.
    while hint_name in bear_typistry:
        hint_name += '~'

    # Register this tuple with the beartypistry singleton.
    bear_typistry[hint_name] = hint

    # Return a Python expression evaluating to this tuple.
    return (
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_PREFIX}{repr(hint_name)}'
        f'{_CODE_TYPISTRY_HINT_NAME_TO_HINT_SUFFIX}'
    )

# ....................{ CLASSES                           }....................
class Beartypistry(dict):
    '''
    **Beartypistry** (i.e., singleton dictionary mapping from strings uniquely
    identifying PEP-noncompliant type hints annotating callables decorated
    by the :func:`beartype.beartype` decorator to those hints).**

    This dictionary implements a global registry for **PEP-noncompliant type
    hints** (i.e., :mod:`beartype`-specific annotation *not* compliant with
    annotation-centric PEPs), including:

    * Non-:mod:`typing` types (i.e., classes *not* defined by the :mod:`typing`
      module, which are PEP-compliant type hints that fail to comply with
      standard type semantics and are thus beyond the limited scope of this
      PEP-noncompliant-specific dictionary).
    * Tuples of non-:mod:`typing` types, commonly referred to as **tuple
      unions** in :mod:`beartype` jargon.

    This dictionary efficiently shares these hints across all type-checking
    wrapper functions generated by this decorator, enabling these functions to:

    * Obtain type and tuple objects at wrapper runtime given only the strings
      uniquely identifying those objects hard-coded into the bodies of those
      wrappers at decoration time.
    * Resolve **forward references** (i.e., type hints whose values are strings
      uniquely identifying type and tuple objects) at wrapper runtime, which
      this dictionary supports by defining a :meth:`__missing__` dunder method
      dynamically adding a new mapping from each such reference to the
      corresponding object on the first attempt to access that reference.
    '''

    # ..................{ DUNDERS                           }..................
    def __setitem__(self, hint_name: str, hint: object) -> None:
        '''
        Dunder method explicitly called by the superclass on setting the passed
        key-value pair with``[``- and ``]``-delimited syntax, mapping the
        passed string uniquely identifying the passed PEP-noncompliant type
        hint to that hint.

        Parameters
        ----------
        hint_name: str : str
            String uniquely identifying this hint in a manner dependent on the
            type of this hint. Specifically, if this hint is:

            * A non-:mod:`typing` type, this is the fully-qualified classname
              of the module attribute defining this type.
            * A tuple of non-:mod:`typing` types, this is a string:

              * Prefixed by the :data:`_TYPISTRY_HINT_NAME_TUPLE_PREFIX`
                substring distinguishing this string from fully-qualified
                classnames.
              * Hash of these types (ignoring duplicate types and type order in
                this tuple).

        Raises
        ----------
        TypeError
            If this hint is **unhashable** (i.e., *not* hashable by the builtin
            :func:`hash` function and thus unusable in hash-based containers
            like dictionaries and sets). All supported type hints are hashable.
        _BeartypeDecorBeartypistryException
            If either:

            * This name either:

              * *Not* a string.
              * Is an existing string key of this dictionary, implying this
                name has already been registered, implying a key collision
                between the type or tuple already registered under this key and
                this passed type or tuple to be reregistered under this key.
                Since the high-level :func:`register_typistry_type` and
                :func:`register_typistry_tuple` functions implicitly calling
                this low-level dunder method are memoized *and* since the
                latter function explicitly avoids key collisions by detecting
                and uniquifying colliding keys, every call to this method
                should be passed a unique key.

            * This hint is either:

              * A type but either:

                * This name is *not* the fully-qualified classname of this
                  type.
                * This type is **PEP-compliant** (i.e., either a class defined
                  by the :mod:`typing` module *or* subclass of such a class and
                  thus a PEP-compliant type hint, which all violate standard
                  type semantics and thus require PEP-specific handling).

              * A tuple but either:

                * This name is *not* prefixed by the magic substring
                  :data:`_TYPISTRY_HINT_NAME_TUPLE_PREFIX`.
                * This tuple contains one or more items that are either:

                  * *Not* types.
                  * PEP-compliant types.
        '''

        # If this name is *NOT* a string, raise an exception.
        if not isinstance(hint_name, str):
            raise _BeartypeDecorBeartypistryException(
                f'Beartypistry key {repr(hint_name)} not string.')
        # Else, this name is a string.
        #
        # If this name is an existing key of this dictionary, this name has
        # already been registered, implying a key collision between the type or
        # tuple already registered under this key and the passed type or
        # tuple to be reregistered under this key. In this case, raise an
        # exception.
        elif hint_name in self:
            raise _BeartypeDecorBeartypistryException(
                f'Beartypistry key "{hint_name}" already registered '
                f'(i.e., key collision between '
                f'prior registered value {repr(self[hint_name])} and '
                f'newly registered value {repr(hint)}).')
        # Else, this name is *NOT* an existing key of this dictionary.
        #
        # If this hint is a class...
        #
        # Note that although *MOST* classes are PEP-noncompliant (e.g., the
        # builtin "str" type), some classes are PEP-compliant (e.g., the
        # stdlib "typing.SupportsInt" protocol). Since both PEP-noncompliant
        # and -compliant classes are shallowly type-checkable via the
        # isinnstance() builtin, there exists no demonstrable benefit to
        # distinguishing between either here.
        elif isinstance(hint, type):
            # Fully-qualified classname of this type as declared by this type.
            hint_clsname = get_object_classname(hint)

            # If...
            if (
                # The passed name is not this classname *AND*...
                hint_name != hint_clsname and
                # This classname does not imply this type to be a builtin...
                #
                # Note that builtin types are registered under their
                # unqualified basenames (e.g., "list" rather than
                # "builtins.list") for runtime efficiency, a core optimization
                # requiring manual whitelisting here.
                not is_classname_builtin(hint_clsname)
            # Then raise an exception.
            ):
                raise _BeartypeDecorBeartypistryException(
                    f'Beartypistry key "{hint_name}" not '
                    f'fully-qualified classname "{hint_clsname}" of '
                    f'type {repr(hint)}.'
                )
        # Else, this hint is *NOT* a class.
        #
        # If this hint is a tuple...
        elif isinstance(hint, tuple):
            # If this tuple is *NOT* PEP-noncompliant (e.g., due to containing
            # PEP-compliant type hints), raise an exception.
            die_unless_hint_nonpep(
                hint=hint,
                hint_label='Beartypistry value',

                #FIXME: Actually, we eventually want to permit this to enable
                #trivial resolution of forward references. For now, this is fine.
                is_str_valid=False,

                # Raise a decoration- rather than call-specific exception, as
                # this setter should *ONLY* be called at decoration time (e.g.,
                # by registration functions defined above).
                exception_cls=_BeartypeDecorBeartypistryException,
            )

            # If this tuple's name is *NOT* prefixed by a magic substring
            # uniquely identifying this hint as a tuple, raise an exception.
            #
            # Ideally, this block would strictly validate this name to be the
            # concatenation of this prefix followed by this tuple's hash.
            # Sadly, Python fails to cache tuple hashes (for largely spurious
            # reasons, like usual):
            #     https://bugs.python.org/issue9685
            #
            # Potentially introducing a performance bottleneck for mostly
            # redundant validation is a bad premise, given that we mostly
            # trust callers to call the higher-level
            # :func:`register_typistry_tuple` function instead, which already
            # guarantees this constraint to be the case.
            if not hint_name.startswith(_TYPISTRY_HINT_NAME_TUPLE_PREFIX):
                raise _BeartypeDecorBeartypistryException(
                    f'Beartypistry key "{hint_name}" not '
                    f'prefixed by "{_TYPISTRY_HINT_NAME_TUPLE_PREFIX}" for '
                    f'tuple {repr(hint)}.'
                )
        # Else, this hint is neither a class nor a tuple. In this case,
        # something has gone terribly awry. Pour out an exception.
        else:
            raise _BeartypeDecorBeartypistryException(
                f'Beartypistry key "{hint_name}" value {repr(hint)} invalid '
                f'(i.e., neither type nor tuple).'
            )

        # Cache this object under this name.
        super().__setitem__(hint_name, hint)


    def __missing__(self, hint_classname: str) -> type:
        '''
        Dunder method explicitly called by the superclass
        :meth:`dict.__getitem__` method implicitly called on caller attempts to
        access the passed missing key with ``[``- and ``]``-delimited syntax.

        This method treats this attempt to get this missing key as the
        intentional resolution of a forward reference whose fully-qualified
        classname is this key.

        Parameters
        ----------
        hint_classname : str
            **Name** (i.e., fully-qualified name of the user-defined class) of
            this hint to be resolved as a forward reference.

        Returns
        ----------
        type
            User-defined class whose fully-qualified name is this missing key.

        Raises
        ----------
        BeartypeCallHintForwardRefException
            If either:

            * This name is *not* a syntactically valid fully-qualified
              classname.
            * *No* module prefixed this name exists.
            * An importable module prefixed by this name exists *but* this
              module declares no attribute by this name.
            * The module attribute to which this name refers is *not* a class.
        '''

        # User-defined class dynamically imported from this name.
        hint_class = import_module_attr(
            module_attr_name=hint_classname,
            exception_label='Forward reference',
            exception_cls=BeartypeCallHintForwardRefException,
        )

        # If this hint is *NOT* a class, raise an exception.
        if not isinstance(hint_class, type):
            raise BeartypeCallHintForwardRefException(
                f'Forward reference "{hint_classname}" '
                f'value {repr(hint_class)} not class.'
            )
        # Else, this hint is a class.

        # Return this class. The superclass dict.__getitem__() dunder method
        # then implicitly maps the passed missing key to this class by
        # effectively assigning this name to this class: e.g.,
        #     self[hint_classname] = hint_class
        return hint_class

# ....................{ SINGLETONS                        }....................
bear_typistry = Beartypistry()
'''
**Beartypistry** (i.e., singleton dictionary mapping from the fully-qualified
classnames of all type hints annotating callables decorated by the
:func:`beartype.beartype` decorator to those types).**

See Also
----------
:class:`Beartypistry`
    Further details.
'''
