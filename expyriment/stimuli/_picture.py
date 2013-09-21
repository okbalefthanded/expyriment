#!/usr/bin/env python

"""
A picture stimulus.

This module contains a class implementing a picture stimulus.

"""

__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'
__version__ = ''
__revision__ = ''
__date__ = ''


import os

import pygame
import expyriment
import defaults
from _visual import Visual


class Picture(Visual):
    """A class implementing a general picture stimulus."""

    def __init__(self, filename, position=None):
        """Create a picture.

        Parameters
        ----------
        filename : str
            filename (incl. path) of the picture file
        position :(int,int), optional
            position of the stimulus

        """

        if position is None:
            position = defaults.picture_position
        Visual.__init__(self, position, log_comment=filename)
        self._filename = filename
        if not(os.path.isfile(self._filename)):
            if isinstance(self._filename, unicode):
                import sys
                ENCODING = sys.getfilesystemencoding()
                if ENCODING is None:
                    ENCODING = u"utf-8"
                filename = self._filename.encode(ENCODING)
            raise IOError("The picture file '{0}' does not exist".format(
                filename))

    _getter_exception_message = "Cannot set {0} if surface exists!"

    @property
    def filename(self):
        """Getter for filename."""

        return self._filename

    @filename.setter
    def filename(self, value):
        """Setter for filename."""

        if self.has_surface:
            raise AttributeError(Picture._getter_exception_message.format(
                "filename"))
        else:
            self._filename = value

    def _create_surface(self):
        """Create the surface of the stimulus."""

        if isinstance(self._filename, unicode):
            import sys
            filename = self._filename.encode(u"utf-8")
            ENCODING = sys.getfilesystemencoding()
            if ENCODING is None:
                ENCODING = u"utf-8"
            log_filename = self._filename.encode(ENCODING)
        else:
            filename = log_filename = self._filename
        surface = pygame.image.load(filename).convert_alpha()
        if self._logging:
            expyriment._active_exp._event_file_log("Picture,loaded,{0}"\
                                   .format(log_filename), 1)
        return surface


if __name__ == "__main__":
    from expyriment import __file__
    from expyriment import control
    control.set_develop_mode(True)
    defaults.event_logging = 0
    exp = control.initialize()
    directory = os.path.dirname(__file__)
    picture = Picture(os.path.join(directory, "expyriment_logo.png"))
    picture.present()
    exp.clock.wait(1000)