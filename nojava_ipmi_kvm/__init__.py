# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals

from .kvm import view_kvm_console
from ._version import __version__, __version_info__  # noqa: F401  # pylint: disable=unused-import

__author__ = "Ingo Heimbach"
__email__ = "i.heimbach@fz-juelich.de"
__copyright__ = "Copyright © 2018 Forschungszentrum Jülich GmbH. All rights reserved."
__license__ = "MIT"


__all__ = ["view_kvm_console"]
