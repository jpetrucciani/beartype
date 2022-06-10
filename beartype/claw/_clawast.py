#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright (c) 2014-2022 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype all-at-once low-level abstract syntax tree (AST) transformation.**

This private submodule defines the low-level abstract syntax tree (AST)
transformation automatically decorating well-typed third-party packages and
modules with runtime type-checking dynamically generated by the
:func:`beartype.beartype` decorator.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                               }....................
#FIXME: Once @beartype supports class decoration, additionally define a new
#BeartypeNodeTransformer.visit_ClassDef() method modelled after the equivelent
#TypeguardTransformer.visit_ClassDef() method residing at:
#    https://github.com/agronholm/typeguard/blob/master/src/typeguard/importhook.py

# ....................{ IMPORTS                            }....................
from ast import (
    AST,
    Expr,
    FunctionDef,
    ImportFrom,
    Load,
    Module,
    Name,
    NodeTransformer,
    Str,
    alias,
)
from beartype._util.py.utilpyversion import IS_PYTHON_AT_LEAST_3_8

# See the "beartype.cave" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ CLASSES                            }....................
#FIXME: Implement us up, please.
#FIXME: Docstring us up, please.
#FIXME: Unit test us up, please.
class BeartypeNodeTransformer(NodeTransformer):
    '''
    **Beartype abstract syntax tree (AST) node transformer** (i.e., visitor
    pattern recursively transforming the AST tree passed to the :meth:`visit`
    method by decorating all typed callables and classes by the
    :func:`beartype.beartype` decorator).

    See Also
    ----------
    * The `comparable "typeguard.importhook" submodule <typeguard import
      hook_>`__ implemented by the incomparable `@agronholm (Alex Grönholm)
      <agronholm_>`__.

    .. _agronholm:
       https://github.com/agronholm
    .. _typeguard import hook:
       https://github.com/agronholm/typeguard/blob/master/src/typeguard/importhook.py
    '''

    # ..................{ VISITORS                           }..................
    def visit_Module(self, node: Module) -> Module:
        '''
        Add a new abstract syntax tree (AST) child node to the passed AST module
        parent node encapsulating the module currently being loaded by the
        :class:`beartype.claw._clawloader.BeartypeSourceFileLoader` object,
        importing our private
        :func:`beartype._decor.decorcore.beartype_object_safe` decorator for
        subsequent use by the other visitor methods defined by this class.

        Parameters
        ----------
        node : Module
            AST module parent node to be transformed.

        Returns
        ----------
        Module
            That same AST module parent node.
        '''

        # 0-based index of the first safe position of the list of all AST child
        # nodes of this AST module parent node to insert an import statement
        # importing our beartype decorator, initialized to the erroneous index
        # "-1" to enable detection of empty modules (i.e., modules whose AST
        # module nodes containing *NO* child nodes) below.
        import_beartype_index = -1

        # AST child node of this AST module parent node immediately preceding
        # the AST import child node to be added below, defaulting to this AST
        # module parent node to ensure that the _copy_node_code_metadata()
        # function below *ALWAYS* copies from a valid AST node for sanity.
        module_child: AST = node

        # Efficiently find this index. Since, this iteration is guaranteed to
        # exhibit worst-case O(1) time complexity despite superficially
        # appearing to perform a linear search of all n child nodes of this
        # module parent node and thus exhibit worst-case O(n) time complexity.
        #
        # For the 0-based index and value of each direct AST child node of this
        # AST module parent node...
        for import_beartype_index, module_child in enumerate(node.body):
            # If this child node signifies either...
            if (
                # A module docstring...
                #
                # If that module defines a docstring, that docstring *MUST* be
                # the first expression of that module. That docstring *MUST* be
                # explicitly found and iterated past to ensure that the import
                # statement added below appears *AFTER* rather than *BEFORE* any
                # docstring. (The latter would destroy the semantics of that
                # docstring by reducing that docstring to an ignorable string.)
                (
                    isinstance(module_child, Expr) and
                    isinstance(module_child.value, Str)
                ) or
                # A future import (i.e., import of the form
                # "from __future__ ...") *OR*...
                #
                # If that module performs one or more future imports, these
                # imports *MUST* necessarily be the first non-docstring
                # statement of that module and thus appear *BEFORE* all import
                # statements that are actually imports -- including the import
                # statement added below.
                (
                    isinstance(module_child, ImportFrom) and
                    module_child.module == '__future__'
                )
            ):
                # Then continue past this child node to the next child node.
                continue

        # If the 0-based index of the first safe position of the list of all AST
        # child nodes of this AST module parent node to insert an import
        # statement importing our beartype decorator is *NOT* the erroneous
        # index to which this index was initialized above, this module contains
        # one or more child nodes and is thus non-empty. In this case...
        if import_beartype_index != -1:
            # AST import child node importing our private
            # beartype._decor.decorcore.beartype_object_safe() decorator for
            # subsequent use by the other visitor methods defined by this class.
            import_beartype = ImportFrom(
                module='beartype._decor.decorcore',
                names=[alias('beartype_object_safe')],
            )

            # Copy all source code metadata from the AST child node of this AST
            # module parent node immediately preceding this AST import child
            # node onto this AST import child node.
            _copy_node_code_metadata(
                node_src=node, node_trg=import_beartype)

            # Insert this AST import child node at this safe position of the
            # list of all AST child nodes of this AST module parent node.
            node.body.insert(import_beartype_index, import_beartype)
        # Else, this module is empty. In this case, silently reduce to a noop.
        # Since this edge case is *EXTREMELY* uncommon, avoid optimizing for
        # this edge case (here or elsewhere).

        # Recursively transform *ALL* AST child nodes of this AST module node.
        self.generic_visit(node)

        # Return this AST module node as is.
        return node


    def visit_FunctionDef(self, node: FunctionDef) -> FunctionDef:
        '''
        Add a new abstract syntax tree (AST) child node to the passed AST
        callable parent node, decorating that callable by our private
        :func:`beartype._decor.decorcore.beartype_object_safe` decorator if and
        only if that callable is **typed** (i.e., annotated by a return type
        hint and/or one or more parameter type hints).

        Parameters
        ----------
        node : FunctionDef
            AST callable parent node to be transformed.

        Returns
        ----------
        FunctionDef
            That same AST callable parent node.
        '''

        # True only if that callable is annotated by a return type hint,
        # trivially decided in O(1) time.
        is_return_typed = bool(node.returns)

        # True only if that callable is annotated by one or more parameter type
        # hints, non-trivially decided in O(n) time for n the number of
        # parameters accepted by that callable.
        is_args_typed = False

        # If that callable is *NOT* annotated by a return type hint, fallback to
        # deciding whether that callable is annotated by one or more parameter
        # type hints. Since doing is considerably more computationally
        # expensive, do so *ONLY* as needed.
        if not is_return_typed:
            for arg in node.args.args:
                if arg.annotation:
                    is_args_typed = True
                    break
        # Else, that callable is annotated by a return type hint. In this case,
        # do *NOT* spend useless time deciding whether that callable is
        # annotated by one or more parameter type hints.

        # If that callable is typed (i.e., annotated by a return type hint
        # and/or one or more parameter type hints)...
        #
        # Note that the former is intentionally tested *BEFORE* the latter, as
        # the detecting former is O(1) time complexity and thus trivial.
        if is_return_typed or is_args_typed:
            # AST decoration child node decorating that callable by our
            # beartype._decor.decorcore.beartype_object_safe() decorator. Note
            # that this syntax derives from the example for the ast.arg() class:
            #     https://docs.python.org/3/library/ast.html#ast.arg
            decorate_callable = Name(id='beartype_object_safe', ctx=Load())

            # Copy all source code metadata from this AST callable parent node
            # onto this AST decoration child node.
            _copy_node_code_metadata(node_src=node, node_trg=decorate_callable)

            # Append this AST decoration child node to the end of the list of
            # all AST decoration child nodes for this AST callable parent node.
            # Since this list is "stored outermost first (i.e. the first in the
            # list will be applied last)", appending guarantees that our
            # decorator will be applied first (i.e., *BEFORE* all subsequent
            # decorators). This is *NOT* simply obsequious greed. The @beartype
            # decorator generally requires that it precede other decorators that
            # obfuscate the identity of the original callable, including:
            # * The builtin @property decorator.
            # * The builtin @classmethod decorator.
            # * The builtin @staticmethod decorator.
            node.decorator_list.append(decorate_callable)
        # Else, that callable is untyped. In this case, avoid needlessly
        # decorating that callable by @beartype for efficiency.

        # Recursively transform *ALL* AST child nodes of this AST callable node.
        self.generic_visit(node)

        # Return this AST callable node as is.
        return node

