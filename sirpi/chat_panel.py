"""FreeCAD Qt dock. Neural inference stays in the project's separate Python."""
from __future__ import annotations

from datetime import datetime
import html
import json
import os
from pathlib import Path
from uuid import uuid4

from PySide import QtCore, QtGui
try:
    from PySide import QtWidgets
except ImportError:
    QtWidgets = QtGui

from .chat import Conversation, EXAMPLES, RequestError

_PANEL = None


class ChatInput(QtWidgets.QPlainTextEdit):
    submitted = QtCore.Signal()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and not event.modifiers() & QtCore.Qt.ShiftModifier:
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChatPanel(QtWidgets.QDockWidget):
    def __init__(self, server, repo: Path, parent):
        super().__init__("Sirpi Chat", parent)
        self.setObjectName("SirpiChatDock")
        self.setMinimumWidth(340)
        self.server, self.repo = server, Path(repo)
        self.conversation = Conversation()
        self.plan = None
        self.process = None
        self.building_plan = None
        self.output_dir = None
        self.cancelled = False
        self._log = ""
        self._partial = ""
        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(root)
        title = QtWidgets.QLabel("<b>Describe a part. Review. Build.</b>")
        layout.addWidget(title)
        note = QtWidgets.QLabel("Local CPU · dimensions in mm\nPlates, squares, cylinders, rings and simple holes")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.history = QtWidgets.QTextBrowser()
        self.history.setOpenExternalLinks(False)
        self.history.setMinimumHeight(140)
        layout.addWidget(self.history, 1)
        self.examples = QtWidgets.QComboBox()
        self.examples.addItem("Choose an example…")
        self.examples.addItems(list(EXAMPLES))
        self.examples.setMinimumContentsLength(20)
        self.examples.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.examples.activated.connect(self.use_example)
        layout.addWidget(self.examples)
        self.input = ChatInput()
        self.input.setObjectName("SirpiChatInput")
        self.input.setPlaceholderText("Make a square at 2*2 mm\nEnter to review · Shift+Enter for a new line")
        self.input.setMaximumHeight(95)
        self.input.textChanged.connect(self.invalidate_plan)
        self.input.submitted.connect(self.submit)
        layout.addWidget(self.input)
        row = QtWidgets.QHBoxLayout()
        self.review = QtWidgets.QPushButton("Review request")
        self.review.clicked.connect(self.submit)
        row.addWidget(self.review)
        self.build = QtWidgets.QPushButton("Build part")
        self.build.setEnabled(False)
        self.build.clicked.connect(self.start_build)
        row.addWidget(self.build)
        self.stop = QtWidgets.QPushButton("Stop")
        self.stop.setEnabled(False)
        self.stop.clicked.connect(self.cancel)
        row.addWidget(self.stop)
        layout.addLayout(row)
        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.open_output = QtWidgets.QPushButton("Open result folder")
        self.open_output.setEnabled(False)
        self.open_output.clicked.connect(self.show_output)
        layout.addWidget(self.open_output)
        self.setWidget(root)
        self.timeout = QtCore.QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.timed_out)
        self.say("Sirpi", "Choose an example or ask for a plate, cylinder or ring. I will review the dimensions before building. This local assistant understands the example formats, not unrestricted conversation.")

    def say(self, who, message):
        self.history.append(f"<p><b>{html.escape(who)}</b><br>{html.escape(str(message)).replace(chr(10), '<br>')}</p>")
        self.history.verticalScrollBar().setValue(self.history.verticalScrollBar().maximum())

    def use_example(self, index):
        if index > 0:
            self.input.setPlainText(EXAMPLES[index - 1])

    def invalidate_plan(self):
        self.plan = None
        self.build.setEnabled(False)

    def submit(self):
        if self.process is not None:
            return
        text = self.input.toPlainText().strip()
        self.invalidate_plan()
        if not text:
            return
        self.say("You", text)
        self.input.clear()
        try:
            self.plan = self.conversation.submit(text)
        except RequestError as exc:
            self.say("Sirpi", str(exc))
            self.status.setText("More information needed — see the reply above.")
            self.input.setFocus()
            return
        self.say("Review", self.plan.summary)
        self.status.setText("Review the dimensions, then click Build part.")
        self.build.setEnabled(True)

    def busy(self, on):
        self.input.setEnabled(not on)
        self.review.setEnabled(not on)
        self.examples.setEnabled(not on)
        self.build.setEnabled(False)
        self.stop.setEnabled(on)

    def start_build(self):
        if self.plan is None or self.process is not None:
            return
        if self.server.conn is not None:
            self.say("Sirpi", "Another client is connected. Wait for its demo to finish, then try Build part again.")
            return
        python = Path(os.environ.get("SIRPI_PYTHON", str(self.repo / ".venv" / "Scripts" / "python.exe")))
        if not python.is_file():
            self.say("Sirpi", "Python environment not found. Complete the README installation steps, then try again.")
            return
        try:
            out = self.repo / "runs" / "chat" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
            out.mkdir(parents=True)
            goals = out / "goal.json"
            goals.write_text(json.dumps({"chat": self.plan.goal.to_json()}, indent=2), encoding="utf-8")
            # The legacy rollout resets/closes its owned document. Release that
            # ownership so a new chat build cannot discard previous user edits.
            session = self.server.worker.session
            if session.doc is not None:
                import FreeCAD as App
                import FreeCADGui as Gui
                try:
                    name = session.doc.Name
                except ReferenceError:  # the user may have closed the last result
                    name = None
                if name in App.listDocuments():
                    gui_doc = Gui.getDocument(name)
                    if gui_doc.getInEdit() is not None:
                        gui_doc.resetEdit()
                session.doc = None
            self.output_dir = out
            self.building_plan = self.plan
            self.open_output.setEnabled(True)
            self.cancelled = False
            self._log = self._partial = ""
            process = QtCore.QProcess(self)
            self.process = process
            process.setWorkingDirectory(str(self.repo))
            process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            process.readyReadStandardOutput.connect(self.read_output)
            process.finished.connect(self.finished)
            process.errorOccurred.connect(self.process_error)
            self.busy(True)
            self.status.setText("Loading the model on CPU…")
            self.say("Sirpi", "Building in a new document. Please wait before editing the model.")
            self.timeout.start(180000)
            process.start(str(python), ["-u", "-m", "sirpi", "demo", "--goals", str(goals),
                                      "--name", "chat", "--port", str(self.server.sock.getsockname()[1]),
                                      "--delay", "0.1", "--out", str(out)])
        except Exception as exc:
            self.timeout.stop()
            self.process = None
            self.busy(False)
            self.say("Sirpi", f"Could not start: {exc}")

    def read_output(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._log += text
        self._partial += text
        lines = self._partial.split("\n")
        self._partial = lines.pop()
        for line in lines:
            if line.strip() and line.lstrip()[:1].isdigit():
                self.status.setText("Building · " + line.strip())

    def process_error(self, error):
        if self.process is not None and error == QtCore.QProcess.FailedToStart:
            self._log += self.process.errorString()
            self.finished(-1, None)

    def finished(self, exit_code, exit_status):
        if self.process is None:
            return
        self.timeout.stop()
        self.read_output()
        process, self.process = self.process, None
        process.deleteLater()
        self.busy(False)
        self.plan = None
        try:
            (self.output_dir / "build.log").write_text(self._log, encoding="utf-8")
            result_path = self.output_dir / "result.json"
            result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
            if self.cancelled:
                message = "Build stopped. Any partial model remains open; it has not been validated."
            elif exit_code == 0 and result.get("success"):
                self.conversation.remember_success(self.building_plan)
                message = f"Part complete. Target overlap: {result['iou']:.1%}. Saved Sirpi.FCStd, Sirpi.png and result.json."
            else:
                message = "Build did not pass validation. Check build.log and any result.json in the result folder. Try a simpler example."
            self.status.setText(message)
            self.say("Sirpi", message + "\n" + str(self.output_dir))
        except Exception as exc:
            self.status.setText("Could not read or save the build report.")
            self.say("Sirpi", str(exc))

    def cancel(self):
        if self.process is not None:
            self.cancelled = True
            self.status.setText("Stopping…")
            self.process.kill()

    def timed_out(self):
        self.say("Sirpi", "Build exceeded three minutes and is being stopped.")
        self.cancel()

    def show_output(self):
        if self.output_dir:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.output_dir)))

    def closeEvent(self, event):
        if self.process is not None:
            self.say("Sirpi", "Stop the current build before closing the chat panel.")
            event.ignore()
        else:
            super().closeEvent(event)


def show(server, repo):
    global _PANEL
    import FreeCADGui as Gui
    if _PANEL is None:
        main = Gui.getMainWindow()
        _PANEL = ChatPanel(server, Path(repo), main)
        main.addDockWidget(QtCore.Qt.RightDockWidgetArea, _PANEL)
    _PANEL.show()
    _PANEL.raise_()
    return _PANEL
