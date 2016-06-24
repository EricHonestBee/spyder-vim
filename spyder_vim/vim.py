# -*- coding: utf-8 -*-
u"""
:author: Joseph Martinot-Lagarde

Created on Sat Jan 19 14:57:57 2013
"""
from __future__ import (
    print_function, unicode_literals, absolute_import, division)

import re

from qtpy.QtWidgets import (QWidget, QLineEdit, QHBoxLayout, QTextEdit, QLabel,
                            QSizePolicy)
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import Qt

# Local imports
# TODO: activate translation
#from spyderlib.baseconfig import get_translation
#_ = get_translation("p_autopep8", dirname="spyderplugins.autopep8")
_ = lambda txt: txt
from spyderlib.utils.qthelpers import create_action
from spyderlib.config.gui import fixed_shortcut
try:
    from spyderlib.py3compat import to_text_string
except ImportError:
    # Python 2
    to_text_string = unicode

from spyderlib.plugins import SpyderPluginMixin


VIM_PREFIX = "cdfFmrtTyzZ@'`\"<>"
VIM_COMMAND_PREFIX = ":!/?"
RE_VIM_PREFIX = re.compile(r"^(\d*)([{0}].|[^{0}123456789])(.*)$".format(VIM_PREFIX))
SYMBOLS_REPLACEMENT = {
    "!": "EXCLAMATION",
    "?": "QUESTION",
    "<": "LESS",
    ">": "GREATER",
    "|": "PIPE",
    " ": "SPACE",
    "@": "AT",
    "$": "DOLLAR",
    "0": "ZERO",
}


# %% Vim shortcuts
class VimKeys(object):
    def __init__(self, widget):
        self._widget = widget

    def __call__(self, key, repeat):
        if key.startswith("_"):
            return
        for symbol, text in SYMBOLS_REPLACEMENT.items():
            key = key.replace(symbol, text)
        try:
            method = self.__getattribute__(key)
        except AttributeError:
            print("unknown key", key)
        else:
            method(repeat)

    def _move_cursor(self, movement, repeat=1):
        editor = self._widget.editor()
        cursor = editor.textCursor()
        cursor.movePosition(movement, n=repeat)
        editor.setTextCursor(cursor)

    # %% Movement
    def h(self, repeat=1):
        # TODO: stop at start of line
        self._move_cursor(QTextCursor.Left, repeat)

    def j(self, repeat=1):
        self._move_cursor(QTextCursor.Down, repeat)

    def k(self, repeat=1):
        self._move_cursor(QTextCursor.Up, repeat)

    def l(self, repeat=1):
        # TODO: stop at end of line
        self._move_cursor(QTextCursor.Right, repeat)

    def w(self, repeat=1):
        self._move_cursor(QTextCursor.NextWord, repeat)

    def SPACE(self, repeat=1):
        self._move_cursor(QTextCursor.Right, repeat)

    def DOLLAR(self, repeat=1):
        self._move_cursor(QTextCursor.EndOfLine)

    def ZERO(self, repeat=1):
        self._move_cursor(QTextCursor.StartOfLine)

    # %% Insertion
    def i(self, repeat):
        self._widget.editor().setFocus()

    def a(self, repeat):
        self.l()
        self._widget.editor().setFocus()

    def A(self, repeat):
        self._move_cursor(QTextCursor.EndOfLine)
        self._widget.editor().setFocus()

    def o(self, repeat):
        editor = self._widget.editor()
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine)
        cursor.insertText("\n")
        editor.setTextCursor(cursor)
        editor.setFocus()

    def O(self, repeat):
        editor = self._widget.editor()
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.insertText("\n")
        cursor.movePosition(QTextCursor.Up)
        editor.setTextCursor(cursor)
        editor.setFocus()

    # %% Editing
    def u(self, repeat):
        for count in range(repeat):
            self._widget.editor().undo()

    # %% Deletions
    def dd(self, repeat):
        editor = self._widget.editor()
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, repeat)
        editor.setTextCursor(cursor)
        editor.cut()

    def D(self, repeat):
        editor = self._widget.editor()
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor,
                            repeat - 1)
        editor.setTextCursor(cursor)
        editor.cut()

    def dw(self, repeat):
        editor = self._widget.editor()
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor,
                            repeat)
        editor.setTextCursor(cursor)
        editor.cut()

    # %% Files
    def ZZ(self, repeat):
        self._widget.main.editor.save_action.trigger()
        self._widget.main.editor.close_action.trigger()
        self._widget.commandline.setFocus()