# ....................{ PRIVATE ~ copiers                  }....................
#FIXME: Call us up above, please.
def _copy_node_code_metadata(node_src: AST, node_trg: AST) -> None:
    '''
    Copy all **source code metadata** (i.e., beginning and ending line and
    column numbers) from the passed source abstract syntax tree (AST) node onto
    the passed target AST node.

    This function is an efficient alternative to the extremely inefficient
    (albeit still useful) :func:`ast.fix_missing_locations` function. The
    tradeoffs are as follows:

    * :func:`ast.fix_missing_locations` is ``O(n)`` time complexity for ``n``
      the number of AST nodes across the entire AST tree, but requires only a
      single trivial call and is thus considerably more "plug-and-play" than
      this function.
    * This function is ``O(1)`` time complexity irrespective of the size of the
      AST tree, but requires one still mostly trivial call for each synthetic
      AST node inserted into the AST tree by the
      :class:`BeartypeNodeTransformer` above.

    Parameters
    ----------
    node_src: AST
        Source AST node to copy source code metadata from.
    node_trg: AST
        Target AST node to copy source code metadata onto.

    See Also
    ----------
    :func:`ast.copy_location`
        Less efficient analogue of this function running in ``O(k)`` time
        complexity for ``k`` the number of types of source code metadata.
        Typically, ``k == 4``.
    '''
    assert isinstance(node_src, AST), f'{repr(node_src)} not AST node.'
    assert isinstance(node_trg, AST), f'{repr(node_trg)} not AST node.'

    # Copy all source code metadata from this source to target AST node.
    node_trg.lineno     = node_src.lineno
    node_trg.col_offset = node_src.col_offset

    # If the active Python interpreter targets Python >= 3.8, then additionally
    # copy all source code metadata exposed by Python >= 3.8.
    if IS_PYTHON_AT_LEAST_3_8:
        node_trg.end_lineno     = node_src.end_lineno  # type: ignore[attr-defined]
        node_trg.end_col_offset = node_src.end_col_offset  # type: ignore[attr-defined]