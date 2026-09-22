"""Sphinx extension to make sure directives have proper signatures.

This is tricky as directives are added as methods to the ``App``
object using the directive decorator, and the signature needs to be
obtained from the action class's ``__init__`` manually.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> None:  # pragma: nocoverage
    # all inline to avoid dependency on sphinx.ext.autodoc which
    # would trip up scanning
    from sphinx.ext.autodoc import MethodDocumenter, ModuleDocumenter

    class DirectiveDocumenter(MethodDocumenter):
        objtype = "morepath_directive"
        priority = MethodDocumenter.priority + 1
        member_order = 49

        @classmethod
        def can_document_member(
            cls: type[MethodDocumenter],
            member: Any,
            membername: str,
            isattr: bool,
            parent: Any,
        ) -> bool:
            return (
                inspect.isroutine(member)
                and not isinstance(parent, ModuleDocumenter)
                and hasattr(member, "action_factory")
            )

        def import_object(self, raiseerror: bool = False) -> bool:
            if not super().import_object(raiseerror):
                return False
            object = getattr(self.object, "action_factory", None)
            if object is None:
                return False
            self.object = object.__init__
            self.directivetype = "classmethod"
            return True

    def decide_to_skip(
        app: Sphinx, what: str, name: str, obj: object, skip: bool, options: object
    ) -> bool:
        if what != "class":
            return skip
        directive = getattr(obj, "action_factory", None)
        if directive is not None:
            return False
        return skip

    app.connect("autodoc-skip-member", decide_to_skip)
    app.add_autodocumenter(DirectiveDocumenter)