# %% Vim commands
class VimCommands(object):
    def __init__(self, widget):
        self._widget = widget

    def __call__(self, cmd):
        if not cmd or cmd.startswith("_"):
            return
        cmd = cmd.split(None, 1)
        args = cmd[1] if len(cmd) > 1 else ""
        cmd = cmd[0]

        if cmd.isdigit():
            self.NUMBER(cmd)
        else:
            try:
                method = self.__getattribute__(cmd)
            except AttributeError:
                print("unknown command", cmd)
            else:
                method(args)

    # %% Files
    def w(self, args=""):
        self._widget.main.editor.save_action.trigger()
        self._widget.commandline.setFocus()

    def q(self, args=""):
        self._widget.main.editor.close_action.trigger()
        self._widget.commandline.setFocus()

    def wq(self, args=""):
        self.w(args)
        self.q()

    def n(self, args=""):
        self._widget.main.editor.new_action.trigger()
        self._widget.commandline.setFocus()

    def e(self, args=""):
        if not args:  # Revert without asking
            editor = self._widget.main.editor
            editorstack = editor.get_current_editorstack()
            editorstack.reload(editorstack.get_stack_index())
        elif args == ".":
            self._widget.main.editor.open_action.trigger()
        else:
            print("not implemented")

        self._widget.commandline.setFocus()

    def NUMBER(self, args=""):
        editor = self._widget.editor()
        editor.go_to_line(int(args))


# %%
class VimLineEdit(QLineEdit):

    def focusInEvent(self, event):
        QWidget.focusInEvent(self, event)
        selection = QTextEdit.ExtraSelection()
        back = Qt.white  # selection.format.background().color()
        fore = Qt.black  # selection.format.foreground().color()
        selection.format.setBackground(fore)
        selection.format.setForeground(back)
        selection.cursor = self.parent().editor().textCursor()
#        selection.cursor.setPosition(pos1)
#        self.found_results.append(selection.cursor.blockNumber())
        selection.cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        self.parent().editor().set_extra_selections('vim_cursor', [selection])
        self.parent().editor().update_extra_selections()

    def focusOutEvent(self, event):
        self.parent().editor().clear_extra_selections('vim_cursor')


class VimWidget(QWidget):
    """
    Vim widget
    """
    def __init__(self, editor_widget):
        self.editor_widget = editor_widget
        QLineEdit.__init__(self, editor_widget)

        # Build widget
        self.commandline = VimLineEdit(self)
        self.commandline.textChanged.connect(self.on_text_changed)
        self.commandline.returnPressed.connect(self.on_return)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Vim:"))
        hlayout.addWidget(self.commandline)
        hlayout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(hlayout)

        # Initialize available commands
        self.vim_keys = VimKeys(self)
        self.vim_commands = VimCommands(self)

    def on_text_changed(self, text):
        if not text or text[0] in VIM_COMMAND_PREFIX:
            return
        match = RE_VIM_PREFIX.match(text)
        print(text)
        if not match:
            return
        repeat, key, leftover = match.groups()
        repeat = int(repeat) if repeat else 1
        if not repeat:
            return
        self.vim_keys(key, repeat)
        self.commandline.setText(leftover)

    def on_return(self):
        text = self.commandline.text()
        if not text:
            return
        cmd_type = text[0]
        print(text)
        if cmd_type == ":":  # Vim command
            self.vim_commands(text[1:])
        elif cmd_type == "!":  # Shell command
            pass
        elif cmd_type == "/":  # Forward search
            pass
        elif cmd_type == "?":  # Reverse search
            pass
        self.commandline.clear()

    def editor(self):
        # Retrieve text of current opened file
        editorstack = self.editor_widget.get_current_editorstack()
        index = editorstack.get_stack_index()
        finfo = editorstack.data[index]
        return finfo.editor


# %%
class Vim(VimWidget, SpyderPluginMixin):  # pylint: disable=R0904

    """Python source code automatic formatting based on autopep8.

    QObject is needed to register the action.
    """
    CONF_SECTION = "Vim"
    CONFIGWIDGET_CLASS = None

    def __init__(self, parent):
        VimWidget.__init__(self, editor_widget=parent.editor)
        SpyderPluginMixin.__init__(self, parent)
        self.initialize_plugin()

    # %% SpyderPlugin API
    def get_plugin_title(self):
        """Return widget title"""
        return _("Vim")

    def get_plugin_icon(self):
        """Return widget icon"""
        return  # self.get_icon('vim.png')

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.editor_widget.layout().addWidget(self)
        fixed_shortcut("Esc", self.editor_widget.editorsplitter,
                       self.commandline.setFocus)

    def apply_plugin_settings(self, options):
        """Needs to be redefined."""
        pass

    def get_plugin_actions(self):
        return []

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.commandline

    def refresh_plugin(self):
        """Refresh widget"""
        pass

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
